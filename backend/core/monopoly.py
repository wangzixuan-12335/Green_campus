"""
绿色大富翁 · 核心玩法逻辑
集中管理：棋盘常量、升级费用、题库、事件应用、徽章颁发、资产价值计算。
"""
import random

from django.db import transaction
from django.utils import timezone

from .models import (
    MonopolyTile, MonopolyPlayer, MonopolyProperty, MonopolyLog,
    MonopolyEvent, Badge, UserBadge,
)

# ─── 棋盘常量 ───
BOARD_SIZE = 24
START_POSITION = 1
START_REWARD = 15          # 经过起点奖励积分
DICE_DAILY_LIMIT = 6       # 每日骰子上限
DICE_MAX_STOCK = 20        # 骰子囤积上限
MAX_PROPERTIES_PER_USER = 3  # 每人最多认领场景数
MAX_LEVEL = 3              # 场景最高等级

# 升级费用表：level -> 升到下一级所需积分（PRD：Lv1认领50，Lv2升级+80，Lv3升级+150）
# 认领价由 tile.claim_cost 决定，升级价由 tile.upgrade_cost 决定，这里仅作兜底默认
DEFAULT_UPGRADE_COST = {1: 80, 2: 150}

# 过路费等级倍率：Lv.1 ×1，Lv.2 ×2，Lv.3 ×3
TOLL_MULTIPLIER = {1: 1, 2: 2, 3: 3}


def get_player(user):
    """获取或创建玩家状态"""
    player, _ = MonopolyPlayer.objects.get_or_create(user=user)
    return player


def get_tile(position):
    """按位置取格子（position 范围 1~24）"""
    pos = ((position - 1) % BOARD_SIZE) + 1
    return MonopolyTile.objects.filter(position=pos, is_active=True).first()


def get_board_tiles():
    """返回按位置排序的全部启用格子"""
    return list(MonopolyTile.objects.filter(is_active=True).order_by('position'))


def property_value(prop):
    """计算单个场景的资产价值（已投入的认领+升级成本）"""
    if not prop or prop.level == 0:
        return 0
    tile = prop.tile
    value = tile.claim_cost
    for lv in range(1, prop.level):
        value += tile.upgrade_cost or DEFAULT_UPGRADE_COST.get(lv, 0)
    return value


def user_asset_value(user):
    """玩家大富翁资产总价值"""
    props = MonopolyProperty.objects.filter(owner=user).select_related('tile')
    return sum(property_value(p) for p in props)


def calc_toll(prop):
    """计算过路费 = 基础过路费 × 等级倍率"""
    if not prop or prop.level == 0:
        return 0
    return prop.tile.base_toll * TOLL_MULTIPLIER.get(prop.level, 1)


def upgrade_cost_for(prop):
    """当前等级升到下一级所需积分"""
    if prop.level >= MAX_LEVEL:
        return None
    return prop.tile.upgrade_cost or DEFAULT_UPGRADE_COST.get(prop.level, 0)


def claim_cost_for(tile):
    return tile.claim_cost


# ─── 低碳知识题库（陷阱格赎身用）───
TRAP_QUIZ = [
    {
        'question': '空调温度设置在多少度以上最节能？',
        'options': ['20℃', '24℃', '26℃', '28℃'],
        'answer': 2,
    },
    {
        'question': '以下哪种出行方式人均碳排放最低？',
        'options': ['私家车', '地铁', '骑行', '飞机'],
        'answer': 2,
    },
    {
        'question': '一个塑料瓶自然降解大约需要多少年？',
        'options': ['1年', '10年', '100年', '450年以上'],
        'answer': 3,
    },
    {
        'question': '“光盘行动”主要倡导的是？',
        'options': ['拒绝浪费食物', '使用光盘存储', '光盘回收', '光盘游戏'],
        'answer': 0,
    },
    {
        'question': '下列哪种行为不能减少碳排放？',
        'options': ['随手关灯', '少用一次性餐具', '长时间开空调', '乘坐公交'],
        'answer': 2,
    },
    {
        'question': '垃圾分类中，废旧电池属于？',
        'options': ['可回收物', '有害垃圾', '厨余垃圾', '其他垃圾'],
        'answer': 1,
    },
    {
        'question': '一棵成年树每年大约能吸收多少千克二氧化碳？',
        'options': ['约2kg', '约22kg', '约220kg', '约2200kg'],
        'answer': 1,
    },
    {
        'question': '以下哪种光源最节能？',
        'options': ['白炽灯', '卤素灯', 'LED灯', '荧光灯'],
        'answer': 2,
    },
]


def get_quiz():
    """随机取一道赎身题"""
    return random.choice(TRAP_QUIZ)


# ─── 大富翁徽章触发 ───
MONOPOLY_BADGE_KEYS = {
    'first_roll': '初次掷骰',
    'first_claim': '场景新主',
    'landlord': '校园地主',
    'max_level': '满级场景',
    'lap': '环游一圈',
    'toll_200': '过路费大亨',
}


def award_monopoly_badge(user, key):
    """按 monopoly_key 颁发大富翁徽章，返回是否新颁发"""
    try:
        badge = Badge.objects.get(category=Badge.Category.MONOPOLY, monopoly_key=key)
    except Badge.DoesNotExist:
        return None
    _, created = UserBadge.objects.get_or_create(user=user, badge=badge)
    return badge if created else None


def check_monopoly_badges(user, player, context=None):
    """根据玩家状态批量检查并颁发大富翁徽章，返回新颁发列表"""
    context = context or {}
    newly = []

    def try_award(key):
        b = award_monopoly_badge(user, key)
        if b:
            newly.append(b)

    # 首次掷骰
    if context.get('first_roll'):
        try_award('first_roll')
    # 认领相关
    if context.get('first_claim'):
        try_award('first_claim')
    owned = MonopolyProperty.objects.filter(owner=user, level__gte=1).count()
    if owned >= 3:
        try_award('landlord')
    # 满级场景
    if MonopolyProperty.objects.filter(owner=user, level=MAX_LEVEL).exists():
        try_award('max_level')
    # 环游一圈
    if player.laps >= 1:
        try_award('lap')
    # 过路费大亨：累计收取 200
    total_toll = MonopolyProperty.objects.filter(owner=user).aggregate(
        s=__import__('django.db.models', fromlist=['Sum']).Sum('total_toll_collected')
    )['s'] or 0
    if total_toll >= 200:
        try_award('toll_200')

    return newly


# ─── 事件应用 ───
def pick_event(event_type):
    """随机抽取一个启用事件"""
    qs = MonopolyEvent.objects.filter(event_type=event_type, is_active=True)
    events = list(qs)
    if not events:
        return None
    return random.choice(events)


def apply_event(user, event):
    """应用机遇/危机事件，返回 (points_change, extra_dice, description)"""
    if not event:
        return 0, 0, '暂无可用事件'
    points_change = event.points_change
    extra_dice = event.extra_dice
    # 负面事件扣分不超过当前可用积分
    if points_change < 0:
        points_change = max(points_change, -user.available_points)
    if points_change:
        user.available_points = max(0, user.available_points + points_change)
    return points_change, extra_dice, event.description


# ─── 日志记录 ───
def log_action(user, action, *, tile_position=None, dice_value=None,
               points_change=0, description=''):
    MonopolyLog.objects.create(
        user=user, action=action,
        tile_position=tile_position, dice_value=dice_value,
        points_change=points_change, description=description,
    )


# ─── 掷骰核心 ───
@transaction.atomic
def roll_dice(user):
    """
    执行一次掷骰，处理：移动、起点奖励、过路费、事件触发、陷阱。
    返回 dict 结果。
    """
    player = get_player(user)
    user.refresh_from_db()

    # 被困：本次跳过并自动释放
    if player.is_trapped:
        player.is_trapped = False
        player.trap_attempts = 0
        player.save()
        log_action(user, MonopolyLog.ActionType.TRAP,
                   tile_position=player.position,
                   description='被困一回合，现已释放')
        return {
            'trapped_released': True,
            'dice_value': 0,
            'new_position': player.position,
            'passed_start': False,
            'tile_event': {'type': 'trap_released', 'message': '被困一回合，现已释放，下次可正常掷骰'},
            'player': _player_snapshot(player, user),
        }

    if player.dice_count <= 0:
        raise ValueError('骰子次数不足，完成低碳任务或小组签到可获得掷骰机会')

    dice = random.randint(1, 6)
    old_position = player.position
    new_position = old_position + dice
    passed_start = new_position > BOARD_SIZE
    # 归位到 1~24
    new_position = ((new_position - 1) % BOARD_SIZE) + 1

    # 消耗一次骰子
    player.dice_count -= 1
    player.total_steps += dice
    player.position = new_position
    player.last_play_at = timezone.now()

    events_summary = []
    points_delta = 0

    # 经过起点奖励
    if passed_start:
        player.laps += 1
        user.available_points += START_REWARD
        points_delta += START_REWARD
        events_summary.append(f'经过起点 +{START_REWARD} 积分')

    tile = get_tile(new_position)
    tile_event = None

    if tile:
        # ── 场景格：过路费 ──
        if tile.tile_type == MonopolyTile.TileType.SCENE:
            prop = getattr(tile, 'property', None)
            if prop and prop.owner_id and prop.owner_id != user.id:
                toll = calc_toll(prop)
                if toll > 0:
                    pay = min(toll, user.available_points)
                    user.available_points -= pay
                    points_delta -= pay
                    # 收取方加积分
                    owner = prop.owner
                    owner.available_points += pay
                    owner.save()
                    prop.total_toll_collected += pay
                    prop.save()
                    log_action(owner, MonopolyLog.ActionType.TOLL,
                               tile_position=tile.position, points_change=pay,
                               description=f'{user.nickname} 路过 {tile.name} 支付过路费')
                    tile_event = {
                        'type': 'toll',
                        'owner': _user_brief(owner),
                        'level': prop.level,
                        'toll': pay,
                        'points_after': user.available_points,
                        'message': f'路过 {tile.name}，向 {owner.nickname} 支付碳排放费 {pay} 积分',
                    }
                    events_summary.append(f'过路费 -{pay}')
            elif prop and prop.owner_id == user.id:
                tile_event = {'type': 'own_scene', 'message': f'回到自己的 {tile.name}，无需支付'}

        # ── 绿色机遇 ──
        elif tile.tile_type == MonopolyTile.TileType.CHANCE:
            event = pick_event(MonopolyEvent.EventType.CHANCE)
            pc, ed, desc = apply_event(user, event)
            points_delta += pc
            if ed:
                player.dice_count = min(DICE_MAX_STOCK, player.dice_count + ed)
            tile_event = {
                'type': 'chance',
                'description': desc,
                'points_change': pc,
                'extra_dice': ed,
                'points_after': user.available_points,
                'message': f'绿色机遇：{desc}' + (f'（+{pc}积分）' if pc else '') + (f'（+{ed}骰子）' if ed else ''),
            }
            log_action(user, MonopolyLog.ActionType.EVENT,
                       tile_position=tile.position, points_change=pc,
                       description=f'机遇：{desc}')
            events_summary.append(desc)

        # ── 碳危机 ──
        elif tile.tile_type == MonopolyTile.TileType.CRISIS:
            event = pick_event(MonopolyEvent.EventType.CRISIS)
            pc, ed, desc = apply_event(user, event)
            points_delta += pc
            tile_event = {
                'type': 'crisis',
                'description': desc,
                'points_change': pc,
                'points_after': user.available_points,
                'message': f'碳危机：{desc}' + (f'（{pc}积分）' if pc else ''),
            }
            log_action(user, MonopolyLog.ActionType.EVENT,
                       tile_position=tile.position, points_change=pc,
                       description=f'危机：{desc}')
            events_summary.append(desc)

        # ── 任务格：提示去完成任务 ──
        elif tile.tile_type == MonopolyTile.TileType.TASK:
            tile_event = {
                'type': 'task',
                'message': '触发任务格！去完成一个低碳任务可获得额外积分',
            }

        # ── 公益格 ──
        elif tile.tile_type == MonopolyTile.TileType.CHARITY:
            tile_event = {
                'type': 'charity',
                'message': '触发公益格！可前往商城捐赠积分做公益',
            }

        # ── 高碳陷阱 ──
        elif tile.tile_type == MonopolyTile.TileType.TRAP:
            player.is_trapped = True
            tile_event = {
                'type': 'trap',
                'message': '踩中高碳陷阱！停留一回合，或答对低碳知识题立即脱困',
                'quiz': get_quiz(),
            }
            log_action(user, MonopolyLog.ActionType.TRAP,
                       tile_position=tile.position,
                       description='踩中高碳陷阱')

        # ── 起点 ──
        elif tile.tile_type == MonopolyTile.TileType.START:
            tile_event = {'type': 'start', 'message': f'回到起点！获得 {START_REWARD} 积分'}

    user.save()
    player.save()

    # 记录掷骰日志
    log_action(user, MonopolyLog.ActionType.ROLL,
               tile_position=new_position, dice_value=dice,
               points_change=points_delta,
               description='掷骰 ' + '；'.join(events_summary) if events_summary else f'掷出 {dice} 点')

    # 首次掷骰徽章
    first_roll = player.total_steps == dice
    newly = check_monopoly_badges(user, player, {'first_roll': first_roll})

    return {
        'dice_value': dice,
        'new_position': new_position,
        'passed_start': passed_start,
        'start_reward': START_REWARD if passed_start else 0,
        'tile': _tile_brief(tile) if tile else None,
        'tile_event': tile_event,
        'points_delta': points_delta,
        'player': _player_snapshot(player, user),
        'new_badges': [_badge_brief(b) for b in newly],
    }


# ─── 认领 / 升级 ───
@transaction.atomic
def claim_property(user, tile):
    """认领场景格"""
    player = get_player(user)
    user.refresh_from_db()
    if tile.tile_type != MonopolyTile.TileType.SCENE:
        raise ValueError('该格子不是低碳场景，无法认领')
    if player.position != tile.position:
        raise ValueError('只能认领当前所在格子')
    prop, _ = MonopolyProperty.objects.get_or_create(tile=tile)
    if prop.owner_id:
        raise ValueError('该场景已被认领')
    owned = MonopolyProperty.objects.filter(owner=user, level__gte=1).count()
    if owned >= MAX_PROPERTIES_PER_USER:
        raise ValueError(f'每人最多认领 {MAX_PROPERTIES_PER_USER} 个场景')
    cost = claim_cost_for(tile)
    if user.available_points < cost:
        raise ValueError('积分不足，无法认领')
    user.available_points -= cost
    user.save()
    prop.owner = user
    prop.level = 1
    prop.claimed_at = timezone.now()
    prop.save()
    log_action(user, MonopolyLog.ActionType.CLAIM,
               tile_position=tile.position, points_change=-cost,
               description=f'认领 {tile.name}')
    newly = check_monopoly_badges(user, player, {'first_claim': owned == 0})
    return {
        'message': f'认领成功！{tile.name} 归你所有',
        'cost': cost,
        'level': prop.level,
        'available_points': user.available_points,
        'new_badges': [_badge_brief(b) for b in newly],
    }


@transaction.atomic
def upgrade_property(user, tile):
    """升级场景格"""
    player = get_player(user)
    user.refresh_from_db()
    if tile.tile_type != MonopolyTile.TileType.SCENE:
        raise ValueError('该格子不是低碳场景，无法升级')
    if player.position != tile.position:
        raise ValueError('只能升级当前所在格子')
    prop = getattr(tile, 'property', None)
    if not prop or prop.owner_id != user.id:
        raise ValueError('只能升级自己拥有的场景')
    if prop.level >= MAX_LEVEL:
        raise ValueError('该场景已满级')
    cost = upgrade_cost_for(prop)
    if cost is None:
        raise ValueError('该场景已满级')
    if user.available_points < cost:
        raise ValueError('积分不足，无法升级')
    user.available_points -= cost
    user.save()
    prop.level += 1
    prop.save()
    log_action(user, MonopolyLog.ActionType.UPGRADE,
               tile_position=tile.position, points_change=-cost,
               description=f'升级 {tile.name} 至 Lv.{prop.level}')
    newly = check_monopoly_badges(user, player, {})
    return {
        'message': f'升级成功！{tile.name} 升至 Lv.{prop.level}',
        'cost': cost,
        'level': prop.level,
        'available_points': user.available_points,
        'new_badges': [_badge_brief(b) for b in newly],
    }


@transaction.atomic
def resolve_trap(user, answer_index):
    """陷阱格答题赎身。answer_index 为选项序号。返回是否脱困。"""
    player = get_player(user)
    if not player.is_trapped:
        return {'released': True, 'message': '当前未被困'}
    quiz = get_quiz()
    player.trap_attempts += 1
    correct = answer_index == quiz['answer']
    if correct:
        player.is_trapped = False
        player.trap_attempts = 0
        player.save()
        log_action(user, MonopolyLog.ActionType.TRAP,
                   tile_position=player.position,
                   description='答对低碳题，成功脱困')
        return {'released': True, 'message': '答对了！成功脱困，可继续掷骰'}
    # 连续 3 次答错强制释放
    if player.trap_attempts >= 3:
        player.is_trapped = False
        player.trap_attempts = 0
        player.save()
        log_action(user, MonopolyLog.ActionType.TRAP,
                   tile_position=player.position,
                   description='连续答错3次，强制释放')
        return {'released': True, 'message': '答错了，但已连续3次，强制释放'}
    player.save()
    return {
        'released': False,
        'message': f'答错了，还剩 {3 - player.trap_attempts} 次机会',
        'quiz': get_quiz(),
    }


# ─── 序列化辅助 ───
def _user_brief(user):
    return {
        'id': user.id,
        'nickname': user.nickname,
        'avatar': user.avatar_emoji,
    }


def _tile_brief(tile):
    return {
        'position': tile.position,
        'tile_type': tile.tile_type,
        'name': tile.name,
        'icon': tile.icon,
        'description': tile.description,
    }


def _player_snapshot(player, user):
    return {
        'position': player.position,
        'dice_count': player.dice_count,
        'total_steps': player.total_steps,
        'laps': player.laps,
        'is_trapped': player.is_trapped,
        'available_points': user.available_points,
    }


def _badge_brief(badge):
    return {
        'id': badge.id,
        'name': badge.name,
        'icon': badge.icon,
        'description': badge.description,
    }


def tile_detail(tile, current_user):
    """格子详情（含所有权）"""
    data = _tile_brief(tile)
    data['claim_cost'] = tile.claim_cost
    data['upgrade_cost'] = tile.upgrade_cost
    data['base_toll'] = tile.base_toll
    prop = getattr(tile, 'property', None)
    if prop and prop.owner_id:
        data['owner'] = _user_brief(prop.owner)
        data['level'] = prop.level
        data['toll'] = calc_toll(prop)
        data['is_mine'] = prop.owner_id == current_user.id
    else:
        data['owner'] = None
        data['level'] = 0
        data['toll'] = 0
        data['is_mine'] = False
    return data
