from django.shortcuts import render, redirect
from .models import Users, Task, QueryHistory, ErrorsRecord, Progress, TaskStatus
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import SignUpForm, LoginForm
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password
from django.db import models
from openai import OpenAI
import os
from dotenv import load_dotenv
import sqlparse


# Create your views here.

def home(request):
  return render(request, "app/home.html")

def testusers(request):
  cursor = connection.cursor()
  cursor.execute("SELECT * FROM users")
  rows = cursor.fetchall()
  context = {
    "data": rows
  }
  return render(request, "app/testusers.html", context)



@login_required(login_url='login')
def user_page(request):
    try:
        current_user_email = request.user.email
        user_record = Users.objects.get(email=current_user_email)
        user_id = user_record.user_id

        # Get user's query and error history
        query_history = QueryHistory.objects.filter(user_id=user_id).order_by('-date')
        error_history = ErrorsRecord.objects.filter(user_id=user_id).order_by('-date')

        # Get user's progress
        try:
            user_progress = Progress.objects.get(user_id=user_id)
        except Progress.DoesNotExist:
            user_progress = None

        # Get task statuses for this user
        task_statuses = TaskStatus.objects.filter(user_id=user_id).select_related('task')
        
        # Create a dictionary of task statuses for quick lookup
        status_dict = {status.task_id: {'status': status.status, 'date': status.date} 
                      for status in task_statuses}

        # Get all tasks and annotate with status
        tasks = Task.objects.all().select_related('cid')
        
        # Define filter options
        time_slots = [
            ('all', 'All Time'),
            ('1', 'Past Day'),
            ('3', 'Past 3 Days'),
            ('7', 'Past 7 Days'),
            ('15', 'Past 15 Days'),
            ('30', 'Past 30 Days')
        ]
        
        difficulty_levels = [
            ('all', 'All Levels'),
            (1, 'Easy'),
            (2, 'Medium'),
            (3, 'Hard')
        ]
        
        completion_statuses = [
            (0, 'Not Started'),
            (1, 'In Progress'),
            (2, 'Completed'),
        ]
        
        # Get filter values from request
        selected_time = request.GET.get('timeSlot', 'all')
        selected_diff = request.GET.get('difficultyLevel', 'all')
        selected_statuses = request.GET.getlist('completionStatus')
        selected_errors = request.GET.get('errorHistory')

        # Apply filters
        if selected_time != 'all':
            days = int(selected_time)
            cutoff_date = timezone.now().date() - timezone.timedelta(days=days)
            query_history = query_history.filter(date__gte=cutoff_date)
            error_history = error_history.filter(date__gte=cutoff_date)

        # Get error counts for each task for the current user
        error_counts = ErrorsRecord.objects.filter(
            user_id=user_id  # Only count errors for current user
        ).values('task_id').annotate(
            error_count=models.Count('error_id')
        )
        
        # Create error count dictionary for quick lookup
        error_dict = {item['task_id']: item['error_count'] for item in error_counts}

        # Apply difficulty filter if selected
        if selected_diff != 'all':
            tasks = tasks.filter(difficulty=int(selected_diff))

        # Convert to list and annotate with status and error count
        tasks = list(tasks)
        for task in tasks:
            status_info = status_dict.get(task.tid, {'status': 0, 'date': None})
            task.status = status_info['status']
            task.start_date = status_info['date']
            task.error_count = error_dict.get(task.tid, 0)  # Get error count for this task

        # Apply status filter after annotation
        if selected_statuses:
            status_values = [int(status) for status in selected_statuses]
            tasks = [task for task in tasks if task.status in status_values]

        # Apply error filter - show only tasks with errors if selected
        if selected_errors == 'true':
            tasks = [task for task in tasks if task.error_count > 0]

        context = {
            'user_data': user_record,
            'query_history': query_history[:5],
            'error_history': error_history[:5],
            'user_progress': user_progress,
            'tasks': tasks,
            'time_slots': time_slots,
            'difficulty_levels': difficulty_levels,
            'completion_statuses': completion_statuses,
            'selected_statuses': selected_statuses,
        }

        return render(request, 'DynamicPage/user_page.html', context)

    except Users.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('login')
    except Exception as e:
        if settings.DEBUG:
            raise e
        messages.error(request, 'An error occurred while loading your profile.')
        return render(request, 'DynamicPage/user_page.html', {'error': str(e)})

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('app-user-page')
        
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                # Create the user and insert into your database
                user = form.save()
                
                # Create initial progress record (optional)
                Progress.objects.create(
                    user_id=Users.objects.get(email=user.email).user_id,
                    progress_percentage=0
                )
                
                # Log the user in
                login(request, user)
                messages.success(request, 'Account created successfully!')
                return redirect('app-user-page')
            except IntegrityError:
                messages.error(request, 'This email is already registered.')
            except Exception as e:
                messages.error(request, str(e))
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")
    else:
        form = SignUpForm()
    
    return render(request, 'app/signup.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('app-user-page')
        
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me')
            
            try:
                # Try to find user in your Users table
                user = Users.objects.get(email=email)
                if check_password(password, user.password):  # Check hashed password
                    # Create a Django user session
                    django_user = User.objects.get_or_create(
                        username=email,  # Use email as username
                        email=email,
                        defaults={'first_name': user.name}
                    )[0]
                    login(request, django_user)
                    
                    if not remember_me:
                        request.session.set_expiry(0)
                    
                    messages.success(request, f'Welcome back, {user.name}!')
                    
                    next_page = request.GET.get('next')
                    if next_page:
                        return redirect(next_page)
                    return redirect('app-user-page')
                else:
                    messages.error(request, 'Invalid email or password.')
            except Users.DoesNotExist:
                messages.error(request, 'No account found with this email address.')
    else:
        form = LoginForm()
    
    return render(request, 'app/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')

@login_required(login_url='login')
def chat_view(request):
    # For now, just render the template
    # Later, we'll add the OpenAI integration
    context = {
        'chat_history': []  # This will store chat messages
    }
    return render(request, 'app/chat.html', context)


@login_required(login_url='login')
def llm_view(request):
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    schema_info = \
        """
        1. users(user_id, name, email, password)  
        2. admins(user_id)
        3. traveler(user_id, progress_percentage)  
        4. task(tid, tname, difficulty, time, hint, description, cid)  
        5. countries(cid, cname)  
        6. task_status(user_id, task_id, status, date)  
        7. errors_record(error_id, user_id, task_id, error_content, date)  
        8. query_history(query_id, user_id, task_id, query_content, date)  
        9. login_history(login_id, user_id, login_timestamp, logout_timestamp, ip_address, login_status)  
        10. messages(message_id, sender_id, receiver_id, message_content, timestamp)  
        11. visa(vid, ispassed, issuedate, userid, cid)
        12. progress(progress_id, user_id, progress_percentage)

        Table Relationships (foreign keys):
        1. admins.user_id -> users.user_id
        2. errors_record.task_id -> task.tid
        3. errors_record.user_id -> users.user_id
        4. login_history.user_id -> users.user_id
        5. messages.sender_id -> users.user_id
        6. messages.receiver_id -> users.user_id
        7. progress.user_id -> users.user_id
        8. query_history.user_id -> users.user_id
        9. query_history.task_id -> task.tid
        10. task.cid -> countries.cid
        11. task_status.user_id -> users.user_id
        12. task_status.task_id -> task.tid
        13. traveler.user_id -> users.user_id
        14. visa.cid -> countries.cid
        15. visa.userid -> users.user_id
        """

    if 'chat_history' not in request.session:
        request.session['chat_history'] = []

    # clean the chat history
    if request.GET.get('clear') == 'true':
        request.session['chat_history'] = []
        return redirect('llm')

    chat_history = request.session['chat_history']

    # get current user
    current_user_email = request.user.email
    from app.models import Users
    user_record = Users.objects.get(email=current_user_email)
    # is_admin = user_record.admin  

    # system prompt with an additional rule: and user is allowed to ask only SQL-related questions.
    system_prompt = \
        f"""
        You are a PostgreSQL expert assistant. Translate natural language into PostgreSQL queries.
        If the user's query is not related to SQL, respond with:
        "❌ Error: Only the SQL-related questions are allowed. Please try again."

        {schema_info}

        RULES:
        1. Only use the tables and columns defined above.
        2. Do not return explanations.
        3. Always return valid SQL only (no markdown or comments).
        4. For data updates (INSERT/UPDATE), the user may be trying to modify real records.
        """

    def translate_to_sql(user_input):
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        )
        return response.choices[0].message.content.strip()

    if request.method == 'POST':
        user_input = request.POST.get('message')
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M')

        chat_history.append({
            'is_user': True,
            'content': user_input,
            'timestamp': timestamp
        })

        # get sqll query
        sql_query = translate_to_sql(user_input)

        result_data = []
        message = None
        formatted_sql = sqlparse.format(sql_query, reindent=True)

        if sql_query.startswith("❌ Error:"):
            message = sql_query
            formatted_sql = ""
        else:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(sql_query)

                    if sql_query.strip().lower().startswith("select"):
                        columns = [col[0] for col in cursor.description]
                        rows = cursor.fetchall()
                        result_data = [dict(zip(columns, row)) for row in rows]
                        message = f"Returned {len(rows)} rows."
                    else:
                        connection.commit()
                        message = "✅ Query executed successfully."

            except Exception as e:
                message = f"❌ Error executing SQL: {str(e)}"

        chat_history.append({
            'is_user': False,
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M'),
            'content': "",  
            'sql': formatted_sql,
            'query_result': result_data,
            'message': message
        })

        request.session['chat_history'] = chat_history
        return redirect('llm')

    return render(request, 'app/llm.html', {'llm_chat_history': chat_history})



@login_required(login_url='login')
def task_detail_view(request, task_id):
    try:
        # Get current user
        current_user_email = request.user.email
        user_record = Users.objects.get(email=current_user_email)
        user_id = user_record.user_id

        # Get task details
        task = Task.objects.select_related('cid').get(tid=task_id)
        
        # Get task status for this user
        try:
            task_status = TaskStatus.objects.get(user_id=user_id, task_id=task_id)
        except TaskStatus.DoesNotExist:
            task_status = None

        # Get all queries for this task by this user
        queries = QueryHistory.objects.filter(
            user_id=user_id,
            task_id=task_id
        ).order_by('-date')

        # Get all errors for this task by this user
        errors = ErrorsRecord.objects.filter(
            user_id=user_id,
            task_id=task_id
        ).order_by('-date')

        context = {
            'task': task,
            'task_status': task_status,
            'queries': queries,
            'errors': errors,
            'user_data': user_record,
        }

        return render(request, 'DynamicPage/task_detail.html', context)

    except Task.DoesNotExist:
        messages.error(request, 'Task not found.')
        return redirect('app-user-page')
    except Exception as e:
        if settings.DEBUG:
            raise e
        messages.error(request, 'An error occurred while loading the task details.')
        return redirect('app-user-page')