"""
核心业务模型 —— 绿动校园
包含：任务、挑战、商品、公益项目、行为记录、兑换记录、徽章、小组
"""
from django.db import models
from django.conf import settings


# ─────────────────────────────────────────────
# 1. 低碳任务
# ─────────────────────────────────────────────
class Task(models.Model):
    """每日低碳任务"""

    class Category(models.TextChoices):
        DINING = 'dining', '餐饮'
        ENERGY = 'energy', '用电'
        TRAVEL = 'travel', '出行'
        SHOPPING = 'shopping', '购物'
        STUDY = 'study', '学习'
        RESOURCE = 'resource', '资源'

    name = models.CharField('任务名称', max_length=50)
    description = models.CharField('任务描述', max_length=200, blank=True, default='')
    category = models.CharField('行为类别', max_length=20, choices=Category.choices, default=Category.DINING)
    icon = models.CharField('图标(emoji)', max_length=10, default='🌱')
    points = models.PositiveIntegerField('积分奖励', default=5)
    carbon_reduction = models.FloatField('减碳量(kg)', default=0.5)
    daily_limit = models.PositiveIntegerField('每日次数上限', default=1)
    is_active = models.BooleanField('是否启用', default=True)
    sort_order = models.PositiveIntegerField('排序', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '低碳任务'
        verbose_name_plural = '低碳任务'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.icon} {self.name} (+{self.points})'


class TaskRecord(models.Model):
    """用户任务完成记录"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_records')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='records')
    completed_date = models.DateField('完成日期', auto_now_add=True)
    created_at = models.DateTimeField('完成时间', auto_now_add=True)
    points_earned = models.PositiveIntegerField('获得积分', default=0)

    class Meta:
        verbose_name = '任务记录'
        verbose_name_plural = '任务记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.nickname} - {self.task.name} - {self.completed_date}'


# ─────────────────────────────────────────────
# 2. 校园挑战
# ─────────────────────────────────────────────
class Challenge(models.Model):
    """校园挑战"""

    class Status(models.TextChoices):
        ONGOING = 'ongoing', '进行中'
        ENDED = 'ended', '已结束'
        UPCOMING = 'upcoming', '即将开始'

    title = models.CharField('挑战名称', max_length=80)
    description = models.TextField('挑战描述', max_length=500, blank=True, default='')
    cover = models.CharField('封面图URL/emoji', max_length=255, default='🌍')
    tag = models.CharField('标签', max_length=20, blank=True, default='热门')
    points = models.PositiveIntegerField('完成积分', default=100)
    target_count = models.PositiveIntegerField('目标完成次数', default=7)
    start_date = models.DateField('开始日期', null=True, blank=True)
    end_date = models.DateField('结束日期', null=True, blank=True)
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.ONGOING)
    participants_count = models.PositiveIntegerField('参与人数', default=0)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '校园挑战'
        verbose_name_plural = '校园挑战'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ChallengeParticipation(models.Model):
    """用户参与挑战记录"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='challenges')
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='participants')
    progress = models.PositiveIntegerField('当前进度', default=0)
    is_completed = models.BooleanField('是否完成', default=False)
    joined_at = models.DateTimeField('加入时间', auto_now_add=True)

    class Meta:
        verbose_name = '挑战参与'
        verbose_name_plural = '挑战参与'
        unique_together = ('user', 'challenge')

    def __str__(self):
        return f'{self.user.nickname} - {self.challenge.title}'


# ─────────────────────────────────────────────
# 3. 积分商城
# ─────────────────────────────────────────────
class ShopItem(models.Model):
    """商城商品"""

    class Tag(models.TextChoices):
        NONE = '', '普通'
        HOT = 'hot', '热门'
        NEW = 'new', '新品'
        RARE = 'rare', '稀有'

    name = models.CharField('商品名称', max_length=80)
    description = models.CharField('商品描述', max_length=200, blank=True, default='')
    image = models.CharField('商品图片URL/emoji', max_length=255, default='🎁')
    cost = models.PositiveIntegerField('兑换积分', default=100)
    stock = models.IntegerField('库存', default=100)
    tag = models.CharField('标签', max_length=10, choices=Tag.choices, default=Tag.NONE)
    is_active = models.BooleanField('是否上架', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '商城商品'
        verbose_name_plural = '商城商品'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.cost}积分)'


class Redemption(models.Model):
    """兑换记录"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='redemptions')
    item = models.ForeignKey(ShopItem, on_delete=models.SET_NULL, null=True, related_name='redemptions')
    item_name = models.CharField('商品名称快照', max_length=80, default='')
    cost = models.PositiveIntegerField('消耗积分', default=0)
    created_at = models.DateTimeField('兑换时间', auto_now_add=True)

    class Meta:
        verbose_name = '兑换记录'
        verbose_name_plural = '兑换记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.nickname} - {self.item_name}'


# ─────────────────────────────────────────────
# 4. 公益项目
# ─────────────────────────────────────────────
class CharityProject(models.Model):
    """公益捐赠项目"""
    name = models.CharField('项目名称', max_length=80)
    description = models.CharField('项目描述', max_length=200, blank=True, default='')
    icon = models.CharField('图标(emoji)', max_length=10, default='🌳')
    cost = models.PositiveIntegerField('捐赠所需积分', default=50)
    is_active = models.BooleanField('是否启用', default=True)
    total_donated = models.PositiveIntegerField('累计捐赠次数', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '公益项目'
        verbose_name_plural = '公益项目'
        ordering = ['id']

    def __str__(self):
        return self.name


class Donation(models.Model):
    """捐赠记录"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='donations')
    project = models.ForeignKey(CharityProject, on_delete=models.SET_NULL, null=True, related_name='donations')
    project_name = models.CharField('项目名称快照', max_length=80, default='')
    cost = models.PositiveIntegerField('消耗积分', default=0)
    created_at = models.DateTimeField('捐赠时间', auto_now_add=True)

    class Meta:
        verbose_name = '捐赠记录'
        verbose_name_plural = '捐赠记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.nickname} - {self.project_name}'


# ─────────────────────────────────────────────
# 5. 徽章
# ─────────────────────────────────────────────
class Badge(models.Model):
    """徽章成就"""

    class Category(models.TextChoices):
        GENERAL = 'general', '通用'
        MONOPOLY = 'monopoly', '大富翁'

    name = models.CharField('徽章名称', max_length=30)
    icon = models.CharField('图标(emoji)', max_length=10, default='🏅')
    description = models.CharField('描述', max_length=100, blank=True, default='')
    category = models.CharField('徽章类别', max_length=20, choices=Category.choices, default=Category.GENERAL)
    condition_points = models.PositiveIntegerField('达成所需累计积分', default=0)
    condition_tasks = models.PositiveIntegerField('达成所需完成任务数', default=0)
    # 大富翁徽章触发标识（如 first_roll / first_claim / landlord / max_level / lap / toll_200）
    monopoly_key = models.CharField('大富翁触发标识', max_length=30, blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '徽章'
        verbose_name_plural = '徽章'
        ordering = ['category', 'condition_points']

    def __str__(self):
        return f'{self.icon} {self.name}'


class UserBadge(models.Model):
    """用户已获得徽章"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='holders')
    earned_at = models.DateTimeField('获得时间', auto_now_add=True)

    class Meta:
        verbose_name = '用户徽章'
        verbose_name_plural = '用户徽章'
        unique_together = ('user', 'badge')

    def __str__(self):
        return f'{self.user.nickname} - {self.badge.name}'


# ─────────────────────────────────────────────
# 6. 低碳小组
# ─────────────────────────────────────────────
class Group(models.Model):
    """低碳小组"""
    name = models.CharField('小组名称', max_length=50)
    description = models.CharField('小组描述', max_length=200, blank=True, default='')
    icon = models.CharField('图标(emoji)', max_length=10, default='👥')
    member_count = models.PositiveIntegerField('成员数', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '低碳小组'
        verbose_name_plural = '低碳小组'
        ordering = ['id']

    def __str__(self):
        return self.name


class GroupCheckin(models.Model):
    """小组签到记录"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_checkins')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='checkins')
    checkin_date = models.DateField('签到日期', auto_now_add=True)
    points_earned = models.PositiveIntegerField('获得积分', default=3)

    class Meta:
        verbose_name = '小组签到'
        verbose_name_plural = '小组签到'
        unique_together = ('user', 'group', 'checkin_date')
        ordering = ['-checkin_date']

    def __str__(self):
        return f'{self.user.nickname} - {self.group.name} - {self.checkin_date}'


# ─────────────────────────────────────────────
# 7. 通知
# ─────────────────────────────────────────────
class Notification(models.Model):
    """站内通知"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField('标题', max_length=80)
    content = models.CharField('内容', max_length=200, blank=True, default='')
    is_read = models.BooleanField('是否已读', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.nickname} - {self.title}'


# ─────────────────────────────────────────────
# 8. 绿色大富翁
# ─────────────────────────────────────────────
class MonopolyTile(models.Model):
    """大富翁棋盘格子配置"""

    class TileType(models.TextChoices):
        START = 'start', '起点'
        SCENE = 'scene', '低碳场景'
        CHANCE = 'chance', '绿色机遇'
        CRISIS = 'crisis', '碳危机'
        TASK = 'task', '任务格'
        CHARITY = 'charity', '公益格'
        TRAP = 'trap', '高碳陷阱'

    position = models.PositiveIntegerField('位置(1-24)', unique=True)
    tile_type = models.CharField('格子类型', max_length=20, choices=TileType.choices)
    name = models.CharField('名称', max_length=30)
    icon = models.CharField('图标', max_length=10, default='📍')
    description = models.CharField('描述', max_length=100, blank=True, default='')
    # 场景格专属
    claim_cost = models.PositiveIntegerField('认领积分', default=0)
    upgrade_cost = models.PositiveIntegerField('升级积分', default=0)
    base_toll = models.PositiveIntegerField('基础过路费', default=0)
    is_active = models.BooleanField('是否启用', default=True)

    class Meta:
        verbose_name = '大富翁格子'
        verbose_name_plural = '大富翁格子'
        ordering = ['position']

    def __str__(self):
        return f'{self.position}. {self.icon} {self.name}'


class MonopolyPlayer(models.Model):
    """玩家大富翁状态（每用户一行）"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='monopoly')
    position = models.PositiveIntegerField('当前位置', default=1)  # 1=起点
    dice_count = models.PositiveIntegerField('可用骰子次数', default=0)
    total_steps = models.PositiveIntegerField('累计步数', default=0)
    laps = models.PositiveIntegerField('绕场圈数', default=0)
    is_trapped = models.BooleanField('是否被困', default=False)
    trap_attempts = models.PositiveIntegerField('脱困答题次数', default=0)
    last_play_at = models.DateTimeField('最后游戏时间', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '大富翁玩家'
        verbose_name_plural = '大富翁玩家'

    def __str__(self):
        return f'{self.user.nickname} @ {self.position} (🎲{self.dice_count})'


class MonopolyProperty(models.Model):
    """低碳场景的认领/升级状态"""
    tile = models.OneToOneField(MonopolyTile, on_delete=models.CASCADE, related_name='property')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='monopoly_properties')
    level = models.PositiveIntegerField('等级', default=0)  # 0=未认领, 1~3
    total_toll_collected = models.PositiveIntegerField('累计收取过路费', default=0)
    claimed_at = models.DateTimeField('认领时间', null=True, blank=True)

    class Meta:
        verbose_name = '大富翁场景'
        verbose_name_plural = '大富翁场景'

    def __str__(self):
        owner = self.owner.nickname if self.owner else '无主'
        return f'{self.tile.name} - {owner} Lv.{self.level}'


class MonopolyLog(models.Model):
    """大富翁操作日志"""

    class ActionType(models.TextChoices):
        ROLL = 'roll', '掷骰'
        CLAIM = 'claim', '认领'
        UPGRADE = 'upgrade', '升级'
        TOLL = 'toll', '过路费'
        EVENT = 'event', '事件'
        TASK = 'task', '任务'
        CHARITY = 'charity', '公益'
        TRAP = 'trap', '陷阱'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='monopoly_logs')
    action = models.CharField('动作类型', max_length=20, choices=ActionType.choices)
    tile_position = models.PositiveIntegerField('相关格子', null=True, blank=True)
    dice_value = models.PositiveIntegerField('骰子点数', null=True, blank=True)
    points_change = models.IntegerField('积分变动', default=0)  # 正=获得，负=消耗
    description = models.CharField('描述', max_length=200, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '大富翁日志'
        verbose_name_plural = '大富翁日志'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.nickname} {self.action} {self.description}'


class MonopolyEvent(models.Model):
    """机遇/危机事件池"""

    class EventType(models.TextChoices):
        CHANCE = 'chance', '绿色机遇'
        CRISIS = 'crisis', '碳危机'

    event_type = models.CharField('事件类型', max_length=10, choices=EventType.choices)
    description = models.CharField('事件描述', max_length=200)
    points_change = models.IntegerField('积分变动', default=0)
    extra_dice = models.PositiveIntegerField('额外骰子', default=0)
    is_active = models.BooleanField('是否启用', default=True)

    class Meta:
        verbose_name = '大富翁事件'
        verbose_name_plural = '大富翁事件'
        ordering = ['id']

    def __str__(self):
        return f'[{self.get_event_type_display()}] {self.description}'
