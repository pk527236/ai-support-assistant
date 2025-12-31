import requests
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class FreshserviceClient:
    def __init__(self):
        self.domain = os.getenv('FRESHSERVICE_DOMAIN')  # e.g., yourcompany.freshservice.com
        self.api_key = os.getenv('FRESHSERVICE_API_KEY')
        self.base_url = f"https://{self.domain}/api/v2"
        self.auth = (self.api_key, 'X')
    
    def create_ticket(self, subject, description, email, priority=1, status=2):
        """
        Create a new ticket in Freshservice
        
        priority: 1=Low, 2=Medium, 3=High, 4=Urgent
        status: 2=Open, 3=Pending, 4=Resolved, 5=Closed
        """
        
        url = f"{self.base_url}/tickets"
        
        payload = {
            "subject": subject,
            "description": description,
            "email": email,
            "priority": priority,
            "status": status,
            "source": 2  # Portal
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, json=payload, auth=self.auth, headers=headers)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Error creating ticket: {e}")
            return None
    
    def add_note_to_ticket(self, ticket_id, note_text, private=True):
        """Add a note/reply to an existing ticket"""
        
        url = f"{self.base_url}/tickets/{ticket_id}/notes"
        
        payload = {
            "body": note_text,
            "private": private
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, json=payload, auth=self.auth, headers=headers)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Error adding note: {e}")
            return None
    
    def get_ticket(self, ticket_id):
        """Retrieve ticket details"""
        
        url = f"{self.base_url}/tickets/{ticket_id}"
        
        try:
            response = requests.get(url, auth=self.auth)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving ticket: {e}")
            return None