from django.shortcuts import render, redirect
from .models import Users, Admins, Task, QueryHistory, ErrorsRecord, Progress, TaskStatus, Countries, Places, Food, Events
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import SignUpForm, LoginForm, InstructorSignUpForm
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password
from django.db import models
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal

# Create your views here.

def home(request):
  return render(request, "app/home.html")


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
        task_name_query = request.GET.get('taskName', '').strip()

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

        # Apply task name filter if provided
        if task_name_query:
            tasks = tasks.filter(tname__icontains=task_name_query)

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

        # Calculate progress percentage
        total_tasks = Task.objects.count()
        completed_tasks = TaskStatus.objects.filter(
            user_id=user_id,
            status=2  # Completed status
        ).count()
        
        progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        
        # Update progress in database
        Progress.objects.update_or_create(
            user_id=user_id,
            defaults={
                'progress_percentage': progress_percentage
            }
        )

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
            'task_name_query': task_name_query,
            'progress_percentage': round(progress_percentage, 1),
            'completed_tasks': completed_tasks,
            'total_tasks': total_tasks,
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


def instructor_signup_view(request):
    if request.user.is_authenticated:
        return redirect('app-user-page')

    if request.method == 'POST':
        form = InstructorSignUpForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                db_user = Users.objects.get(email=user.email)
                Admins.objects.create(user=db_user)
                login(request, user)
                messages.success(request, 'Instructor account created successfully!')
                return redirect('app-user-page')
            except IntegrityError:
                messages.error(request, 'This email is already registered.')
                return render(request, 'app/signup.html', {'form': form, 'instructor': True})
            except Exception as e:
                messages.error(request, str(e))
                return render(request, 'app/signup.html', {'form': form, 'instructor': True})
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")
            return render(request, 'app/signup.html', {'form': form, 'instructor': True})
    else:
        form = InstructorSignUpForm()

    return render(request, 'app/signup.html', {'form': form, 'instructor': True})

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
                user = Users.objects.get(email=email)
                if check_password(password, user.password):
                    # Create a Django user session
                    django_user = User.objects.get_or_create(
                        username=email,
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

########################################################
# chat bot
########################################################
from django.shortcuts import render
from django.db import connection
from datetime import datetime
from .llm_utils import generate_sql_from_prompt
from .models import Admins
from django.contrib.auth.decorators import login_required

@login_required(login_url='login')
def chat_view(request):
    chat_history = []

    try:
        # 获取当前用户信息
        current_user = request.user
        db_user = Users.objects.get(email=current_user.email)

        # 判断是否为 Instructor
        is_admin = Admins.objects.filter(user=db_user).exists()
        role = "Instructor" if is_admin else "Student"

        if request.method == "POST":
            prompt = request.POST.get("message", "").strip()
            if prompt:
                # 加入用户发言到聊天记录
                chat_history.append({
                    "content": prompt,
                    "is_user": True,
                    "timestamp": datetime.now().strftime("%I:%M %p")
                })

                try:
                    # ✅ 使用 LLM 生成 SQL 并执行，返回格式化结果
                    response_text = generate_sql_from_prompt(prompt, is_admin=is_admin)

                    # 加入 AI 回复到聊天记录
                    chat_history.append({
                        "content": response_text,
                        "is_user": False,
                        "timestamp": datetime.now().strftime("%I:%M %p")
                    })

                except Exception as e:
                    chat_history.append({
                        "content": f"❌ Error: {str(e)}",
                        "is_user": False,
                        "timestamp": datetime.now().strftime("%I:%M %p")
                    })

        return render(request, 'app/chat.html', {
            "chat_history": chat_history,
            "role": role
        })

    except Users.DoesNotExist:
        messages.error(request, "User profile not found.")
        return redirect("login")

    except Exception as e:
        messages.error(request, str(e))
        return render(request, 'app/chat.html', {
            "chat_history": chat_history,
            "error": str(e)
        })


########################################################
# LLM Query
########################################################

from django.shortcuts import render
from django.db import connection
from .llm_utils import generate_sql_from_prompt

def llm_query_view(request):
    sql = None
    result = None
    error = None
    prompt = ""

    if request.method == "POST":
        prompt = request.POST.get("question", "")
        is_admin = request.user.is_staff if request.user.is_authenticated else False

        try:
            sql = generate_sql_from_prompt(prompt, is_admin=is_admin)

            with connection.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchall()

        except Exception as e:
            error = str(e)

    return render(request, 'app/llm_query.html', {
        'prompt': prompt,
        'sql': sql,
        'result': result,
        'error': error
    })

    ##################################
    # Game Section
    ##################################

import json
import time
import psycopg2  # PostgreSQL client (use psycopg2 instead of mysql.connector for PostgreSQL)
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Task  # Import Task model which has the expected_result

def question_detail(request, question_id):
    question = get_object_or_404(Task, id=question_id)
    hints = question.hints.all()
    
    context = {
        'question': question.tname,
        'description': question.description,
        'expected_result': json.loads(question.expected_result),
        'difficulty': question.difficulty,
        'hint': question.hint,
    }
    
    return render(request, 'coding_game/game_page.html', context)

@login_required(login_url='login')
def execute_query(request, task_id):
    if request.method == 'POST':
        query = request.POST.get('query', '')
        try:
            # Get the task and its country
            task = Task.objects.select_related('cid').get(tid=task_id)
            country_id = task.cid.cid
            current_user = Users.objects.get(email=request.user.email)
            
            # Modify query to include country filter
            if 'WHERE' in query.upper():
                query = query.replace('WHERE', f'WHERE country_id = {country_id} AND')
            else:
                query = query + f' WHERE country_id = {country_id}'
            
            print(f"Modified query: {query}")
            
            # Record query history regardless of success
            QueryHistory.objects.create(
                user_id=current_user.user_id,
                task_id=task_id,
                query_content=query,
                date=timezone.now()
            )
            
            # Execute query safely
            with connection.cursor() as cursor:
                cursor.execute(query)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                # Convert Decimal to float
                result = []
                for row in rows:
                    row_dict = {}
                    for col, val in zip(columns, row):
                        if isinstance(val, Decimal):
                            row_dict[col] = float(val)
                        else:
                            row_dict[col] = val
                    result.append(row_dict)

            # Get expected result from task
            expected_result = task.expected_result
            
            print(f"Query result: {result}")
            print(f"Expected result: {expected_result}")
            print(f"Result type: {type(result)}")
            print(f"Expected result type: {type(expected_result)}")

            # Compare results
            success = (result == expected_result)
            print(f"Comparison result: {success}")

            if success:
                # Update task status to completed (2)
                TaskStatus.objects.update_or_create(
                    user_id=current_user.user_id,
                    task_id=task_id,
                    defaults={'status': 2, 'date': timezone.now()}
                )
                print(f"Task status updated for user {current_user.user_id}, task {task_id}")

            return JsonResponse({
                'success': success,
                'result': result,
                'redirect': '/app_dev/tasks/' if success else None
            })

        except Exception as e:
            print(f"Error executing query: {str(e)}")
            # Record error
            ErrorsRecord.objects.create(
                user_id=current_user.user_id,
                task_id=task_id,
                error_content=str(e),
                date=timezone.now()
            )
            # Record failed query
            QueryHistory.objects.create(
                user_id=current_user.user_id,
                task_id=task_id,
                query_content=query,
                date=timezone.now()
            )
            return JsonResponse({
                'success': False,
                'error': str(e),
                'redirect': '/app_dev/tasks/'  # Add redirect even for errors
            })

    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required(login_url='login')
def game_page(request, task_id):
    try:
        print(f"Attempting to fetch task with ID: {task_id}")
        task = Task.objects.select_related('cid').get(tid=task_id)
        
        # Get the expected columns from expected_result
        expected_columns = []
        if task.expected_result and len(task.expected_result) > 0:
            expected_columns = list(task.expected_result[0].keys())
        
        # Get example data based on task type
        example_data = []
        try:
            if task.task_type == 1:
                example_data = list(Places.objects.filter(country_id=task.cid.cid))
                print(f"Fetching Places data for country {task.cid.cid}")
            elif task.task_type == 2:
                example_data = list(Food.objects.filter(country_id=task.cid.cid))
                print(f"Fetching Food data for country {task.cid.cid}")
            elif task.task_type == 3:
                example_data = list(Events.objects.filter(country_id=task.cid.cid))
                print(f"Fetching Events data for country {task.cid.cid}")
                
            print(f"Example data count: {len(example_data)}")
        except Exception as e:
            print(f"Error fetching example data: {str(e)}")
            pass
        
        context = {
            'task': task,
            'example_data': example_data,
            'task_type': task.task_type,
            'expected_columns': expected_columns
        }
        print("Context prepared successfully")
        
        return render(request, 'app/game_page.html', context)
    except Task.DoesNotExist:
        print(f"Task with ID {task_id} not found")
        messages.error(request, 'Task not found.')
        return redirect('app-user-page')
    except Exception as e:
        print(f"Error in game_page view: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('app-user-page')

@login_required(login_url='login')
def task_list(request):
    try:
        # Get current user
        current_user_email = request.user.email
        user_record = Users.objects.get(email=current_user_email)
        user_id = user_record.user_id

        # Get all countries
        countries = Countries.objects.all()
        
        # Get task statuses for this user
        task_statuses = TaskStatus.objects.filter(user_id=user_id)
        completed_tasks = {status.task_id for status in task_statuses if status.status == 2}

        # Get tasks with attempts (any query history indicates an attempt)
        tasks_with_attempts = set(QueryHistory.objects.filter(
            user_id=user_id
        ).values_list('task_id', flat=True))

        # Create country-based task structure
        country_tasks = []
        for country in countries:
            # Get tasks for this country, ordered by difficulty
            tasks = Task.objects.filter(cid=country).order_by('difficulty')
            
            # Initialize country data structure
            country_data = {
                'country': country,
                'tasks': [],
                'unlocked_difficulty': 1  # Start with easy difficulty
            }
            
            # First task is always unlocked
            prev_task_completed = True
            for task in tasks:
                # Check if task is locked based on previous task completion
                is_locked = not prev_task_completed
                
                # Get task status
                status = task_statuses.filter(task_id=task.tid).first()
                task.status = status.status if status else 0
                task.is_locked = is_locked
                
                # Check if user has attempted this task
                task.has_attempts = task.tid in tasks_with_attempts
                
                country_data['tasks'].append(task)
                
                # Update completion status for next task
                prev_task_completed = task.tid in completed_tasks

            country_tasks.append(country_data)

        context = {
            'country_tasks': country_tasks,
            'user_data': user_record,
        }
        return render(request, 'DynamicPage/task_list.html', context)
    except Exception as e:
        messages.error(request, str(e))
        return redirect('app-home')
