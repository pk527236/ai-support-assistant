import json
import os

def convert_teams_chat_to_training_data(teams_json_file, output_file):
    """
    Convert Teams chat JSON to a formatted text file for training
    
    Expected Teams JSON format:
    [
        {"sender": "John", "timestamp": "2024-01-01", "content": "How do I..."},
        {"sender": "Support", "timestamp": "2024-01-01", "content": "You can..."}
    ]
    """
    
    with open(teams_json_file, 'r', encoding='utf-8') as f:
        chats = json.load(f)
    
    formatted_text = "# Customer Support Chat History\n\n"
    
    for chat in chats:
        sender = chat.get('sender', 'Unknown')
        content = chat.get('content', '')
        timestamp = chat.get('timestamp', '')
        
        formatted_text += f"**{sender}** ({timestamp}):\n{content}\n\n---\n\n"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(formatted_text)
    
    print(f"✅ Converted {len(chats)} messages to {output_file}")

# Example usage
if __name__ == "__main__":
    # Place your Teams export JSON in the data folder
    # convert_teams_chat_to_training_data('data/teams_export.json', 'data/formatted_chats.txt')
    pass