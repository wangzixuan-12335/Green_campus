from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'nickname', 'college', 'total_points', 'level', 'streak_days', 'is_active')
    list_filter = ('level', 'is_active', 'college')
    search_fields = ('username', 'nickname', 'student_id', 'phone')
    list_editable = ('is_active',)
    ordering = ('-total_points',)
