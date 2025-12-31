"""
SMART HYBRID SEARCH
Uses scraped articles for fast search + optionally fetches latest content
"""

import json
import os
import re
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from datetime import datetime

class SmartHybridSearch:
    def __init__(self, articles_json_path="./data/zendesk_articles.json"):
        self.articles = []
        self.articles_json_path = articles_json_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.load_articles()
    
    def load_articles(self):
        """Load the scraped articles from JSON"""
        if os.path.exists(self.articles_json_path):
            try:
                with open(self.articles_json_path, 'r', encoding='utf-8') as f:
                    self.articles = json.load(f)
                print(f"✅ Loaded {len(self.articles)} articles from scraped data")
            except Exception as e:
                print(f"⚠️ Could not load articles: {e}")
                self.articles = []
        else:
            print(f"⚠️ Articles file not found: {self.articles_json_path}")
            self.articles = []
    
    def calculate_relevance_score(self, query: str, article: Dict) -> float:
        """Calculate how relevant an article is to the query"""
        query_lower = query.lower()
        title_lower = article['title'].lower()
        content_lower = article['content'].lower()
        
        score = 0.0
        
        # Extract keywords from query (filter out common words)
        stop_words = {'how', 'can', 'the', 'what', 'when', 'where', 'why', 'is', 'in', 'to', 'a', 'an', 'and', 'or'}
        query_keywords = [w for w in re.findall(r'\w+', query_lower) if len(w) > 2 and w not in stop_words]
        
        if not query_keywords:
            return 0.0
        
        # Title matches (highest weight)
        title_matches = sum(1 for keyword in query_keywords if keyword in title_lower)
        score += (title_matches / len(query_keywords)) * 0.5
        
        # Content matches
        content_matches = sum(1 for keyword in query_keywords if keyword in content_lower)
        score += (content_matches / len(query_keywords)) * 0.3
        
        # Exact phrase match (bonus)
        if query_lower in title_lower:
            score += 0.3
        elif query_lower in content_lower:
            score += 0.15
        
        # Multi-word phrase proximity bonus
        if len(query_keywords) >= 2:
            # Check if keywords appear close together
            for i in range(len(query_keywords) - 1):
                word1 = query_keywords[i]
                word2 = query_keywords[i + 1]
                # Simple proximity check
                if word1 in content_lower and word2 in content_lower:
                    pos1 = content_lower.find(word1)
                    pos2 = content_lower.find(word2, pos1)
                    if 0 < pos2 - pos1 < 100:  # Within 100 chars
                        score += 0.1
                        break
        
        return min(score, 1.0)
    
    def search(self, query: str, max_results: int = 5, min_score: float = 0.1) -> List[Dict]:
        """Search through scraped articles using keyword matching"""
        if not self.articles:
            print("⚠️ No articles loaded")
            return []
        
        print(f"🔍 Searching {len(self.articles)} articles for: '{query}'")
        
        # Calculate relevance scores
        scored_articles = []
        for article in self.articles:
            score = self.calculate_relevance_score(query, article)
            if score >= min_score:
                scored_articles.append({
                    'article': article,
                    'score': score
                })
        
        # Sort by score (descending)
        scored_articles.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top results
        results = []
        for item in scored_articles[:max_results]:
            article = item['article']
            snippet = self._extract_relevant_snippet(query, article['content'])
            
            results.append({
                'title': article['title'],
                'url': article['url'],
                'snippet': snippet,
                'score': item['score'],
                'scraped_at': article.get('scraped_at', 'Unknown')
            })
        
        if results:
            print(f"✅ Found {len(results)} relevant articles")
            for i, r in enumerate(results[:3], 1):
                print(f"   {i}. {r['title'][:60]}... (score: {r['score']:.2f})")
        else:
            print(f"❌ No relevant articles found")
        
        return results
    
    def _extract_relevant_snippet(self, query: str, content: str, snippet_length: int = 300) -> str:
        """Extract a relevant snippet from content"""
        query_keywords = [w for w in re.findall(r'\w+', query.lower()) if len(w) > 3]
        content_lower = content.lower()
        
        # Find position of first keyword
        positions = []
        for keyword in query_keywords:
            pos = content_lower.find(keyword)
            if pos != -1:
                positions.append(pos)
        
        if not positions:
            return content[:snippet_length] + "..."
        
        # Get snippet around first keyword
        start_pos = max(0, min(positions) - 100)
        end_pos = min(len(content), start_pos + snippet_length)
        
        snippet = content[start_pos:end_pos]
        
        if start_pos > 0:
            snippet = "..." + snippet
        if end_pos < len(content):
            snippet = snippet + "..."
        
        return snippet.strip()
    
    def fetch_fresh_article(self, url: str) -> Optional[Dict]:
        """
        Fetch the latest version of an article from its URL
        This ensures you get up-to-date content
        """
        try:
            print(f"   📡 Fetching fresh content from: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = soup.find('h1')
            title_text = title.get_text(strip=True) if title else ""
            
            # Extract content using the structure you showed me
            content = None
            for selector in [
                {'class': 'article-body'},
                {'class': 'article-content'},
                {'id': 'article-body'},
            ]:
                content = soup.find('div', **selector) or soup.find('section', **selector)
                if content:
                    break
            
            if not content:
                content = soup.find('article') or soup.find('main')
            
            if not content:
                print(f"   ⚠️ Could not extract content")
                return None
            
            # Clean content
            for element in content(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            content_text = content.get_text(separator='\n', strip=True)
            content_text = re.sub(r'\n\s*\n', '\n\n', content_text)
            content_text = re.sub(r' +', ' ', content_text)
            
            print(f"   ✅ Fetched fresh content ({len(content_text)} chars)")
            
            return {
                'title': title_text,
                'url': url,
                'content': content_text,
                'fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_fresh': True
            }
            
        except Exception as e:
            print(f"   ⚠️ Could not fetch fresh content: {e}")
            return None
    
    def search_and_get_context(self, query: str, max_articles: int = 2, fetch_fresh: bool = False) -> Optional[str]:
        """
        Main function: Search articles and return context for LLM
        
        Args:
            query: Search query
            max_articles: Number of articles to include
            fetch_fresh: If True, fetch latest content from URLs (slower but more current)
        """
        # Search scraped articles
        results = self.search(query, max_results=max_articles * 2, min_score=0.15)
        
        if not results:
            print("❌ No relevant articles found")
            return None
        
        # Get article content
        context_articles = []
        for result in results[:max_articles]:
            # Option 1: Use scraped content (fast)
            if not fetch_fresh:
                # Find the full article in our scraped data
                article = next((a for a in self.articles if a['url'] == result['url']), None)
                if article:
                    context_articles.append(article)
            
            # Option 2: Fetch fresh content (slower but current)
            else:
                fresh_article = self.fetch_fresh_article(result['url'])
                if fresh_article:
                    context_articles.append(fresh_article)
                else:
                    # Fallback to scraped content
                    article = next((a for a in self.articles if a['url'] == result['url']), None)
                    if article:
                        context_articles.append(article)
        
        if not context_articles:
            return None
        
        # Format context for LLM
        context = "RELEVANT INFORMATION FROM DVSUM KNOWLEDGE BASE:\n\n"
        
        for i, article in enumerate(context_articles, 1):
            context += f"Article {i}: {article['title']}\n"
            context += f"URL: {article['url']}\n"
            
            if article.get('is_fresh'):
                context += f"Status: ✨ Fresh content (fetched just now)\n"
            else:
                context += f"Scraped: {article.get('scraped_at', 'Unknown')}\n"
            
            context += f"\nContent:\n{article['content'][:3500]}\n\n"  # First 3500 chars
            context += "-" * 80 + "\n\n"
        
        return context


def is_dvsum_related(question: str) -> bool:
    """Determine if a question is related to DVSum"""
    dvsum_keywords = [
        'dvsum', 'dv sum', 'dv-sum',
        'data vault', 'datavault',
        'snowflake', 'data warehouse',
        'etl', 'data integration',
        'data pipeline', 'data modeling',
        'data load', 'source system',
        'gateway', 'scan', 'connection'
    ]
    
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in dvsum_keywords)


# Singleton
_smart_searcher = None

def get_smart_searcher():
    """Get or create singleton searcher"""
    global _smart_searcher
    if _smart_searcher is None:
        _smart_searcher = SmartHybridSearch()
    return _smart_searcher


# Test
if __name__ == "__main__":
    import sys
    
    searcher = SmartHybridSearch()
    
    if not searcher.articles:
        print("\n❌ No articles loaded!")
        print("💡 Run: python zendesk_scraper.py")
        sys.exit(1)
    
    # Test queries
    queries = [
        "how to connect to snowflake",
        "gateway installation",
        "sample data",
        "certificate validation"
    ]
    
    query = sys.argv[1] if len(sys.argv) > 1 else queries[0]
    fetch_fresh = '--fresh' in sys.argv
    
    print(f"\n{'='*80}")
    print(f"🔍 Testing search: '{query}'")
    print(f"📡 Fetch fresh: {fetch_fresh}")
    print(f"{'='*80}\n")
    
    # Get context
    context = searcher.search_and_get_context(query, max_articles=2, fetch_fresh=fetch_fresh)
    
    if context:
        print(f"\n{'='*80}")
        print("CONTEXT FOR LLM:")
        print(f"{'='*80}\n")
        print(context[:2000] + "..." if len(context) > 2000 else context)
    else:
        print("\n❌ No context generated")