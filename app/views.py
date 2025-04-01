from django.shortcuts import render
from .models import Users, Task
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.utils import timezone

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

def user_page(request):
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

    # Query tasks
    tasks = Task.objects.all()

    # Apply filters
    if selected_time != 'all':
        days = int(selected_time)
        tasks = tasks.filter(time__gte=timezone.now() - timezone.timedelta(days=days))

    if selected_diff != 'all':
        tasks = tasks.filter(difficulty=selected_diff)

    if selected_statuses:
        tasks = tasks.filter(status__in=selected_statuses)

    if selected_errors == 'true':
        tasks = tasks.exclude(errors=0)

    if selected_query_types:
        tasks = tasks.filter(query_type__in=selected_query_types)

    context = {
        'tasks': tasks,
        'time_slots': time_slots,
        'difficulty_levels': difficulty_levels,
        'completion_statuses': completion_statuses,
        'query_types': query_types,
        'selected_statuses': selected_statuses,
        'selected_query_types': selected_query_types,
    }

    return render(request, 'DynamicPage/user_page.html', context)
