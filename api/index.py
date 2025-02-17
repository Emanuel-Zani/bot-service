import os
import requests
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from flask import Flask, request, jsonify
from telegram import Bot, Update

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Configure LangChain with GPT-3.5
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3, openai_api_key=OPENAI_API_KEY)

# Initialize Flask app and Telegram bot
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

# Extract expense details using GPT-3.5
def extract_expense_details(text):
    system_prompt = """You are an expert assistant for processing personal expenses. 
    Analyze the message and classify it into one of three categories:
    1. Expense-related: Extract the description, amount, and category.
    2. Ambiguous: The message suggests an expense but lacks key details.
    3. Irrelevant: The message is not related to expenses.

    If the message is irrelevant, return {"valid": false, "type": "irrelevant"}.
    If the message is ambiguous, return {"valid": false, "type": "ambiguous"}.
    If the message is valid, return the extracted details.

    Valid categories: Housing, Transportation, Food, Utilities, 
    Insurance, Medical/Healthcare, Savings, Debt, Education, Entertainment, Other.

    Example: "Lunch 15 dollars" → {"valid": true, "description": "Lunch", "amount": 15, "category": "Food"}
    Example: "Bought a new phone" → {"valid": true, "description": "New phone", "amount": null, "category": "Other"}
    Example: "Hello, how are you?" → {"valid": false, "type": "irrelevant"}
    Example: "I spent money" → {"valid": false, "type": "ambiguous"}
    """

    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=f"Process this message: {text}")])
    
    try:
        expense_data = json.loads(response.content)
        valid_categories = {
            "Housing", "Transportation", "Food", "Utilities", "Insurance",
            "Medical/Healthcare", "Savings", "Debt", "Education", "Entertainment", "Other"
        }

        if isinstance(expense_data, dict) and "valid" in expense_data:
            if expense_data["valid"]:
                if expense_data["category"] not in valid_categories:
                    expense_data["category"] = "Other"
            return expense_data
    except json.JSONDecodeError:
        pass

    return {"valid": False}

# Check if the user is in the whitelist
def is_user_whitelisted(telegram_id):
    url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}"
    headers = {"apikey": SUPABASE_API_KEY, "Authorization": f"Bearer {SUPABASE_API_KEY}"}
    response = requests.get(url, headers=headers)
    
    return response.status_code == 200 and len(response.json()) > 0

# Register user in the database
def register_user(telegram_id, user_id):
    url = f"{SUPABASE_URL}/rest/v1/users"
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    user_data = {
        "telegram_id": telegram_id,
        "user_id": user_id
    }

    response = requests.post(url, json=user_data, headers=headers)
    return response.status_code == 201

# Save expense to Supabase
def save_to_database(expense):
    url = f"{SUPABASE_URL}/rest/v1/expenses"
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    expense["added_at"] = "now()"
    response = requests.post(url, json=expense, headers=headers)

    return response.status_code == 201

# Ask user to register if not whitelisted
def ask_to_register(telegram_id, user_id):
    return {
        "message": "It seems you're not registered. Would you like to register to add your expenses to our database? Reply 'Yes' to register.",
        "status": "ask_for_confirmation"
    }

# Handle the incoming webhook message
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    update = Update.de_json(data, bot)

    telegram_id = str(update.message.from_user.id)
    user_id = telegram_id
    text = update.message.text

    if not text:
        update.message.reply_text("⚠️ Please provide a valid message.")
        return 'ok'

    if not is_user_whitelisted(telegram_id):
        # Ask if the user wants to be registered
        registration_response = ask_to_register(telegram_id, user_id)
        update.message.reply_text(registration_response["message"])
        return 'ok'

    # If user is whitelisted, process the expense
    expense_details = extract_expense_details(text)
    
    if not expense_details["valid"]:
        if expense_details.get("type") == "irrelevant":
            update.message.reply_text("This message is not related to expenses.")
            return 'ok'
        elif expense_details.get("type") == "ambiguous":
            update.message.reply_text("Please provide more details about your expense.")
            return 'ok'
        update.message.reply_text("This message does not seem to be a valid expense.")
        return 'ok'

    category = expense_details["category"]

    expense = {
        "user_id": user_id,
        "description": expense_details["description"],
        "amount": expense_details["amount"],
        "category": category
    }

    # Save to the database
    if not save_to_database(expense):
        update.message.reply_text("Failed to save expense.")
        return 'ok'

    response_message = f"{category} expense added ✅"
    update.message.reply_text(response_message)

    return 'ok'

# Set up the webhook
def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    webhook_url = "https://your-server-url/webhook"  # Replace with your actual server URL
    payload = {"url": webhook_url}
    response = requests.post(url, data=payload)
    
    if response.status_code == 200:
        print("Webhook set successfully!")
    else:
        print("Failed to set webhook", response.status_code, response.text)

if __name__ == "__main__":
    set_webhook()
    app.run(debug=True, host="0.0.0.0", port=5000)
