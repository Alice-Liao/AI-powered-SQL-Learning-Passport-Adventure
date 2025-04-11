import os
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import re
from django.db import connection

client = OpenAI()

DB_SCHEMA_DESCRIPTION = """
You are a helpful assistant that translates English into PostgreSQL SQL queries.

The database has the following tables and relationships:


traveler(user_id, progress_percentage)  
task(tid, tname, difficulty, time, hint, description, cid)  
countries(cid, cname)  
task_status(user_id, task_id, status, date)  
errors_record(error_id, user_id, task_id, error_content, date)  
query_history(query_id, user_id, task_id, query_content, date)  
login_history(login_id, user_id, login_timestamp, logout_timestamp, ip_address, login_status)  
messages(message_id, sender, receiver, message_content, timestamp)  
visa(vid, ispassed, issuedate, userid, cid)
progress(progress_id, user_id, progress_percentage)
places(pid, name, city, country_id, category, visitors_per_year)
food(fid, name, type, price, country_id)
events(eid, name, month, description, city, country_id)

Table Relationships (foreign keys):
admins.user_id -> users.user_id
errors_record.task_id -> task.tid
errors_record.user_id -> users.user_id
login_history.user_id -> users.user_id
messages.sender_id -> users.user_id
messages.receiver_id -> users.user_id
progress.user_id -> users.user_id
query_history.user_id -> users.user_id
query_history.task_id -> task.tid
task.cid -> countries.cid
task_status.user_id -> users.user_id
task_status.task_id -> task.tid
traveler.user_id -> users.user_id
visa.cid -> countries.cid
visa.userid -> users.user_id
places.country_id -> countries.cid
food.country_id -> countries.cid
events.country_id -> countries.cid

Guidelines:
- Only return a single SQL statement. No explanation.
- Do NOT include markdown formatting (e.g., no ```sql).
- Admin users may generate SELECT and INSERT queries.
- Student users may ONLY generate SELECT queries.
- Always include WHERE or JOIN if required. Format clearly.
- End your query with a semicolon.
- Do NOT query the users or admins table or generate SQL involving them.
"""

def generate_sql_from_prompt(prompt, is_admin=False):
    role_instructions = "Assume the user is an admin." if is_admin else "Assume the user is a student."

    messages = [
        {"role": "system", "content": DB_SCHEMA_DESCRIPTION + "\n" + role_instructions},
        {"role": "user", "content": prompt}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.2
        )

        raw_sql = response.choices[0].message.content.strip()
        sql = extract_clean_sql(raw_sql)

        if not is_admin and not sql.strip().lower().startswith("select"):
            raise ValueError("Permission denied: student users can only perform SELECT queries.")

        try:
            with connection.cursor() as cursor:
                print("🧠 Final SQL to run:\n", sql)
                cursor.execute(sql)
                if sql.lower().startswith("select"):
                    rows = cursor.fetchall()
                    formatted_result = "\n".join(str(row) for row in rows) or "No results."
                else:
                    formatted_result = "✅ SQL executed successfully."
        except Exception as e:
            formatted_result = f"❌ Execution error: {str(e)}"

        return f"SQL:\n{sql}\n\nResult:\n{formatted_result}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def extract_clean_sql(text):
    text = text.replace("```sql", "").replace("```", "").strip()
    lines = text.splitlines()

    sql_lines = []
    for line in lines:
        clean_line = line.strip().lower()
        if not line.strip():
            continue
        if clean_line.startswith("sql:"):
            continue
        if clean_line.startswith("this query") or clean_line.startswith("--"):
            continue
        sql_lines.append(line)

    return "\n".join(sql_lines).strip()
