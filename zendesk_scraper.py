"""
Zendesk Help Center Scraper with Selenium
Scrapes articles from DVSum Zendesk help center using browser automation
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import time
import os
import re
from urllib.parse import urljoin

class ZendeskSeleniumScraper:
    def __init__(self, base_url, headless=True):
        self.base_url = base_url
        self.articles = []
        self.visited_urls = set()
        self.driver = None
        self.headless = headless
        
    def setup_driver(self):
        """Setup Selenium Chrome driver with options"""
        print("🔧 Setting up Chrome driver...")
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")  # Run in background
        
        # Anti-detection options
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Disable automation flags
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # Auto-install ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("✅ Chrome driver ready!")
            return True
        except Exception as e:
            print(f"❌ Failed to setup driver: {e}")
            return False
    
    def get_page(self, url, wait_time=10):
        """Load a page and wait for it to render"""
        try:
            print(f"🌐 Loading: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for dynamic content
            time.sleep(2)
            
            return True
        except Exception as e:
            print(f"⚠️ Error loading {url}: {e}")
            return False
    
    def get_all_categories(self):
        """Get all category URLs from the help center"""
        print(f"🔍 Fetching categories from {self.base_url}...")
        
        if not self.get_page(self.base_url):
            return []
        
        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        categories = []
        
        # Find all category/section links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/categories/' in href or '/sections/' in href:
                full_url = urljoin(self.base_url, href)
                if full_url not in categories:
                    categories.append(full_url)
        
        print(f"✅ Found {len(categories)} categories/sections")
        return categories
    
    def get_articles_from_category(self, category_url):
        """Get all article URLs from a category page"""
        print(f"📂 Fetching articles from: {category_url}")
        
        if not self.get_page(category_url):
            return []
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        article_urls = []
        
        # Find all article links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/articles/' in href:
                full_url = urljoin(self.base_url, href)
                if full_url not in self.visited_urls:
                    article_urls.append(full_url)
                    self.visited_urls.add(full_url)
        
        print(f"   Found {len(article_urls)} articles")
        return article_urls
    
    def scrape_article(self, article_url):
        """Scrape content from a single article"""
        print(f"📄 Scraping: {article_url}")
        
        if not self.get_page(article_url):
            return None
        
        try:
            # Wait for article content to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract title
            title = soup.find('h1')
            title_text = title.get_text(strip=True) if title else "No Title"
            
            # Try multiple content selectors
            content = None
            content_selectors = [
                {'class': 'article-body'},
                {'class': 'article-content'},
                {'class': 'article__body'},
                {'id': 'article-body'},
                'article',
                'main'
            ]
            
            for selector in content_selectors:
                if isinstance(selector, dict):
                    content = soup.find(**selector)
                else:
                    content = soup.find(selector)
                if content:
                    break
            
            if not content:
                print(f"⚠️ Could not find content for {article_url}")
                return None
            
            # Clean the content
            for element in content(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            # Extract text
            content_text = content.get_text(separator='\n', strip=True)
            
            # Clean up whitespace
            content_text = re.sub(r'\n\s*\n', '\n\n', content_text)
            content_text = re.sub(r' +', ' ', content_text)
            
            article_data = {
                'title': title_text,
                'url': article_url,
                'content': content_text,
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            print(f"✅ Scraped: {title_text[:60]}...")
            return article_data
            
        except Exception as e:
            print(f"❌ Error scraping {article_url}: {e}")
            return None
    
    def scrape_all(self):
        """Main method to scrape all articles"""
        print("="*80)
        print("🚀 Starting Selenium-based Zendesk scraper...")
        print("="*80)
        
        # Setup driver
        if not self.setup_driver():
            print("❌ Failed to initialize browser. Please install Chrome/Chromium.")
            print("\n🔧 Install Chrome:")
            print("   Ubuntu/Debian: sudo apt-get install chromium-browser")
            print("   Or download from: https://www.google.com/chrome/")
            return []
        
        try:
            # Get all categories
            categories = self.get_all_categories()
            
            if not categories:
                print("⚠️ No categories found. Trying to find articles directly...")
                if self.get_page(self.base_url):
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    for link in soup.find_all('a', href=True):
                        if '/articles/' in link['href']:
                            full_url = urljoin(self.base_url, link['href'])
                            if full_url not in self.visited_urls:
                                categories.append(full_url)
                                self.visited_urls.add(full_url)
            
            if not categories:
                print("❌ No articles found. The site structure may be different.")
                print("💡 Try visiting the site manually to check if it's accessible.")
                return []
            
            # Get articles from each category
            all_article_urls = []
            for category_url in categories:
                if '/articles/' in category_url:
                    # It's already an article URL
                    all_article_urls.append(category_url)
                else:
                    # It's a category, get articles from it
                    article_urls = self.get_articles_from_category(category_url)
                    all_article_urls.extend(article_urls)
                time.sleep(1)  # Be polite
            
            print(f"\n📊 Found {len(all_article_urls)} unique articles to scrape")
            
            if not all_article_urls:
                return []
            
            # Scrape each article
            for i, article_url in enumerate(all_article_urls, 1):
                print(f"\n[{i}/{len(all_article_urls)}]", end=" ")
                article_data = self.scrape_article(article_url)
                if article_data:
                    self.articles.append(article_data)
                time.sleep(1.5)  # Be polite
            
            print(f"\n\n✅ Successfully scraped {len(self.articles)} articles")
            return self.articles
            
        finally:
            # Always close the browser
            if self.driver:
                print("\n🔒 Closing browser...")
                self.driver.quit()
    
    def save_articles(self, output_dir='./data'):
        """Save scraped articles to files"""
        if not self.articles:
            print("⚠️ No articles to save!")
            return
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Save as JSON
        json_file = os.path.join(output_dir, 'zendesk_articles.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved JSON to: {json_file}")
        
        # Save as text file (better for RAG/training)
        txt_file = os.path.join(output_dir, 'zendesk_knowledge_base.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            for article in self.articles:
                f.write(f"{'='*80}\n")
                f.write(f"TITLE: {article['title']}\n")
                f.write(f"URL: {article['url']}\n")
                f.write(f"{'='*80}\n\n")
                f.write(f"{article['content']}\n\n")
                f.write(f"{'-'*80}\n\n")
        print(f"💾 Saved text to: {txt_file}")
        
        # Save individual article files
        articles_dir = os.path.join(output_dir, 'zendesk_articles')
        if not os.path.exists(articles_dir):
            os.makedirs(articles_dir)
        
        for i, article in enumerate(self.articles):
            # Create safe filename
            safe_title = re.sub(r'[^\w\s-]', '', article['title'])[:50]
            filename = f"{i+1:03d}_{safe_title}.txt"
            filepath = os.path.join(articles_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Title: {article['title']}\n")
                f.write(f"URL: {article['url']}\n")
                f.write(f"{'='*80}\n\n")
                f.write(article['content'])
        
        print(f"💾 Saved {len(self.articles)} individual articles to: {articles_dir}")
        
        # Create a summary file
        summary_file = os.path.join(output_dir, 'scraping_summary.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"Zendesk Scraping Summary\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"Scraped at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total articles: {len(self.articles)}\n\n")
            f.write(f"Articles:\n")
            for i, article in enumerate(self.articles, 1):
                f.write(f"{i}. {article['title']}\n")
                f.write(f"   URL: {article['url']}\n\n")
        print(f"📋 Saved summary to: {summary_file}")


def main():
    """Main execution function"""
    ZENDESK_URL = "https://dvsum.zendesk.com/hc/en-us"
    
    print("="*80)
    print("DVSum Zendesk Knowledge Base Scraper (Selenium)")
    print("="*80)
    print("\n⚙️ Configuration:")
    print(f"   URL: {ZENDESK_URL}")
    print(f"   Mode: Headless Chrome")
    print("="*80 + "\n")
    
    # Create scraper instance
    scraper = ZendeskSeleniumScraper(ZENDESK_URL, headless=True)
    
    try:
        # Scrape all articles
        articles = scraper.scrape_all()
        
        if articles:
            # Save the articles
            scraper.save_articles()
            
            print("\n" + "="*80)
            print("✅ SCRAPING COMPLETED SUCCESSFULLY!")
            print("="*80)
            print(f"📊 Total articles scraped: {len(articles)}")
            print("\n📁 Files created:")
            print("  ✓ ./data/zendesk_articles.json")
            print("  ✓ ./data/zendesk_knowledge_base.txt")
            print("  ✓ ./data/zendesk_articles/ (individual files)")
            print("  ✓ ./data/scraping_summary.txt")
            print("\n🚀 Next steps:")
            print("  1. Review the scraped content in ./data/")
            print("  2. Run your data ingestion: python ingest_data.py")
            print("  3. Start your bot: python app.py")
            print("="*80)
        else:
            print("\n⚠️ No articles were scraped.")
            print("\n🔧 Troubleshooting:")
            print("  1. Check if the URL is correct and accessible")
            print("  2. Try running with headless=False to see the browser")
            print("  3. Check if the site requires login/authentication")
            print("  4. Verify Chrome/Chromium is installed")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Scraping interrupted by user")
        if scraper.articles:
            save = input("Save partially scraped articles? (y/n): ")
            if save.lower() == 'y':
                scraper.save_articles()
    
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 If you see Chrome-related errors, install Chrome:")
        print("   Ubuntu/Debian: sudo apt-get install chromium-browser")


if __name__ == "__main__":
    main()