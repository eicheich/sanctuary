from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from .models import GroupMembership, StudyGroup

def super_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_super_admin:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    return _wrapped_view

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Allow super admins
        if request.user.is_authenticated and request.user.is_super_admin:
            return view_func(request, *args, **kwargs)

        # Allow users who are admins of any group (created a group or have admin role)
        if request.user.is_authenticated and (
            request.user.created_groups.exists() or
            GroupMembership.objects.filter(user=request.user, role='admin').exists()
        ):
            return view_func(request, *args, **kwargs)

        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    return _wrapped_view

def user_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'You need to be logged in to access this page.')
        return redirect('login')
    return _wrapped_view

def group_admin_required(group_id_kwarg='group_id'):
    """
    Decorator to check if a user is an admin of the specific group.
    Requires the group_id to be passed as a URL parameter.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Allow super admins access to any group
            if request.user.is_super_admin:
                return view_func(request, *args, **kwargs)

            # Get the group_id from kwargs
            group_id = kwargs.get(group_id_kwarg)
            if not group_id:
                messages.error(request, 'Invalid group specified.')
                return redirect('home')

            # Check if user is creator or admin of this specific group
            try:
                group = StudyGroup.objects.get(id=group_id)
                if group.created_by == request.user:
                    return view_func(request, *args, **kwargs)

                # Check for admin role in this group
                membership = GroupMembership.objects.filter(
                    user=request.user, group=group, role='admin'
                ).exists()

                if membership:
                    return view_func(request, *args, **kwargs)

            except StudyGroup.DoesNotExist:
                pass

            messages.error(request, 'You do not have permission to manage this group.')
            return redirect('home')
        return _wrapped_view
    return decorator
