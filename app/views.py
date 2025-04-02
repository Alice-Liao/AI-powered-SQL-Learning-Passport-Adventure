from django.shortcuts import render, redirect
from .models import Users, Task, QueryHistory, ErrorsRecord, Progress
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

# def user_page(request):
#     cursor = connection.cursor()
#     cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])  # Change table name as needed
#     users = cursor.fetchone()

#     context = {
#         "users": users
#     }
#     return render(request, "app/user_page.html")

# def user_page(request):
#     try:
#         # Define the filter options
#         time_slots = [
#             ('all', 'All Time'),
#             ('1', 'Past Day'),
#             ('3', 'Past 3 Days'),
#             ('7', 'Past 7 Days'),
#             ('15', 'Past 15 Days'),
#             ('30', 'Past 30 Days')
#         ]
        
#         difficulty_levels = [
#             ('all', 'All Levels'),
#             ('easy', 'Easy'),
#             ('medium', 'Medium'),
#             ('hard', 'Hard')
#         ]
        
#         # For now, just return an empty list of tasks
#         tasks = []
        
#         context = {
#             'tasks': tasks,
#             'time_slots': time_slots,
#             'difficulty_levels': difficulty_levels,
#         }
        
#         # Try the template path without 'app/' prefix since it's in the app templates directory
#         return render(request, 'DynamicPage/user_page.html', context)
        
#     except Exception as e:
#         if settings.DEBUG:
#             # In development, show the error
#             raise e
#         return render(request, 'app/error.html', {'error': str(e)}, status=500)

@login_required(login_url='login')
def user_page(request):
    try:
        # Get the current logged-in user's email and find corresponding Users record
        current_user_email = request.user.email
        user_record = Users.objects.get(email=current_user_email)
        user_id = user_record.user_id

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
            ('easy', 'Easy'),
            ('medium', 'Medium'),
            ('hard', 'Hard')
        ]
        
        completion_statuses = [
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ]
        
        query_types = [
            ('select', 'SELECT'),
            ('union', 'UNION'),
            ('join', 'JOIN')
        ]

        # Get filter values from request
        selected_time = request.GET.get('timeSlot', 'all')
        selected_diff = request.GET.get('difficultyLevel', 'all')
        selected_statuses = request.GET.getlist('completionStatus')
        selected_errors = request.GET.get('errorHistory')
        selected_query_types = request.GET.getlist('queryType')

        # Get user's query history
        query_history = QueryHistory.objects.filter(user_id=user_id).order_by('-timestamp')

        # Get user's error history
        error_history = ErrorsRecord.objects.filter(user_id=user_id).order_by('-timestamp')

        # Get user's progress
        user_progress = Progress.objects.filter(user_id=user_id).first()

        # Get all tasks
        tasks = Task.objects.all().select_related('queryid')

        # Apply filters
        if selected_time != 'all':
            days = int(selected_time)
            cutoff_date = timezone.now() - timezone.timedelta(days=days)
            tasks = tasks.filter(time__gte=cutoff_date)

        if selected_diff != 'all':
            tasks = tasks.filter(difficulty=selected_diff)

        # Get task completion status for the current user
        completed_task_ids = set(QueryHistory.objects.filter(
            user_id=user_id
        ).values_list('task_id', flat=True).distinct())

        # Prepare task data
        tasks_list = []
        for task in tasks:
            task_data = {
                'id': task.tid,
                'name': task.tname,
                'difficulty': task.difficulty,
                'status': 'completed' if task.tid in completed_task_ids else 'not_started',
                'start_date': task.time,
                'last_updated': query_history.filter(task_id=task.tid).order_by('-timestamp').first(),
                'query_type': task.queryid.content if task.queryid else '',
                'errors': error_history.filter(task_id=task.tid).count()
            }
            tasks_list.append(task_data)

        context = {
            'user_data': user_record,
            'query_history': query_history,
            'error_history': error_history,
            'user_progress': user_progress,
            'tasks': tasks_list,  # Send the prepared task list
            'time_slots': time_slots,
            'difficulty_levels': difficulty_levels,
            'completion_statuses': completion_statuses,
            'query_types': query_types,
            'selected_statuses': selected_statuses,
            'selected_query_types': selected_query_types,
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
