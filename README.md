# 绿动校园 · 绿色积分平台

内在驱动型高校低碳生活激励平台，基于 TPB、SDT、TTM 三大行为科学模型，通过绿色积分激励大学生践行低碳生活。

## 📁 项目结构

```
绿动校园/
├── PRD.md                  # 产品需求文档
├── README.md               # 项目说明（本文件）
├── backend/                # 后端（Django + DRF）
│   ├── manage.py
│   ├── requirements.txt
│   ├── green_campus/       # 项目配置
│   ├── users/              # 用户模块（注册/登录/个人信息）
│   └── core/               # 核心业务（任务/挑战/商城/排行/徽章/小组/大富翁）
├── deploy/                 # 一键部署脚本与 Nginx/Systemd 配置
│   ├── deploy.sh
│   ├── DEPLOY.md
│   ├── nginx_green_campus.conf
│   └── green_campus.service
└── frontend/               # 前端（原生 HTML/CSS/JS）
    ├── index.html
    ├── css/style.css
    └── js/app.js
```

## 🚀 快速开始

### 一、后端启动

```bash
cd backend

# 1. 安装依赖
pip install -r requirements.txt

# 2. 数据库迁移
python manage.py makemigrations users core
python manage.py migrate

# 3. 初始化演示数据
python manage.py init_data

# 4. 创建超级管理员（可选，用于后台管理）
python manage.py createsuperuser

# 5. 启动服务
python manage.py runserver
```

后端运行在 `http://127.0.0.1:8000`
后台管理：`http://127.0.0.1:8000/admin`

### 二、前端启动

前端为纯静态文件，直接用浏览器打开 `frontend/index.html` 即可。
推荐用 VS Code Live Server 或任意静态服务器：

```bash
cd frontend
python -m http.server 5500
# 访问 http://127.0.0.1:5500
```

### 三、演示账号

| 账号 | 密码 | 说明 |
| :--- | :--- | :--- |
| demo | demo123456 | 演示用户（已含积分数据） |
| alice ~ grace | 123456 | 排行榜演示用户 |

## 📋 功能模块

| 模块 | 说明 |
| :--- | :--- |
| 首页 | 积分总览、今日进度、任务列表、排行速览 |
| 校园挑战 | 挑战列表、分类筛选、加入挑战 |
| 积分商城 | 商品兑换、公益捐赠 |
| 排行榜 | 领奖台、完整排行、本周/本月/总榜切换 |
| 🎲 绿色大富翁 | 24 格环形棋盘、掷骰移动、认领/升级场景、机遇/危机/陷阱事件、资产排行 |
| 我的 | 个人信息、徽章成就、绿色记录、低碳小组签到、设置 |

### 🎲 绿色大富翁玩法

完成低碳任务或小组签到可获得掷骰机会（每日上限 6 次，最多囤积 20 次），掷骰在 24 格环形棋盘上移动：

- **起点格**：经过即奖励 +15 积分
- **场景格**（太阳能食堂、LED 教学楼等）：花费积分认领（50–150），升级 Lv.1→2（+80）/ Lv.2→3（+150），他人路过需支付过路费（基础费 × 等级倍率）
- **机遇格**：随机正向事件（+5~+20 积分）
- **危机格**：随机负向事件（扣分，不超过当前积分）
- **陷阱格**：被困一回合，答对低碳知识题即可脱困（3 次答错强制释放）
- **任务格 / 公益格**：触发对应任务或公益事件

每人最多持有 3 处场景，等级上限 Lv.3。资产价值 = 场景过路费总和，用于资产排行。详细规则见 [PRD_大富翁模式.md](PRD_大富翁模式.md)。

## 🎨 设计说明

- **主色调**：绿色系（深绿 #1c4532 → 鲜绿 #38a169）
- **辅助色**：琥珀色 #f59e0b
- **字体**：中文 Noto Sans SC，数字 Syne
- **响应式**：Web 端左侧边栏布局，移动端底部 Tab 导航，断点 768px

## 🔌 API 概览

| 接口 | 方法 | 说明 |
| :--- | :--- | :--- |
| `/api/auth/register/` | POST | 注册 |
| `/api/auth/login/` | POST | 登录 |
| `/api/auth/me/` | GET | 当前用户信息 |
| `/api/home/` | GET | 首页聚合数据 |
| `/api/tasks/` | GET | 任务列表 |
| `/api/tasks/<id>/complete/` | POST | 完成任务 |
| `/api/challenges/` | GET | 挑战列表 |
| `/api/challenges/<id>/join/` | POST | 加入挑战 |
| `/api/shop/` | GET | 商城商品 |
| `/api/shop/<id>/redeem/` | POST | 兑换商品 |
| `/api/charity/` | GET | 公益项目 |
| `/api/charity/<id>/donate/` | POST | 公益捐赠 |
| `/api/leaderboard/` | GET | 排行榜 |
| `/api/green-records/` | GET | 绿色记录 |
| `/api/badges/` | GET | 徽章列表 |
| `/api/groups/` | GET | 小组列表 |
| `/api/groups/<id>/checkin/` | POST | 小组签到 |
| `/api/monopoly/` | GET | 大富翁全景（棋盘/玩家/资产/排行） |
| `/api/monopoly/roll/` | POST | 掷骰子 |
| `/api/monopoly/claim/` | POST | 认领当前场景 |
| `/api/monopoly/upgrade/` | POST | 升级当前场景 |
| `/api/monopoly/resolve-event/` | POST | 解答陷阱题目 |
| `/api/monopoly/logs/` | GET | 大富翁游戏日志 |
| `/api/monopoly/leaderboard/` | GET | 大富翁资产排行 |

## 🚀 服务器部署

项目内置一键部署脚本，可在 Linux 服务器（Ubuntu 20.04+ / Debian 11+）上快速部署，自动完成虚拟环境、数据库迁移、Systemd 服务、Nginx 反向代理配置。

```bash
# 上传项目到服务器后执行
sudo bash deploy/deploy.sh
```

部署完成后访问 `http://服务器IP/` 即前端，`/api/` 为后端接口，`/admin/` 为管理后台。

**数据安全：** 默认部署/更新只执行 `migrate`，不会清空数据；仅首次部署库为空时自动初始化演示数据。更新代码用 `--update`，清空数据用 `--flush`（会先备份）。

常用命令：

```bash
sudo bash deploy/deploy.sh --update     # 快速更新代码（数据安全）
sudo bash deploy/deploy.sh --status     # 查看状态 + API 健康检查
sudo bash deploy/deploy.sh --logs       # 实时日志
sudo bash deploy/deploy.sh --restart    # 重启服务
```

完整部署说明见 [deploy/DEPLOY.md](deploy/DEPLOY.md)。

## 🛠 技术栈

- **后端**：Python 3.10+ / Django 4.2 / Django REST Framework / SimpleJWT
- **数据库**：SQLite（开发）/ MySQL（生产可切换）
- **前端**：原生 HTML5 / CSS3 / JavaScript（无框架依赖）
