import requests
import json

def test_chat(question):
    url = "http://localhost:5000/chat"
    
    payload = {
        "question": question,
        "email": "user@example.com"
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n🤖 Question: {question}")
        print(f"💬 Answer: {result['answer']}")
        print(f"📚 Sources: {len(result['sources'])} documents used")
        if result.get('suggest_ticket'):
            print("🎫 Suggestion: Create a support ticket for better assistance")
    else:
        print(f"❌ Error: {response.json()}")

if __name__ == "__main__":
    # Test questions
    test_chat("How do I reset my password?")
    test_chat("What are the system requirements?")
    test_chat("How do I troubleshoot network issues?")