from django.shortcuts import render, redirect

from .models import Users, Admins, Task, QueryHistory, ErrorsRecord, Progress, TaskStatus, MbRecord, Countries, Places, Food, Events, Messages

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
import json
from datetime import datetime
from .llm_utils import generate_sql_from_prompt

# Create your views here.

def home(request):
  return render(request, "app/home.html")


@login_required(login_url='login')
def user_page(request):
    try:
        current_user_email = request.user.email
        user_record = Users.objects.get(email=current_user_email)
        user_id = user_record.user_id

        # Check if user is an instructor
        is_instructor = Admins.objects.filter(user=user_record).exists()
        if is_instructor:
            return redirect('instructor-dashboard')

        # Get user's query and error history
        query_history = QueryHistory.objects.filter(user_id=user_id).order_by('-date')
        error_history = ErrorsRecord.objects.filter(user_id=user_id).order_by('-date')

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

        # Get task statuses for this user
        task_statuses = TaskStatus.objects.filter(user_id=user_id)
        completed_tasks = {status.task_id for status in task_statuses if status.status == 2}

        # Get tasks with attempts
        tasks_with_attempts = set(QueryHistory.objects.filter(
            user_id=user_id
        ).values_list('task_id', flat=True))

        # Get all tasks and organize by difficulty
        tasks = Task.objects.all().order_by('difficulty')

        # Apply time slot filter
        if selected_time != 'all':
            days = int(selected_time)
            cutoff_date = timezone.now().date() - timezone.timedelta(days=days)
            # Filter tasks based on query and error history within the time slot
            task_ids_with_activity = set(query_history.filter(date__gte=cutoff_date).values_list('task_id', flat=True)) | \
                                     set(error_history.filter(date__gte=cutoff_date).values_list('task_id', flat=True))
            tasks = tasks.filter(tid__in=task_ids_with_activity)

        # Apply other filters
        if selected_diff != 'all':
            tasks = tasks.filter(difficulty=selected_diff)

        if selected_statuses:
            tasks = tasks.filter(tid__in=[status.task_id for status in task_statuses if status.status in map(int, selected_statuses)])

        if selected_errors == 'true':
            # Use distinct to ensure each task appears only once
            tasks = tasks.filter(errorsrecord__user_id=user_id).distinct()

        if task_name_query:
            tasks = tasks.filter(tname__icontains=task_name_query)

        # Get all countries
        countries = Countries.objects.all()

        # Create country-based task structure
        tasks_list = []
        for country in countries:
            country_tasks = Task.objects.filter(cid=country).order_by('difficulty')
            
            prev_task_completed = True
            for task in country_tasks:
                # Check if task is locked
                is_locked = not prev_task_completed
                
                # Get task status
                status = task_statuses.filter(task_id=task.tid).first()
                
                # Set task status
                if task.tid in completed_tasks:
                    task.status = 2  # Completed
                elif task.tid in tasks_with_attempts:
                    task.status = 1  # In Progress
                else:
                    task.status = 0  # Not Started
                
                task.is_locked = is_locked
                task.has_attempts = task.tid in tasks_with_attempts
                
                # Update completion status for next task
                prev_task_completed = task.tid in completed_tasks
                
                tasks_list.append(task)

        # Calculate progress percentage
        total_tasks = Task.objects.count()
        completed_tasks_count = len(completed_tasks)
        progress_percentage = (completed_tasks_count / total_tasks * 100) if total_tasks > 0 else 0

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
            'tasks': tasks_list,
            'progress_percentage': round(progress_percentage, 1),
            'completed_tasks': completed_tasks_count,
            'total_tasks': total_tasks,
            'task_name_query': task_name_query,
            'time_slots': time_slots,
            'difficulty_levels': difficulty_levels,
            'completion_statuses': completion_statuses,
            'selected_time': selected_time,
            'selected_diff': selected_diff,
            'selected_statuses': selected_statuses,
            'selected_errors': selected_errors,
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
                
                # Create initial progress record
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
                messages.error(request, f'An error occurred: {str(e)}')
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
                login(request, user)
                messages.success(request, 'Instructor account created successfully!')
                return redirect('app-user-page')
            except IntegrityError:
                messages.error(request, 'This email is already registered.')
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")
    else:
        form = InstructorSignUpForm()

    return render(request, 'app/signup.html', {'form': form, 'instructor': True})

def login_view(request):
    if request.user.is_authenticated:
        # Check if user is an instructor
        try:
            user_record = Users.objects.get(email=request.user.email)
            is_instructor = Admins.objects.filter(user=user_record).exists()
            if is_instructor:
                return redirect('instructor-dashboard')
            else:
                return redirect('app-user-page')
        except Users.DoesNotExist:
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
                    
                    # Check if user is an instructor
                    is_instructor = Admins.objects.filter(user=user).exists()
                    
                    next_page = request.GET.get('next')
                    if next_page:
                        return redirect(next_page)
                    elif is_instructor:
                        return redirect('instructor-dashboard')
                    else:
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
    chat_history = []

    try:
        current_user = request.user
        db_user = Users.objects.get(email=current_user.email)

        is_instructor = Admins.objects.filter(user=db_user).exists()
        role = "Instructor" if is_instructor else "Student"

        if request.method == "POST":
            prompt = request.POST.get("message", "").strip()
            if prompt:
                chat_history.append({
                    "content": prompt,
                    "is_user": True,
                    "timestamp": timezone.now().strftime("%I:%M %p")
                })

                try:
                    response_text = generate_sql_from_prompt(prompt, is_admin=is_instructor)

                    chat_history.append({
                        "content": response_text,
                        "is_user": False,
                        "timestamp": timezone.now().strftime("%I:%M %p")
                    })

                except Exception as e:
                    chat_history.append({
                        "content": f"❌ Error: {str(e)}",
                        "is_user": False,
                        "timestamp": timezone.now().strftime("%I:%M %p")
                    })

        return render(request, 'app/chat.html', {
            "chat_history": chat_history,
            "role": role,
            "is_instructor": is_instructor
        })

    except Users.DoesNotExist:
        messages.error(request, "User profile not found.")
        return redirect("login")

    except Exception as e:
        messages.error(request, str(e))
        return render(request, 'app/chat.html', {
            "chat_history": chat_history,
            "error": str(e),
            "is_instructor": False
        })

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
# LLM Query
########################################################

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

@login_required(login_url='login')
def board_view(request):
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            try:
                current_user = Users.objects.get(email=request.user.email)
                is_instructor = Admins.objects.filter(user=current_user).exists()
                MbRecord.objects.create(
                    content=content,
                    uid=current_user,
                    date=timezone.now()
                )
                messages.success(request, 'Your message has been posted!')
            except Exception as e:
                messages.error(request, 'Error posting message. Please try again.')
            return redirect('board')
    
    # Get all messages ordered by date (newest first)
    board_messages = MbRecord.objects.select_related('uid').order_by('-date')
    
    # Get current user's instructor status
    current_user = Users.objects.get(email=request.user.email)
    is_instructor = Admins.objects.filter(user=current_user).exists()
    
    return render(request, 'app/board.html', {
        'board_messages': board_messages,
        'is_instructor': is_instructor
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
        is_submit = request.POST.get('submit', 'false') == 'true'  # Check if this is a submit action
        
        try:
            # Remove semicolon from the end of query if present
            query = query.strip().rstrip(';')
            
            # Get the task and its country
            task = Task.objects.select_related('cid').get(tid=task_id)
            country_id = task.cid.cid
            current_user = Users.objects.get(email=request.user.email)
            
            # Modify query to include country filter
            if 'GROUP BY' in query.upper():
                # Insert WHERE clause before GROUP BY
                group_by_index = query.upper().find('GROUP BY')
                query = (
                    query[:group_by_index] + 
                    f' WHERE country_id = {country_id} ' +
                    query[group_by_index:]
                )
            elif 'WHERE' in query.upper():
                query = query.replace('WHERE', f'WHERE country_id = {country_id} AND')
            else:
                query = query + f' WHERE country_id = {country_id}'
            
            print(f"Modified query: {query}")
            
            # Record query history
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
            
            # Compare results
            success = (result == expected_result)
            print(f"Comparison result: {success}")

            if success and is_submit:  # Only update status if this is a submit action
                # Update task status to completed (2)
                TaskStatus.objects.update_or_create(
                    user_id=current_user.user_id,
                    task_id=task_id,
                    defaults={'status': 2, 'date': timezone.now()}
                )

            return JsonResponse({
                'success': success,
                'result': result
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
            return JsonResponse({
                'success': False,
                'error': str(e)
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
        
        # Get tasks with attempts
        tasks_with_attempts = set(QueryHistory.objects.filter(
            user_id=user_id
        ).values_list('task_id', flat=True))

        # Create country-based task structure
        country_tasks = []
        for country in countries:
            tasks = Task.objects.filter(cid=country).order_by('difficulty')
            
            country_data = {
                'country': country,
                'tasks': [],
                'unlocked_difficulty': 1
            }
            
            prev_task_completed = True
            for task in tasks:
                # Check if task is locked
                is_locked = not prev_task_completed
                
                # Get task status
                status = task_statuses.filter(task_id=task.tid).first()
                
                # Set task status
                if task.tid in completed_tasks:
                    task.status = 2  # Completed
                elif task.tid in tasks_with_attempts:
                    task.status = 1  # In Progress
                else:
                    task.status = 0  # Not Started
                
                task.is_locked = is_locked
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

@login_required(login_url='login')
def instructor_dashboard(request):
    try:
        current_user_email = request.user.email
        user_record = Users.objects.get(email=current_user_email)
        user_id = user_record.user_id

        # Verify user is an instructor
        is_instructor = Admins.objects.filter(user=user_record).exists()
        if not is_instructor:
            return redirect('app-user-page')

        # Get all students (users who are not instructors)
        students = Users.objects.filter(
            traveler__isnull=False
        ).exclude(
            admins__isnull=False
        )
        
        # Get student statistics
        student_data = []
        total_students = students.count()
        active_students = 0
        total_completed_tasks = 0
        total_tasks = Task.objects.count()
        
        for student in students:
            # Get last login time from Django User model
            try:
                last_login = User.objects.get(email=student.email).last_login
                if last_login and (timezone.now() - last_login).days < 30:
                    active_students += 1
            except User.DoesNotExist:
                last_login = None
            
            # Get number of completed tasks
            completed_tasks = TaskStatus.objects.filter(
                user_id=student.user_id,
                status=2
            ).count()
            total_completed_tasks += completed_tasks
            
            # Calculate progress percentage
            progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            student_data.append({
                'name': student.name,
                'email': student.email,
                'last_login': last_login,
                'completed_tasks': completed_tasks,
                'progress_percentage': round(progress_percentage, 1)
            })

        # Calculate average progress
        average_progress = (total_completed_tasks / (total_students * total_tasks * 100)) if total_students > 0 else 0

        # Get task statistics
        tasks = Task.objects.all()
        task_stats = []
        for task in tasks:
            completed_count = TaskStatus.objects.filter(
                task_id=task.tid,
                status=2
            ).count()
            in_progress_count = TaskStatus.objects.filter(
                task_id=task.tid,
                status=1
            ).count()
            not_started_count = total_students - completed_count - in_progress_count
            
            task_stats.append({
                'name': task.tname,
                'difficulty': task.difficulty,
                'completed': completed_count,
                'in_progress': in_progress_count,
                'not_started': not_started_count
            })

        context = {
            'user_data': user_record,
            'total_students': total_students,
            'active_students': active_students,
            'average_progress': round(average_progress, 2),
            'total_completed_tasks': total_completed_tasks,
            'student_data': student_data,
            'task_stats': task_stats,
            'total_tasks': total_tasks,
            'is_instructor': is_instructor,
        }

        return render(request, 'DynamicPage/instructor_dashboard.html', context)

    except Users.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('login')
    except Exception as e:
        if settings.DEBUG:
            raise e
        messages.error(request, 'An error occurred while loading the dashboard.')
        return render(request, 'DynamicPage/instructor_dashboard.html', {'error': str(e)})

@login_required(login_url='login')
@csrf_exempt
def send_message(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            recipient_email = data.get('recipient_email')
            message_content = data.get('message_content')
            
            if not recipient_email or not message_content:
                return JsonResponse({'success': False, 'error': 'Recipient email and message content are required'})
            
            # Get sender and recipient
            sender = Users.objects.get(email=request.user.email)
            recipient = Users.objects.get(email=recipient_email)
            
            # Verify sender is an instructor
            is_instructor = Admins.objects.filter(user=sender).exists()
            if not is_instructor:
                return JsonResponse({'success': False, 'error': 'Only instructors can send messages'})
            
            # Create message
            Messages.objects.create(
                sender=sender,
                receiver=recipient,
                message_content=message_content,
                timestamp=timezone.now()
            )
            
            return JsonResponse({'success': True})
        except Users.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Recipient not found'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required(login_url='login')
def message_inbox(request):
    try:
        current_user = Users.objects.get(email=request.user.email)
        
        # Get all messages involving the current user (both sent and received)
        all_messages = Messages.objects.filter(
            models.Q(receiver=current_user) | models.Q(sender=current_user)
        ).select_related('sender', 'receiver').order_by('timestamp')
        
        # Group messages by conversation partner (instructor)
        conversations = {}
        for message in all_messages:
            # Determine the conversation partner (the instructor)
            if message.sender == current_user:
                partner = message.receiver
            else:
                partner = message.sender
                
            if partner not in conversations:
                conversations[partner] = []
            conversations[partner].append(message)
        
        # Convert conversations dict to list and sort by latest message
        conversation_list = []
        for partner, messages in conversations.items():
            conversation_list.append({
                'instructor': partner,
                'messages': messages,
                'latest_message': messages[-1].timestamp
            })
        
        # Sort conversations by latest message timestamp, newest first
        conversation_list.sort(key=lambda x: x['latest_message'], reverse=True)
        
        context = {
            'conversations': conversation_list,
            'user_data': current_user,
            'is_instructor': False
        }
        
        return render(request, 'DynamicPage/message_inbox.html', context)
    except Users.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('login')
    except Exception as e:
        if settings.DEBUG:
            raise e
        messages.error(request, 'An error occurred while loading messages.')
        return redirect('app-user-page')

@login_required(login_url='login')
@csrf_exempt
def reply_message(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            recipient_email = data.get('recipient_email')
            message_content = data.get('message_content')
            
            if not recipient_email or not message_content:
                return JsonResponse({'success': False, 'error': 'Recipient email and message content are required'})
            
            # Get sender and recipient
            sender = Users.objects.get(email=request.user.email)
            recipient = Users.objects.get(email=recipient_email)
            
            # Check if sender is an instructor
            is_instructor = Admins.objects.filter(user=sender).exists()
            
            # If sender is an instructor, they can reply to students
            # If sender is a student, they can only reply to instructors
            if not is_instructor:
                recipient_is_instructor = Admins.objects.filter(user=recipient).exists()
                if not recipient_is_instructor:
                    return JsonResponse({'success': False, 'error': 'Students can only reply to instructors'})
            
            # Create message
            Messages.objects.create(
                sender=sender,
                receiver=recipient,
                message_content=message_content,
                timestamp=timezone.now()
            )
            
            return JsonResponse({'success': True})
        except Users.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Recipient not found'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required(login_url='login')
def instructor_message_inbox(request):
    try:
        current_user = Users.objects.get(email=request.user.email)
        
        # Verify user is an instructor
        is_instructor = Admins.objects.filter(user=current_user).exists()
        if not is_instructor:
            return redirect('app-user-page')
        
        # Get all messages involving the current instructor (both sent and received)
        all_messages = Messages.objects.filter(
            models.Q(receiver=current_user) | models.Q(sender=current_user)
        ).select_related('sender', 'receiver').order_by('timestamp')
        
        # Group messages by conversation partner (student)
        conversations = {}
        for message in all_messages:
            # Determine the conversation partner (the student)
            if message.sender == current_user:
                partner = message.receiver
            else:
                partner = message.sender
                
            if partner not in conversations:
                conversations[partner] = []
            conversations[partner].append(message)
        
        # Convert conversations dict to list and sort by latest message
        conversation_list = []
        for partner, messages in conversations.items():
            conversation_list.append({
                'student': partner,
                'messages': messages,
                'latest_message': messages[-1].timestamp
            })
        
        # Sort conversations by latest message timestamp, newest first
        conversation_list.sort(key=lambda x: x['latest_message'], reverse=True)
        
        context = {
            'conversations': conversation_list,
            'user_data': current_user,
            'is_instructor': True
        }
        
        return render(request, 'DynamicPage/instructor_message_inbox.html', context)
    except Users.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('login')
    except Exception as e:
        if settings.DEBUG:
            raise e
        messages.error(request, 'An error occurred while loading messages.')
        return redirect('instructor-dashboard')
