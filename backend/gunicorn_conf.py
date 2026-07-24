"""
Gunicorn 配置 —— 绿动校园
"""
import os
import multiprocessing

# 项目根目录（gunicorn_conf.py 在 backend/ 下，根目录就是其所在目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 绑定地址
bind = os.environ.get('GUNICORN_BIND', '127.0.0.1:8000')

# 工作进程数
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))

# 工作类型（同步模式，Django 标准选择）
worker_class = 'sync'

# 超时
timeout = 60

# 长连接（keep-alive）
keepalive = 5

# 最大请求数后重启 worker（防止内存泄漏）
max_requests = 1000
max_requests_jitter = 50

# 预加载应用（节省内存，加快启动）
preload_app = True

# 日志
accesslog = os.path.join(LOG_DIR, 'gunicorn_access.log')
errorlog = os.path.join(LOG_DIR, 'gunicorn_error.log')
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sms'

# 进程名
proc_name = 'green_campus'

# 优雅重启超时
graceful_timeout = 30
