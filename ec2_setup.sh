#!/bin/bash

# DVSum AI Support Bot - EC2 Initial Setup Script
# Run this ONCE on your EC2 instance after launching it

set -e

echo "=================================="
echo "DVSum Bot - EC2 Initial Setup"
echo "=================================="

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3 and pip
echo "🐍 Installing Python 3..."
sudo apt install -y python3 python3-pip python3-venv

# Install git
echo "📥 Installing Git..."
sudo apt install -y git

# Install system dependencies for Chrome/Chromium (for Selenium scraper)
echo "🌐 Installing Chrome dependencies..."
sudo apt install -y chromium-browser chromium-chromedriver

# Install build essentials (needed for some Python packages)
echo "🔧 Installing build essentials..."
sudo apt install -y build-essential python3-dev

# Create application directory
echo "📁 Creating application directory..."
mkdir -p ~/ai-support-bot
cd ~/ai-support-bot

# Clone repository (you'll need to replace with your actual repo URL)
echo "📥 Cloning repository..."
read -p "Enter your GitHub repository URL: " REPO_URL
git clone $REPO_URL .

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
echo "🔧 Creating .env file..."
read -p "Enter your GROQ API KEY: " GROQ_KEY
cat > .env << EOF
GROQ_API_KEY=$GROQ_KEY
FRESHSERVICE_DOMAIN=yourcompany.freshservice.com
FRESHSERVICE_API_KEY=your_api_key_here
EOF

# Create data directory
echo "📁 Creating data directory..."
mkdir -p data

# Create log directory
echo "📝 Creating log directory..."
sudo mkdir -p /var/log/dvsum-bot
sudo chown $USER:$USER /var/log/dvsum-bot

# Copy systemd service file
echo "⚙️ Setting up systemd service..."
sudo cp dvsum-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dvsum-bot.service

# Start the service
echo "🚀 Starting DVSum Bot service..."
sudo systemctl start dvsum-bot.service

# Check status
echo "✅ Checking service status..."
sudo systemctl status dvsum-bot.service --no-pager

# Setup nginx as reverse proxy (optional but recommended)
echo ""
read -p "Do you want to setup Nginx reverse proxy? (y/n): " SETUP_NGINX

if [ "$SETUP_NGINX" = "y" ]; then
    echo "🌐 Installing Nginx..."
    sudo apt install -y nginx
    
    echo "🔧 Configuring Nginx..."
    sudo tee /etc/nginx/sites-available/dvsum-bot << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
    
    sudo ln -sf /etc/nginx/sites-available/dvsum-bot /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    
    echo "✅ Nginx configured! Access your bot at http://YOUR_EC2_IP"
fi

echo ""
echo "=================================="
echo "✅ Setup Complete!"
echo "=================================="
echo ""
echo "📋 Next Steps:"
echo "1. Run Zendesk scraper: source venv/bin/activate && python zendesk_scraper.py"
echo "2. Ingest data: python data_ingestion.py"
echo "3. Check service: sudo systemctl status dvsum-bot.service"
echo "4. View logs: sudo journalctl -u dvsum-bot.service -f"
echo "5. Access app: http://YOUR_EC2_IP (if Nginx setup)"
echo ""
echo "🔧 Useful Commands:"
echo "  - Restart service: sudo systemctl restart dvsum-bot.service"
echo "  - View logs: tail -f /var/log/dvsum-bot/output.log"
echo "  - Pull updates: cd ~/ai-support-bot && git pull"
echo ""