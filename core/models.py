from django.db import models
from django.contrib.auth.models import AbstractUser
import os
import uuid
import mimetypes
from django.utils.crypto import get_random_string
from django.urls import reverse

def get_hashed_filename(instance, filename):
    """
    Generate a unique hashed filename while preserving the original extension.
    Args:
        instance: The model instance where the file is being attached
        filename: The original filename
    Returns:
        A unique path for the file using UUID
    """
    # Get the file extension from the original filename
    ext = filename.split('.')[-1] if '.' in filename else ''
    # Generate a unique filename using UUID
    hashed_filename = f"{uuid.uuid4().hex}.{ext}" if ext else f"{uuid.uuid4().hex}"
    # Return the complete path
    return os.path.join('learning_files', hashed_filename)

def get_file_type_from_extension(filename):
    """
    Determine file type from extension
    """
    if not filename:
        return 'other'

    # Get MIME type from file extension
    mime_type, _ = mimetypes.guess_type(filename)

    # Detect image files
    if mime_type and mime_type.startswith('image/'):
        return 'image'

    # Detect PDF files
    if mime_type == 'application/pdf':
        return 'pdf'

    # Detect document files
    document_extensions = ['.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt', '.rtf', '.odt']
    if any(filename.lower().endswith(ext) for ext in document_extensions) or (mime_type and mime_type.startswith('application/vnd.')):
        return 'document'

    # Detect video files
    if mime_type and mime_type.startswith('video/'):
        return 'video'

    # Detect audio files
    if mime_type and mime_type.startswith('audio/'):
        return 'audio'

    # Detect code files
    code_extensions = ['.py', '.js', '.html', '.css', '.php', '.java', '.c', '.cpp', '.json']
    if any(filename.lower().endswith(ext) for ext in code_extensions):
        return 'code'

    # Default
    return 'other'

class User(AbstractUser):
    is_super_admin = models.BooleanField(default=False)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)

    def __str__(self):
        return f"{self.username}"

    def get_role_in_group(self, group):
        """Get the user's role in a specific group"""
        try:
            membership = self.group_memberships.get(group=group)
            return membership.role
        except GroupMembership.DoesNotExist:
            return None

    def is_group_admin(self, group):
        """Check if the user is an admin in the given group"""
        return self.get_role_in_group(group) == 'admin'

    def is_group_moderator(self, group):
        """Check if the user is a moderator in the given group"""
        return self.get_role_in_group(group) == 'moderator'

    def is_group_member(self, group):
        """Check if the user is a regular member in the given group"""
        return self.get_role_in_group(group) == 'user'

class StudyGroup(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    group_name = models.CharField(max_length=100)
    institution = models.CharField(max_length=100)
    purpose = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    members = models.ManyToManyField(User, related_name='study_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.group_name} ({self.get_status_display()})"

    def add_member(self, user, role='user'):
        """Add a user to the group with specified role"""
        membership, created = GroupMembership.objects.get_or_create(
            user=user,
            group=self,
            defaults={'role': role}
        )
        if not created and membership.role != role:
            membership.role = role
            membership.save()
        return membership

    def remove_member(self, user):
        """Remove a user from the group"""
        return GroupMembership.objects.filter(user=user, group=self).delete()

    def get_admins(self):
        """Get all admin users in this group"""
        return User.objects.filter(group_memberships__group=self, group_memberships__role='admin')

    def get_moderators(self):
        """Get all moderator users in this group"""
        return User.objects.filter(group_memberships__group=self, group_memberships__role='moderator')

    def get_regular_members(self):
        """Get all regular members in this group"""
        return User.objects.filter(group_memberships__group=self, group_memberships__role='user')

    def get_user_role(self, user):
        """Get the role of a specific user in this group"""
        try:
            membership = GroupMembership.objects.get(user=user, group=self)
            return membership.role
        except GroupMembership.DoesNotExist:
            return None

class GroupMembership(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('user', 'User'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    group = models.ForeignKey('StudyGroup', on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.group.group_name} ({self.get_role_display()})"

    class Meta:
        unique_together = ['user', 'group']

class Course(models.Model):
    course_name = models.CharField(max_length=100)
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='courses')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_courses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course_name} - {self.group.group_name}"

class Topic(models.Model):
    topic_name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='topics')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_topics')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.topic_name} - {self.course.course_name}"

class LearningFile(models.Model):
    FILE_TYPE_CHOICES = (
        ('image', 'Image'),
        ('pdf', 'PDF'),
        ('code', 'Code'),
        ('document', 'Document'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('other', 'Other'),
    )

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to=get_hashed_filename)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='other')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='files')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='files')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    share_token = models.CharField(max_length=32, null=True, blank=True)
    views_count = models.PositiveIntegerField(default=0)
    downloads_count = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.file_type or self.file_type == 'other':
            self.file_type = get_file_type_from_extension(self.file.name)
        if not self.share_token:
            self.share_token = get_random_string(32)
        super().save(*args, **kwargs)

    def get_share_url(self):
        return reverse('file_share', kwargs={'token': self.share_token})

    def __str__(self):
        return f"{self.title} ({self.get_file_type_display()})"

class FileInteraction(models.Model):
    INTERACTION_CHOICES = (
        ('view', 'View'),
        ('download', 'Download'),
        ('comment', 'Comment'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='file_interactions')
    file = models.ForeignKey(LearningFile, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_CHOICES)
    content = models.TextField(blank=True, null=True)  # For comments
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_interaction_type_display()} - {self.file.title}"

class Report(models.Model):
    REPORT_TYPE_CHOICES = (
        ('inappropriate_content', 'Inappropriate Content'),
        ('copyright_violation', 'Copyright Violation'),
        ('spam', 'Spam'),
        ('other', 'Other'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    )

    file = models.ForeignKey(LearningFile, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_files')
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_reports')

    def __str__(self):
        return f"{self.file.title} - {self.get_report_type_display()} - {self.get_status_display()}"

class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = (
        ('file_interaction', 'File Interaction'),
        ('new_file', 'New File'),
        ('report_update', 'Report Update'),
        ('system', 'System Notification'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=100)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    related_file = models.ForeignKey(LearningFile, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    related_report = models.ForeignKey(Report, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title} - {self.created_at}"

class ActivityLog(models.Model):
    ACTION_CHOICES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('upload_file', 'Upload File'),
        ('create_topic', 'Create Topic'),
        ('edit_topic', 'Edit Topic'),
        ('delete_topic', 'Delete Topic'),
        ('delete_file', 'Delete File'),
        ('create_course', 'Create Course'),
        ('edit_course', 'Edit Course'),
        ('delete_course', 'Delete Course'),
        ('add_member', 'Add Member'),
        ('approve_group', 'Approve Group'),
        ('reject_group', 'Reject Group'),
        ('update_profile', 'Update Profile'),
        ('view_file', 'View File'),
        ('download_file', 'Download File'),
        ('comment_file', 'Comment on File'),
        ('like_file', 'Like File'),
        ('share_file', 'Share File'),
        ('report_file', 'Report File'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    group = models.ForeignKey(StudyGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()} at {self.timestamp}"

# New models for enhanced features
class UserAchievement(models.Model):
    ACHIEVEMENT_TYPE_CHOICES = (
        ('active_user', 'Most Active User'),
        ('contributor', 'Top Contributor'),
        ('helpful', 'Most Helpful'),
        ('engaged', 'Most Engaged')
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='user_achievements')
    achievement_type = models.CharField(max_length=30, choices=ACHIEVEMENT_TYPE_CHOICES)
    title = models.CharField(max_length=100)
    description = models.TextField()
    awarded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class CommentReport(models.Model):
    REPORT_TYPE_CHOICES = (
        ('inappropriate', 'Inappropriate Content'),
        ('spam', 'Spam'),
        ('irrelevant', 'Irrelevant'),
        ('offensive', 'Offensive')
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected')
    )

    comment = models.ForeignKey(FileInteraction, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_comments')
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='resolved_comment_reports')

    def __str__(self):
        return f"Report on comment by {self.comment.user.username} - {self.get_report_type_display()}"

class GroupInvitation(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired')
    )

    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='invitations')
    invitation_code = models.CharField(max_length=32, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # Can be null for never-expiring invitations
    revoked_at = models.DateTimeField(null=True, blank=True)
    is_multiple_use = models.BooleanField(default=True)  # New field to allow multiple uses
    usage_count = models.PositiveIntegerField(default=0)  # Track how many times it's been used
    max_uses = models.PositiveIntegerField(null=True, blank=True)  # Optional limit on number of uses

    def __str__(self):
        return f"Invitation to {self.group.group_name} ({self.get_status_display()})"

    @property
    def is_expired(self):
        from django.utils import timezone
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if invitation is still valid for use"""
        # Check if invitation is active and not expired
        if self.status != 'active' or self.is_expired:
            return False

        # Check if it's reached max uses (if specified)
        if self.max_uses is not None and self.usage_count >= self.max_uses:
            return False

        return True

class GroupLeaderboard(models.Model):
    LEADERBOARD_TYPE_CHOICES = (
        ('activity', 'Most Active'),
        ('contribution', 'Top Contributor'),
        ('files', 'Most Files'),
        ('downloads', 'Most Downloads')
    )

    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='leaderboards')
    leaderboard_type = models.CharField(max_length=20, choices=LEADERBOARD_TYPE_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.group.group_name} - {self.get_leaderboard_type_display()} Leaderboard"

class LeaderboardEntry(models.Model):
    leaderboard = models.ForeignKey(GroupLeaderboard, on_delete=models.CASCADE, related_name='entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leaderboard_entries')
    score = models.PositiveIntegerField(default=0)
    rank = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.user.username} - Rank {self.rank} in {self.leaderboard}"

    class Meta:
        ordering = ['rank']
        unique_together = ['leaderboard', 'user']

class InvitationUse(models.Model):
    """Track users who have accepted a specific invitation"""
    invitation = models.ForeignKey(GroupInvitation, on_delete=models.CASCADE, related_name='uses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accepted_invitations')
    accepted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} used invitation to {self.invitation.group.group_name}"

    class Meta:
        unique_together = ['invitation', 'user']
        ordering = ['-accepted_at']
