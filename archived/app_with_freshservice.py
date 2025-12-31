from flask import Flask, request, jsonify
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from freshservice_integration import FreshserviceClient
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize systems
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'}
)

vector_store = None
qa_chain = None
freshservice = FreshserviceClient()

def initialize_qa_system():
    global vector_store, qa_chain
    
    persist_directory = "./chroma_db"
    
    if os.path.exists(persist_directory):
        vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )
        
        llm = Ollama(
            model="llama3.2",
            temperature=0.3,
            base_url="http://localhost:11434"
        )
        
        prompt_template = """You are a helpful technical support assistant. Use the following context to answer the question. If you don't know the answer based on the context, say so clearly and suggest creating a support ticket.

Context: {context}

Question: {question}

Answer: Provide a clear, step-by-step answer if applicable."""

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
        
        print("✅ QA System initialized successfully")

@app.route('/chat', methods=['POST'])
def chat():
    if not qa_chain:
        return jsonify({"error": "Knowledge base not initialized"}), 400
    
    data = request.json
    question = data.get('question', '')
    email = data.get('email', '')
    
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    try:
        result = qa_chain({"query": question})
        answer = result['result']
        
        # Check if answer indicates inability to help
        unclear_indicators = ["don't know", "cannot answer", "unclear", "not sure"]
        should_create_ticket = any(indicator in answer.lower() for indicator in unclear_indicators)
        
        response = {
            "answer": answer,
            "sources": [doc.page_content[:200] + "..." for doc in result['source_documents']],
            "suggest_ticket": should_create_ticket
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/create-ticket', methods=['POST'])
def create_ticket():
    """Create a Freshservice ticket"""
    
    data = request.json
    
    required_fields = ['subject', 'description', 'email']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    
    ticket = freshservice.create_ticket(
        subject=data['subject'],
        description=data['description'],
        email=data['email'],
        priority=data.get('priority', 2)
    )
    
    if ticket:
        return jsonify({
            "success": True,
            "ticket_id": ticket['ticket']['id'],
            "message": "Ticket created successfully"
        })
    else:
        return jsonify({"error": "Failed to create ticket"}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "qa_system": "initialized" if qa_chain else "not initialized"
    })

if __name__ == '__main__':
    initialize_qa_system()
    app.run(host='0.0.0.0', port=5000, debug=True)