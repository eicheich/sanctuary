from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect, FileResponse
from django.db.models import Count
from django.urls import reverse
from django.http import JsonResponse
from django.utils.crypto import get_random_string
import os

from .models import User, StudyGroup, Course, Topic, LearningFile, ActivityLog, FileInteraction, Report, Notification
from .models import UserAchievement, CommentReport, GroupInvitation, GroupLeaderboard, LeaderboardEntry
from .decorators import super_admin_required, admin_required, user_required

# Import additional modules for new features
from django.utils import timezone
from datetime import timedelta
import uuid
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count, Sum, Q
from django.template.loader import render_to_string

def landing_page(request):
    """Landing page view that displays before user logs in"""
    # Jika pengguna sudah login, redirect ke halaman home dashboard
    if request.user.is_authenticated:
        return redirect('home')

    return render(request, 'core/landing_page.html')

def request_study_group(request):
    """Handle study group requests from landing page"""
    # Redirect to register if not authenticated
    if not request.user.is_authenticated:
        messages.info(request, "Please create an account first to request a study group.")
        return redirect('register')

    if request.method == 'POST':
        group_name = request.POST.get('group_name')
        institution = request.POST.get('institution')
        purpose = request.POST.get('purpose')
        agree_terms = request.POST.get('agree_terms')

        # Check if user agreed to terms
        if not agree_terms:
            messages.error(request, "You must agree to use the study group for proper academic purposes only.")
            return render(request, 'core/request_group.html')

        # Create a pending study group associated with the user
        study_group = StudyGroup.objects.create(
            group_name=group_name,
            institution=institution,
            purpose=purpose,
            created_by=request.user,
            status='pending'
        )

        # Add the creator as member
        study_group.members.add(request.user)

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            group=study_group,
            action_type='create_group',
            description=f"Study Group Request: {group_name} by {request.user.username} from {institution}. Purpose: {purpose}"
        )

        # Kirim notifikasi ke Super Admin
        admins = User.objects.filter(role='super_admin')
        for admin in admins:
            Notification.objects.create(
                user=admin,
                notification_type='system',
                title='New Study Group Request',
                message=f"{request.user.username} requested to create study group '{group_name}' from {institution}"
            )

        messages.success(request, "Study group request submitted successfully! Our admin will review and contact you soon.")
        return redirect('home')

    return render(request, 'core/request_group.html')

# Authentication Views
def register_view(request):
    """View for user registration"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Basic validation
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
            return render(request, 'auth/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' is already registered.")
            return render(request, 'auth/register.html')

        if password1 != password2:
            messages.error(request, "Passwords don't match.")
            return render(request, 'auth/register.html')

        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'auth/register.html')

        # Create new user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            role='user'  # Default role for new users
        )

        # Log activity
        ActivityLog.objects.create(
            user=user,
            action_type='register',
            description=f"New user account created: {username}"
        )

        messages.success(request, f"Account created successfully! You can now log in.")
        return redirect('login')

    return render(request, 'auth/register.html')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Log activity
                ActivityLog.objects.create(
                    user=user,
                    action_type='login',
                    description=f"{user.username} logged in"
                )
                messages.success(request, f"Welcome back, {username}!")
                return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'auth/login.html', {'form': form})

def logout_view(request):
    if request.user.is_authenticated:
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='logout',
            description=f"{request.user.username} logged out"
        )
        logout(request)
        messages.info(request, "You have successfully logged out.")
    return redirect('login')

# Home View
@login_required
def home(request):
    # Common data for all users
    user_groups = request.user.study_groups.all()
    user_courses = Course.objects.filter(group__in=user_groups)
    recent_files = LearningFile.objects.filter(course__in=user_courses).order_by('-created_at')[:10]

    # Super admin specific data
    if request.user.role == 'super_admin':
        pending_groups = StudyGroup.objects.filter(status='pending').count()
        total_groups = StudyGroup.objects.count()
        total_admins = User.objects.filter(role='admin').count()
        total_users = User.objects.filter(role='user').count()
        total_reports = Report.objects.all().count()
        recent_activities = ActivityLog.objects.all().order_by('-timestamp')[:10]

        additional_context = {
            'pending_groups': pending_groups,
            'total_groups': total_groups,
            'total_admins': total_admins,
            'total_users': total_users,
            'total_reports': total_reports,
            'recent_activities': recent_activities,
            'is_super_admin': True
        }

    # Regular admin/group admin specific data
    elif request.user.role == 'admin':
        admin_groups = StudyGroup.objects.filter(created_by=request.user)
        total_courses = Course.objects.filter(group__created_by=request.user).count()
        total_members = sum(group.members.count() for group in admin_groups)
        pending_reports = Report.objects.filter(
            file__course__group__in=admin_groups,
            status='pending'
        ).count()
        recent_activities = ActivityLog.objects.filter(group__created_by=request.user).order_by('-timestamp')[:10]

        additional_context = {
            'admin_groups': admin_groups,
            'total_courses': total_courses,
            'total_members': total_members,
            'pending_reports': pending_reports,
            'recent_activities': recent_activities,
            'is_admin': True
        }
    else:
        # Regular user doesn't need additional context
        additional_context = {}

    # Common context for all users
    context = {
        'user_groups': user_groups,
        'user_courses': user_courses,
        'recent_files': recent_files,
    }

    # Add user-specific context
    context.update(additional_context)

    return render(request, 'core/user_dashboard.html', context)

# Super Admin Views
@super_admin_required
def pending_groups(request):
    groups = StudyGroup.objects.filter(status='pending')
    return render(request, 'core/pending_groups.html', {'groups': groups})

@super_admin_required
def approve_group(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)
    group.status = 'approved'
    group.save()

    # Make the group creator an admin
    group_creator = group.created_by
    group_creator.role = 'admin'
    group_creator.save()

    # Log activity
    ActivityLog.objects.create(
        user=request.user,
        group=group,
        action_type='approve_group',
        description=f"Group '{group.group_name}' approved by {request.user.username}. {group_creator.username} was promoted to admin."
    )

    # Create notification for group creator
    Notification.objects.create(
        user=group_creator,
        notification_type='system',
        title='Your group has been approved!',
        message=f"Your study group '{group.group_name}' has been approved and you've been promoted to admin status."
    )

    messages.success(request, f"Group '{group.group_name}' has been approved and {group_creator.username} was promoted to admin.")
    return redirect('pending_groups')

@super_admin_required
def reject_group(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)
    group.status = 'rejected'
    group.save()

    # Log activity
    ActivityLog.objects.create(
        user=request.user,
        group=group,
        action_type='reject_group',
        description=f"Group '{group.group_name}' rejected by {request.user.username}"
    )

    messages.success(request, f"Group '{group.group_name}' has been rejected.")
    return redirect('pending_groups')

@super_admin_required
def all_admins(request):
    admins = User.objects.filter(role='admin')
    return render(request, 'core/all_admins.html', {'admins': admins})

@super_admin_required
def activity_logs(request):
    logs = ActivityLog.objects.all().order_by('-timestamp')
    return render(request, 'core/activity_logs.html', {'logs': logs})

# Admin Views
@admin_required
def create_group(request):
    if request.method == 'POST':
        group_name = request.POST.get('group_name')
        institution = request.POST.get('institution')
        purpose = request.POST.get('purpose')

        group = StudyGroup.objects.create(
            group_name=group_name,
            institution=institution,
            purpose=purpose,
            created_by=request.user
        )

        # Add creator as member
        group.members.add(request.user)

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            group=group,
            action_type='create_group',
            description=f"Group '{group_name}' created by {request.user.username}"
        )

        messages.success(request, "Group created successfully! Waiting for approval.")
        return redirect('home')

    return render(request, 'core/create_group.html')

@admin_required
def manage_group(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)

    # Only allow group creator to manage it
    if group.created_by != request.user and not request.user.is_super_admin():
        return HttpResponseForbidden("You don't have permission to manage this group.")

    return render(request, 'core/manage_group.html', {'group': group})

@admin_required
def add_member(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)

    # Only allow group creator to add members
    if group.created_by != request.user and not request.user.is_super_admin():
        return HttpResponseForbidden("You don't have permission to add members to this group.")

    if request.method == 'POST':
        username = request.POST.get('username')
        try:
            user = User.objects.get(username=username)
            group.members.add(user)

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                group=group,
                action_type='add_member',
                description=f"{user.username} was added to group '{group.group_name}' by {request.user.username}"
            )

            messages.success(request, f"{username} added to the group successfully!")
        except User.DoesNotExist:
            messages.error(request, f"User '{username}' not found.")

        return redirect('manage_group', group_id=group_id)

    return render(request, 'core/add_member.html', {'group': group})

@admin_required
def create_course(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)

    # Only allow group creator or super admin to create courses
    if group.created_by != request.user and not request.user.is_super_admin():
        return HttpResponseForbidden("You don't have permission to create courses for this group.")

    if request.method == 'POST':
        course_name = request.POST.get('course_name')

        course = Course.objects.create(
            course_name=course_name,
            group=group,
            created_by=request.user
        )

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            group=group,
            action_type='create_course',
            description=f"Course '{course_name}' created by {request.user.username} for group '{group.group_name}'"
        )

        messages.success(request, f"Course '{course_name}' created successfully!")
        return redirect('manage_group', group_id=group_id)

    return render(request, 'core/create_course.html', {'group': group})

@login_required
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    group = course.group

    # Only allow admin, group creator, or super admin to edit courses
    if not (request.user.is_super_admin() or request.user == group.created_by or
            (request.user.is_group_admin() and group.members.filter(id=request.user.id).exists())):
        return HttpResponseForbidden("You don't have permission to edit this course.")

    if request.method == 'POST':
        course_name = request.POST.get('course_name')

        # Update course
        course.course_name = course_name
        course.save()

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            group=group,
            action_type='edit_course',
            description=f"Course '{course_name}' updated by {request.user.username}"
        )

        messages.success(request, f"Course '{course_name}' updated successfully!")
        return redirect('course_detail', course_id=course.id)

    return render(request, 'core/edit_course.html', {'course': course})

@login_required
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    group = course.group

    # Only allow admin, group creator, or super admin to delete courses
    if not (request.user.is_super_admin() or request.user == group.created_by or
            (request.user.is_group_admin() and group.members.filter(id=request.user.id).exists())):
        return HttpResponseForbidden("You don't have permission to delete this course.")

    if request.method == 'POST':
        course_name = course.course_name
        group_id = course.group.id

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            group=group,
            action_type='delete_course',
            description=f"Course '{course_name}' deleted by {request.user.username}"
        )

        # Delete course
        course.delete()

        messages.success(request, f"Course '{course_name}' has been deleted.")
        return redirect('manage_group', group_id=group_id)

    return render(request, 'core/delete_course.html', {'course': course})

@admin_required
def group_activity(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)

    # Only allow group creator or super admin to view group activity
    if group.created_by != request.user and not request.user.is_super_admin():
        return HttpResponseForbidden("You don't have permission to view this group's activity.")

    logs = ActivityLog.objects.filter(group=group).order_by('-timestamp')
    return render(request, 'core/group_activity.html', {'group': group, 'logs': logs})

@admin_required
def create_user(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)

    # Only allow group creator to add members
    if group.created_by != request.user and not request.user.is_super_admin():
        return HttpResponseForbidden("You don't have permission to add members to this group.")

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Basic validation
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
            return render(request, 'core/create_user.html', {'group': group})

        if User.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' is already registered.")
            return render(request, 'core/create_user.html', {'group': group})

        if password1 != password2:
            messages.error(request, "Passwords don't match.")
            return render(request, 'core/create_user.html', {'group': group})

        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'core/create_user.html', {'group': group})

        # Create new user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            role='user'  # Default role for new users
        )

        # Add user to the group
        group.members.add(user)

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            group=group,
            action_type='add_member',
            description=f"New user '{username}' was created and added to group '{group.group_name}' by {request.user.username}"
        )

        messages.success(request, f"User '{username}' created successfully and added to the group!")
        return redirect('manage_group', group_id=group_id)

    return render(request, 'core/create_user.html', {'group': group})

# User Views
@user_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Check if user is a member of the group that owns the course
    if not request.user.study_groups.filter(id=course.group.id).exists() and not request.user.is_super_admin():
        return HttpResponseForbidden("You don't have permission to view this course.")

    topics = Topic.objects.filter(course=course)
    # Get all files for this course to display in the All Files tab
    course_files = LearningFile.objects.filter(course=course).order_by('-created_at')

    return render(request, 'core/course_detail.html', {
        'course': course,
        'topics': topics,
        'course_files': course_files
    })

@user_required
def create_topic(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Check if user is a member of the group that owns the course
    if not request.user.study_groups.filter(id=course.group.id).exists() and not request.user.is_super_admin():
        return HttpResponseForbidden("You don't have permission to create topics for this course.")

    if request.method == 'POST':
        topic_name = request.POST.get('topic_name')

        topic = Topic.objects.create(
            topic_name=topic_name,
            course=course,
            created_by=request.user
        )

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            group=course.group,
            action_type='create_topic',
            description=f"Topic '{topic_name}' created by {request.user.username} for course '{course.course_name}'"
        )

        messages.success(request, f"Topic '{topic_name}' created successfully!")
        return redirect('course_detail', course_id=course_id)

    return render(request, 'core/create_topic.html', {'course': course})

@login_required
def edit_topic(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    course = topic.course
    group = course.group

    # Check if user is a member of the group that owns the course
    if not (request.user.is_super_admin() or request.user == group.created_by or
            request.user.study_groups.filter(id=group.id).exists()):
        return HttpResponseForbidden("You don't have permission to edit this topic.")

    if request.method == 'POST':
        topic_name = request.POST.get('topic_name')

        # Update topic
        topic.topic_name = topic_name
        topic.save()

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            group=group,
            action_type='edit_topic',
            description=f"Topic '{topic_name}' updated by {request.user.username}"
        )

        messages.success(request, f"Topic '{topic_name}' updated successfully!")
        return redirect('topic_detail', topic_id=topic.id)

    return render(request, 'core/edit_topic.html', {'topic': topic})

@login_required
def delete_topic(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    course = topic.course
    group = course.group

    # Check if user is a member of the group that owns the course
    if not (request.user.is_super_admin() or request.user == group.created_by or
            (request.user.is_group_admin() and group.members.filter(id=request.user.id).exists())):
        return HttpResponseForbidden("You don't have permission to delete this topic.")

    if request.method == 'POST':
        topic_name = topic.topic_name
        course_id = topic.course.id

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            group=group,
            action_type='delete_topic',
            description=f"Topic '{topic_name}' deleted by {request.user.username}"
        )

        # Delete topic
        topic.delete()

        messages.success(request, f"Topic '{topic_name}' has been deleted.")
        return redirect('course_detail', course_id=course_id)

    return render(request, 'core/delete_topic.html', {'topic': topic})

@user_required
def topic_detail(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)

    # Check if user is a member of the group that owns the course
    if not request.user.study_groups.filter(id=topic.course.group.id).exists() and not request.user.is_super_admin():
        return HttpResponseForbidden("You don't have permission to view this topic.")

    learning_files = LearningFile.objects.filter(topic=topic)
    # Get all files for the entire course to display in All Files tab
    all_course_files = LearningFile.objects.filter(course=topic.course).order_by('-created_at')

    # Pre-compute liked files for the current user
    liked_file_ids = []
    if request.user.is_authenticated:
        liked_file_ids = FileInteraction.objects.filter(
            user=request.user,
            interaction_type='like',
            file__in=learning_files
        ).values_list('file_id', flat=True)

    return render(request, 'core/topic_detail.html', {
        'topic': topic,
        'learning_files': learning_files,
        'all_course_files': all_course_files,
        'liked_file_ids': liked_file_ids
    })

@user_required
def upload_file(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)

    # Check if user is a member of the group that owns the course
    if not request.user.study_groups.filter(id=topic.course.group.id).exists() and not request.user.is_super_admin():
        return HttpResponseForbidden("You don't have permission to upload files to this topic.")

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        file_type = request.POST.get('file_type')
        file = request.FILES.get('file')

        if file:
            learning_file = LearningFile.objects.create(
                title=title,
                description=description,
                file=file,
                file_type=file_type,
                topic=topic,
                course=topic.course,
                uploaded_by=request.user
            )

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                group=topic.course.group,
                action_type='upload_file',
                description=f"File '{title}' uploaded by {request.user.username} to topic '{topic.topic_name}'"
            )

            messages.success(request, "File uploaded successfully!")
            return redirect('topic_detail', topic_id=topic_id)
        else:
            messages.error(request, "Please select a file to upload.")

    return render(request, 'core/upload_file.html', {'topic': topic})

@login_required
def profile_view(request):
    # Get user's recent activities
    user_activities = ActivityLog.objects.filter(user=request.user).order_by('-timestamp')[:10]

    if request.method == 'POST':
        # Handle profile updates
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        current_password = request.POST.get('current_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        # Update basic profile information
        request.user.email = email
        request.user.first_name = first_name
        request.user.last_name = last_name

        # Handle password change if requested
        if current_password and new_password1 and new_password2:
            # Check if current password is correct
            if not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                return redirect('profile')

            # Check if new passwords match
            if new_password1 != new_password2:
                messages.error(request, "New passwords don't match.")
                return redirect('profile')

            # Check password complexity
            if len(new_password1) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                return redirect('profile')

            # Set the new password
            request.user.set_password(new_password1)
            password_changed = True
        else:
            password_changed = False

        # Save user changes
        request.user.save()

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='update_profile',
            description=f"{request.user.username} updated their profile information"
        )

        messages.success(request, "Profile updated successfully!")

        # If password was changed, re-authenticate
        if password_changed:
            # Re-authenticate with new password
            user = authenticate(username=request.user.username, password=new_password1)
            if user:
                login(request, user)
                messages.info(request, "Password changed successfully.")
            else:
                messages.warning(request, "Password changed, please log in again.")
                return redirect('logout')

        return redirect('profile')

    return render(request, 'core/profile.html', {'user_activities': user_activities})

@login_required
def update_profile_photo(request):
    """Handle the profile photo upload"""
    if request.method == 'POST' and request.FILES.get('profile_photo'):
        # Get the uploaded file
        profile_photo = request.FILES['profile_photo']

        # Check file type (accept only images)
        if not profile_photo.content_type.startswith('image'):
            messages.error(request, "Please upload a valid image file.")
            return redirect('profile')

        # Delete old profile photo if it exists
        if request.user.profile_photo:
            old_photo_path = request.user.profile_photo.path
            if os.path.exists(old_photo_path):
                os.remove(old_photo_path)

        # Set new profile photo
        request.user.profile_photo = profile_photo
        request.user.save()

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='update_profile',
            description=f"{request.user.username} updated their profile photo"
        )

        messages.success(request, "Profile photo updated successfully!")

    return redirect('profile')

# File Sharing Views
def file_share(request, token):
    """View for accessing shared files with a token"""
    file = get_object_or_404(LearningFile, share_token=token)

    # Increment view count
    file.views_count += 1
    file.save()

    # Log interaction if user is authenticated
    if request.user.is_authenticated:
        FileInteraction.objects.create(
            user=request.user,
            file=file,
            interaction_type='view'
        )

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            group=file.course.group,
            action_type='view_file',
            description=f"{request.user.username} viewed shared file '{file.title}'"
        )

    return render(request, 'core/shared_file.html', {'file': file})

@login_required
def generate_share_link(request, file_id):
    """Generate or regenerate a share link for a file"""
    file = get_object_or_404(LearningFile, id=file_id)

    # Check if user has permission
    if not (request.user.is_super_admin() or request.user == file.uploaded_by or
            request.user.study_groups.filter(id=file.course.group.id).exists()):
        return HttpResponseForbidden("You don't have permission to share this file.")

    # Generate new token
    file.share_token = get_random_string(32)
    file.save()

    # Log activity
    ActivityLog.objects.create(
        user=request.user,
        group=file.course.group,
        action_type='share_file',
        description=f"{request.user.username} generated share link for file '{file.title}'"
    )

    # Create notification for file owner if not the current user
    if file.uploaded_by != request.user:
        Notification.objects.create(
            user=file.uploaded_by,
            notification_type='file_interaction',
            title='Your file was shared',
            message=f"{request.user.username} shared your file '{file.title}'",
            related_file=file
        )

    share_url = request.build_absolute_uri(file.get_share_url())
    messages.success(request, "Share link generated successfully!")

    return JsonResponse({'share_url': share_url})

# File Interaction Views
@login_required
def download_file(request, file_id):
    """Handle file download and track it"""
    file = get_object_or_404(LearningFile, id=file_id)

    # Check if user has permission
    if not (request.user.is_super_admin() or
            request.user.study_groups.filter(id=file.course.group.id).exists()):
        return HttpResponseForbidden("You don't have permission to download this file.")

    # Increment download count
    file.downloads_count += 1
    file.save()

    # Log interaction
    FileInteraction.objects.create(
        user=request.user,
        file=file,
        interaction_type='download'
    )

    # Log activity
    ActivityLog.objects.create(
        user=request.user,
        group=file.course.group,
        action_type='download_file',
        description=f"{request.user.username} downloaded file '{file.title}'"
    )

    # Create notification for file owner if not the current user
    if file.uploaded_by != request.user:
        Notification.objects.create(
            user=file.uploaded_by,
            notification_type='file_interaction',
            title='Your file was downloaded',
            message=f"{request.user.username} downloaded your file '{file.title}'",
            related_file=file
        )

    # Get original filename from the file path
    original_filename = os.path.basename(file.file.name)

    # Serve the file as an attachment to force download
    file_path = file.file.path
    response = FileResponse(open(file_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{original_filename}"'

    # Set the appropriate content type based on file extension
    import mimetypes
    content_type, encoding = mimetypes.guess_type(file_path)
    if content_type:
        response['Content-Type'] = content_type

    return response

@login_required
def add_comment(request, file_id):
    """Add a comment to a file"""
    file = get_object_or_404(LearningFile, id=file_id)

    # Check if user has permission
    if not (request.user.is_super_admin() or
            request.user.study_groups.filter(id=file.course.group.id).exists()):
        return HttpResponseForbidden("You don't have permission to comment on this file.")

    if request.method == 'POST':
        comment_content = request.POST.get('comment')

        if comment_content:
            # Create interaction for the comment
            FileInteraction.objects.create(
                user=request.user,
                file=file,
                interaction_type='comment',
                content=comment_content
            )

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                group=file.course.group,
                action_type='comment_file',
                description=f"{request.user.username} commented on file '{file.title}'"
            )

            # Create notification for file owner if not the current user
            if file.uploaded_by != request.user:
                Notification.objects.create(
                    user=file.uploaded_by,
                    notification_type='file_interaction',
                    title='New comment on your file',
                    message=f"{request.user.username} commented on your file '{file.title}'",
                    related_file=file
                )

            messages.success(request, "Comment added successfully!")
        else:
            messages.error(request, "Comment cannot be empty.")

    return redirect(request.META.get('HTTP_REFERER', reverse('topic_detail', args=[file.topic.id])))

@login_required
def like_file(request, file_id):
    """Like or unlike a file"""
    file = get_object_or_404(LearningFile, id=file_id)

    # Check if user has permission
    if not (request.user.is_super_admin() or
            request.user.study_groups.filter(id=file.course.group.id).exists()):
        return HttpResponseForbidden("You don't have permission to like this file.")

    # Check if user already liked the file
    existing_like = FileInteraction.objects.filter(
        user=request.user,
        file=file,
        interaction_type='like'
    ).first()

    if existing_like:
        # Unlike
        existing_like.delete()
        liked = False
        messages.info(request, "You unliked the file.")
    else:
        # Like
        FileInteraction.objects.create(
            user=request.user,
            file=file,
            interaction_type='like'
        )
        liked = True

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            group=file.course.group,
            action_type='like_file',
            description=f"{request.user.username} liked file '{file.title}'"
        )

        # Create notification for file owner if not the current user
        if file.uploaded_by != request.user:
            Notification.objects.create(
                user=file.uploaded_by,
                notification_type='file_interaction',
                title='Someone liked your file',
                message=f"{request.user.username} liked your file '{file.title}'",
                related_file=file
            )

        messages.success(request, "You liked the file!")

    if request.is_ajax():
        return JsonResponse({'liked': liked})
    else:
        return redirect(request.META.get('HTTP_REFERER', reverse('topic_detail', args=[file.topic.id])))

# Report Feature Views
@login_required
def report_file(request, file_id):
    """Report a file for inappropriate content"""
    file = get_object_or_404(LearningFile, id=file_id)

    # Check if user has permission to view the file
    if not (request.user.is_super_admin() or
            request.user.study_groups.filter(id=file.course.group.id).exists()):
        return HttpResponseForbidden("You don't have permission to report this file.")

    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        description = request.POST.get('description')

        if report_type and description:
            # Create report
            report = Report.objects.create(
                file=file,
                reported_by=request.user,
                report_type=report_type,
                description=description
            )

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                group=file.course.group,
                action_type='report_file',
                description=f"{request.user.username} reported file '{file.title}'"
            )

            # Notify admins
            admins = User.objects.filter(role__in=['super_admin', 'admin'])
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    notification_type='report_update',
                    title='New file report',
                    message=f"File '{file.title}' was reported for {report.get_report_type_display()}",
                    related_file=file,
                    related_report=report
                )

            messages.success(request, "File reported successfully. An admin will review it.")
            return redirect('topic_detail', topic_id=file.topic.id)
        else:
            messages.error(request, "Please select a report type and provide a description.")

    return render(request, 'core/report_file.html', {'file': file})

@login_required
def manage_reports(request):
    """View to manage file reports - accessible by super admins, admins, and group leaders"""
    # Super admins see all reports
    if request.user.is_super_admin():
        reports = Report.objects.all().order_by('-created_at')
    # Regular admins see reports for their groups
    elif request.user.role == 'admin':
        admin_groups = StudyGroup.objects.filter(created_by=request.user)
        reports = Report.objects.filter(file__course__group__in=admin_groups).order_by('-created_at')
    # Group leaders (users who created a group) see reports for their groups
    else:
        user_groups = StudyGroup.objects.filter(created_by=request.user)
        if user_groups.exists():  # Make sure the user is a group leader
            reports = Report.objects.filter(file__course__group__in=user_groups).order_by('-created_at')
        else:
            return HttpResponseForbidden("You don't have permission to view reports.")

    return render(request, 'core/manage_reports.html', {'reports': reports})

@login_required
def review_report(request, report_id):
    """Review a specific report - accessible by super admins, admins, and group leaders"""
    report = get_object_or_404(Report, id=report_id)

    # Check if user has permission
    if not request.user.is_super_admin() and not (
        # Group creator/admin permission
        request.user.role == 'admin' and report.file.course.group.created_by == request.user or
        # Group leader permission (user who created a group but isn't admin)
        StudyGroup.objects.filter(created_by=request.user, id=report.file.course.group.id).exists()
    ):
        return HttpResponseForbidden("You don't have permission to review this report.")

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'resolve':
            report.status = 'resolved'
            report.resolved_by = request.user
            report.save()

            # Notify reporter
            Notification.objects.create(
                user=report.reported_by,
                notification_type='report_update',
                title='Your report was resolved',
                message=f"Your report for file '{report.file.title}' was reviewed and resolved",
                related_file=report.file,
                related_report=report
            )

            messages.success(request, "Report marked as resolved.")

        elif action == 'reject':
            report.status = 'rejected'
            report.resolved_by = request.user
            report.save()

            # Notify reporter
            Notification.objects.create(
                user=report.reported_by,
                notification_type='report_update',
                title='Your report was rejected',
                message=f"Your report for file '{report.file.title}' was reviewed and rejected",
                related_file=report.file,
                related_report=report
            )

            messages.success(request, "Report rejected.")

        elif action == 'delete_file':
            file_title = report.file.title
            topic_id = report.file.topic.id

            # Notify file owner
            Notification.objects.create(
                user=report.file.uploaded_by,
                notification_type='system',
                title='Your file was removed',
                message=f"Your file '{file_title}' was removed due to a report"
            )

            # Notify reporter
            Notification.objects.create(
                user=report.reported_by,
                notification_type='report_update',
                title='File was removed based on your report',
                message=f"The file '{file_title}' was removed after your report"
            )

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                group=report.file.course.group,
                action_type='delete_file',
                description=f"{request.user.username} removed file '{file_title}' based on a report"
            )

            # Delete the file
            report.file.delete()

            messages.success(request, f"File '{file_title}' was removed.")
            return redirect('topic_detail', topic_id=topic_id)

        return redirect('manage_reports')

    return render(request, 'core/review_report.html', {'report': report})

# Notification Views
@login_required
def notifications(request):
    """View all notifications for the current user"""
    user_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    # Mark all as read if requested
    if request.GET.get('mark_all_read'):
        user_notifications.update(is_read=True)
        messages.info(request, "All notifications marked as read.")

    return render(request, 'core/notifications.html', {'notifications': user_notifications})

@login_required
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()

    # If AJAX request, return JSON
    if request.is_ajax():
        return JsonResponse({'status': 'success'})

    # Redirect back or to notifications page
    return redirect(request.META.get('HTTP_REFERER', reverse('notifications')))

# Invitation System Views
@login_required
def generate_invitation(request, group_id):
    """Generate invitation link for approved study groups"""
    group = get_object_or_404(StudyGroup, id=group_id)

    # Check if user has permission (group admin or super admin)
    if not (request.user.is_super_admin() or group.created_by == request.user):
        return HttpResponseForbidden("You don't have permission to create invitations for this group.")

    # Check if group is approved
    if group.status != 'approved':
        messages.error(request, "Only approved groups can send invitations.")
        return redirect('manage_group', group_id=group_id)

    if request.method == 'POST':
        # Get form data for invitation settings
        expiry_type = request.POST.get('expiry_type', 'never')
        custom_expiry_days = request.POST.get('custom_expiry_days')
        max_uses = request.POST.get('max_uses')

        # Create invitation with appropriate expiration
        invitation_code = uuid.uuid4().hex

        # Set expiration date based on selection
        expires_at = None
        if expiry_type == 'never':
            expires_at = None
        elif expiry_type == '7days':
            expires_at = timezone.now() + timedelta(days=7)
        elif expiry_type == '30days':
            expires_at = timezone.now() + timedelta(days=30)
        elif expiry_type == 'custom' and custom_expiry_days:
            try:
                expires_at = timezone.now() + timedelta(days=int(custom_expiry_days))
            except ValueError:
                messages.error(request, "Please enter a valid number of days.")
                return render(request, 'core/generate_invitation.html', {'group': group})

        # Set max uses if specified
        max_uses_int = None
        if max_uses:
            try:
                max_uses_int = int(max_uses)
                if max_uses_int < 1:
                    raise ValueError("Max uses must be positive")
            except ValueError:
                messages.error(request, "Please enter a valid number for maximum uses.")
                return render(request, 'core/generate_invitation.html', {'group': group})

        # Create the invitation
        invitation = GroupInvitation.objects.create(
            group=group,
            invitation_code=invitation_code,
            created_by=request.user,
            expires_at=expires_at,
            max_uses=max_uses_int,
            is_multiple_use=True,
            status='active'
        )

        # Create invitation URL
        invitation_url = request.build_absolute_uri(
            reverse('accept_invitation', kwargs={'code': invitation_code})
        )

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            group=group,
            action_type='invite_user',
            description=f"Multi-use invitation link generated for group '{group.group_name}' by {request.user.username}"
        )

        # Return with context showing the generated invitation link
        return render(request, 'core/generate_invitation.html', {
            'group': group,
            'invitation_created': True,
            'invitation_url': invitation_url,
            'invitation': invitation
        })

    return render(request, 'core/generate_invitation.html', {'group': group})

@login_required
def manage_invitations(request, group_id):
    """Manage all invitations for a group"""
    group = get_object_or_404(StudyGroup, id=group_id)

    # Check if user has permission (group admin or super admin)
    if not (request.user.is_super_admin() or group.created_by == request.user):
        return HttpResponseForbidden("You don't have permission to manage invitations for this group.")

    # Get all invitations for the group
    invitations = GroupInvitation.objects.filter(group=group).order_by('-created_at')

    # Mark expired invitations
    now = timezone.now()
    for invitation in invitations:
        if invitation.status == 'pending' and invitation.expires_at < now:
            invitation.status = 'expired'
            invitation.save()

    return render(request, 'core/manage_invitations.html', {
        'group': group,
        'invitations': invitations
    })

def accept_invitation(request, code):
    """Accept an invitation to join a group"""
    # Find invitation by code
    invitation = get_object_or_404(GroupInvitation, invitation_code=code)

    # Check if invitation is valid
    if not invitation.is_valid:
        if invitation.status == 'expired' or invitation.is_expired:
            messages.error(request, "This invitation has expired.")
        elif invitation.status == 'revoked':
            messages.error(request, "This invitation has been revoked by the group administrator.")
        elif invitation.max_uses is not None and invitation.usage_count >= invitation.max_uses:
            messages.error(request, "This invitation has reached its maximum number of uses.")
        else:
            messages.error(request, "This invitation is no longer valid.")
        return redirect('landing_page')

    # If not logged in, ask to log in or register
    if not request.user.is_authenticated:
        # Save invitation code in session to process after login/registration
        request.session['pending_invitation_code'] = code
        messages.info(request, "Please log in or register to join this study group.")
        return redirect('login')

    # Check if user is already in the group
    if invitation.group.members.filter(id=request.user.id).exists():
        messages.info(request, f"You are already a member of the {invitation.group.group_name} group.")
        return redirect('home')

    # Handle confirmation and joining
    if request.method == 'POST':
        # Add user to the group
        invitation.group.members.add(request.user)

        # Create an invitation use record
        from .models import InvitationUse
        InvitationUse.objects.create(
            invitation=invitation,
            user=request.user
        )

        # Increment usage count
        invitation.usage_count += 1

        # If max_uses is defined and reached, update status
        if invitation.max_uses is not None and invitation.usage_count >= invitation.max_uses:
            invitation.status = 'expired'

        invitation.save()

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            group=invitation.group,
            action_type='join_group',
            description=f"{request.user.username} joined group '{invitation.group.group_name}' via invitation"
        )

        # Notify group admin
        Notification.objects.create(
            user=invitation.group.created_by,
            notification_type='system',
            title='New Member Joined',
            message=f"{request.user.username} joined your group '{invitation.group.group_name}' using an invitation link"
        )

        messages.success(request, f"You have successfully joined {invitation.group.group_name}!")
        return redirect('home')

    # Show confirmation page
    return render(request, 'core/confirm_invitation.html', {
        'invitation': invitation,
        'group': invitation.group
    })

@login_required
def cancel_invitation(request, invitation_id):
    """Cancel a pending invitation"""
    invitation = get_object_or_404(GroupInvitation, id=invitation_id)

    # Check if user has permission
    if not (request.user.is_super_admin() or invitation.group.created_by == request.user):
        return HttpResponseForbidden("You don't have permission to cancel this invitation.")

    # Only cancel if pending
    if invitation.status == 'pending':
        invitation.status = 'rejected'
        invitation.save()
        messages.success(request, "Invitation has been cancelled.")
    else:
        messages.error(request, "Only pending invitations can be cancelled.")

    return redirect('manage_invitations', group_id=invitation.group.id)

@login_required
def delete_invitation(request, invitation_id):
    """Permanently delete an invitation from history"""
    invitation = get_object_or_404(GroupInvitation, id=invitation_id)
    group_id = invitation.group.id

    # Check if user has permission (group admin or super admin)
    if not (request.user.is_super_admin() or invitation.group.created_by == request.user):
        return HttpResponseForbidden("You don't have permission to delete this invitation.")

    # Store info for activity log
    invitation_info = f"Invitation to group '{invitation.group.group_name}'"

    # Delete invitation
    invitation.delete()

    # Log activity
    ActivityLog.objects.create(
        user=request.user,
        group=invitation.group,
        action_type='delete_invitation',
        description=f"{request.user.username} deleted {invitation_info}"
    )

    messages.success(request, "Invitation has been permanently deleted from history.")
    return redirect('manage_invitations', group_id=group_id)

# Leaderboard and Achievement Views
@login_required
def group_leaderboard(request, group_id):
    """View leaderboards for a specific study group"""
    group = get_object_or_404(StudyGroup, id=group_id)

    # Check if user is a member of the group
    if not (request.user.is_super_admin() or
            request.user.study_groups.filter(id=group.id).exists()):
        return HttpResponseForbidden("You don't have permission to view this group's leaderboard.")

    # Get or create leaderboards
    leaderboard_types = GroupLeaderboard.LEADERBOARD_TYPE_CHOICES
    leaderboards = {}

    for lb_code, lb_name in leaderboard_types:
        leaderboard, created = GroupLeaderboard.objects.get_or_create(
            group=group,
            leaderboard_type=lb_code
        )

        # Get entries for this leaderboard
        entries = LeaderboardEntry.objects.filter(leaderboard=leaderboard)
        leaderboards[lb_code] = {
            'name': lb_name,
            'entries': entries
        }

    # Get achievements for this group
    achievements = UserAchievement.objects.filter(
        group=group,
        is_active=True
    ).select_related('user')

    return render(request, 'core/group_leaderboard.html', {
        'group': group,
        'leaderboards': leaderboards,
        'achievements': achievements
    })

@admin_required
def update_leaderboards(request, group_id):
    """Admin function to update leaderboards for a group"""
    group = get_object_or_404(StudyGroup, id=group_id)

    # Check if user has permission
    if not (request.user.is_super_admin() or group.created_by == request.user):
        return HttpResponseForbidden("You don't have permission to update leaderboards for this group.")

    # Calculate and update each type of leaderboard
    update_activity_leaderboard(group)
    update_contribution_leaderboard(group)
    update_files_leaderboard(group)
    update_downloads_leaderboard(group)

    # Update achievements based on leaderboards
    update_group_achievements(group)

    messages.success(request, "Group leaderboards and achievements have been updated!")
    return redirect('group_leaderboard', group_id=group_id)

# Helper functions for leaderboard calculations
def update_activity_leaderboard(group):
    """Update activity leaderboard based on ActivityLog entries"""
    # Get or create the leaderboard
    leaderboard, created = GroupLeaderboard.objects.get_or_create(
        group=group,
        leaderboard_type='activity'
    )

    # Get activities for users in this group within the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    user_activities = ActivityLog.objects.filter(
        group=group,
        timestamp__gte=thirty_days_ago
    ).values('user').annotate(
        score=Count('id')
    ).order_by('-score')

    # Clear existing entries
    LeaderboardEntry.objects.filter(leaderboard=leaderboard).delete()

    # Create new entries
    rank = 1
    for activity in user_activities:
        user = User.objects.get(id=activity['user'])
        LeaderboardEntry.objects.create(
            leaderboard=leaderboard,
            user=user,
            score=activity['score'],
            rank=rank
        )
        rank += 1

    # Update leaderboard timestamp
    leaderboard.save()

def update_contribution_leaderboard(group):
    """Update contribution leaderboard based on files and topics created"""
    # Get or create the leaderboard
    leaderboard, created = GroupLeaderboard.objects.get_or_create(
        group=group,
        leaderboard_type='contribution'
    )

    # Get all users in this group
    users = group.members.all()

    # Calculate contribution scores (1 point per file, 3 points per topic)
    user_scores = []
    for user in users:
        # Count files uploaded in this group
        file_count = LearningFile.objects.filter(
            course__group=group,
            uploaded_by=user
        ).count()

        # Count topics created in this group
        topic_count = Topic.objects.filter(
            course__group=group,
            created_by=user
        ).count()

        # Calculate total score
        score = file_count + (topic_count * 3)

        if score > 0:
            user_scores.append({
                'user': user,
                'score': score
            })

    # Sort by score
    user_scores.sort(key=lambda x: x['score'], reverse=True)

    # Clear existing entries
    LeaderboardEntry.objects.filter(leaderboard=leaderboard).delete()

    # Create new entries
    for i, entry in enumerate(user_scores):
        LeaderboardEntry.objects.create(
            leaderboard=leaderboard,
            user=entry['user'],
            score=entry['score'],
            rank=i + 1
        )

    # Update leaderboard timestamp
    leaderboard.save()

def update_files_leaderboard(group):
    """Update files leaderboard based on number of files uploaded"""
    # Get or create the leaderboard
    leaderboard, created = GroupLeaderboard.objects.get_or_create(
        group=group,
        leaderboard_type='files'
    )

    # Get file counts by user
    user_files = LearningFile.objects.filter(
        course__group=group
    ).values('uploaded_by').annotate(
        score=Count('id')
    ).order_by('-score')

    # Clear existing entries
    LeaderboardEntry.objects.filter(leaderboard=leaderboard).delete()

    # Create new entries
    rank = 1
    for entry in user_files:
        user = User.objects.get(id=entry['uploaded_by'])
        LeaderboardEntry.objects.create(
            leaderboard=leaderboard,
            user=user,
            score=entry['score'],
            rank=rank
        )
        rank += 1

    # Update leaderboard timestamp
    leaderboard.save()

def update_downloads_leaderboard(group):
    """Update downloads leaderboard based on file downloads"""
    # Get or create the leaderboard
    leaderboard, created = GroupLeaderboard.objects.get_or_create(
        group=group,
        leaderboard_type='downloads'
    )

    # Get download counts by user (based on their uploaded files)
    user_downloads = LearningFile.objects.filter(
        course__group=group
    ).values('uploaded_by').annotate(
        score=Sum('downloads_count')
    ).order_by('-score')

    # Clear existing entries
    LeaderboardEntry.objects.filter(leaderboard=leaderboard).delete()

    # Create new entries
    rank = 1
    for entry in user_downloads:
        # Skip entries with no downloads
        if not entry['score']:
            continue

        user = User.objects.get(id=entry['uploaded_by'])
        LeaderboardEntry.objects.create(
            leaderboard=leaderboard,
            user=user,
            score=entry['score'],
            rank=rank
        )
        rank += 1

    # Update leaderboard timestamp
    leaderboard.save()

def update_group_achievements(group):
    """Update achievement titles based on leaderboard positions"""
    # Get the current top users from each leaderboard
    achievement_mapping = {
        'activity': {
            'type': 'active_user',
            'title': 'Most Active Contributor',
            'description': 'Most active member in the study group over the last 30 days'
        },
        'contribution': {
            'type': 'contributor',
            'title': 'Top Content Creator',
            'description': 'Contributed the most topics and files to the study group'
        },
        'downloads': {
            'type': 'helpful',
            'title': 'Most Helpful Member',
            'description': 'Their files have been downloaded more than anyone else\'s'
        }
    }

    # First, deactivate all current achievements for this group
    UserAchievement.objects.filter(
        group=group,
        is_active=True
    ).update(is_active=False)

    # Then create new achievements for the top users in each category
    for lb_type, achievement_info in achievement_mapping.items():
        try:
            # Get the #1 ranked user in this leaderboard category
            leaderboard = GroupLeaderboard.objects.get(group=group, leaderboard_type=lb_type)
            top_entry = LeaderboardEntry.objects.filter(leaderboard=leaderboard, rank=1).first()

            if top_entry:
                # Create or update achievement
                achievement, created = UserAchievement.objects.get_or_create(
                    user=top_entry.user,
                    group=group,
                    achievement_type=achievement_info['type'],
                    defaults={
                        'title': achievement_info['title'],
                        'description': achievement_info['description'],
                        'is_active': True
                    }
                )

                if not created:
                    achievement.is_active = True
                    achievement.awarded_at = timezone.now()
                    achievement.save()

                # Create notification for the user
                Notification.objects.create(
                    user=top_entry.user,
                    notification_type='system',
                    title=f"Achievement Earned: {achievement_info['title']}",
                    message=f"Congratulations! You've earned the '{achievement_info['title']}' achievement in {group.group_name}"
                )
        except GroupLeaderboard.DoesNotExist:
            continue

# Comment Report Views
@login_required
def report_comment(request, comment_id):
    """Report a comment"""
    comment = get_object_or_404(FileInteraction, id=comment_id, interaction_type='comment')

    # Check if user has permission to view this comment
    if not (request.user.is_super_admin() or
            request.user.study_groups.filter(id=comment.file.course.group.id).exists()):
        return HttpResponseForbidden("You don't have permission to report this comment.")

    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        description = request.POST.get('description')

        if report_type and description:
            # Create report
            report = CommentReport.objects.create(
                comment=comment,
                reported_by=request.user,
                report_type=report_type,
                description=description
            )

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                group=comment.file.course.group,
                action_type='report_comment',
                description=f"{request.user.username} reported a comment by {comment.user.username}"
            )

            # Notify admins
            admins = User.objects.filter(Q(role='super_admin') |
                                        Q(id=comment.file.course.group.created_by.id))

            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    notification_type='report_update',
                    title='New comment report',
                    message=f"A comment was reported for {report.get_report_type_display()}"
                )

            messages.success(request, "Comment reported successfully. An admin will review it.")
            return redirect('topic_detail', topic_id=comment.file.topic.id)
        else:
            messages.error(request, "Please select a report type and provide a description.")

    return render(request, 'core/report_comment.html', {'comment': comment})

@login_required
def manage_comment_reports(request):
    """View to manage comment reports - accessible by super admins, admins, and group leaders"""
    # Super admins see all reports
    if request.user.is_super_admin():
        reports = CommentReport.objects.all().order_by('-created_at')
    # Regular admins see reports for their groups
    elif request.user.role == 'admin':
        admin_groups = StudyGroup.objects.filter(created_by=request.user)
        reports = CommentReport.objects.filter(
            comment__file__course__group__in=admin_groups
        ).order_by('-created_at')
    # Group leaders (users who created a group) see reports for their groups
    else:
        user_groups = StudyGroup.objects.filter(created_by=request.user)
        if user_groups.exists():  # Make sure the user is a group leader
            reports = CommentReport.objects.filter(
                comment__file__course__group__in=user_groups
            ).order_by('-created_at')
        else:
            return HttpResponseForbidden("You don't have permission to view reports.")

    return render(request, 'core/manage_comment_reports.html', {'reports': reports})

@login_required
def review_comment_report(request, report_id):
    """Review a specific comment report"""
    report = get_object_or_404(CommentReport, id=report_id)

    # Check if user has permission
    if not request.user.is_super_admin() and not (
        # Group creator/admin permission
        request.user.role == 'admin' and report.comment.file.course.group.created_by == request.user or
        # Group leader permission (user who created a group but isn't admin)
        StudyGroup.objects.filter(created_by=request.user, id=report.comment.file.course.group.id).exists()
    ):
        return HttpResponseForbidden("You don't have permission to review this report.")

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'resolve':
            report.status = 'resolved'
            report.resolved_by = request.user
            report.save()

            # Notify reporter
            Notification.objects.create(
                user=report.reported_by,
                notification_type='report_update',
                title='Your report was resolved',
                message=f"Your report for a comment was reviewed and resolved"
            )

            messages.success(request, "Comment report marked as resolved.")

        elif action == 'reject':
            report.status = 'rejected'
            report.resolved_by = request.user
            report.save()

            # Notify reporter
            Notification.objects.create(
                user=report.reported_by,
                notification_type='report_update',
                title='Your report was rejected',
                message=f"Your report for a comment was reviewed and rejected"
            )

            messages.success(request, "Comment report rejected.")

        elif action == 'delete_comment':
            comment = report.comment
            topic_id = comment.file.topic.id

            # Notify comment owner
            Notification.objects.create(
                user=comment.user,
                notification_type='system',
                title='Your comment was removed',
                message=f"Your comment was removed due to a report"
            )

            # Notify reporter
            Notification.objects.create(
                user=report.reported_by,
                notification_type='report_update',
                title='Comment was removed based on your report',
                message=f"The comment you reported was removed"
            )

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                group=comment.file.course.group,
                action_type='delete_comment',
                description=f"{request.user.username} removed a comment by {comment.user.username} based on a report"
            )

            # Delete the comment
            comment.delete()

            messages.success(request, "Comment was removed.")
            return redirect('topic_detail', topic_id=topic_id)

        return redirect('manage_comment_reports')

    return render(request, 'core/review_comment_report.html', {'report': report})

@login_required
def leave_group(request, group_id):
    """Allow users to leave a study group they are a member of"""
    group = get_object_or_404(StudyGroup, id=group_id)

    # Check if user is a member of the group
    if not request.user.study_groups.filter(id=group_id).exists():
        messages.error(request, "You are not a member of this group.")
        return redirect('home')

    # Group creator cannot leave their own group
    if group.created_by == request.user:
        messages.error(request, "As the group creator, you cannot leave your own group. Please contact an admin if you wish to close this group.")
        return redirect('home')

    if request.method == 'POST':
        # Remove user from group
        group.members.remove(request.user)

        # Log the action
        ActivityLog.objects.create(
            user=request.user,
            group=group,
            action_type='leave_group',
            description=f"{request.user.username} left group '{group.group_name}'"
        )

        # Notify group admin
        Notification.objects.create(
            user=group.created_by,
            notification_type='system',
            title='Member Left Group',
            message=f"{request.user.username} has left your study group '{group.group_name}'"
        )

        messages.success(request, f"You have successfully left the group '{group.group_name}'.")
        return redirect('home')

    return render(request, 'core/leave_group_confirmation.html', {'group': group})
