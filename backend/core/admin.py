from django.contrib import admin
from .models import (
    Task, TaskRecord, Challenge, ChallengeParticipation,
    ShopItem, Redemption, CharityProject, Donation,
    Badge, UserBadge, Group, GroupCheckin, Notification,
    MonopolyTile, MonopolyPlayer, MonopolyProperty, MonopolyLog, MonopolyEvent,
)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('icon', 'name', 'category', 'points', 'daily_limit', 'is_active', 'sort_order')
    list_filter = ('category', 'is_active')
    list_editable = ('is_active', 'points', 'daily_limit')
    search_fields = ('name',)
    ordering = ('sort_order',)


@admin.register(TaskRecord)
class TaskRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'task', 'completed_date', 'points_earned')
    list_filter = ('completed_date',)


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'tag', 'points', 'status', 'participants_count', 'is_active')
    list_filter = ('status', 'is_active')
    list_editable = ('status', 'is_active', 'points')


@admin.register(ShopItem)
class ShopItemAdmin(admin.ModelAdmin):
    list_display = ('image', 'name', 'cost', 'stock', 'tag', 'is_active')
    list_filter = ('tag', 'is_active')
    list_editable = ('cost', 'stock', 'is_active')


@admin.register(CharityProject)
class CharityProjectAdmin(admin.ModelAdmin):
    list_display = ('icon', 'name', 'cost', 'total_donated', 'is_active')
    list_editable = ('is_active',)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('icon', 'name', 'category', 'monopoly_key', 'condition_points', 'condition_tasks')
    list_filter = ('category',)
    list_editable = ('category',)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('icon', 'name', 'member_count')


# ─── 大富翁 ───
@admin.register(MonopolyTile)
class MonopolyTileAdmin(admin.ModelAdmin):
    list_display = ('position', 'icon', 'name', 'tile_type', 'claim_cost', 'upgrade_cost', 'base_toll', 'is_active')
    list_filter = ('tile_type', 'is_active')
    list_editable = ('is_active', 'claim_cost', 'upgrade_cost', 'base_toll')
    ordering = ('position',)


@admin.register(MonopolyPlayer)
class MonopolyPlayerAdmin(admin.ModelAdmin):
    list_display = ('user', 'position', 'dice_count', 'laps', 'is_trapped', 'last_play_at')
    list_filter = ('is_trapped',)
    search_fields = ('user__username', 'user__nickname')


@admin.register(MonopolyProperty)
class MonopolyPropertyAdmin(admin.ModelAdmin):
    list_display = ('tile', 'owner', 'level', 'total_toll_collected', 'claimed_at')
    list_filter = ('level',)
    search_fields = ('tile__name', 'owner__nickname')


@admin.register(MonopolyLog)
class MonopolyLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'tile_position', 'dice_value', 'points_change', 'description', 'created_at')
    list_filter = ('action',)
    search_fields = ('user__nickname', 'description')


@admin.register(MonopolyEvent)
class MonopolyEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'description', 'points_change', 'extra_dice', 'is_active')
    list_filter = ('event_type', 'is_active')
    list_editable = ('is_active',)
