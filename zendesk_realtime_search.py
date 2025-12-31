"""
Real-time Zendesk Search Module - IMPROVED VERSION
Searches DVSum Zendesk with better page structure detection
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, quote_plus

class ZendeskRealTimeSearch:
    def __init__(self, base_url="https://dvsum.zendesk.com/hc/en-us"):
        self.base_url = base_url
        self.driver = None
        self.search_cache = {}
        
    def setup_driver(self):
        """Setup Chrome driver for searching"""
        if self.driver:
            return True
            
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return True
        except Exception as e:
            print(f"❌ Failed to setup driver: {e}")
            return False
    
    def search_zendesk(self, query, max_results=3):
        """
        Search Zendesk help center for relevant articles
        Enhanced with multiple search strategies
        """
        # Check cache
        cache_key = query.lower().strip()
        if cache_key in self.search_cache:
            print(f"📦 Using cached results for: {query}")
            return self.search_cache[cache_key]
        
        if not self.setup_driver():
            return []
        
        try:
            # Strategy 1: Try Zendesk search page
            search_url = f"{self.base_url}/search?query={quote_plus(query)}"
            print(f"🔍 Searching Zendesk: {query}")
            print(f"   URL: {search_url}")
            
            self.driver.get(search_url)
            time.sleep(4)  # Give more time for page to load
            
            # Save debug HTML
            with open('/tmp/zendesk_search_debug.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print("   💾 Saved debug HTML to /tmp/zendesk_search_debug.html")
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            results = []
            
            # Try multiple selectors for Zendesk results
            selectors_to_try = [
                ('div', 'search-result'),
                ('li', 'search-result-item'),
                ('article', None),
                ('div', 'article-list-item'),
                ('li', 'article-list-item'),
                ('a', None, re.compile(r'/articles/\d+')),  # Direct article links
            ]
            
            for selector_type, class_name, href_pattern in [(s[0], s[1], s[2] if len(s) > 2 else None) for s in selectors_to_try]:
                if href_pattern:
                    items = soup.find_all(selector_type, href=href_pattern)
                elif class_name:
                    items = soup.find_all(selector_type, class_=class_name)
                else:
                    items = soup.find_all(selector_type)
                
                if items:
                    print(f"   ✓ Found {len(items)} items with selector: {selector_type}.{class_name}")
                    
                    for item in items[:max_results]:
                        try:
                            # Get title and URL
                            if selector_type == 'a':
                                title = item.get_text(strip=True)
                                url = urljoin(self.base_url, item.get('href', ''))
                            else:
                                link = item.find('a', href=re.compile(r'/articles/'))
                                if not link:
                                    link = item.find('a')
                                if not link:
                                    continue
                                
                                title = link.get_text(strip=True)
                                url = urljoin(self.base_url, link.get('href', ''))
                            
                            # Skip if no title or invalid URL
                            if not title or '/articles/' not in url:
                                continue
                            
                            # Get snippet
                            snippet = ""
                            snippet_elem = item.find('p') or item.find('div', class_=re.compile(r'description|excerpt|snippet'))
                            if snippet_elem:
                                snippet = snippet_elem.get_text(strip=True)[:200]
                            
                            if url not in [r['url'] for r in results]:
                                results.append({
                                    'title': title,
                                    'url': url,
                                    'snippet': snippet
                                })
                                print(f"   ✓ Found: {title[:60]}...")
                            
                        except Exception as e:
                            print(f"   ⚠️ Error parsing item: {e}")
                            continue
                    
                    if results:
                        break  # Found results, stop trying other selectors
            
            # Strategy 2: If no results, try using search box with Enter key
            if not results:
                print("   ⚠️ No results from URL search, trying search box...")
                try:
                    self.driver.get(self.base_url)
                    time.sleep(2)
                    
                    # Find search input
                    search_input = None
                    for selector in ['input[type="search"]', 'input[name="query"]', '#query', '.search-input']:
                        try:
                            search_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if search_input:
                                break
                        except:
                            continue
                    
                    if search_input:
                        search_input.clear()
                        search_input.send_keys(query)
                        search_input.send_keys(Keys.RETURN)
                        time.sleep(4)
                        
                        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                        
                        # Try to extract results again
                        article_links = soup.find_all('a', href=re.compile(r'/articles/\d+'))
                        for link in article_links[:max_results]:
                            title = link.get_text(strip=True)
                            url = urljoin(self.base_url, link.get('href', ''))
                            
                            if title and url not in [r['url'] for r in results]:
                                results.append({
                                    'title': title,
                                    'url': url,
                                    'snippet': ''
                                })
                                print(f"   ✓ Found via search box: {title[:60]}...")
                
                except Exception as e:
                    print(f"   ⚠️ Search box method failed: {e}")
            
            # Strategy 3: If still no results, browse categories
            if not results:
                print("   ⚠️ Trying to browse categories instead...")
                results = self._browse_categories_for_keywords(query, max_results)
            
            if results:
                print(f"✅ Found {len(results)} total results")
            else:
                print(f"❌ No results found. The site may have changed structure or requires authentication.")
            
            # Cache results
            self.search_cache[cache_key] = results
            
            return results
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _browse_categories_for_keywords(self, query, max_results):
        """Fallback: Browse main page and categories for matching articles"""
        try:
            self.driver.get(self.base_url)
            time.sleep(3)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Get all article links from main page
            article_links = soup.find_all('a', href=re.compile(r'/articles/'))
            
            results = []
            query_keywords = query.lower().split()
            
            for link in article_links:
                title = link.get_text(strip=True)
                url = urljoin(self.base_url, link.get('href', ''))
                
                # Check if any query keyword is in the title
                title_lower = title.lower()
                if any(keyword in title_lower for keyword in query_keywords):
                    if url not in [r['url'] for r in results]:
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': ''
                        })
                        print(f"   ✓ Found by category browse: {title[:60]}...")
                        
                        if len(results) >= max_results:
                            break
            
            return results
            
        except Exception as e:
            print(f"   ⚠️ Category browsing failed: {e}")
            return []
    
    def get_article_content(self, url):
        """Fetch full content from an article URL"""
        if not self.setup_driver():
            return None
        
        try:
            print(f"📄 Fetching article: {url}")
            self.driver.get(url)
            time.sleep(3)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract title
            title = soup.find('h1')
            title_text = title.get_text(strip=True) if title else ""
            
            # Extract content - try multiple selectors
            content = None
            for selector in [
                {'class': 'article-body'},
                {'class': 'article-content'},
                {'class': 'article__body'},
                {'id': 'article-body'},
            ]:
                content = soup.find('div', **selector) or soup.find('section', **selector)
                if content:
                    break
            
            if not content:
                content = soup.find('article') or soup.find('main')
            
            if not content:
                print(f"   ⚠️ Could not find content body")
                return None
            
            # Clean content
            for element in content(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            content_text = content.get_text(separator='\n', strip=True)
            content_text = re.sub(r'\n\s*\n', '\n\n', content_text)
            content_text = re.sub(r' +', ' ', content_text)
            
            return {
                'title': title_text,
                'url': url,
                'content': content_text[:4000]  # Limit to 4000 chars
            }
            
        except Exception as e:
            print(f"❌ Error fetching article: {e}")
            return None
    
    def search_and_get_context(self, query, max_articles=2):
        """
        Search Zendesk and return full context from top articles
        This is what you'll use in your AI assistant
        """
        # Search for relevant articles
        results = self.search_zendesk(query, max_results=5)
        
        if not results:
            print("❌ No search results to fetch")
            return None
        
        # Get full content from top articles
        context_articles = []
        for result in results[:max_articles]:
            article = self.get_article_content(result['url'])
            if article:
                context_articles.append(article)
                time.sleep(1)
        
        if not context_articles:
            print("❌ Could not fetch any article content")
            return None
        
        # Format context for LLM
        context = "RELEVANT INFORMATION FROM DVSUM KNOWLEDGE BASE:\n\n"
        
        for i, article in enumerate(context_articles, 1):
            context += f"Article {i}: {article['title']}\n"
            context += f"URL: {article['url']}\n"
            context += f"Content:\n{article['content']}\n\n"
            context += "-" * 80 + "\n\n"
        
        return context
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()


# Singleton instance
_searcher_instance = None

def get_zendesk_searcher():
    """Get or create singleton searcher instance"""
    global _searcher_instance
    if _searcher_instance is None:
        _searcher_instance = ZendeskRealTimeSearch()
    return _searcher_instance


def is_dvsum_related(question):
    """
    Determine if a question is related to DVSum
    """
    dvsum_keywords = [
        'dvsum',
        'dv sum',
        'dv-sum',
        'data vault',
        'datavault',
        'snowflake',
        'data warehouse',
        'etl',
        'data integration',
        'data pipeline',
        'data modeling',
        'data load',
        'source system'
    ]
    
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in dvsum_keywords)


# Test/Debug function
if __name__ == "__main__":
    import sys
    
    searcher = ZendeskRealTimeSearch()
    
    # Test search
    query = sys.argv[1] if len(sys.argv) > 1 else "snowflake connection"
    print(f"\n{'='*80}")
    print(f"🔍 Testing search for: {query}")
    print(f"{'='*80}\n")
    
    # First, just try to get search results
    results = searcher.search_zendesk(query, max_results=5)
    
    if results:
        print(f"\n✅ Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            if result['snippet']:
                print(f"   Snippet: {result['snippet'][:100]}...")
        
        # Now try to get full context
        print(f"\n{'='*80}")
        print("📄 Fetching full article content...")
        print(f"{'='*80}\n")
        
        context = searcher.search_and_get_context(query, max_articles=2)
        
        if context:
            print("\n" + "="*80)
            print("CONTEXT RETRIEVED:")
            print("="*80)
            print(context[:1500] + "..." if len(context) > 1500 else context)
        else:
            print("❌ No context retrieved")
    else:
        print("❌ No search results found")
        print("\n💡 Check the debug HTML file: /tmp/zendesk_search_debug.html")
    
    searcher.close()