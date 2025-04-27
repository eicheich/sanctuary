"""
URL configuration for sanctuary project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Landing Page
    path('', views.landing_page, name='landing'),
    path('request-study-group/', views.request_study_group, name='request_study_group'),

    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),  # Added register URL pattern

    # Profile URLs
    path('profile/', views.profile_view, name='profile'),
    path('profile/update-photo/', views.update_profile_photo, name='update_profile_photo'),

    # Home Dashboard
    path('dashboard/', views.home, name='home'),

    # Super Admin URLs
    path('pending-groups/', views.pending_groups, name='pending_groups'),
    path('approve-group/<int:group_id>/', views.approve_group, name='approve_group'),
    path('reject-group/<int:group_id>/', views.reject_group, name='reject_group'),
    path('admins/', views.all_admins, name='all_admins'),
    path('activity-logs/', views.activity_logs, name='activity_logs'),

    # Admin URLs
    path('create-group/', views.create_group, name='create_group'),
    path('manage-group/<int:group_id>/', views.manage_group, name='manage_group'),
    path('add-member/<int:group_id>/', views.add_member, name='add_member'),
    path('create-course/<int:group_id>/', views.create_course, name='create_course'),
    path('group-activity/<int:group_id>/', views.group_activity, name='group_activity'),

    # Group membership management
    path('group/<int:group_id>/leave/', views.leave_group, name='leave_group'),

    # User URLs
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('edit-course/<int:course_id>/', views.edit_course, name='edit_course'),
    path('delete-course/<int:course_id>/', views.delete_course, name='delete_course'),
    path('create-topic/<int:course_id>/', views.create_topic, name='create_topic'),
    path('edit-topic/<int:topic_id>/', views.edit_topic, name='edit_topic'),
    path('delete-topic/<int:topic_id>/', views.delete_topic, name='delete_topic'),
    path('topic/<int:topic_id>/', views.topic_detail, name='topic_detail'),
    path('upload-file/<int:topic_id>/', views.upload_file, name='upload_file'),

    # File Sharing URLs
    path('shared/file/<str:token>/', views.file_share, name='file_share'),
    path('file/<int:file_id>/share/', views.generate_share_link, name='generate_share_link'),

    # File Interaction URLs
    path('file/<int:file_id>/download/', views.download_file, name='download_file'),
    path('file/<int:file_id>/comment/', views.add_comment, name='add_comment'),
    path('file/<int:file_id>/like/', views.like_file, name='like_file'),

    # Report Feature URLs
    path('file/<int:file_id>/report/', views.report_file, name='report_file'),
    path('reports/', views.manage_reports, name='manage_reports'),
    path('reports/<int:report_id>/review/', views.review_report, name='review_report'),

    # Comment Report URLs
    path('comment/<int:comment_id>/report/', views.report_comment, name='report_comment'),
    path('comment-reports/', views.manage_comment_reports, name='manage_comment_reports'),
    path('comment-reports/<int:report_id>/review/', views.review_comment_report, name='review_comment_report'),

    # Invitation System URLs
    path('group/<int:group_id>/invite/', views.generate_invitation, name='generate_invitation'),
    path('group/<int:group_id>/invitations/', views.manage_invitations, name='manage_invitations'),
    path('invitation/<str:code>/', views.accept_invitation, name='accept_invitation'),
    path('invitation/<int:invitation_id>/cancel/', views.cancel_invitation, name='cancel_invitation'),
    path('invitations/delete/<int:invitation_id>/', views.delete_invitation, name='delete_invitation'),

    # Leaderboard and Achievement URLs
    path('group/<int:group_id>/leaderboard/', views.group_leaderboard, name='group_leaderboard'),
    path('group/<int:group_id>/update-leaderboards/', views.update_leaderboards, name='update_leaderboards'),

    # Notification URLs
    path('notifications/', views.notifications, name='notifications'),
    path('notification/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
]

# Add media URL configuration for development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
