"""
核心业务视图
"""
from django.db import transaction
from django.db.models import Sum, Count, F
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import User
from .models import (
    Task, TaskRecord, Challenge, ChallengeParticipation,
    ShopItem, Redemption, CharityProject, Donation,
    Badge, UserBadge, Group, GroupCheckin, Notification,
    MonopolyTile, MonopolyPlayer, MonopolyProperty, MonopolyLog,
)
from .serializers import (
    TaskSerializer, TaskRecordSerializer,
    ChallengeSerializer, ChallengeParticipationSerializer,
    ShopItemSerializer, RedemptionSerializer,
    CharityProjectSerializer, DonationSerializer,
    BadgeSerializer, UserBadgeSerializer,
    GroupSerializer, GroupCheckinSerializer,
    NotificationSerializer,
    MonopolyTileSerializer, MonopolyLogSerializer,
)
from . import monopoly as mp


# ═════════════════════════════════════════════
# 首页聚合
# ═════════════════════════════════════════════
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def home_overview(request):
    """首页聚合数据：今日任务、进度、排行榜速览"""
    user = request.user
    today = timezone.localdate()

    # 今日任务
    tasks = Task.objects.filter(is_active=True).order_by('sort_order', 'id')
    today_records = TaskRecord.objects.filter(user=user, completed_date=today)
    done_task_ids = set(today_records.values_list('task_id', flat=True))

    task_list = []
    for t in tasks:
        done_count = today_records.filter(task=t).count()
        task_list.append({
            'id': t.id,
            'name': t.name,
            'description': t.description,
            'category': t.category,
            'category_label': t.get_category_display(),
            'icon': t.icon,
            'points': t.points,
            'carbon_reduction': t.carbon_reduction,
            'daily_limit': t.daily_limit,
            'done_count': done_count,
            'is_done': done_count >= t.daily_limit,
        })

    today_points = today_records.aggregate(s=Sum('points_earned'))['s'] or 0
    total_tasks = len(task_list)
    done_tasks = sum(1 for t in task_list if t['is_done'])
    progress = int(done_tasks / total_tasks * 100) if total_tasks else 0

    # 排行榜速览（本周）
    week_start = today - timezone.timedelta(days=today.weekday())
    top_users = (
        User.objects.filter(is_active=True)
        .annotate(week_points=Sum(
            'task_records__points_earned',
            filter=models_Q_week(week_start)
        ))
        .order_by('-week_points', '-total_points')[:5]
    )
    rank_list = []
    for idx, u in enumerate(top_users, 1):
        rank_list.append({
            'rank': idx,
            'id': u.id,
            'nickname': u.nickname,
            'avatar': u.avatar_emoji,
            'points': u.total_points,
            'is_me': u.id == user.id,
        })

    return Response({
        'user': {
            'nickname': user.nickname,
            'total_points': user.total_points,
            'available_points': user.available_points,
            'streak_days': user.streak_days,
            'level': user.level,
            'level_title': user.level_title,
            'total_carbon_reduction': round(user.total_carbon_reduction, 2),
            'total_tasks_done': user.total_tasks_done,
        },
        'today': {
            'points': today_points,
            'done_tasks': done_tasks,
            'total_tasks': total_tasks,
            'progress': progress,
        },
        'tasks': task_list,
        'rank_mini': rank_list,
    })


def models_Q_week(week_start):
    """构造本周过滤 Q 对象"""
    from django.db.models import Q
    return Q(task_records__completed_date__gte=week_start)


# ═════════════════════════════════════════════
# 任务
# ═════════════════════════════════════════════
class TaskListView(generics.ListAPIView):
    """任务列表"""
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(is_active=True).order_by('sort_order', 'id')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_task(request, pk):
    """完成低碳任务，获得积分"""
    user = request.user
    today = timezone.localdate()
    try:
        task = Task.objects.get(pk=pk, is_active=True)
    except Task.DoesNotExist:
        return Response({'detail': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)

    today_count = TaskRecord.objects.filter(user=user, task=task, completed_date=today).count()
    if today_count >= task.daily_limit:
        return Response({'detail': '今日该任务已达上限'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        record = TaskRecord.objects.create(
            user=user, task=task, points_earned=task.points
        )
        user.total_points += task.points
        user.available_points += task.points
        user.total_carbon_reduction += task.carbon_reduction
        user.total_tasks_done += 1
        # 连续打卡
        if user.last_checkin_date != today:
            yesterday = today - timezone.timedelta(days=1)
            if user.last_checkin_date == yesterday:
                user.streak_days += 1
            else:
                user.streak_days = 1
            user.last_checkin_date = today
        # 等级
        user.level = _calc_level(user.total_points)
        user.save()

        # 大富翁：完成任务获得掷骰机会
        dice_granted = _grant_dice(user, 1)

        # 自动颁发徽章
        _award_badges(user)

    return Response({
        'message': f'完成成功！+{task.points} 积分' + (f'，获得 1 次掷骰机会 🎲' if dice_granted else ''),
        'points_earned': task.points,
        'dice_granted': dice_granted,
        'user': {
            'total_points': user.total_points,
            'available_points': user.available_points,
            'streak_days': user.streak_days,
            'level': user.level,
            'level_title': user.level_title,
        },
    })


def _grant_dice(user, count):
    """给用户增加骰子次数（受每日上限与囤积上限约束），返回是否实际增加"""
    from .monopoly import DICE_MAX_STOCK, get_player
    player = get_player(user)
    if player.dice_count >= DICE_MAX_STOCK:
        return False
    player.dice_count = min(DICE_MAX_STOCK, player.dice_count + count)
    player.save()
    return True


def _calc_level(total_points):
    """根据累计积分计算等级"""
    if total_points >= 5000:
        return 5
    elif total_points >= 2000:
        return 4
    elif total_points >= 800:
        return 3
    elif total_points >= 300:
        return 2
    return 1


def _award_badges(user):
    """自动颁发满足条件的徽章"""
    badges = Badge.objects.all()
    for b in badges:
        if b.condition_points and user.total_points < b.condition_points:
            continue
        if b.condition_tasks and user.total_tasks_done < b.condition_tasks:
            continue
        UserBadge.objects.get_or_create(user=user, badge=b)


# ═════════════════════════════════════════════
# 挑战
# ═════════════════════════════════════════════
class ChallengeListView(generics.ListAPIView):
    """挑战列表"""
    serializer_class = ChallengeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Challenge.objects.filter(is_active=True).order_by('-created_at')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_challenge(request, pk):
    """加入挑战"""
    user = request.user
    try:
        challenge = Challenge.objects.get(pk=pk, is_active=True)
    except Challenge.DoesNotExist:
        return Response({'detail': '挑战不存在'}, status=status.HTTP_404_NOT_FOUND)

    participation, created = ChallengeParticipation.objects.get_or_create(
        user=user, challenge=challenge
    )
    if not created:
        return Response({'detail': '已加入该挑战'}, status=status.HTTP_400_BAD_REQUEST)

    challenge.participants_count += 1
    challenge.save()
    return Response({'message': '加入成功', 'participation': ChallengeParticipationSerializer(participation).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_challenges(request):
    """我参与的挑战"""
    parts = ChallengeParticipation.objects.filter(user=request.user).select_related('challenge')
    return Response(ChallengeParticipationSerializer(parts, many=True).data)


# ═════════════════════════════════════════════
# 商城
# ═════════════════════════════════════════════
class ShopItemListView(generics.ListAPIView):
    """商城商品列表"""
    serializer_class = ShopItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ShopItem.objects.filter(is_active=True).order_by('-created_at')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def redeem_item(request, pk):
    """兑换商品"""
    user = request.user
    try:
        item = ShopItem.objects.get(pk=pk, is_active=True)
    except ShopItem.DoesNotExist:
        return Response({'detail': '商品不存在'}, status=status.HTTP_404_NOT_FOUND)

    if user.available_points < item.cost:
        return Response({'detail': '积分不足'}, status=status.HTTP_400_BAD_REQUEST)
    if item.stock <= 0:
        return Response({'detail': '库存不足'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        user.available_points -= item.cost
        user.save()
        item.stock -= 1
        item.save()
        Redemption.objects.create(
            user=user, item=item, item_name=item.name, cost=item.cost
        )
    return Response({
        'message': '兑换成功！',
        'available_points': user.available_points,
    })


# ═════════════════════════════════════════════
# 公益捐赠
# ═════════════════════════════════════════════
class CharityProjectListView(generics.ListAPIView):
    """公益项目列表"""
    serializer_class = CharityProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CharityProject.objects.filter(is_active=True).order_by('id')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def donate(request, pk):
    """公益捐赠"""
    user = request.user
    try:
        project = CharityProject.objects.get(pk=pk, is_active=True)
    except CharityProject.DoesNotExist:
        return Response({'detail': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

    if user.available_points < project.cost:
        return Response({'detail': '积分不足'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        user.available_points -= project.cost
        user.save()
        project.total_donated += 1
        project.save()
        Donation.objects.create(
            user=user, project=project, project_name=project.name, cost=project.cost
        )
    return Response({
        'message': '捐赠成功！感谢您的善心',
        'available_points': user.available_points,
    })


# ═════════════════════════════════════════════
# 排行榜
# ═════════════════════════════════════════════
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leaderboard(request):
    """完整排行榜"""
    period = request.query_params.get('period', 'total')  # week/month/total
    today = timezone.localdate()

    if period == 'week':
        start = today - timezone.timedelta(days=today.weekday())
    elif period == 'month':
        start = today.replace(day=1)
    else:
        start = None

    if start:
        users = (
            User.objects.filter(is_active=True)
            .annotate(period_points=Sum(
                'task_records__points_earned',
                filter=__period_filter(start)
            ))
            .order_by('-period_points', '-total_points')
        )
        users_list = [(u, u.period_points or 0) for u in users]
    else:
        users = User.objects.filter(is_active=True).order_by('-total_points')
        users_list = [(u, u.total_points) for u in users]

    result = []
    for idx, (u, pts) in enumerate(users_list[:100], 1):
        result.append({
            'rank': idx,
            'id': u.id,
            'nickname': u.nickname,
            'avatar': u.avatar_emoji,
            'college': u.college,
            'major': u.major,
            'points': pts,
            'total_points': u.total_points,
            'is_me': u.id == request.user.id,
        })
    return Response(result)


def __period_filter(start):
    from django.db.models import Q
    return Q(task_records__completed_date__gte=start)


# ═════════════════════════════════════════════
# 我的 - 绿色记录
# ═════════════════════════════════════════════
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def green_records(request):
    """绿色行为记录（任务记录 + 兑换 + 捐赠）"""
    user = request.user
    records = []

    for r in user.task_records.select_related('task').order_by('-created_at')[:50]:
        records.append({
            'type': 'task',
            'icon': r.task.icon,
            'name': r.task.name,
            'date': r.created_at.strftime('%Y-%m-%d %H:%M'),
            'points': r.points_earned,
            'sign': '+',
        })
    for r in user.redemptions.order_by('-created_at')[:20]:
        records.append({
            'type': 'redeem',
            'icon': '🎁',
            'name': f'兑换 {r.item_name}',
            'date': r.created_at.strftime('%Y-%m-%d %H:%M'),
            'points': r.cost,
            'sign': '-',
        })
    for r in user.donations.order_by('-created_at')[:20]:
        records.append({
            'type': 'donate',
            'icon': '🌳',
            'name': f'捐赠 {r.project_name}',
            'date': r.created_at.strftime('%Y-%m-%d %H:%M'),
            'points': r.cost,
            'sign': '-',
        })

    records.sort(key=lambda x: x['date'], reverse=True)
    return Response(records[:50])


# ═════════════════════════════════════════════
# 徽章
# ═════════════════════════════════════════════
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_badges(request):
    """我的徽章（含未解锁）"""
    user = request.user
    all_badges = Badge.objects.all().order_by('condition_points')
    earned_ids = set(user.badges.values_list('badge_id', flat=True))
    result = []
    for b in all_badges:
        result.append({
            'id': b.id,
            'name': b.name,
            'icon': b.icon,
            'description': b.description,
            'earned': b.id in earned_ids,
        })
    return Response(result)


# ═════════════════════════════════════════════
# 小组
# ═════════════════════════════════════════════
class GroupListView(generics.ListAPIView):
    """小组列表"""
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Group.objects.all().order_by('id')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def group_checkin(request, pk):
    """小组签到"""
    user = request.user
    today = timezone.localdate()
    try:
        group = Group.objects.get(pk=pk)
    except Group.DoesNotExist:
        return Response({'detail': '小组不存在'}, status=status.HTTP_404_NOT_FOUND)

    checkin, created = GroupCheckin.objects.get_or_create(
        user=user, group=group, checkin_date=today
    )
    if not created:
        return Response({'detail': '今日已签到'}, status=status.HTTP_400_BAD_REQUEST)

    user.available_points += checkin.points_earned
    user.total_points += checkin.points_earned
    user.save()
    # 大富翁：小组签到获得掷骰机会
    dice_granted = _grant_dice(user, 1)
    return Response({
        'message': f'签到成功！+{checkin.points_earned} 积分' + (f'，获得 1 次掷骰机会 🎲' if dice_granted else ''),
        'dice_granted': dice_granted,
    })


# ═════════════════════════════════════════════
# 通知
# ═════════════════════════════════════════════
class NotificationListView(generics.ListAPIView):
    """通知列表"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=request.user).order_by('-created_at')[:30]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def read_notification(request, pk):
    """标记通知已读"""
    try:
        n = Notification.objects.get(pk=pk, user=request.user)
    except Notification.DoesNotExist:
        return Response({'detail': '通知不存在'}, status=status.HTTP_404_NOT_FOUND)
    n.is_read = True
    n.save()
    return Response({'message': '已标记已读'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_count(request):
    """未读通知数"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return Response({'count': count})


# ═════════════════════════════════════════════
# 绿色大富翁
# ═════════════════════════════════════════════
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monopoly_overview(request):
    """棋盘全景 + 玩家状态 + 资产 + 排名速览"""
    user = request.user
    player = mp.get_player(user)
    user.refresh_from_db()

    tiles = mp.get_board_tiles()
    board = [mp.tile_detail(t, user) for t in tiles]

    # 我的资产
    my_props = MonopolyProperty.objects.filter(owner=user).select_related('tile', 'owner')
    assets = []
    for p in my_props:
        assets.append({
            'tile_position': p.tile.position,
            'name': p.tile.name,
            'icon': p.tile.icon,
            'level': p.level,
            'toll': mp.calc_toll(p),
            'value': mp.property_value(p),
            'total_toll_collected': p.total_toll_collected,
        })
    asset_value = sum(a['value'] for a in assets)

    # 排名速览（资产榜前5）
    from django.db.models import Sum, F, Value, IntegerField
    from django.db.models.functions import Coalesce
    top = (
        User.objects.annotate(
            prop_count=Coalesce(
                Sum('monopoly_properties__level'), Value(0),
                output_field=IntegerField()
            )
        )
        .filter(prop_count__gt=0)
        .order_by('-prop_count')[:5]
    )
    # 用 Python 计算资产价值（含升级成本，SQL 难以表达）
    rank_list = []
    candidates = list(top) + [user]
    seen = set()
    scored = []
    for u in candidates:
        if u.id in seen:
            continue
        seen.add(u.id)
        scored.append((u, mp.user_asset_value(u)))
    scored.sort(key=lambda x: x[1], reverse=True)
    for idx, (u, val) in enumerate(scored[:5], 1):
        rank_list.append({
            'rank': idx,
            'id': u.id,
            'nickname': u.nickname,
            'avatar': u.avatar_emoji,
            'asset_value': val,
            'is_me': u.id == user.id,
        })

    return Response({
        'player': mp._player_snapshot(player, user),
        'board': board,
        'assets': assets,
        'asset_value': asset_value,
        'rules': {
            'board_size': mp.BOARD_SIZE,
            'start_reward': mp.START_REWARD,
            'dice_daily_limit': mp.DICE_DAILY_LIMIT,
            'dice_max_stock': mp.DICE_MAX_STOCK,
            'max_properties': mp.MAX_PROPERTIES_PER_USER,
            'max_level': mp.MAX_LEVEL,
        },
        'rank_mini': rank_list,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def monopoly_roll(request):
    """掷骰子"""
    try:
        result = mp.roll_dice(request.user)
    except ValueError as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def monopoly_claim(request):
    """认领当前所在场景格"""
    user = request.user
    player = mp.get_player(user)
    tile = mp.get_tile(player.position)
    if not tile:
        return Response({'detail': '格子不存在'}, status=status.HTTP_404_NOT_FOUND)
    try:
        result = mp.claim_property(user, tile)
    except ValueError as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def monopoly_upgrade(request):
    """升级当前所在场景格"""
    user = request.user
    player = mp.get_player(user)
    tile = mp.get_tile(player.position)
    if not tile:
        return Response({'detail': '格子不存在'}, status=status.HTTP_404_NOT_FOUND)
    try:
        result = mp.upgrade_property(user, tile)
    except ValueError as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def monopoly_resolve_event(request):
    """处理事件结果：陷阱答题 / 任务格完成 / 公益格捐赠"""
    user = request.user
    action = request.data.get('action', '')
    player = mp.get_player(user)

    if action == 'trap_answer':
        answer = request.data.get('answer')
        if answer is None:
            return Response({'detail': '缺少 answer 参数'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            answer = int(answer)
        except (TypeError, ValueError):
            return Response({'detail': 'answer 必须是数字'}, status=status.HTTP_400_BAD_REQUEST)
        result = mp.resolve_trap(user, answer)
        return Response(result)

    if action == 'task_done':
        # 任务格：奖励少量积分（复用任务完成思路，给固定奖励）
        from .monopoly import log_action
        reward = 10
        user.refresh_from_db()
        user.available_points += reward
        user.save()
        log_action(user, MonopolyLog.ActionType.TASK,
                   tile_position=player.position, points_change=reward,
                   description='任务格完成奖励')
        return Response({'message': f'任务格奖励 +{reward} 积分', 'reward': reward,
                         'available_points': user.available_points})

    if action == 'charity_done':
        # 公益格：标记已处理（实际捐赠走商城公益接口）
        return Response({'message': '请前往商城完成公益捐赠'})

    return Response({'detail': '未知 action'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monopoly_logs(request):
    """我的游戏日志"""
    logs = MonopolyLog.objects.filter(user=request.user)[:30]
    return Response(MonopolyLogSerializer(logs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monopoly_leaderboard(request):
    """大富翁资产排行榜"""
    user = request.user
    # 取所有拥有场景的用户
    owner_ids = MonopolyProperty.objects.filter(level__gte=1).values_list('owner_id', flat=True).distinct()
    users = list(User.objects.filter(id__in=owner_ids))
    if user.id not in {u.id for u in users}:
        users.append(user)
    scored = [(u, mp.user_asset_value(u)) for u in users]
    scored.sort(key=lambda x: x[1], reverse=True)

    result = []
    for idx, (u, val) in enumerate(scored[:100], 1):
        prop_count = MonopolyProperty.objects.filter(owner=u, level__gte=1).count()
        result.append({
            'rank': idx,
            'id': u.id,
            'nickname': u.nickname,
            'avatar': u.avatar_emoji,
            'college': u.college,
            'asset_value': val,
            'property_count': prop_count,
            'is_me': u.id == user.id,
        })
    return Response(result)
