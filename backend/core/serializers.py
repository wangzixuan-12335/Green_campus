"""
核心业务序列化器
"""
from rest_framework import serializers
from .models import (
    Task, TaskRecord, Challenge, ChallengeParticipation,
    ShopItem, Redemption, CharityProject, Donation,
    Badge, UserBadge, Group, GroupCheckin, Notification,
    MonopolyTile, MonopolyPlayer, MonopolyProperty, MonopolyLog, MonopolyEvent,
)


# ─── 任务 ───
class TaskSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Task
        fields = '__all__'


class TaskRecordSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source='task.name', read_only=True)
    task_icon = serializers.CharField(source='task.icon', read_only=True)

    class Meta:
        model = TaskRecord
        fields = ['id', 'task', 'task_name', 'task_icon', 'completed_date', 'created_at', 'points_earned']


# ─── 挑战 ───
class ChallengeSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Challenge
        fields = '__all__'


class ChallengeParticipationSerializer(serializers.ModelSerializer):
    challenge_title = serializers.CharField(source='challenge.title', read_only=True)
    challenge_cover = serializers.CharField(source='challenge.cover', read_only=True)
    challenge_points = serializers.IntegerField(source='challenge.points', read_only=True)

    class Meta:
        model = ChallengeParticipation
        fields = '__all__'


# ─── 商城 ───
class ShopItemSerializer(serializers.ModelSerializer):
    tag_label = serializers.CharField(source='get_tag_display', read_only=True)

    class Meta:
        model = ShopItem
        fields = '__all__'


class RedemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Redemption
        fields = '__all__'


# ─── 公益 ───
class CharityProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharityProject
        fields = '__all__'


class DonationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donation
        fields = '__all__'


# ─── 徽章 ───
class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = '__all__'


class UserBadgeSerializer(serializers.ModelSerializer):
    badge_name = serializers.CharField(source='badge.name', read_only=True)
    badge_icon = serializers.CharField(source='badge.icon', read_only=True)
    badge_description = serializers.CharField(source='badge.description', read_only=True)

    class Meta:
        model = UserBadge
        fields = ['id', 'badge_name', 'badge_icon', 'badge_description', 'earned_at']


# ─── 小组 ───
class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'


class GroupCheckinSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)

    class Meta:
        model = GroupCheckin
        fields = ['id', 'group', 'group_name', 'checkin_date', 'points_earned']


# ─── 通知 ───
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


# ─── 大富翁 ───
class MonopolyTileSerializer(serializers.ModelSerializer):
    tile_type_label = serializers.CharField(source='get_tile_type_display', read_only=True)

    class Meta:
        model = MonopolyTile
        fields = '__all__'


class MonopolyPlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonopolyPlayer
        fields = '__all__'


class MonopolyPropertySerializer(serializers.ModelSerializer):
    tile_name = serializers.CharField(source='tile.name', read_only=True)
    owner_name = serializers.CharField(source='owner.nickname', read_only=True, default='无主')

    class Meta:
        model = MonopolyProperty
        fields = '__all__'


class MonopolyLogSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source='get_action_display', read_only=True)
    created_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M', read_only=True)

    class Meta:
        model = MonopolyLog
        fields = ['id', 'action', 'action_label', 'tile_position', 'dice_value',
                  'points_change', 'description', 'created_at']


class MonopolyEventSerializer(serializers.ModelSerializer):
    event_type_label = serializers.CharField(source='get_event_type_display', read_only=True)

    class Meta:
        model = MonopolyEvent
        fields = '__all__'
