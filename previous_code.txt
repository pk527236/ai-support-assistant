__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from unittest.mock import MagicMock
sys.modules['posthog'] = MagicMock()

from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
import requests
import re

# Import smart hybrid search
from smart_hybrid_search import get_smart_searcher, is_dvsum_related

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
FRESHSERVICE_DOMAIN = os.getenv('FRESHSERVICE_DOMAIN', 'your-domain.freshservice.com')
FRESHSERVICE_API_KEY = os.getenv('FRESHSERVICE_API_KEY', 'your-api-key')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')

# Global variables
vector_store = None
qa_chain = None
standalone_llm = None
smart_searcher = None

def get_embeddings():
    """Get embeddings for vector store"""
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        print("🔧 Loading HuggingFace embeddings...")
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        print("✅ Embeddings loaded")
        return embeddings
    except Exception as e:
        print(f"❌ Embeddings failed: {e}")
        raise

def initialize_llm():
    """Initialize Groq LLM"""
    global standalone_llm
    
    if not GROQ_API_KEY:
        print("⚠️ No GROQ_API_KEY found")
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
    """
    Initialize BOTH search methods:
    1. Smart Hybrid Search (keyword-based, fast)
    2. Vector Search (semantic, trained)
    """
    global vector_store, qa_chain, smart_searcher
    
    # Initialize LLM
    llm = initialize_llm()
    if not llm:
        return
    
    print("\n" + "="*80)
    print("🚀 Initializing AI Support Bot")
    print("="*80)
    
    # Method 1: Smart Hybrid Search (Keyword-based)
    print("\n📊 Method 1: Smart Hybrid Search (Keyword-based)")
    smart_searcher = get_smart_searcher()
    
    if smart_searcher and smart_searcher.articles:
        print(f"✅ Loaded {len(smart_searcher.articles)} articles")
        print(f"   → Fast keyword search enabled")
    else:
        print("⚠️ No articles found. Run: python zendesk_scraper.py")
    
    # Method 2: Vector Search (Semantic, trained)
    print("\n🧠 Method 2: Vector Search (Semantic, trained)")
    persist_directory = "./chroma_db"
    
    if os.path.exists(persist_directory):
        try:
            embeddings = get_embeddings()
            vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=embeddings
            )
            
            # Test if vector store has data
            test_results = vector_store.similarity_search("test", k=1)
            if test_results:
                print(f"✅ Vector database loaded")
                print(f"   → Semantic search enabled")
                
                # Create QA chain
                prompt_template = """You are an expert DVSum technical support assistant.

Context from knowledge base:
{context}

Question: {question}

Provide a clear, detailed answer using the context above. Include step-by-step instructions when relevant.

Answer:"""

                PROMPT = PromptTemplate(
                    template=prompt_template, 
                    input_variables=["context", "question"]
                )
                
                qa_chain = RetrievalQA.from_chain_type(
                    llm=llm,
                    chain_type="stuff",
                    retriever=vector_store.as_retriever(search_kwargs={"k": 3}),
                    chain_type_kwargs={"prompt": PROMPT},
                    return_source_documents=True
                )
            else:
                print("⚠️ Vector database is empty")
                vector_store = None
                
        except Exception as e:
            print(f"⚠️ Vector search failed: {e}")
            vector_store = None
    else:
        print("⚠️ No vector database found")
        print("   💡 To enable semantic search:")
        print("   1. Run: python data_ingestion.py")
        print("   2. This will create chroma_db/ with embeddings")
    
    # Summary
    print("\n" + "="*80)
    print("📊 Search Methods Available:")
    if smart_searcher and smart_searcher.articles:
        print("   ✅ Keyword Search (Fast)")
    else:
        print("   ❌ Keyword Search (No data)")
    
    if vector_store:
        print("   ✅ Semantic Search (Intelligent)")
    else:
        print("   ❌ Semantic Search (Not trained)")
    
    if not (smart_searcher and smart_searcher.articles) and not vector_store:
        print("\n⚠️ WARNING: No search methods available!")
        print("   Run: python zendesk_scraper.py")
        print("   Then: python data_ingestion.py")
    
    print("="*80 + "\n")

def should_suggest_ticket(answer):
    """Check if we should suggest ticket creation"""
    uncertainty_phrases = [
        "i don't know", "i'm not sure", "cannot answer",
        "don't have information", "unclear",
        "recommend creating a support ticket",
        "need more information", "contact support"
    ]
    return any(phrase in answer.lower() for phrase in uncertainty_phrases)

def create_freshservice_ticket(email, subject, description, priority=2):
    """Create a Freshservice ticket"""
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/tickets"
    
    payload = {
        "email": email,
        "subject": subject,
        "description": description,
        "priority": priority,
        "status": 2
    }
    
    try:
        response = requests.post(
            url,
            auth=(FRESHSERVICE_API_KEY, 'X'),
            headers={"Content-Type": "application/json"},
            json=payload
        )
        
        if response.status_code == 201:
            return {
                "success": True,
                "ticket_id": response.json()['ticket']['id']
            }
        return {"success": False, "error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route('/chat', methods=['POST'])
def chat():
    """
    Enhanced chat using BOTH search methods:
    1. Try keyword search first (fast)
    2. Augment with semantic search if available
    3. Fallback to general knowledge
    """
    if not standalone_llm:
        return jsonify({
            "error": "LLM not initialized. Set GROQ_API_KEY in .env"
        }), 400
    
    data = request.json
    question = data.get('question', '')
    
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    try:
        sources = []
        answer = ""
        search_methods_used = []
        
        # Strategy: Use both search methods for DVSum questions
        if is_dvsum_related(question):
            print(f"\n{'='*80}")
            print(f"🎯 DVSum Question: '{question[:60]}...'")
            print(f"{'='*80}")
            
            context_parts = []
            
            # Method 1: Keyword Search (Fast)
            if smart_searcher and smart_searcher.articles:
                print("\n🔍 Method 1: Keyword Search")
                try:
                    keyword_context = smart_searcher.search_and_get_context(
                        question, 
                        max_articles=2
                    )
                    
                    if keyword_context:
                        context_parts.append(("Keyword Search", keyword_context))
                        search_methods_used.append("Keyword Search")
                        print("   ✅ Found relevant articles via keywords")
                        
                        # Extract URLs
                        urls = re.findall(r'URL: (https?://[^\s]+)', keyword_context)
                        sources.extend(urls)
                except Exception as e:
                    print(f"   ⚠️ Keyword search failed: {e}")
            
            # Method 2: Semantic Search (Intelligent)
            if vector_store:
                print("\n🧠 Method 2: Semantic Search")
                try:
                    # Get semantically similar documents
                    docs = vector_store.similarity_search(question, k=2)
                    
                    if docs:
                        semantic_context = "\n\nSEMANTIC SEARCH RESULTS:\n\n"
                        for i, doc in enumerate(docs, 1):
                            semantic_context += f"Result {i}:\n{doc.page_content[:1500]}\n\n"
                        
                        context_parts.append(("Semantic Search", semantic_context))
                        search_methods_used.append("Semantic Search")
                        print(f"   ✅ Found {len(docs)} semantically similar articles")
                except Exception as e:
                    print(f"   ⚠️ Semantic search failed: {e}")
            
            # Combine contexts from both methods
            if context_parts:
                combined_context = ""
                for method, context in context_parts:
                    combined_context += f"\n{'='*80}\n"
                    combined_context += f"FROM {method.upper()}:\n"
                    combined_context += f"{'='*80}\n"
                    combined_context += context + "\n"
                
                # Create enhanced prompt
                enhanced_prompt = f"""You are an expert DVSum technical support assistant.

I've searched the knowledge base using multiple methods and found this information:

{combined_context}

User Question: {question}

Using the information above, provide a clear, detailed, step-by-step answer. Combine insights from all sources. Reference specific articles when relevant.

Answer:"""
                
                print(f"\n💬 Generating answer using {len(context_parts)} search methods...")
                response = standalone_llm.invoke(enhanced_prompt)
                answer = response.content
                
                if not sources:
                    sources = ["DVSum Knowledge Base"]
            
            else:
                print("\n⚠️ No results from any search method")
        
        # Fallback: Use general knowledge or QA chain
        if not answer:
            print("\n🌐 Using general knowledge / QA chain")
            
            if qa_chain:
                result = qa_chain({"query": question})
                answer = result['result']
                sources = [doc.page_content[:200] + "..." for doc in result['source_documents']]
                search_methods_used.append("QA Chain")
            else:
                # Pure LLM response
                general_prompt = f"""You are an expert technical support assistant specializing in DVSum, AWS, DevOps, and IT Support.

Question: {question}

Provide a clear, accurate, helpful answer with step-by-step instructions when relevant.

Answer:"""
                
                response = standalone_llm.invoke(general_prompt)
                answer = response.content
                sources = ["General AI Knowledge"]
                search_methods_used.append("General Knowledge")
        
        suggest_ticket = should_suggest_ticket(answer)
        
        print(f"\n✅ Answer generated using: {', '.join(search_methods_used)}")
        print(f"{'='*80}\n")
        
        return jsonify({
            "answer": answer,
            "sources": sources,
            "suggest_ticket": suggest_ticket,
            "search_methods_used": search_methods_used,
            "total_methods": len(search_methods_used)
        })
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "message": "Error processing request"
        }), 500

@app.route('/search', methods=['POST'])
def search_articles():
    """Direct keyword search endpoint"""
    if not smart_searcher or not smart_searcher.articles:
        return jsonify({"error": "No articles loaded"}), 400
    
    data = request.json
    query = data.get('query', '')
    max_results = data.get('max_results', 5)
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        results = smart_searcher.search(query, max_results=max_results)
        return jsonify({
            "success": True,
            "query": query,
            "results": results,
            "total_found": len(results)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/create-ticket', methods=['POST'])
def create_ticket():
    """Create a Freshservice ticket"""
    data = request.json
    
    email = data.get('email')
    subject = data.get('subject')
    description = data.get('description')
    priority = data.get('priority', 2)
    
    if not all([email, subject, description]):
        return jsonify({
            "success": False,
            "error": "Missing required fields"
        }), 400
    
    result = create_freshservice_ticket(email, subject, description, priority)
    return jsonify(result), 200 if result['success'] else 500

@app.route('/health', methods=['GET'])
def health():
    """Health check with detailed status"""
    article_count = len(smart_searcher.articles) if smart_searcher else 0
    
    return jsonify({
        "status": "healthy",
        "llm": "initialized" if standalone_llm else "not initialized",
        "search_methods": {
            "keyword_search": {
                "enabled": bool(smart_searcher and smart_searcher.articles),
                "articles_count": article_count
            },
            "semantic_search": {
                "enabled": bool(vector_store),
                "database_exists": os.path.exists("./chroma_db")
            }
        },
        "recommendations": get_recommendations()
    })

def get_recommendations():
    """Get setup recommendations"""
    recs = []
    
    if not (smart_searcher and smart_searcher.articles):
        recs.append("Run: python zendesk_scraper.py (to scrape articles)")
    
    if not vector_store:
        recs.append("Run: python data_ingestion.py (to enable semantic search)")
    
    if not recs:
        recs.append("All systems operational! ✅")
    
    return recs

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 AI Support Bot - Dual Search Engine")
    print("="*80)
    print("Features:")
    print("  • Keyword Search (Fast, pattern matching)")
    print("  • Semantic Search (Intelligent, understands meaning)")
    print("  • Groq LLM (Fast inference)")
    print("="*80 + "\n")
    
    initialize_qa_system()
    app.run(host='0.0.0.0', port=5000, debug=True)