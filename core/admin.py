from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, StudyGroup, Course, Topic, LearningFile, ActivityLog,
    UserAchievement, CommentReport, GroupInvitation, GroupLeaderboard, LeaderboardEntry, InvitationUse
)

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_super_admin', 'is_staff')
    list_filter = ('is_super_admin', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Admin Status', {'fields': ('is_super_admin',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Admin Status', {'fields': ('is_super_admin',)}),
    )

class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ('group_name', 'institution', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'institution')
    search_fields = ('group_name', 'institution')
    readonly_fields = ('created_at', 'updated_at')

class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'group', 'created_by', 'created_at')
    list_filter = ('group',)
    search_fields = ('course_name',)
    readonly_fields = ('created_at', 'updated_at')

class TopicAdmin(admin.ModelAdmin):
    list_display = ('topic_name', 'course', 'created_by', 'created_at')
    list_filter = ('course',)
    search_fields = ('topic_name',)
    readonly_fields = ('created_at', 'updated_at')

class LearningFileAdmin(admin.ModelAdmin):
    list_display = ('title', 'file_type', 'topic', 'course', 'uploaded_by', 'created_at')
    list_filter = ('file_type', 'course', 'topic')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')

class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action_type', 'group', 'timestamp')
    list_filter = ('action_type', 'group')
    search_fields = ('description', 'user__username')
    readonly_fields = ('timestamp',)

class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'achievement_type', 'title', 'awarded_at', 'is_active')
    list_filter = ('achievement_type', 'group', 'is_active')
    search_fields = ('user__username', 'title')
    readonly_fields = ('awarded_at',)

class CommentReportAdmin(admin.ModelAdmin):
    list_display = ('comment', 'reported_by', 'report_type', 'status', 'created_at')
    list_filter = ('report_type', 'status')
    search_fields = ('description', 'comment__content', 'reported_by__username')
    readonly_fields = ('created_at', 'updated_at')

class GroupInvitationAdmin(admin.ModelAdmin):
    list_display = ('group', 'status', 'created_by', 'created_at', 'expires_at', 'usage_count', 'is_multiple_use')
    list_filter = ('status', 'group', 'is_multiple_use')
    search_fields = ('group__group_name', 'invitation_code')
    readonly_fields = ('created_at', 'invitation_code', 'usage_count')

class GroupLeaderboardAdmin(admin.ModelAdmin):
    list_display = ('group', 'leaderboard_type', 'updated_at')
    list_filter = ('leaderboard_type', 'group')
    search_fields = ('group__group_name',)
    readonly_fields = ('updated_at',)

class LeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ('leaderboard', 'user', 'score', 'rank')
    list_filter = ('leaderboard__group', 'leaderboard__leaderboard_type')
    search_fields = ('user__username',)

class InvitationUseAdmin(admin.ModelAdmin):
    list_display = ('invitation', 'user', 'accepted_at')
    list_filter = ('invitation__group', 'accepted_at')
    search_fields = ('user__username', 'invitation__group__group_name')
    readonly_fields = ('accepted_at',)

admin.site.register(User, CustomUserAdmin)
admin.site.register(StudyGroup, StudyGroupAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Topic, TopicAdmin)
admin.site.register(LearningFile, LearningFileAdmin)
admin.site.register(ActivityLog, ActivityLogAdmin)
admin.site.register(UserAchievement, UserAchievementAdmin)
admin.site.register(CommentReport, CommentReportAdmin)
admin.site.register(GroupInvitation, GroupInvitationAdmin)
admin.site.register(GroupLeaderboard, GroupLeaderboardAdmin)
admin.site.register(LeaderboardEntry, LeaderboardEntryAdmin)
admin.site.register(InvitationUse, InvitationUseAdmin)
