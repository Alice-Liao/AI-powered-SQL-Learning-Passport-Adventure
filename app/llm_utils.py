import os
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import re

client = OpenAI()

DB_SCHEMA_DESCRIPTION = """
You are a helpful assistant that translates English into PostgreSQL SQL queries.

The database has the following tables and relationships:

users(user_id, name, email, password)  
admins(user_id) — one-to-one link to users  
traveler(user_id, progress_percentage)  
task(tid, tname, difficulty, time, hint, description, cid)  
countries(cid, cname)  
task_status(user_id, task_id, status, date)  
errors_record(error_id, user_id, task_id, error_content, date)  
query_history(query_id, user_id, task_id, query_content, date)  
login_history(login_id, user_id, login_timestamp, logout_timestamp, ip_address, login_status)  
messages(message_id, sender, receiver, message_content, timestamp)  
visa(vid, ispassed, issuedate, userid, cid)

Guidelines:
- Only return a single SQL statement. No explanation.
- Do NOT include markdown formatting (e.g., no ```sql).
- Admin users may generate SELECT and INSERT queries.
- Student users may ONLY generate SELECT queries.
- Always include WHERE or JOIN if required. Format clearly.
- End your query with a semicolon.
"""

def generate_sql_from_prompt(prompt, is_admin=False):
    role_instructions = "Assume the user is an admin." if is_admin else "Assume the user is a student."

    messages = [
        {"role": "system", "content": DB_SCHEMA_DESCRIPTION + "\n" + role_instructions},
        {"role": "user", "content": prompt}
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.2
    )

    raw_sql = response.choices[0].message.content.strip()

    sql = extract_clean_sql(raw_sql)

    if not is_admin and not sql.strip().lower().startswith("select"):
        raise ValueError("Permission denied: student users can only perform SELECT queries.")

    return sql


def extract_clean_sql(text):
    text = text.replace("```sql", "").replace("```", "").strip()
    lines = text.splitlines()
    sql_lines = [line for line in lines if not line.lower().startswith("this query") and not line.strip().startswith("--")]
    return "\n".join(sql_lines).strip()