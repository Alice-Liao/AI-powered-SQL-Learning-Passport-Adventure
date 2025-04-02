import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def ask_for_sql(user_prompt):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert in SQL. Please generate an SQL query based on the user's request."},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content

def main():
    print("Welcome to the SQL Generator! (Type 'exit' to quit)")
    while True:
        user_input = input("Please enter your request: ")
        if user_input.lower() == "exit":
            break
        sql_query = ask_for_sql(user_input)
        print("\nGenerated SQL query:\n")
        print(sql_query)
        print("-" * 50)

if __name__ == "__main__":
    main()
