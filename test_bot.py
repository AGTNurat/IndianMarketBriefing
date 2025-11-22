import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

def get_chat_id():
    """Fetches the latest chat ID from updates."""
    try:
        response = requests.get(f"{BASE_URL}/getUpdates")
        response.raise_for_status()
        data = response.json()
        
        if not data.get("ok"):
            print(f"Error: {data.get('description')}")
            return None
            
        results = data.get("result", [])
        if not results:
            print("No updates found. Please send a message to the bot first.")
            return None
            
        # Get the chat ID from the last message
        last_update = results[-1]
        if "message" in last_update:
            return last_update["message"]["chat"]["id"]
        elif "my_chat_member" in last_update:
             return last_update["my_chat_member"]["chat"]["id"]
        else:
            print("Could not determine chat ID from the last update.")
            return None

    except Exception as e:
        print(f"Error fetching updates: {e}")
        return None

def send_message(chat_id, text):
    """Sends a message to the specified chat ID."""
    try:
        payload = {"chat_id": chat_id, "text": text}
        response = requests.post(f"{BASE_URL}/sendMessage", json=payload)
        response.raise_for_status()
        print("Message sent successfully!")
    except Exception as e:
        print(f"Error sending message: {e}")

if __name__ == "__main__":
    if not TOKEN:
        print("Error: TELEGRAM_TOKEN not found in .env file.")
    else:
        print("Checking for updates...")
        chat_id = get_chat_id()
        if chat_id:
            print(f"Found Chat ID: {chat_id}")
            send_message(chat_id, "System Online: Quant Sentinel Ready")
        else:
            print("\nTo fix this:")
            print("1. Open your bot in Telegram.")
            print("2. Send a message (e.g., 'Hello').")
            print("3. Run this script again.")
