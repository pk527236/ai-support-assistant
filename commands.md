# 🚀 Quick Command Reference

## Initial Setup (One Time)

```bash
# 1. Create project directory
mkdir ai-support-bot
cd ai-support-bot

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2

# 5. Create .env file
cat > .env << EOF
FRESHSERVICE_DOMAIN=yourcompany.freshservice.com
FRESHSERVICE_API_KEY=your_api_key_here
EOF

# 6. Create data directory and add files
mkdir data
# Add your training files to data/

# 7. Process data
python data_ingestion.py
```

---

## Daily Usage

### Start Everything (3 Terminals)

**Terminal 1: Ollama**
```bash
ollama serve
```

**Terminal 2: Flask Backend**
```bash
cd ai-support-bot
source venv/bin/activate
python app.py
```

**Terminal 3: Frontend Server (Optional)**
```bash
cd ai-support-bot
python -m http.server 8000
# Then open: http://localhost:8000/index.html
```

**Or just open `index.html` directly in your browser**

---

## Common Commands

### Activate Virtual Environment
```bash
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### Update Knowledge Base
```bash
# 1. Add new files to data/
cp new_document.txt data/

# 2. Re-process
python data_ingestion.py

# 3. Restart Flask
# Ctrl+C to stop, then:
python app.py
```

### Test System
```bash
# Run automated tests
python test_system.py

# Manual tests
curl http://localhost:5000/health
curl http://localhost:5000/test-freshservice
```

### Check Status
```bash
# Flask health
curl http://localhost:5000/health | python -m json.tool

# Ollama models
ollama list

# Freshservice connection
python freshservice_integration.py
```

---

## Troubleshooting Commands

### Flask Issues
```bash
# Check if running
curl http://localhost:5000/health

# Check process
lsof -i :5000  # Linux/Mac
netstat -ano | findstr :5000  # Windows

# Kill process if stuck
kill -9 $(lsof -t -i:5000)  # Linux/Mac
```

### Ollama Issues
```bash
# Check status
curl http://localhost:11434

# Restart Ollama
killall ollama
ollama serve

# Re-pull model
ollama pull llama3.2

# Test model
ollama run llama3.2 "Hello"
```

### Database Issues
```bash
# Reset database
rm -rf chroma_db/
python data_ingestion.py

# Check database
ls -la chroma_db/
```

### Freshservice Issues
```bash
# Test connection
python freshservice_integration.py

# Check credentials
cat .env | grep FRESHSERVICE

# Test API manually
curl -u YOUR_API_KEY:X https://yourcompany.freshservice.com/api/v2/tickets
```

---

## Development Commands

### Install New Package
```bash
source venv/bin/activate
pip install package-name
pip freeze > requirements.txt
```

### View Logs
```bash
# Flask logs
python app.py 2>&1 | tee logs/flask.log

# Tail logs
tail -f logs/flask.log
```

### Clean Up
```bash
# Remove cache
rm -rf __pycache__/
find . -name "*.pyc" -delete

# Remove database
rm -rf chroma_db/

# Remove virtual environment
rm -rf venv/
```

---

## Production Commands

### Using Gunicorn
```bash
# Install
pip install gunicorn

# Run production server
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# With logging
gunicorn -w 4 -b 0.0.0.0:5000 app:app \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

### Using Docker
```bash
# Build
docker build -t ai-support-bot .

# Run
docker run -p 5000:5000 --env-file .env ai-support-bot

# Run with Ollama
docker-compose up
```

---

## API Testing Commands

### Chat Endpoint
```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do I reset my password?",
    "email": "user@example.com"
  }'
```

### Create Ticket
```bash
curl -X POST http://localhost:5000/create-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Test Ticket",
    "description": "This is a test ticket",
    "email": "user@example.com",
    "priority": 2
  }'
```

### Search Tickets
```bash
curl -X POST http://localhost:5000/tickets/search \
  -H "Content-Type: application/json" \
  -d '{"query": "password reset"}'
```

### Health Check
```bash
curl http://localhost:5000/health | python -m json.tool
```

---

## Backup & Restore

### Backup
```bash
# Backup everything
tar -czf backup_$(date +%Y%m%d).tar.gz \
  data/ chroma_db/ .env app.py freshservice_integration.py

# Backup database only
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz chroma_db/
```

### Restore
```bash
# Restore from backup
tar -xzf backup_20241209.tar.gz
```

---

## Performance Monitoring

### Check Resources
```bash
# CPU and Memory
top | grep python

# Disk usage
du -sh chroma_db/

# Connection count
netstat -an | grep 5000 | wc -l
```

### Benchmark
```bash
# Response time test
time curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}'

# Load test with ab (Apache Bench)
ab -n 100 -c 10 http://localhost:5000/health
```

---

## Git Commands

### Initial Setup
```bash
git init
git add .
git commit -m "Initial commit"

# Important: Create .gitignore first!
cat > .gitignore << EOF
.env
venv/
chroma_db/
__pycache__/
*.pyc
*.log
EOF
```

### Daily Work
```bash
git add .
git commit -m "Update: description"
git push origin main
```

---

## Quick Fixes

### Port Already in Use
```bash
# Kill process on port 5000
kill -9 $(lsof -t -i:5000)
```

### Permission Denied
```bash
chmod +x start.sh
```

### Module Not Found
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Database Locked
```bash
rm -rf chroma_db/
python data_ingestion.py
```

---

## One-Line Setup
```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && ollama pull llama3.2 && mkdir -p data && python data_ingestion.py
```

## One-Line Start
```bash
source venv/bin/activate && python app.py
```

---

## Help & Documentation

```bash
# Python help
python app.py --help

# Flask routes
flask routes  # If Flask CLI is configured

# Ollama help
ollama --help

# Test everything
python test_system.py
```