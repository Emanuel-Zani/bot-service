# Bot Service

The Bot Service is a Telegram chatbot that helps users add expenses to a PostgreSQL database. Users can send short messages like "Pizza 20 bucks," and the bot processes these messages to extract expense details.

## Summary

This service is part of a larger system that consists of two services:

1. **Bot Service (this service):** Developed in Python, it analyzes incoming messages to identify and extract expense details before storing them in a database.
2. **Connector Service:** Built using Node.js, it serves as the interface between the Telegram API and the Bot Service.

## Features

- Recognizes a whitelist of Telegram users sourced from the database.
- Verifies incoming messages to distinguish between expense-related inputs and non-expense texts.
- Automatically categorizes expenses into predefined categories.
- Responds to users with a confirmation message upon the successful addition of an expense.

## Requirements

- **Python 3.8+**
- **Flask:** A micro web framework for Python.
- **Requests:** For making HTTP requests.
- **LangChain:** For natural language processing and expense extraction.
- **Dotenv:** For loading environment variables.

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Emanuel-Zani/bot-service.git
   cd bot-service
   ```

2. **Install dependencies:**  
   Ensure you have Python 3.8 or higher installed. Then install the required packages:
   ```bash
   pip install Flask requests langchain-openai python-dotenv
   ```

3. **Environment Variables:**  
   Create a `.env` file in the root directory of your project and add the following environment variables:
   ```plaintext
   SUPABASE_URL=<your_supabase_url>
   SUPABASE_API_KEY=<your_supabase_api_key>
   OPENAI_API_KEY=<your_openai_api_key>
   ```

4. **Run the Bot Service:**  
   You can start the service by running:
   ```bash
   python index.py
   ```
   The service will run on `http://localhost:5000`.

## How It Works

1. The bot listens for messages on the `/process-message` endpoint.
2. Upon receiving a message, it extracts expense details using the LangChain library and OpenAI's GPT-3.5 model.
3. Valid expense messages are saved to the PostgreSQL database, and the bot sends a confirmation message back to the user.

## Database Schema

### Users Table
```sql
CREATE TABLE users (
  "id" SERIAL PRIMARY KEY,
  "telegram_id" text UNIQUE NOT NULL
);
```

### Expenses Table
```sql
CREATE TABLE expenses (
  "id" SERIAL PRIMARY KEY,
  "user_id" integer NOT NULL REFERENCES users("id"),
  "description" text NOT NULL,
  "amount" money NOT NULL,
  "category" text NOT NULL,
  "added_at" timestamp NOT NULL
);
```
