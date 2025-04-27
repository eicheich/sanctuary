from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from functools import wraps
from .models import GroupMembership, StudyGroup

def super_admin_required(view_func):
    """Decorator to check if a user is a super admin."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if user is authenticated first
        if not request.user.is_authenticated:
            messages.error(request, 'You need to be logged in to access this page.')
            return redirect('login')

        # Check if user is a super admin
        if not request.user.is_super_admin:
            messages.error(request, 'You need to be a super admin to access this page.')
            return redirect('home')

        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    """Decorator to check if a user has admin-level permissions."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if user is authenticated first
        if not request.user.is_authenticated:
            messages.error(request, 'You need to be logged in to access this page.')
            return redirect('login')

        # Check if user is a super admin or regular admin
        if not request.user.is_super_admin:
            # Check if user created at least one group
            if not request.user.created_groups.exists():
                messages.error(request, 'You need to be a group admin to access this page.')
                return redirect('home')

        return view_func(request, *args, **kwargs)
    return _wrapped_view

def user_required(view_func):
    """Basic decorator to ensure user is authenticated."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You need to be logged in to access this page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def group_admin_required(group_id_kwarg='group_id'):
    """
    Decorator to check if a user is an admin of the specific group.
    Requires the group_id to be passed as a URL parameter.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Check if user is authenticated first
            if not request.user.is_authenticated:
                messages.error(request, 'You need to be logged in to access this page.')
                return redirect('login')

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

def approved_group_required(group_id_kwarg='group_id'):
    """
    Decorator to check if a group is approved before allowing actions.
    Requires the group_id to be passed as a URL parameter.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Get the group_id from kwargs
            group_id = kwargs.get(group_id_kwarg)
            if not group_id:
                messages.error(request, 'Invalid group specified.')
                return redirect('home')

            # Check if group is approved
            try:
                group = StudyGroup.objects.get(id=group_id)
                if group.status != 'approved':
                    messages.error(request, f'This group is not approved yet. Status: {group.status.title()}. You cannot perform this action until the group is approved.')
                    return redirect('manage_group', group_id=group_id)

                return view_func(request, *args, **kwargs)

            except StudyGroup.DoesNotExist:
                messages.error(request, 'Group not found.')
                return redirect('home')

        return _wrapped_view
    return decorator
