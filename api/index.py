import os
import requests
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure LangChain with GPT-3.5
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3, openai_api_key=OPENAI_API_KEY)

# Extract expense details using GPT-3.5
def extract_expense_details(text):
    system_prompt = """You are an expert assistant for processing personal expenses. 
    Extract the description, amount, and category from an expense-related message. 
    If no valid expense is found, return {"valid": false}. 

    Example: "Lunch 15 dollars" → {"valid": true, "description": "Lunch", "amount": 15, "category": "Food"} 
    Example: "Bought a new phone" → {"valid": false} 
    """

    # Request GPT-3.5 to process the message
    response = llm.invoke([ 
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Process this message: {text}")
    ])

    try:
        expense_data = json.loads(response['content'])
        if isinstance(expense_data, dict) and "valid" in expense_data:
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

# Handler for Vercel serverless function
def handler(req, res):
    data = req.get_json()
    user_id = data.get('userId')
    telegram_id = data.get('telegramId')
    text = data.get('text')

    if not user_id or not telegram_id or not text:
        return res.json({"status": "error", "message": "Missing required fields"}), 400

    if not is_user_whitelisted(telegram_id):
        return res.json({"status": "error", "message": "User not whitelisted"}), 403

    # Extract expense details using GPT-3.5
    expense_details = extract_expense_details(text)
    
    if not expense_details["valid"]:
        return res.json({"status": "error", "message": "This message does not seem to be a valid expense."}), 400

    category = expense_details["category"]

    expense = {
        "user_id": user_id,
        "description": expense_details["description"],
        "amount": expense_details["amount"],
        "category": category
    }

    # Save to the database
    if not save_to_database(expense):
        return res.json({"status": "error", "message": "Failed to save expense"}), 500

    response_message = f"{category} expense added ✅"

    return res.json({
        "status": "success",
        "message": response_message,
        "expense": expense
    })

