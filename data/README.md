# 🤖 AI Support Bot with Freshservice Integration

An intelligent customer support chatbot powered by LangChain and Ollama, with seamless Freshservice ticket creation for escalations.

## ✨ Features

- 💬 **AI-Powered Chat** - Natural language Q&A using your knowledge base
- 🎫 **Smart Ticket Creation** - Automatically suggests creating tickets when AI can't help
- 🔗 **Freshservice Integration** - Direct ticket creation in your Freshservice account
- 📚 **Knowledge Base** - Train on your own documents (txt, md, json)
- 🎨 **Beautiful UI** - Modern, responsive chat interface
- 🚀 **Easy Setup** - Ready to run in minutes

## 🏗️ Architecture

```
Frontend (HTML/JS) ←→ Flask API ←→ LangChain + Ollama
                          ↓
                    Chroma Vector DB
                          ↓
                   Freshservice API
```

## 📋 Prerequisites

- Python 3.8+
- Ollama (local LLM runtime)
- Freshservice account with API access
- 4GB RAM minimum

## 🚀 Quick Start

### 1. Clone & Setup

```bash
# Create project directory
mkdir ai-support-bot
cd ai-support-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Install Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the model
ollama pull llama3.2

# Start Ollama (keep this running)
ollama serve
```

### 3. Configure Freshservice

Create `.env` file:

```bash
FRESHSERVICE_DOMAIN=yourcompany.freshservice.com
FRESHSERVICE_API_KEY=your_api_key_here
```

**Get API Key:**
1. Log in to Freshservice
2. Admin → API Settings
3. Generate API Key

### 4. Prepare Knowledge Base

```bash
# Create data directory
mkdir data

# Add your training files
# Example files:
# - data/faq.txt
# - data/user_manual.md
# - data/troubleshooting.txt
```

### 5. Create Vector Database

```bash
python data_ingestion.py
```

### 6. Run Application

```bash
# Start Flask server
python app.py

# Open index.html in your browser
# Or serve it: python -m http.server 8000
```

## 📁 Project Structure

```
ai-support-bot/
├── app.py                          # Main Flask application
├── freshservice_integration.py     # Freshservice API client
├── data_ingestion.py              # Knowledge base processor
├── index.html                      # Frontend UI
├── requirements.txt                # Python dependencies
├── .env                            # Configuration (create this)
├── data/                           # Your knowledge base
│   ├── faq.txt
│   ├── user_manual.md
│   └── troubleshooting.txt
└── chroma_db/                      # Vector database (auto-generated)
```

## 🎯 Usage

### Chat with AI

1. Open the frontend (`index.html`)
2. Wait for "Connected & Ready" status
3. Type your question
4. Get instant AI-powered answers

### Create Support Tickets

1. Ask a question the AI can't answer
2. Click "Create Support Ticket" button
3. Fill in the form:
   - Email
   - Subject (auto-filled)
   - Description
   - Priority
4. Submit and get ticket ID

### Update Knowledge Base

```bash
# Add new files to data/ folder
cp new_document.txt data/

# Re-run ingestion
python data_ingestion.py

# Restart app
python app.py
```

## 🔧 Configuration

### Environment Variables

```bash
# Required
FRESHSERVICE_DOMAIN=yourcompany.freshservice.com
FRESHSERVICE_API_KEY=your_api_key_here

# Optional
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Supported Document Formats

- `.txt` - Plain text
- `.md` - Markdown
- `.json` - JSON (Teams chat history, etc.)

## 🧪 Testing

### Test Backend

```bash
# Health check
curl http://localhost:5000/health

# Test chat
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I reset my password?"}'

# Test Freshservice
curl http://localhost:5000/test-freshservice
```

### Test Frontend

1. Open `index.html`
2. Verify connection status
3. Send test message
4. Try ticket creation

## 🐛 Troubleshooting

### "Cannot connect to server"
```bash
# Check Flask status
curl http://localhost:5000/health

# Restart Flask
python app.py
```

### "QA System not initialized"
```bash
# Run data ingestion
python data_ingestion.py

# Verify database exists
ls -la chroma_db/
```

### "Ollama not responding"
```bash
# Check Ollama
ollama list

# Restart Ollama
ollama serve

# Pull model
ollama pull llama3.2
```

### "Failed to create ticket"
```bash
# Test Freshservice connection
python freshservice_integration.py

# Verify .env credentials
cat .env
```

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/chat` | POST | Chat with AI |
| `/create-ticket` | POST | Create support ticket |
| `/test-freshservice` | GET | Test Freshservice connection |
| `/tickets/search` | POST | Search existing tickets |

## 🔒 Security

- ✅ API keys in environment variables
- ✅ Input validation
- ✅ CORS enabled for frontend
- ✅ Error handling

**Important:**
```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo "chroma_db/" >> .gitignore
echo "venv/" >> .gitignore
```

## 🚢 Deployment

### Production with Gunicorn

```bash
# Install gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

Build and run:
```bash
docker build -t ai-support-bot .
docker run -p 5000:5000 --env-file .env ai-support-bot
```

## 📈 Performance Tips

1. **Use HuggingFace embeddings** (faster than Ollama)
2. **Adjust chunk size** in `data_ingestion.py`
3. **Increase retriever `k` value** for more context
4. **Use SSD** for faster vector database access

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- [ ] Add user authentication
- [ ] Support more document formats (PDF, DOCX)
- [ ] Add conversation memory
- [ ] Implement caching
- [ ] Add analytics dashboard
- [ ] Multi-language support

## 📝 License

MIT License - feel free to use for commercial projects

## 🆘 Support

- **Issues:** Create a GitHub issue
- **Questions:** Check the troubleshooting section
- **Freshservice Docs:** https://api.freshservice.com/

## 🎉 Acknowledgments

- **LangChain** - AI orchestration framework
- **Ollama** - Local LLM runtime
- **ChromaDB** - Vector database
- **Freshservice** - Ticketing system

---

**Made with ❤️ for better customer support**















# AI Support Bot Setup Guide - Zendesk Integration

## 🎯 Overview
This guide will help you integrate DVSum's Zendesk knowledge base into your AI support bot.

## 📋 Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Internet connection (for scraping Zendesk)

## 🚀 Step-by-Step Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

**Note:** If you encounter issues with `pysqlite3-binary`, try:
```bash
pip install pysqlite3-binary --no-cache-dir
```

### Step 2: Configure Environment Variables
Create or update your `.env` file:
```env
# Groq API (FREE - Get from https://console.groq.com)
GROQ_API_KEY=your_groq_api_key_here

# Freshservice Configuration (Optional)
FRESHSERVICE_DOMAIN=your-domain.freshservice.com
FRESHSERVICE_API_KEY=your_freshservice_api_key
```

### Step 3: Scrape Zendesk Knowledge Base
Run the Zendesk scraper to download all articles:
```bash
python zendesk_scraper.py
```

**What this does:**
- Scrapes all articles from `https://dvsum.zendesk.com/hc/en-us`
- Saves them to `./data/` directory
- Creates three outputs:
  - `zendesk_articles.json` - JSON format with metadata
  - `zendesk_knowledge_base.txt` - Text format for training
  - `zendesk_articles/` - Individual article files

**Expected output:**
```
🚀 Starting Zendesk scraper...
🔍 Fetching categories from https://dvsum.zendesk.com/hc/en-us...
✅ Found 15 categories/sections
📂 Fetching articles from category: ...
✅ Scraped: Article Title
...
✅ SCRAPING COMPLETED SUCCESSFULLY!
📊 Total articles scraped: 50
```

### Step 4: Ingest Data into Vector Store
Process all documents and create the knowledge base:
```bash
python ingest_data.py
```

**What this does:**
- Reads all files from `./data/` directory
- Splits content into chunks
- Creates embeddings using HuggingFace (free, runs locally)
- Stores vectors in ChromaDB (`./chroma_db/`)

**Expected output:**
```
📚 Loading documents from ./data directory...
✅ Loaded: zendesk_knowledge_base.txt (450000 chars)
✅ Loaded: faqs.txt (5000 chars)
✅ Loaded: knowledge_base.txt (3000 chars)

✂️ Splitting documents into chunks...
✅ Created 850 chunks

🧠 Creating embeddings...
✅ Vector store created
✅ TRAINING COMPLETE!
```

### Step 5: Start the AI Assistant
```bash
python app.py
```

Access the bot at: `http://localhost:5000`

## 📁 Project Structure
```
your-project/
├── app.py                          # Main Flask application
├── ingest_data.py                  # Data ingestion script
├── zendesk_scraper.py              # NEW: Zendesk scraper
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables
├── data/                           # Training data
│   ├── zendesk_knowledge_base.txt  # Scraped Zendesk articles
│   ├── zendesk_articles.json       # JSON format
│   ├── faqs.txt                    # Your FAQs
│   ├── knowledge_base.txt          # Your knowledge base
│   └── teams_chat_history.json     # Teams chat history
├── chroma_db/                      # Vector database (auto-generated)
└── index.html                      # Frontend interface
```

## 🔍 How It Works

### 1. **Web Scraping**
`zendesk_scraper.py` crawls the Zendesk help center:
- Finds all categories and sections
- Extracts article URLs
- Scrapes article titles and content
- Saves in multiple formats

### 2. **Data Ingestion**
`ingest_data.py` processes the scraped data:
- Loads all documents from `./data/`
- Splits into 1000-character chunks (200 overlap)
- Creates embeddings using sentence transformers
- Stores in ChromaDB vector database

### 3. **AI Assistant**
`app.py` serves the chatbot:
- Uses Groq API (free, fast) with Llama 3.3 70B
- Retrieves relevant chunks from vector store
- Generates contextual responses
- Suggests ticket creation when needed

## 🎨 Customization Options

### Update Zendesk Content
Re-run the scraper periodically to keep content fresh:
```bash
# Scrape latest articles
python zendesk_scraper.py

# Re-ingest data
python ingest_data.py

# Restart app
python app.py
```

### Modify Scraper Settings
Edit `zendesk_scraper.py`:
```python
# Change base URL
ZENDESK_URL = "https://your-company.zendesk.com/hc/en-us"

# Adjust politeness delay (seconds between requests)
time.sleep(1)  # Change to 2 for slower scraping
```

### Adjust Chunk Size
Edit `ingest_data.py`:
```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,      # Increase for longer chunks
    chunk_overlap=300,    # Increase for more context overlap
)
```

### Change AI Model
Edit `app.py`:
```python
standalone_llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",  # Try: "mixtral-8x7b-32768"
    temperature=0.3,                        # Lower = more focused
)
```

## 🐛 Troubleshooting

### Issue: "No articles scraped"
**Solutions:**
1. Check if Zendesk URL is accessible in browser
2. Verify help center is not behind authentication
3. Check internet connection
4. Try running with verbose logging

### Issue: "Could not load embedding model"
**Solutions:**
```bash
# Install sentence transformers
pip install sentence-transformers --upgrade

# If still fails, try CPU-only version
pip install sentence-transformers --no-deps
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### Issue: "ChromaDB SQLite error"
**Solutions:**
```bash
# Install pysqlite3
pip install pysqlite3-binary --force-reinstall
```

### Issue: "Groq API rate limit"
**Solution:** Get a free API key from https://console.groq.com
- Free tier: 30 requests/minute
- Upgrade for higher limits

## 📊 Testing Your Bot

### Test Questions to Try:
1. **Zendesk content:** "How do I configure data pipelines?"
2. **General knowledge:** "What is AWS Lambda?"
3. **Troubleshooting:** "Why is my API failing?"
4. **Complex queries:** "Compare S3 vs Glacier storage"

### Expected Behavior:
- ✅ Answers should reference Zendesk articles when relevant
- ✅ Should cite sources from knowledge base
- ✅ Should offer ticket creation if uncertain
- ✅ Should provide step-by-step instructions

## 🔄 Maintenance

### Regular Updates
Run weekly or monthly to keep content fresh:
```bash
# Automated update script (save as update_knowledge.sh)
#!/bin/bash
echo "Updating Zendesk knowledge base..."
python zendesk_scraper.py
python ingest_data.py
echo "✅ Knowledge base updated!"
```

### Monitor Performance
Check logs for:
- Scraping errors
- Embedding issues
- API rate limits
- User feedback

## 🎉 You're All Set!

Your AI support bot now has access to:
- ✅ All DVSum Zendesk articles
- ✅ Your custom FAQs
- ✅ Team chat history
- ✅ General AI knowledge

**Next Steps:**
1. Test with real user queries
2. Monitor and improve responses
3. Add more training data as needed
4. Collect user feedback

## 📞 Support

If you need help:
1. Check logs in terminal
2. Review error messages
3. Verify all dependencies installed
4. Ensure .env file configured correctly

---

**Made with ❤️ for better customer support**