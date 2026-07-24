"""
核心业务路由
"""
from django.urls import path
from . import views

urlpatterns = [
    # 首页
    path('home/', views.home_overview, name='home'),

    # 任务
    path('tasks/', views.TaskListView.as_view(), name='task-list'),
    path('tasks/<int:pk>/complete/', views.complete_task, name='task-complete'),

    # 挑战
    path('challenges/', views.ChallengeListView.as_view(), name='challenge-list'),
    path('challenges/<int:pk>/join/', views.join_challenge, name='challenge-join'),
    path('challenges/mine/', views.my_challenges, name='my-challenges'),

    # 商城
    path('shop/', views.ShopItemListView.as_view(), name='shop-list'),
    path('shop/<int:pk>/redeem/', views.redeem_item, name='shop-redeem'),

    # 公益
    path('charity/', views.CharityProjectListView.as_view(), name='charity-list'),
    path('charity/<int:pk>/donate/', views.donate, name='charity-donate'),

    # 排行榜
    path('leaderboard/', views.leaderboard, name='leaderboard'),

    # 我的
    path('green-records/', views.green_records, name='green-records'),
    path('badges/', views.my_badges, name='my-badges'),

    # 小组
    path('groups/', views.GroupListView.as_view(), name='group-list'),
    path('groups/<int:pk>/checkin/', views.group_checkin, name='group-checkin'),

    # 通知
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/read/', views.read_notification, name='notification-read'),
    path('notifications/unread-count/', views.unread_count, name='unread-count'),

    # 绿色大富翁
    path('monopoly/', views.monopoly_overview, name='monopoly-overview'),
    path('monopoly/roll/', views.monopoly_roll, name='monopoly-roll'),
    path('monopoly/claim/', views.monopoly_claim, name='monopoly-claim'),
    path('monopoly/upgrade/', views.monopoly_upgrade, name='monopoly-upgrade'),
    path('monopoly/resolve-event/', views.monopoly_resolve_event, name='monopoly-resolve'),
    path('monopoly/logs/', views.monopoly_logs, name='monopoly-logs'),
    path('monopoly/leaderboard/', views.monopoly_leaderboard, name='monopoly-leaderboard'),
]
