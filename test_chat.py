import requests
import json
from datetime import datetime

# Test ticket examples
TEST_TICKETS = {
    "s1_critical": "DATA Intelligence CADDI is down. Our production environment is completely inaccessible and users cannot generate any reports. This is blocking all our data analysis work.",
    
    "s2_important": "Our scheduled ETL jobs are stuck and not running since this morning. Users are reporting they cannot see updated data in their dashboards.",
    
    "s3_question": "How do I configure a new data source connection in DVSum DI? I need to connect to our PostgreSQL database.",
    
    "enhancement": "We would like to request a new feature in CADDI where it can automatically suggest data quality rules based on our historical data patterns and anomalies detected.",
    
    "non_dvsum_training": "I need to enroll in the DVSum certification course for data quality. Can you provide me with the training schedule?",
}

def test_ticket_handler(ticket_text, ticket_name="Test Ticket"):
    """Test the /handle-ticket endpoint"""
    
    url = "http://localhost:5000/handle-ticket"
    
    payload = {
        "ticket_text": ticket_text
    }
    
    print("=" * 100)
    print(f"🎫 TESTING: {ticket_name}")
    print("=" * 100)
    print(f"\n📝 TICKET CONTENT:\n{ticket_text}\n")
    print("-" * 100)
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if redirected
            if data.get("redirected"):
                print("\n🔀 TICKET REDIRECTED (Non-DVSum)")
                print(f"Category: {data.get('redirect_category')}")
                print(f"Redirect to: {data.get('redirect_email')}")
                print(f"\nMessage:\n{data.get('message')}")
                return
            
            # Display classification
            classification = data.get("classification", {})
            print("\n📊 CLASSIFICATION:")
            print(f"   Severity: {classification.get('severity')} - {classification.get('severity_name')}")
            print(f"   Type: {classification.get('ticket_type')} - {classification.get('ticket_type_description')}")
            print(f"   Reasoning: {classification.get('reasoning')}")
            
            # Display simple explanation
            print(f"\n💬 SIMPLE EXPLANATION:")
            print(f"   {data.get('simple_explanation')}")
            
            # Display acknowledgment
            print(f"\n✉️ ACKNOWLEDGMENT:")
            print(data.get('acknowledgment'))
            
            # Display SLA
            sla = data.get("sla", {})
            print(f"⏰ SLA:")
            print(f"   Response Time: {sla.get('response_time')}")
            print(f"   Resolution Time: {sla.get('resolution_time')}")
            
            # Display immediate solution if available
            if "immediate_solution" in data:
                solution_data = data["immediate_solution"]
                print(f"\n🔍 IMMEDIATE SOLUTION FOUND:")
                print(f"   Search Methods: {', '.join(solution_data.get('search_methods', []))}")
                print(f"\n{solution_data.get('solution')}")
                
                if solution_data.get('sources'):
                    print(f"\n📚 Sources:")
                    for source in solution_data['sources']:
                        print(f"   - {source}")
            
            # Display FR summary if enhancement
            if "fr_summary" in data:
                print(f"\n📝 FUTURE REQUEST (FR) SUMMARY:")
                print(data['fr_summary'])
            
            print(f"\n✅ Processed at: {data.get('timestamp')}")
            
        else:
            print(f"\n❌ ERROR: {response.status_code}")
            print(response.text)
    
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to bot. Make sure it's running:")
        print("   python app.py")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
    
    print("\n" + "=" * 100 + "\n")

def test_chat(question):
    """Test the /chat endpoint"""
    
    url = "http://localhost:5000/chat"
    
    payload = {
        "question": question
    }
    
    print("=" * 100)
    print("💬 TESTING CHAT ENDPOINT")
    print("=" * 100)
    print(f"\nQuestion: {question}\n")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Answer:\n{data.get('answer')}")
            print(f"\nSearch Methods: {', '.join(data.get('search_methods_used', []))}")
            
            if data.get('sources'):
                print(f"\nSources:")
                for source in data['sources']:
                    print(f"  - {source[:100]}...")
        else:
            print(f"ERROR: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        print(f"ERROR: {e}")
    
    print("\n" + "=" * 100 + "\n")

def check_health():
    """Check bot health status"""
    
    url = "http://localhost:5000/health"
    
    print("=" * 100)
    print("🏥 HEALTH CHECK")
    print("=" * 100)
    
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nStatus: {data.get('status').upper()}")
            print(f"Agent Mode: {data.get('agent_mode')}")
            print(f"LLM: {data.get('llm')}")
            
            search_methods = data.get('search_methods', {})
            print(f"\nSearch Methods:")
            
            keyword_search = search_methods.get('keyword_search', {})
            print(f"  Keyword Search: {'✅ Enabled' if keyword_search.get('enabled') else '❌ Disabled'}")
            if keyword_search.get('enabled'):
                print(f"    Articles: {keyword_search.get('articles_count')}")
            
            semantic_search = search_methods.get('semantic_search', {})
            print(f"  Semantic Search: {'✅ Enabled' if semantic_search.get('enabled') else '❌ Disabled'}")
            
            print(f"\nCapabilities:")
            for capability in data.get('capabilities', []):
                print(f"  ✓ {capability}")
        else:
            print(f"ERROR: {response.status_code}")
    
    except Exception as e:
        print(f"ERROR: {e}")
        print("\nMake sure the bot is running: python app.py")
    
    print("\n" + "=" * 100 + "\n")

def main():
    """Main test runner"""
    
    print("\n" + "=" * 100)
    print("🤖 DVSUM AI SUPPORT BOT - TEST SUITE")
    print("=" * 100)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100 + "\n")
    
    # Check health first
    check_health()
    
    input("Press Enter to start testing tickets...")
    
    # Test each ticket type
    print("\n" + "🔥" * 50)
    print("TEST 1: S1 CRITICAL INCIDENT - CADDI DOWN")
    print("🔥" * 50 + "\n")
    test_ticket_handler(TEST_TICKETS["s1_critical"], "S1 Critical - CADDI Down")
    
    input("Press Enter for next test...")
    
    print("\n" + "⚠️" * 50)
    print("TEST 2: S2 IMPORTANT INCIDENT - JOBS STUCK")
    print("⚠️" * 50 + "\n")
    test_ticket_handler(TEST_TICKETS["s2_important"], "S2 Important - Jobs Stuck")
    
    input("Press Enter for next test...")
    
    print("\n" + "❓" * 50)
    print("TEST 3: S3 REGULAR - CONFIGURATION QUESTION")
    print("❓" * 50 + "\n")
    test_ticket_handler(TEST_TICKETS["s3_question"], "S3 Question - Data Source Config")
    
    input("Press Enter for next test...")
    
    print("\n" + "💡" * 50)
    print("TEST 4: ENHANCEMENT REQUEST")
    print("💡" * 50 + "\n")
    test_ticket_handler(TEST_TICKETS["enhancement"], "Enhancement - Auto Rule Suggestions")
    
    input("Press Enter for next test...")
    
    print("\n" + "🔀" * 50)
    print("TEST 5: NON-DVSUM TICKET (Should Redirect)")
    print("🔀" * 50 + "\n")
    test_ticket_handler(TEST_TICKETS["non_dvsum_training"], "Non-DVSum - Training Request")
    
    input("Press Enter to test chat endpoint...")
    
    # Test chat endpoint
    test_chat("How do I create a data quality rule in DVSum?")
    
    print("\n" + "=" * 100)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 100 + "\n")

if __name__ == "__main__":
    main()