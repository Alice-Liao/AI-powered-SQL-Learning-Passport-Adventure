from django.shortcuts import render, redirect
from .models import Users, Task, QueryHistory, ErrorsRecord, Progress, TaskStatus, Admins
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import SignUpForm, LoginForm, InstructorSignUpForm
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password
from django.db import models
from .models import Users, Admins

def home(request):
    return render(request, "app/home.html")

def testusers(request):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    context = {"data": rows}
    return render(request, "app/testusers.html", context)

@login_required(login_url='login')
def user_page(request):
    try:
        current_user_email = request.user.email
        user_record = Users.objects.get(email=current_user_email)
        user_id = user_record.user_id

        query_history = QueryHistory.objects.filter(user_id=user_id).order_by('-date')
        error_history = ErrorsRecord.objects.filter(user_id=user_id).order_by('-date')

        try:
            user_progress = Progress.objects.get(user_id=user_id)
        except Progress.DoesNotExist:
            user_progress = None

        task_statuses = TaskStatus.objects.filter(user_id=user_id).select_related('task')
        status_dict = {status.task_id: {'status': status.status, 'date': status.date} for status in task_statuses}

        tasks = Task.objects.all().select_related('cid')

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

        selected_time = request.GET.get('timeSlot', 'all')
        selected_diff = request.GET.get('difficultyLevel', 'all')
        selected_statuses = request.GET.getlist('completionStatus')
        selected_errors = request.GET.get('errorHistory')

        if selected_time != 'all':
            days = int(selected_time)
            cutoff_date = timezone.now().date() - timezone.timedelta(days=days)
            query_history = query_history.filter(date__gte=cutoff_date)
            error_history = error_history.filter(date__gte=cutoff_date)

        error_counts = ErrorsRecord.objects.filter(user_id=user_id).values('task_id').annotate(error_count=models.Count('error_id'))
        error_dict = {item['task_id']: item['error_count'] for item in error_counts}

        if selected_diff != 'all':
            tasks = tasks.filter(difficulty=int(selected_diff))

        tasks = list(tasks)
        for task in tasks:
            status_info = status_dict.get(task.tid, {'status': 0, 'date': None})
            task.status = status_info['status']
            task.start_date = status_info['date']
            task.error_count = error_dict.get(task.tid, 0)

        if selected_statuses:
            status_values = [int(status) for status in selected_statuses]
            tasks = [task for task in tasks if task.status in status_values]

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
                user = form.save()
                Progress.objects.create(
                    user_id=Users.objects.get(email=user.email).user_id,
                    progress_percentage=0
                )
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
                    return redirect(next_page or 'app-user-page')
                else:
                    messages.error(request, 'Invalid email or password.')
            except Users.DoesNotExist:
                messages.error(request, 'No account found with this email address.')
    else:
        form = LoginForm()

    return render(request, 'app/login.html', {'form': form})

@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect('login')
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
        # Get the current user's email and Users instance
        current_user = request.user
        db_user = Users.objects.get(email=current_user.email)
        
        # Determine if the user is an instructor
        is_admin = Admins.objects.filter(user=db_user).exists()
        role = "Instructor" if is_admin else "Student"

        if request.method == "POST":
            prompt = request.POST.get("message", "").strip()
            if prompt:
                # Add user message to chat history
                chat_history.append({
                    "content": prompt,
                    "is_user": True,
                    "timestamp": datetime.now().strftime("%I:%M %p")
                })

                try:
                    # Generate and execute SQL
                    sql = generate_sql_from_prompt(prompt, is_admin=is_admin)
                    
                    with connection.cursor() as cursor:
                        cursor.execute(sql)
                        if sql.strip().lower().startswith("select"):
                            rows = cursor.fetchall()
                            formatted = "\n".join([str(row) for row in rows]) or "No results."
                        else:
                            formatted = "✅ SQL executed successfully."

                    # Add response to chat history
                    chat_history.append({
                        "content": f"SQL:\n{sql}\n\nResult:\n{formatted}",
                        "is_user": False,
                        "timestamp": datetime.now().strftime("%I:%M %p")
                    })

                except Exception as e:
                    # Add error message to chat history
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
            # 调用 LLM 生成 SQL
            sql = generate_sql_from_prompt(prompt, is_admin=is_admin)

            # 执行 SQL 查询
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
