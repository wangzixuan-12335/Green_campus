"""
清除所有测试数据 —— 绿动校园
运行: python manage.py flush_test_data

会清除：
  - 所有用户任务记录、挑战参与、兑换、捐赠、徽章
  - 所有演示用户（demo, alice, bob, carol, dave, eve, frank, grace）
  - 所有基础数据（任务、挑战、商品、公益、徽章、小组、通知）
  - 重置自增ID
然后重新初始化干净的基础数据。
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import (
    Task, TaskRecord, Challenge, ChallengeParticipation,
    ShopItem, Redemption, CharityProject, Donation,
    Badge, UserBadge, Group, GroupCheckin, Notification,
    MonopolyTile, MonopolyPlayer, MonopolyProperty, MonopolyLog, MonopolyEvent,
)

User = get_user_model()


class Command(BaseCommand):
    help = '清除所有测试数据并重置（不会删除超级管理员账号）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-superuser',
            action='store_true',
            default=True,
            help='保留超级管理员账号（默认保留）',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('⚠  开始清除所有测试数据...'))

        # ─── 1. 清除业务记录 ───
        counts = {}
        counts['任务记录'] = TaskRecord.objects.all().delete()[0]
        counts['挑战参与'] = ChallengeParticipation.objects.all().delete()[0]
        counts['兑换记录'] = Redemption.objects.all().delete()[0]
        counts['捐赠记录'] = Donation.objects.all().delete()[0]
        counts['用户徽章'] = UserBadge.objects.all().delete()[0]
        counts['小组打卡'] = GroupCheckin.objects.all().delete()[0]
        counts['通知'] = Notification.objects.all().delete()[0]
        # 大富翁记录
        counts['大富翁日志'] = MonopolyLog.objects.all().delete()[0]
        counts['大富翁玩家'] = MonopolyPlayer.objects.all().delete()[0]
        counts['大富翁场景'] = MonopolyProperty.objects.all().delete()[0]

        # ─── 2. 清除基础数据 ───
        counts['任务'] = Task.objects.all().delete()[0]
        counts['挑战'] = Challenge.objects.all().delete()[0]
        counts['商品'] = ShopItem.objects.all().delete()[0]
        counts['公益项目'] = CharityProject.objects.all().delete()[0]
        counts['徽章'] = Badge.objects.all().delete()[0]
        counts['小组'] = Group.objects.all().delete()[0]
        counts['大富翁格子'] = MonopolyTile.objects.all().delete()[0]
        counts['大富翁事件'] = MonopolyEvent.objects.all().delete()[0]

        # ─── 3. 清除演示用户（保留超级管理员）───
        demo_usernames = ['demo', 'alice', 'bob', 'carol', 'dave', 'eve', 'frank', 'grace']
        demo_users = User.objects.filter(username__in=demo_usernames)
        counts['演示用户'] = demo_users.count()
        demo_users.delete()

        # ─── 4. 重置自增ID（SQLite）───
        from django.db import connection
        with connection.cursor() as cursor:
            if connection.vendor == 'sqlite':
                tables = connection.introspection.table_names()
                for table in tables:
                    if table.startswith('sqlite_'):
                        continue
                    try:
                        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}';")
                    except Exception:
                        pass

        # ─── 5. 打印清除结果 ───
        self.stdout.write(self.style.SUCCESS('\n✅ 测试数据已清除：'))
        for name, cnt in counts.items():
            self.stdout.write(f'   {name}: {cnt} 条')

        # ─── 6. 重新初始化基础数据 ───
        self.stdout.write(self.style.SUCCESS('\n🔄 重新初始化基础数据...'))
        from django.core.management import call_command
        call_command('init_data')

        self.stdout.write(self.style.SUCCESS('\n🎉 数据重置完成！'))
        self.stdout.write(self.style.WARNING('演示账号: demo / demo123456'))
