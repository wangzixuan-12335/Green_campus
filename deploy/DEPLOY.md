# 绿动校园 · 服务端部署指南

> 一键部署脚本，3 条命令上线。默认**数据安全**：更新代码不会丢数据。

---

## 🚀 3 分钟快速部署

适用于全新 Ubuntu / Debian 服务器。

```bash
# 1. 上传项目到服务器
scp -r 绿动校园/ user@你的服务器IP:/tmp/green-campus

# 2. SSH 登录服务器
ssh user@你的服务器IP

# 3. 一键部署
cd /tmp/green-campus && sudo bash deploy/deploy.sh
```

脚本会自动完成：安装系统依赖 → 创建虚拟环境 → 配置 .env → 数据库迁移 → 初始化演示数据 → 配置 Systemd + Nginx → 启动服务 → 健康检查。

部署完成后访问：

| 地址 | 说明 |
|------|------|
| `http://服务器IP/` | 前端页面 |
| `http://服务器IP/api/` | 后端 API |
| `http://服务器IP/admin/` | Django 管理后台 |

**演示账号：** `demo` / `demo123456`

---

## 📋 常用命令

```bash
sudo bash deploy/deploy.sh              # 完整部署（首次安装 / 更新代码，数据安全）
sudo bash deploy/deploy.sh --update     # 快速更新：仅代码+依赖+迁移+重启（不碰配置）
sudo bash deploy/deploy.sh --status     # 查看服务状态 + API 健康检查
sudo bash deploy/deploy.sh --restart    # 重启服务
sudo bash deploy/deploy.sh --logs       # 实时查看日志（Ctrl+C 退出）
sudo bash deploy/deploy.sh --flush      # 清空所有业务数据并重新初始化（会丢数据！）
sudo bash deploy/deploy.sh --uninstall  # 卸载服务（保留项目文件）
sudo bash deploy/deploy.sh --help       # 查看帮助
```

### 手动管理服务

```bash
# Gunicorn 服务
sudo systemctl start green_campus
sudo systemctl stop green_campus
sudo systemctl restart green_campus
sudo systemctl status green_campus

# Nginx
sudo systemctl restart nginx
sudo nginx -t              # 测试配置

# 查看实时日志
sudo journalctl -u green_campus -f
sudo tail -f /var/log/nginx/green_campus_error.log
```

---

## 🔐 首次部署创建管理员

默认部署只创建演示用户 `demo`。如需 Django 管理后台超管，二选一：

**方式一：部署时通过环境变量自动创建（推荐）**

```bash
sudo ADMIN_USERNAME=admin ADMIN_PASSWORD=YourStrong123 bash deploy/deploy.sh
```

**方式二：部署后手动创建**

```bash
cd /opt/green-campus/backend
/opt/green-campus/venv/bin/python manage.py createsuperuser
```

---

## ⚙️ 配置说明

### 环境变量 `.env`

配置文件位置：`/opt/green-campus/backend/.env`

```ini
# Django 核心
DJANGO_SECRET_KEY=your-random-secret-key    # 首次部署自动生成
DJANGO_DEBUG=False                          # 生产环境关闭调试
DJANGO_ALLOWED_HOSTS=*                      # 可改为具体域名/IP

# 数据库（默认 SQLite，可切换 MySQL）
DB_ENGINE=sqlite
# DB_ENGINE=mysql
# DB_NAME=green_campus
# DB_USER=root
# DB_PASSWORD=your_password
# DB_HOST=127.0.0.1
# DB_PORT=3306

# CORS 跨域（配置前端域名）
CORS_ALLOWED_ORIGINS=https://green.example.com
```

修改后需重启服务：`sudo bash deploy/deploy.sh --restart`

### Nginx 配置

配置文件位置：`/etc/nginx/sites-available/green_campus`

修改 `server_name` 为你的域名：

```nginx
server {
    listen 80;
    server_name green.yourdomain.com;  # ← 修改这里
    ...
}
```

修改后：`sudo nginx -t && sudo systemctl restart nginx`

### 自定义部署路径

通过环境变量覆盖默认路径：

```bash
sudo DEPLOY_DIR=/data/green-campus DEPLOY_USER=ubuntu bash deploy/deploy.sh
```

---

## 🔄 更新代码

**日常更新（推荐）：** 只复制代码、更新依赖、跑迁移、重启，不碰 Nginx/Systemd 配置。

```bash
# 1. 上传新代码到服务器
scp -r backend/ user@server:/tmp/green-campus/backend/
scp -r frontend/ user@server:/tmp/green-campus/frontend/

# 2. 快速更新
cd /tmp/green-campus
sudo bash deploy/deploy.sh --update
```

> 💡 更新前会自动备份 `db.sqlite3` 为 `db.sqlite3.bak.<时间戳>`，放心更新。

**完整重新部署：** 改动了 Nginx/Systemd 配置或 .env 模板时用无参数模式，同样数据安全（只跑 migrate，不丢数据）。

```bash
sudo bash deploy/deploy.sh
```

---

## 🗄️ 数据库切换 MySQL

1. 安装 MySQL 并创建数据库：

```sql
CREATE DATABASE green_campus CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'green'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL ON green_campus.* TO 'green'@'localhost';
FLUSH PRIVILEGES;
```

2. 修改 `.env`：

```ini
DB_ENGINE=mysql
DB_NAME=green_campus
DB_USER=green
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

3. 重新部署：

```bash
sudo bash deploy/deploy.sh --restart
```

---

## 🧹 清空数据（演示/重置用）

> ⚠️ **会删除所有用户、任务记录、积分等业务数据**，超级管理员保留。执行前会自动备份。

```bash
sudo bash deploy/deploy.sh --flush
```

清空内容包括：
- 所有用户任务记录、挑战参与、兑换、捐赠、徽章
- 所有演示用户（demo, alice, bob 等）
- 所有基础数据（任务、挑战、商品等）
- 重置自增 ID
- 重新初始化干净的基础数据

---

## 🔒 HTTPS 配置（推荐）

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 自动配置 SSL 证书（会自动修改 Nginx 配置）
sudo certbot --nginx -d green.yourdomain.com

# 自动续期已配置，测试续期：
sudo certbot renew --dry-run
```

配置 HTTPS 后，建议在 `.env` 中开启强制跳转：

```ini
SECURE_SSL_REDIRECT=True
```

然后 `sudo bash deploy/deploy.sh --restart`。

---

## 📂 目录结构

```
/opt/green-campus/              # 部署根目录
├── backend/                    # 后端代码
│   ├── .env                    # 环境变量配置
│   ├── db.sqlite3              # SQLite 数据库（如使用）
│   ├── db.sqlite3.bak.*        # 部署/清空前自动备份
│   ├── staticfiles/            # 收集的静态文件
│   ├── logs/                   # 日志目录
│   │   ├── django.log
│   │   ├── gunicorn_access.log
│   │   └── gunicorn_error.log
│   └── ...
├── frontend/                   # 前端代码
│   ├── index.html
│   ├── css/
│   └── js/
├── venv/                       # Python 虚拟环境
└── deploy/                     # 部署配置
    ├── deploy.sh               # 一键部署脚本
    ├── nginx_green_campus.conf # Nginx 配置
    └── green_campus.service    # Systemd 配置

/etc/systemd/system/green_campus.service   # 服务配置
/etc/nginx/sites-available/green_campus    # Nginx 配置
```

---

## ❓ 常见问题

### Q: 端口 80 被占用？

```bash
sudo lsof -i :80
# 停止占用进程或修改 Nginx 监听端口
```

### Q: Gunicorn 启动失败？

```bash
# 查看详细日志
sudo bash deploy/deploy.sh --logs
# 或
sudo journalctl -u green_campus -n 50

# 手动测试启动
cd /opt/green-campus/backend
/opt/green-campus/venv/bin/gunicorn --config gunicorn_conf.py green_campus.wsgi:application
```

### Q: 前端页面空白？

检查浏览器控制台网络请求，确认 API 路径正确。前端 `app.js` 中 API_BASE 在非 localhost 环境下使用 `/api` 相对路径，由 Nginx 代理。

### Q: 更新代码后页面没变化？

浏览器缓存。强制刷新：`Ctrl+Shift+R`（Windows）或 `Cmd+Shift+R`（Mac）。

### Q: 如何创建管理员账号？

见上文 [首次部署创建管理员](#-首次部署创建管理员) 章节。

### Q: 部署后 API 返回 401/403？

正常。大部分接口需要登录鉴权，用 `demo / demo123456` 登录后即可访问。`--status` 健康检查中 401/403 表示服务正常响应。

### Q: 想重新开始，清空所有数据？

```bash
sudo bash deploy/deploy.sh --flush
```

会自动备份后清空，输入 `yes` 确认。
