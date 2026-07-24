"""
用户模型 —— 绿动校园
自定义用户模型，集成绿色积分、等级、连续打卡等字段
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """扩展用户模型"""

    class Gender(models.TextChoices):
        MALE = 'male', '男'
        FEMALE = 'female', '女'
        UNKNOWN = 'unknown', '保密'

    # 基础信息
    nickname = models.CharField('昵称', max_length=30, default='低碳新人')
    avatar = models.CharField('头像URL', max_length=255, blank=True, default='')
    gender = models.CharField('性别', max_length=10, choices=Gender.choices, default=Gender.UNKNOWN)
    phone = models.CharField('手机号', max_length=20, blank=True, default='')
    student_id = models.CharField('学号', max_length=20, blank=True, default='')
    college = models.CharField('学院', max_length=50, blank=True, default='')
    major = models.CharField('专业', max_length=50, blank=True, default='')

    # 积分与等级
    total_points = models.PositiveIntegerField('累计绿色积分', default=0)
    available_points = models.PositiveIntegerField('可用积分', default=0)
    level = models.PositiveIntegerField('等级', default=1)

    # 打卡与减碳
    streak_days = models.PositiveIntegerField('连续打卡天数', default=0)
    last_checkin_date = models.DateField('最后打卡日期', null=True, blank=True)
    total_carbon_reduction = models.FloatField('累计减碳量(kg)', default=0.0)
    total_tasks_done = models.PositiveIntegerField('累计完成任务数', default=0)

    # 时间
    created_at = models.DateTimeField('注册时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        ordering = ['-total_points']

    def __str__(self):
        return f'{self.nickname}({self.username})'

    @property
    def level_title(self):
        """根据累计积分返回等级称号"""
        titles = [
            (300, '低碳新人'),
            (800, '低碳学徒'),
            (2000, '低碳达人'),
            (5000, '低碳先锋'),
            (999999, '低碳守护者'),
        ]
        for threshold, title in titles:
            if self.total_points < threshold:
                return title
        return '低碳守护者'

    @property
    def avatar_emoji(self):
        """无头像时返回 emoji 占位"""
        return self.avatar or '🌱'
