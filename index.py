import os
import requests
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from flask import Flask, request, jsonify

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure LangChain with GPT-3.5
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3, openai_api_key=OPENAI_API_KEY)

app = Flask(__name__)

# Feature to extract expense details with GPT
def extract_expense_details(text):
    system_prompt = """You are an expert assistant for processing personal expenses... (MISMA DESCRIPCIÓN)"""

    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=f"Process this message: {text}")])

    try:
        expense_data = json.loads(response.content)
        valid_categories = {"Housing", "Transportation", "Food", "Utilities", "Insurance", "Medical/Healthcare", "Savings", "Debt", "Education", "Entertainment", "Other"}

        if isinstance(expense_data, dict) and "valid" in expense_data:
            if expense_data["valid"]:
                if expense_data["category"] not in valid_categories:
                    expense_data["category"] = "Other"
            return expense_data
    except json.JSONDecodeError:
        pass

    return {"valid": False}

# Save the expense in the database
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

@app.route('/process-message', methods=['POST'])
def process_message():
    data = request.json
    user_id = data.get('userId') 
    text = data.get('text')

    if not user_id or not text:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    # Extract expense details with GPT
    expense_details = extract_expense_details(text)

    if not expense_details["valid"]:
        return jsonify({
            "status": "error",
            "message": "Invalid expense message",
            "reason": expense_details.get("type", "unknown")
        }), 400

    category = expense_details["category"]

    expense = {
        "user_id": user_id,
        "description": expense_details["description"],
        "amount": expense_details["amount"],
        "category": category
    }
    
    # Save to database
    if not save_to_database(expense):
        return jsonify({"status": "error", "message": "Failed to save expense"}), 500

    return jsonify({
        "status": "success",
        "message": f"{category} expense added ✅",
        "expense": expense
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
