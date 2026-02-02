__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from unittest.mock import MagicMock
sys.modules['posthog'] = MagicMock()

from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
import re
from datetime import datetime

# Import smart hybrid search (if available)
try:
    from smart_hybrid_search import get_smart_searcher, is_dvsum_related
    SMART_SEARCH_AVAILABLE = True
except ImportError:
    print("⚠️ smart_hybrid_search not available")
    SMART_SEARCH_AVAILABLE = False
    def is_dvsum_related(text):
        return True

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')

# Global variables
vector_store = None
standalone_llm = None
smart_searcher = None

# Severity Configurations (S1, S2, S3 - DVSum Standard)
SEVERITY_CONFIGS = {
    "S1": {
        "name": "Critical Incident",
        "sla_response": "Immediate",
        "sla_resolution": "4 hours",
        "priority": "Critical",
        "description": "System down, complete crash, production outage, data loss, security breach"
    },
    "S2": {
        "name": "Important Incident", 
        "sla_response": "Within 30 minutes",
        "sla_resolution": "8 hours",
        "priority": "High",
        "description": "Major functionality broken, connectivity issues, jobs stuck, access denied"
    },
    "S3": {
        "name": "Regular Problem",
        "sla_response": "Within 2 hours",
        "sla_resolution": "2 business days",
        "priority": "Normal",
        "description": "Questions, configuration, feature requests, minor issues"
    }
}

# Ticket Type Definitions
TICKET_TYPES = {
    "BUG": "A defect or error in the system causing unexpected behavior",
    "ENHANCEMENT": "Request for new features or improvements to existing functionality",
    "QUESTION": "Inquiry about how to use features or clarification needed",
    "REQUEST": "Configuration changes, access requests, or general service requests"
}

def get_embeddings():
    """Get embeddings for vector store"""
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        return embeddings
    except Exception as e:
        print(f"❌ Embeddings failed: {e}")
        return None

def initialize_llm():
    """Initialize Groq LLM"""
    global standalone_llm
    
    if not GROQ_API_KEY:
        print("⚠️ No GROQ_API_KEY found in .env file")
        return None
    
    try:
        standalone_llm = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=2048
        )
        print("✅ Groq LLM initialized")
        return standalone_llm
    except Exception as e:
        print(f"❌ Error initializing Groq: {e}")
        return None

def initialize_qa_system():
    """Initialize search systems"""
    global vector_store, smart_searcher
    
    llm = initialize_llm()
    if not llm:
        print("⚠️ LLM not initialized - bot will have limited functionality")
        return
    
    print("\n" + "="*80)
    print("🚀 Initializing DVSum AI Support Agent")
    print("="*80)
    
    # Method 1: Smart Hybrid Search
    if SMART_SEARCH_AVAILABLE:
        print("\n📊 Loading Keyword Search...")
        try:
            smart_searcher = get_smart_searcher()
            if smart_searcher and hasattr(smart_searcher, 'articles'):
                print(f"✅ Loaded {len(smart_searcher.articles)} articles")
            else:
                print("⚠️ No articles found")
        except Exception as e:
            print(f"⚠️ Keyword search failed: {e}")
    
    # Method 2: Vector Search
    print("\n🧠 Loading Vector Search...")
    persist_directory = "./chroma_db"
    
    if os.path.exists(persist_directory):
        try:
            embeddings = get_embeddings()
            if embeddings:
                vector_store = Chroma(
                    persist_directory=persist_directory,
                    embedding_function=embeddings
                )
                test_results = vector_store.similarity_search("test", k=1)
                if test_results:
                    print(f"✅ Vector database loaded")
                else:
                    print("⚠️ Vector database is empty")
                    vector_store = None
        except Exception as e:
            print(f"⚠️ Vector search failed: {e}")
            vector_store = None
    else:
        print("⚠️ No vector database found at ./chroma_db")
    
    print("="*80 + "\n")

def check_dvsum_relevance(ticket_text):
    """Check if ticket is DVSum product-related"""
    redirect_keywords = {
        "training": ["training", "course", "certification", "learning", "workshop"],
        "it_helpdesk": ["laptop", "hardware", "vpn", "network access", "wifi", "password reset", "account creation"],
        "infosec": ["security policy", "security incident", "phishing", "vulnerability", "infosec"],
        "hr_us": ["benefits", "pto", "vacation", "leave", "onboarding", "offboarding", "401k"],
        "payroll_us": ["paycheck", "salary", "tax", "w2", "payment", "payroll"],
        "hr_india": ["india office", "bangalore office", "india hr", "indian employee"]
    }
    
    redirect_emails = {
        "training": "training@dvsum.com",
        "it_helpdesk": "helpdesk@dvsum.com",
        "infosec": "infosec@dvsum.com",
        "hr_us": "hr@dvsum.com",
        "payroll_us": "finance@dvsum.com",
        "hr_india": "hr-india@dvsum.com"
    }
    
    ticket_lower = ticket_text.lower()
    
    for category, keywords in redirect_keywords.items():
        if any(keyword in ticket_lower for keyword in keywords):
            return False, category, redirect_emails[category]
    
    return True, None, None

def analyze_severity_and_type(ticket_text):
    """Analyze ticket severity (S1/S2/S3) and type (Bug/Enhancement/Question/Request)"""
    if not standalone_llm:
        return "S3", "QUESTION", "Default classification - LLM not available"
    
    analysis_prompt = f"""You are a DVSum support ticket classifier. Analyze this ticket and classify it.

TICKET:
{ticket_text}

SEVERITY LEVELS (DVSum Standard):

S1 - CRITICAL INCIDENT:
Examples: "CADDI is down", "application not accessible", "SAWS error", "production outage", 
"system crash", "data loss", "bots not working", "complete system failure"
Impact: Multiple users affected, production blocked, business stopped

S2 - IMPORTANT INCIDENT:
Examples: "data source not working", "jobs stuck", "cannot login", "access denied", 
"rules not running", "connectivity issue", "performance degraded"
Impact: Major functionality broken, workflow impacted, workaround may exist

S3 - REGULAR PROBLEM:
Examples: "how to configure", "question about feature", "documentation request", 
"feature request", "minor bug with workaround", "general inquiry"
Impact: Minimal interruption, normal operation continues

TICKET TYPES:
BUG - System error, defect, broken functionality, unexpected behavior
ENHANCEMENT - New feature request, improvement suggestion, capability addition
QUESTION - How-to query, clarification, usage guidance, documentation request
REQUEST - Configuration change, access request, setup assistance, administrative task

CLASSIFICATION RULES:
1. Keywords "down", "not accessible", "error", "crash" → Usually S1 or S2
2. Keywords "stuck", "not working", "access denied" → Usually S2
3. Keywords "how to", "question", "configure", "request" → Usually S3
4. If uncertain between severities, choose the HIGHER severity for safety
5. Type BUG only if something is actually broken/erroring

Respond EXACTLY in this format (no extra text):
SEVERITY: S1
TYPE: BUG
REASONING: CADDI application is completely down affecting production users"""

    try:
        response = standalone_llm.invoke(analysis_prompt)
        analysis = response.content.strip()
        
        # Parse response with better regex
        severity_match = re.search(r'SEVERITY:\s*(S[123])', analysis, re.IGNORECASE)
        type_match = re.search(r'TYPE:\s*(BUG|ENHANCEMENT|QUESTION|REQUEST)', analysis, re.IGNORECASE)
        reasoning_match = re.search(r'REASONING:\s*(.+?)(?:\n|$)', analysis, re.DOTALL)
        
        severity = severity_match.group(1).upper() if severity_match else "S3"
        ticket_type = type_match.group(1).upper() if type_match else "QUESTION"
        reasoning = reasoning_match.group(1).strip() if reasoning_match else "Standard classification"
        
        # Validation: Ensure valid values
        if severity not in ["S1", "S2", "S3"]:
            severity = "S3"
        if ticket_type not in ["BUG", "ENHANCEMENT", "QUESTION", "REQUEST"]:
            ticket_type = "QUESTION"
        
        print(f"✅ Classification: {severity} - {ticket_type}")
        return severity, ticket_type, reasoning
    
    except Exception as e:
        print(f"⚠️ Severity analysis failed: {e}")
        return "S3", "QUESTION", "Default classification due to error"

def explain_in_simple_english(ticket_text):
    """Explain what the customer is requesting in factual, clear terms for the support agent"""
    if not standalone_llm:
        return "The customer has submitted a support request regarding DVSum product functionality."
    
    explanation_prompt = f"""You are analyzing a support ticket for a DVSum support agent.

TICKET:
{ticket_text}

Task: Explain IN FACTUAL TERMS what the customer is requesting or reporting. This explanation is for the SUPPORT AGENT, not the customer.

Requirements:
- Be factual and objective - state WHAT they're asking for, not how they might be feeling
- Use clear, technical language appropriate for support agents
- Extract the key components: What system/product? What action? What's the goal?
- Keep it to 2-3 sentences maximum
- Do NOT add empathetic language or assumptions about feelings
- Focus on: WHAT is being requested, WHICH system, and WHAT is the desired outcome

Examples:
BAD: "I understand you're frustrated that your account isn't working..."
GOOD: "The customer is requesting decommissioning of a TBC account on the DQ Legacy system."

BAD: "It must be difficult to have this issue..."
GOOD: "The customer reports that CADDI application is not accessible, blocking their team from generating reports."

BAD: "I can imagine how this is causing problems..."
GOOD: "The customer is asking how to configure data source connections for their new integration project."

Your factual explanation (2-3 sentences):"""

    try:
        response = standalone_llm.invoke(explanation_prompt)
        explanation = response.content.strip()
        
        # Remove any quotes that the LLM might add
        explanation = explanation.strip('"\'')
        
        # Remove common empathetic phrases if they somehow got through
        empathetic_phrases = [
            "I understand", "I can imagine", "It must be", "I know",
            "must be frustrating", "must be difficult", "I appreciate",
            "Thank you for", "I'm sorry"
        ]
        
        for phrase in empathetic_phrases:
            if phrase.lower() in explanation.lower():
                # If empathetic language detected, regenerate with stricter prompt
                explanation = explanation.split('.')[0] + "."  # Take first sentence only
                break
        
        print(f"✅ Generated explanation")
        return explanation
    except Exception as e:
        print(f"⚠️ Explanation generation failed: {e}")
        return "The customer has submitted a support request regarding DVSum product functionality."

def generate_acknowledgment(severity, ticket_type, explanation):
    """Generate formal acknowledgment based on DVSum standards"""
    severity_config = SEVERITY_CONFIGS[severity]
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    ack = f"""
{'='*80}
🎫 TICKET ACKNOWLEDGMENT
{'='*80}

**ISSUE SUMMARY:**
{explanation}

**TICKET CLASSIFICATION:**
• Severity: {severity} - {severity_config['name']}
• Type: {ticket_type} - {TICKET_TYPES[ticket_type]}
• Priority: {severity_config['priority']}

**SERVICE LEVEL AGREEMENT (SLA):**
• Response Time: {severity_config['sla_response']}
• Resolution Target: {severity_config['sla_resolution']}

"""

    if severity == "S1":
        ack += """**🔥 IMMEDIATE ACTIONS BEING TAKEN:**
✓ Escalated to Product Engineering Team for immediate investigation
✓ Setting up dedicated bridge call for real-time collaboration
✓ This is being handled as our TOP PRIORITY

**NEXT STEPS:**
• You will receive bridge call details shortly
• Please join the call so we can resolve this as quickly as possible
• A senior engineer will be assigned immediately

We understand the critical nature of this issue and are committed to resolving it urgently.
"""
    
    elif severity == "S2":
        ack += """**⚡ ACTIONS BEING TAKEN:**
✓ Support team is actively investigating the issue
✓ Working to identify root cause and provide resolution
✓ You will receive regular updates on progress

**NEXT STEPS:**
• Our team will provide updates as we make progress
• If we need additional information, we'll reach out to you
• Expected resolution within the SLA timeframe

We appreciate your patience as we work to resolve this matter promptly.
"""
    
    else:  # S3
        ack += """**✓ ACTIONS BEING TAKEN:**
✓ Your request has been logged and assigned to our support team
✓ We will review the details and respond with required information

**NEXT STEPS:**
• Our team will investigate and provide a detailed response
• If we need any additional information, we'll contact you
• We aim to resolve this within the SLA timeframe

Thank you for your patience.
"""
    
    ack += f"""
**STATUS:** ✅ Acknowledged and Assigned
**TIMESTAMP:** {timestamp}

Best regards,
DVSum Support Team
{'='*80}
"""
    
    return ack

def search_knowledge_base(ticket_text):
    """Search knowledge base for solutions"""
    sources = []
    context_parts = []
    search_methods = []
    
    try:
        # Method 1: Keyword Search
        if SMART_SEARCH_AVAILABLE and smart_searcher:
            print("🔍 Searching articles (Keyword)...")
            try:
                if hasattr(smart_searcher, 'search_and_get_context'):
                    keyword_context = smart_searcher.search_and_get_context(ticket_text, max_articles=3)
                    if keyword_context:
                        context_parts.append(("Knowledge Base Articles", keyword_context))
                        search_methods.append("Knowledge Base Articles")
                        urls = re.findall(r'URL: (https?://[^\s]+)', keyword_context)
                        sources.extend(urls)
            except Exception as e:
                print(f"⚠️ Keyword search failed: {e}")
        
        # Method 2: Vector Search
        if vector_store:
            print("🧠 Searching documentation (Semantic)...")
            try:
                docs = vector_store.similarity_search(ticket_text, k=3)
                if docs:
                    semantic_context = "\n\nRELATED DOCUMENTATION:\n"
                    for i, doc in enumerate(docs, 1):
                        semantic_context += f"Document {i}:\n{doc.page_content[:800]}\n\n"
                    context_parts.append(("Documentation Database", semantic_context))
                    search_methods.append("Documentation Database")
            except Exception as e:
                print(f"⚠️ Semantic search failed: {e}")
        
        return context_parts, sources, search_methods
    
    except Exception as e:
        print(f"❌ Knowledge base search failed: {e}")
        return [], [], []

def generate_solution(ticket_text, context_parts, severity):
    """Generate solution based on knowledge base"""
    if not context_parts or not standalone_llm:
        return None
    
    combined_context = ""
    for method, context in context_parts:
        combined_context += f"\n{'='*60}\n{method}\n{'='*60}\n{context}\n"
    
    severity_config = SEVERITY_CONFIGS[severity]
    
    solution_prompt = f"""You are a DVSum technical support expert providing a solution.

TICKET ISSUE:
{ticket_text}

PRIORITY: {severity} - {severity_config['name']}

KNOWLEDGE BASE INFORMATION:
{combined_context}

Task: Provide a clear, actionable solution based on the knowledge base.

IMPORTANT FORMATTING RULES:
1. Each step MUST be on a NEW LINE
2. Use numbered lists (1., 2., 3., etc.) for sequential steps
3. Add a blank line between major sections
4. Keep each step clear and concise
5. If there are sub-steps, indent them with "   - " (3 spaces + dash)

Format your response as:

**IMMEDIATE SOLUTION:**

1. First step here
   - Sub-step if needed
   - Another sub-step

2. Second step here

3. Third step here

**REFERENCE DOCUMENTATION:**
[Mention relevant articles or documentation]

**VERIFICATION:**
[How to confirm the issue is resolved]

If knowledge base doesn't have complete solution, say: "Based on available documentation, I recommend consulting with our engineering team for the most accurate resolution. I will escalate this and update you shortly."

Your solution:"""

    try:
        response = standalone_llm.invoke(solution_prompt)
        print(f"✅ Generated solution")
        return response.content.strip()
    except Exception as e:
        print(f"⚠️ Solution generation failed: {e}")
        return None

def generate_fr_summary(ticket_text):
    """Generate Future Request summary for enhancements"""
    if not standalone_llm:
        return None
    
    fr_prompt = f"""You are a product manager creating a Future Request (FR) summary.

ENHANCEMENT REQUEST:
{ticket_text}

Create a structured FR summary for the product backlog.

Format:

**FR TITLE:**
[Short, descriptive title]

**BUSINESS JUSTIFICATION:**
[Why is this needed? What problem does it solve?]

**DETAILED DESCRIPTION:**
[What exactly is being requested?]

**EXPECTED BENEFIT:**
[How will this improve the product/user experience?]

**PRIORITY RECOMMENDATION:**
[Hotlist (Critical) / Sprint (High) / Backlog (Low) - with brief reasoning]

Your FR summary:"""

    try:
        response = standalone_llm.invoke(fr_prompt)
        print(f"✅ Generated FR summary")
        return response.content.strip()
    except Exception as e:
        print(f"⚠️ FR generation failed: {e}")
        return None

@app.route('/handle-ticket', methods=['POST'])
def handle_ticket():
    """Main ticket processing endpoint"""
    if not standalone_llm:
        return jsonify({
            "error": "AI agent not initialized. Please check GROQ_API_KEY in .env file"
        }), 400
    
    data = request.json
    ticket_text = data.get('ticket_text', '').strip()
    
    if not ticket_text:
        return jsonify({"error": "No ticket text provided"}), 400
    
    try:
        print(f"\n{'='*80}")
        print(f"🎫 NEW TICKET RECEIVED")
        print(f"{'='*80}")
        print(f"Content: {ticket_text[:100]}...\n")
        
        # STEP 0: Check if DVSum-related
        print("🔍 Checking ticket relevance...")
        is_dvsum, redirect_category, redirect_email = check_dvsum_relevance(ticket_text)
        
        if not is_dvsum:
            redirect_msg = f"""Thank you for reaching out to DVSum Support.

This help desk is specifically for DVSum product-related questions (Data Integration, Data Quality, CADDI).

Your request appears to be related to {redirect_category.replace('_', ' ').title()}.

**Please submit your request to:** {redirect_email}

Feel free to contact us again for DVSum product-related issues.

Best regards,
DVSum Support Team"""
            
            return jsonify({
                "success": True,
                "redirected": True,
                "redirect_category": redirect_category,
                "redirect_email": redirect_email,
                "message": redirect_msg
            })
        
        # STEP 1: Classify severity and type
        print("🎯 Analyzing severity and type...")
        severity, ticket_type, reasoning = analyze_severity_and_type(ticket_text)
        
        # STEP 2: Generate simple explanation
        print("💬 Generating explanation...")
        simple_explanation = explain_in_simple_english(ticket_text)
        
        # STEP 3: Generate acknowledgment
        print("✉️ Generating acknowledgment...")
        acknowledgment = generate_acknowledgment(severity, ticket_type, simple_explanation)
        
        # Build base response
        response_data = {
            "success": True,
            "redirected": False,
            "classification": {
                "severity": severity,
                "severity_name": SEVERITY_CONFIGS[severity]['name'],
                "ticket_type": ticket_type,
                "ticket_type_description": TICKET_TYPES[ticket_type],
                "reasoning": reasoning
            },
            "simple_explanation": simple_explanation,
            "acknowledgment": acknowledgment,
            "sla": {
                "response_time": SEVERITY_CONFIGS[severity]['sla_response'],
                "resolution_time": SEVERITY_CONFIGS[severity]['sla_resolution']
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # STEP 4: Search for solution (if Bug/Question/Request)
        if ticket_type in ["BUG", "QUESTION", "REQUEST"]:
            print("🔍 Searching knowledge base...")
            context_parts, sources, search_methods = search_knowledge_base(ticket_text)
            
            if context_parts:
                solution = generate_solution(ticket_text, context_parts, severity)
                if solution:
                    response_data["immediate_solution"] = {
                        "solution": solution,
                        "sources": sources if sources else ["DVSum Knowledge Base"],
                        "search_methods": search_methods
                    }
        
        # STEP 5: Generate FR summary (if Enhancement)
        if ticket_type == "ENHANCEMENT":
            print("📝 Generating FR summary...")
            fr_summary = generate_fr_summary(ticket_text)
            if fr_summary:
                response_data["fr_summary"] = fr_summary
        
        print(f"✅ Ticket processed successfully")
        print(f"{'='*80}\n")
        
        return jsonify(response_data)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "message": "Error processing ticket"
        }), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Enhanced chat endpoint for follow-up questions with proper formatting"""
    if not standalone_llm:
        return jsonify({"error": "LLM not initialized"}), 400
    
    data = request.json
    question = data.get('question', '').strip()
    context = data.get('context', '')  # Original ticket for context
    
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    try:
        # Search knowledge base
        context_parts, sources, search_methods = search_knowledge_base(question)
        
        if context_parts:
            combined_context = ""
            for method, ctx in context_parts:
                combined_context += f"{ctx}\n"
            
            prompt = f"""You are a DVSum support expert answering a follow-up question.

ORIGINAL TICKET CONTEXT:
{context}

KNOWLEDGE BASE:
{combined_context}

FOLLOW-UP QUESTION: {question}

CRITICAL FORMATTING REQUIREMENTS:
1. Each step or point MUST be on a SEPARATE LINE
2. Use numbered lists (1., 2., 3., etc.) for sequential steps
3. Use bullet points (•) for non-sequential items
4. Add a blank line between major sections
5. Keep explanations clear and well-structured
6. For step-by-step guides, break down EACH step on a new line

EXAMPLE FORMAT (Follow this exactly):

**Creating an Agent:**

1. Navigate to the Sources Detail page
   • Any Source with Chat Enabled will have the Agent Tab

2. Click on the "Agents" tab

3. Click on "Create Agent" button

4. Configure the agent settings
   • Select tables from Available Tables
   • Set up detailed question parameters

**Training the Agent:**

1. Go to the Definition Tab after creating the Agent

2. Add tables from Available Tables
   • You can use all tables or limit to specific ones

3. Enable detailed question features
   • SQL Code and Logs generation
   • Visualization options (Grid, Chart, Pivot)

Provide a clear, helpful answer using the knowledge base information. Put EACH step on its own line with proper numbering.

Answer:"""
            
            response = standalone_llm.invoke(prompt)
            answer = response.content.strip()
        else:
            prompt = f"""You are a DVSum support expert answering a follow-up question.

ORIGINAL TICKET CONTEXT:
{context}

FOLLOW-UP QUESTION: {question}

CRITICAL FORMATTING REQUIREMENTS:
1. Each step or point MUST be on a SEPARATE LINE
2. Use numbered lists (1., 2., 3., etc.) for sequential steps
3. Use bullet points (•) for non-sequential items
4. Add a blank line between major sections
5. Keep explanations clear and well-structured

Provide a clear, helpful answer based on your DVSum product knowledge. Put EACH step on its own line.

Answer:"""
            
            response = standalone_llm.invoke(prompt)
            answer = response.content.strip()
            sources = ["General Knowledge"]
            search_methods = ["General AI"]
        
        return jsonify({
            "answer": answer,
            "sources": sources,
            "search_methods_used": search_methods
        })
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    article_count = 0
    if SMART_SEARCH_AVAILABLE and smart_searcher:
        if hasattr(smart_searcher, 'articles'):
            article_count = len(smart_searcher.articles)
    
    return jsonify({
        "status": "healthy",
        "agent_mode": "dvsum_support_agent",
        "llm": "initialized" if standalone_llm else "not initialized",
        "search_methods": {
            "keyword_search": {
                "enabled": bool(SMART_SEARCH_AVAILABLE and smart_searcher),
                "articles_count": article_count
            },
            "semantic_search": {
                "enabled": bool(vector_store),
                "database_exists": os.path.exists("./chroma_db")
            }
        },
        "capabilities": [
            "Ticket triage and routing",
            "Severity classification (S1/S2/S3)",
            "Type detection (Bug/Enhancement/Question/Request)",
            "Factual issue summaries for support agents",
            "Formal acknowledgments per DVSum SLA",
            "Knowledge base search for solutions",
            "Follow-up chat support",
            "FR summary generation for enhancements"
        ]
    })

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🎫 DVSUM AI SUPPORT AGENT")
    print("="*80)
    print("Workflow:")
    print("  1. ✅ Ticket Triage (DVSum vs. Redirect)")
    print("  2. 🎯 Severity Classification (S1/S2/S3)")
    print("  3. 🏷️  Type Detection (Bug/Enhancement/Question/Request)")
    print("  4. 💬 Factual Issue Summary")
    print("  5. ✉️  Formal Acknowledgment with SLA")
    print("  6. 🔍 Knowledge Base Search for Solutions")
    print("  7. 💭 Follow-up Chat Support")
    print("  8. 📝 FR Summary for Enhancements")
    print("="*80 + "\n")
    
    initialize_qa_system()
    app.run(host='0.0.0.0', port=5000, debug=True)