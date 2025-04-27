from django import template
from django.db.models import Q
from core.models import GroupMembership

register = template.Library()

@register.filter
def get_role_in_group(user, group):
    """Get the role of a user in a specific group"""
    try:
        membership = GroupMembership.objects.get(user=user, group=group)
        return membership.role
    except GroupMembership.DoesNotExist:
        return None

@register.filter
def is_admin_in_group(user, group):
    """Check if user is an admin in the group"""
    try:
        membership = GroupMembership.objects.get(user=user, group=group)
        return membership.role == 'admin'
    except GroupMembership.DoesNotExist:
        return False

@register.filter
def is_moderator_in_group(user, group):
    """Check if user is a moderator in the group"""
    try:
        membership = GroupMembership.objects.get(user=user, group=group)
        return membership.role == 'moderator'
    except GroupMembership.DoesNotExist:
        return False

@register.filter
def can_manage_group(user, group):
    """Check if user has management permissions in the group"""
    # Group creator or admin can manage the group
    return (group.created_by == user or
            GroupMembership.objects.filter(user=user, group=group, role='admin').exists())
