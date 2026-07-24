"""
初始化演示数据 —— 绿动校园
运行: python manage.py init_data
"""
import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import (
    Task, Challenge, ShopItem, CharityProject, Badge, Group, Notification,
    MonopolyTile, MonopolyProperty, MonopolyEvent,
)

User = get_user_model()


class Command(BaseCommand):
    help = '初始化演示数据：任务、挑战、商品、公益、徽章、小组、演示用户'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始初始化数据...'))

        # ─── 演示用户 ───
        demo, created = User.objects.get_or_create(
            username='demo',
            defaults={
                'nickname': '低碳达人',
                'student_id': '2492306',
                'college': '爱恩学院',
                'major': '市场营销',
                'total_points': 1280,
                'available_points': 560,
                'level': 3,
                'streak_days': 7,
                'total_carbon_reduction': 12.5,
                'total_tasks_done': 45,
            }
        )
        if created:
            demo.set_password('demo123456')
            demo.save()
            self.stdout.write('  ✓ 创建演示用户 demo/demo123456')

        # 额外演示用户（用于排行榜）
        extra_users = [
            ('alice', '爱丽丝', '爱恩学院', '信管', 3200),
            ('bob', '鲍勃', '海洋学院', '海洋科学', 2800),
            ('carol', '凯萝', '食品学院', '食品工程', 2100),
            ('dave', '大卫', '经济学院', '经济学', 1800),
            ('eve', '伊芙', '爱恩学院', '信管', 1500),
            ('frank', '弗兰克', '工程学院', '机械工程', 980),
            ('grace', '格蕾丝', '外国语学院', '英语', 760),
        ]
        for uname, nick, college, major, pts in extra_users:
            u, c = User.objects.get_or_create(
                username=uname,
                defaults={
                    'nickname': nick, 'college': college, 'major': major,
                    'total_points': pts, 'available_points': pts // 2,
                    'level': 3 if pts >= 800 else 2,
                    'streak_days': random.randint(1, 15),
                    'total_carbon_reduction': round(pts * 0.01, 1),
                    'total_tasks_done': pts // 30,
                }
            )
            if c:
                u.set_password('123456')
                u.save()
        self.stdout.write(f'  ✓ 创建 {len(extra_users)} 个排行榜演示用户')

        # ─── 低碳任务 ───
        tasks_data = [
            ('dining', '🍚', '光盘行动', '餐餐吃光，拒绝浪费', 8, 0.3, 3),
            ('dining', '🥢', '自带餐具', '减少一次性餐具使用', 6, 0.2, 2),
            ('energy', '💡', '随手关灯', '离开教室宿舍随手关灯', 5, 0.4, 2),
            ('energy', '❄️', '空调26℃', '空调温度不低于26度', 7, 0.5, 1),
            ('travel', '🚶', '绿色出行', '步行/骑行/公交出行', 10, 1.2, 2),
            ('travel', '🚲', '骑行打卡', '骑行代替打车', 12, 1.5, 1),
            ('shopping', '🛍️', '自带购物袋', '购物自带环保袋', 5, 0.1, 2),
            ('shopping', '♻️', '二手交易', '闲置物品二手流转', 8, 0.6, 1),
            ('study', '📚', '低碳学习', '学习低碳知识并答题', 15, 0.0, 1),
            ('resource', '📄', '废纸回收', '纸张分类回收', 6, 0.3, 2),
            ('resource', '🥤', '塑料瓶回收', '塑料瓶分类回收', 6, 0.2, 2),
        ]
        for i, (cat, icon, name, desc, pts, carbon, limit) in enumerate(tasks_data):
            Task.objects.get_or_create(
                name=name,
                defaults={
                    'category': cat, 'icon': icon, 'description': desc,
                    'points': pts, 'carbon_reduction': carbon,
                    'daily_limit': limit, 'sort_order': i,
                }
            )
        self.stdout.write(f'  ✓ 创建 {len(tasks_data)} 个低碳任务')

        # ─── 校园挑战 ───
        challenges_data = [
            ('🌍', '热门', '21天光盘行动', '连续21天践行光盘行动，养成节约粮食好习惯', 200, 21, 'ongoing', 156),
            ('🚲', '热门', '骑行通勤周', '一周内骑行通勤累计50公里', 150, 7, 'ongoing', 89),
            ('💡', '节能', '宿舍节能挑战', '本月宿舍用电量同比下降20%', 300, 30, 'ongoing', 234),
            ('🌳', '公益', '植树节特别行动', '参与校园植树或线上认养树木', 100, 1, 'upcoming', 0),
            ('♻️', '环保', '旧物改造大赛', '将废旧物品改造成实用好物并展示', 250, 14, 'ongoing', 67),
            ('📝', '学习', '低碳知识竞赛', '参与线上低碳知识答题挑战', 120, 7, 'ended', 312),
        ]
        for cover, tag, title, desc, pts, target, status, pcount in challenges_data:
            Challenge.objects.get_or_create(
                title=title,
                defaults={
                    'cover': cover, 'tag': tag, 'description': desc,
                    'points': pts, 'target_count': target,
                    'status': status, 'participants_count': pcount,
                }
            )
        self.stdout.write(f'  ✓ 创建 {len(challenges_data)} 个校园挑战')

        # ─── 商城商品 ───
        items_data = [
            ('🎒', '环保帆布袋', 80, 50, 'hot'),
            ('🍶', '玻璃水杯', 120, 30, 'new'),
            ('🌱', '多肉盆栽', 150, 20, 'rare'),
            ('📓', '再生纸笔记本', 60, 100, ''),
            ('🥤', '不锈钢吸管套装', 90, 40, ''),
            ('🧴', '环保洗护套装', 200, 15, 'hot'),
            ('🎧', '校园文创耳机', 500, 10, 'rare'),
            ('🎫', '图书馆VIP座位券', 300, 5, 'new'),
            ('🍫', '公平贸易巧克力', 100, 25, ''),
            ('🧦', '竹纤维袜子', 70, 60, ''),
            ('📚', '二手书籍兑换券', 50, 80, ''),
            ('☀️', '太阳能充电宝', 400, 8, 'rare'),
        ]
        for image, name, cost, stock, tag in items_data:
            ShopItem.objects.get_or_create(
                name=name,
                defaults={'image': image, 'cost': cost, 'stock': stock, 'tag': tag}
            )
        self.stdout.write(f'  ✓ 创建 {len(items_data)} 个商城商品')

        # ─── 公益项目 ───
        charity_data = [
            ('🌳', '沙漠植树', '在荒漠地区种下一棵树', 50),
            ('🌊', '海洋净化', '支持海洋塑料清理行动', 80),
            ('🐼', '保护大熊猫', '资助大熊猫栖息地保护', 100),
            ('🐝', '蜜蜂保护', '保护濒危蜜蜂种群', 60),
            ('🌾', '助农扶贫', '帮助贫困地区发展生态农业', 120),
        ]
        for icon, name, desc, cost in charity_data:
            CharityProject.objects.get_or_create(
                name=name,
                defaults={'icon': icon, 'description': desc, 'cost': cost}
            )
        self.stdout.write(f'  ✓ 创建 {len(charity_data)} 个公益项目')

        # ─── 徽章 ───
        badges_data = [
            ('🌱', '低碳萌芽', '完成第一个低碳任务', 'general', '', 0, 1),
            ('🌿', '绿色行者', '累计获得100积分', 'general', '', 100, 0),
            ('🌳', '低碳达人', '累计获得500积分', 'general', '', 500, 0),
            ('🏆', '低碳先锋', '累计获得2000积分', 'general', '', 2000, 0),
            ('👑', '低碳守护者', '累计获得5000积分', 'general', '', 5000, 0),
            ('🔥', '坚持7天', '连续打卡7天', 'general', '', 0, 20),
            ('⭐', '百任务达成', '完成100个任务', 'general', '', 0, 100),
            # 大富翁主题徽章
            ('🎲', '初次掷骰', '首次掷骰子', 'monopoly', 'first_roll', 0, 0),
            ('🏠', '场景新主', '认领第一个低碳场景', 'monopoly', 'first_claim', 0, 0),
            ('🏘️', '校园地主', '认领3个低碳场景', 'monopoly', 'landlord', 0, 0),
            ('⭐', '满级场景', '将任意场景升至 Lv.3', 'monopoly', 'max_level', 0, 0),
            ('🔄', '环游一圈', '棋盘绕场1圈', 'monopoly', 'lap', 0, 0),
            ('💰', '过路费大亨', '累计收取过路费200积分', 'monopoly', 'toll_200', 0, 0),
        ]
        for icon, name, desc, category, mkey, pts, tasks in badges_data:
            Badge.objects.get_or_create(
                name=name,
                defaults={
                    'icon': icon, 'description': desc,
                    'category': category, 'monopoly_key': mkey,
                    'condition_points': pts, 'condition_tasks': tasks,
                }
            )
        self.stdout.write(f'  ✓ 创建 {len(badges_data)} 个徽章（含大富翁徽章）')

        # ─── 低碳小组 ───
        groups_data = [
            ('👥', '光盘行动小分队', '每天光盘，拒绝浪费', 128),
            ('🚴', '骑行通勤社', '绿色出行，低碳通勤', 86),
            ('♻️', '环保回收站', '垃圾分类，资源回收', 95),
            ('📚', '低碳学习营', '学习低碳知识，共同进步', 72),
        ]
        for icon, name, desc, count in groups_data:
            Group.objects.get_or_create(
                name=name,
                defaults={'icon': icon, 'description': desc, 'member_count': count}
            )
        self.stdout.write(f'  ✓ 创建 {len(groups_data)} 个低碳小组')

        # ─── 大富翁棋盘（24格）───
        # (position, type, icon, name, desc, claim_cost, upgrade_cost, base_toll)
        board_data = [
            (1, 'start', '🏁', '绿色起点', '经过起点获得积分奖励', 0, 0, 0),
            (2, 'scene', '☀️', '太阳能食堂', '食堂屋顶光伏发电', 50, 80, 8),
            (3, 'chance', '🎲', '绿色机遇', '触发随机正面事件', 0, 0, 0),
            (4, 'task', '📋', '低碳任务', '触发即时低碳小任务', 0, 0, 0),
            (5, 'scene', '💧', '雨水回收宿舍', '宿舍雨水回收利用', 50, 80, 8),
            (6, 'charity', '🌳', '公益捐赠', '触发公益捐赠选项', 0, 0, 0),
            (7, 'crisis', '🌪️', '碳危机', '触发随机负面事件', 0, 0, 0),
            (8, 'scene', '💡', 'LED教学楼', '教学楼全面换装LED', 70, 80, 12),
            (9, 'chance', '🎲', '绿色机遇', '触发随机正面事件', 0, 0, 0),
            (10, 'task', '📋', '低碳任务', '触发即时低碳小任务', 0, 0, 0),
            (11, 'scene', '🚲', '共享单车驿站', '校园共享单车驿站', 70, 80, 12),
            (12, 'trap', '⛽', '高碳陷阱', '停留一回合，可答题赎身', 0, 0, 0),
            (13, 'crisis', '🌪️', '碳危机', '触发随机负面事件', 0, 0, 0),
            (14, 'scene', '📚', '无纸化图书馆', '图书馆无纸化办公', 90, 150, 16),
            (15, 'chance', '🎲', '绿色机遇', '触发随机正面事件', 0, 0, 0),
            (16, 'task', '📋', '低碳任务', '触发即时低碳小任务', 0, 0, 0),
            (17, 'scene', '♻️', '垃圾分类站', '校园垃圾分类回收站', 90, 150, 16),
            (18, 'charity', '🌳', '公益捐赠', '触发公益捐赠选项', 0, 0, 0),
            (19, 'scene', '🌿', '屋顶花园', '教学楼屋顶花园绿化', 120, 150, 22),
            (20, 'crisis', '🌪️', '碳危机', '触发随机负面事件', 0, 0, 0),
            (21, 'scene', '🔋', '光伏停车场', '停车场光伏顶棚发电', 120, 150, 22),
            (22, 'chance', '🎲', '绿色机遇', '触发随机正面事件', 0, 0, 0),
            (23, 'scene', '🏪', '零碳便利店', '校园零碳便利店', 150, 150, 28),
            (24, 'scene', '🌳', '碳汇林', '校园碳汇林保护区', 150, 150, 28),
        ]
        tile_count = 0
        for pos, ttype, icon, name, desc, claim, upg, toll in board_data:
            _, created = MonopolyTile.objects.get_or_create(
                position=pos,
                defaults={
                    'tile_type': ttype, 'name': name, 'icon': icon,
                    'description': desc, 'claim_cost': claim,
                    'upgrade_cost': upg, 'base_toll': toll,
                }
            )
            if created:
                tile_count += 1
            # 场景格创建对应的空 Property
            if ttype == 'scene':
                MonopolyProperty.objects.get_or_create(tile_id=MonopolyTile.objects.get(position=pos).id)
        self.stdout.write(f'  ✓ 创建 {tile_count} 个大富翁棋盘格子（共24格）')

        # ─── 大富翁事件池 ───
        events_data = [
            # 绿色机遇（正面）
            ('chance', '今天光盘行动，食堂阿姨点赞', 10, 0),
            ('chance', '发现教室灯没关，随手关掉', 8, 0),
            ('chance', '参加低碳讲座，收获满满', 15, 0),
            ('chance', '旧物改造成功，获同学点赞', 12, 0),
            ('chance', '骑行通勤一周，身体更棒了', 20, 0),
            ('chance', '获得"额外骰子"道具', 0, 2),
            ('chance', '宿舍被评为节能示范寝室', 18, 0),
            # 碳危机（负面，幅度可控）
            ('crisis', '忘记关空调，宿舍耗电超标', -8, 0),
            ('crisis', '外卖产生塑料垃圾', -5, 0),
            ('crisis', '打车去本可步行到达的地方', -10, 0),
            ('crisis', '打印了大量不必要的资料', -6, 0),
        ]
        for etype, desc, pts, edice in events_data:
            MonopolyEvent.objects.get_or_create(
                description=desc,
                defaults={
                    'event_type': etype, 'points_change': pts,
                    'extra_dice': edice,
                }
            )
        self.stdout.write(f'  ✓ 创建 {len(events_data)} 个大富翁事件')

        # ─── 演示通知 ───
        if demo and not Notification.objects.filter(user=demo).exists():
            Notification.objects.create(
                user=demo, title='欢迎来到绿动校园！',
                content='完成今日低碳任务，获取绿色积分吧～'
            )
            Notification.objects.create(
                user=demo, title='连续打卡7天达成！',
                content='恭喜你连续打卡7天，获得「坚持7天」徽章！'
            )
            self.stdout.write('  ✓ 创建演示通知')

        self.stdout.write(self.style.SUCCESS('\n✅ 数据初始化完成！'))
        self.stdout.write(self.style.WARNING('\n演示账号: demo / demo123456'))
