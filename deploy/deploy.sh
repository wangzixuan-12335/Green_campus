#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 绿动校园 · 一键部署脚本 v2.0
# ═══════════════════════════════════════════════════════════════
#
# 用法:
#   sudo bash deploy.sh              # 完整部署（首次安装 / 更新代码均可，数据安全）
#   sudo bash deploy.sh --update     # 仅更新代码+依赖+迁移+重启（快速迭代，不碰配置）
#   sudo bash deploy.sh --flush      # 清空所有业务数据并重新初始化（演示用，会丢数据！）
#   sudo bash deploy.sh --restart    # 仅重启服务
#   sudo bash deploy.sh --status     # 查看服务状态 + API 健康检查
#   sudo bash deploy.sh --logs       # 实时查看日志（Ctrl+C 退出）
#   sudo bash deploy.sh --uninstall  # 卸载服务（保留项目文件）
#
# 数据安全:
#   - 默认部署/更新只执行 migrate，绝不自动清空数据
#   - 仅当数据库为空（首次部署）时自动初始化演示数据
#   - 更新前自动备份 db.sqlite3
#
# 可选环境变量（首次部署时可传入）:
#   ADMIN_USERNAME=admin ADMIN_PASSWORD=xxx  自动创建超级管理员
#   INIT_DEMO_DATA=1                          强制初始化演示数据
#   DEPLOY_DIR=/opt/green-campus              自定义部署路径
#   DEPLOY_USER=www-data                      自定义运行用户
#
# 前提: 以 root 或 sudo 权限运行，系统已安装 python3 nginx
# ═══════════════════════════════════════════════════════════════

set -e

# ─── 颜色输出 ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[⚠]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }
step()  { echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BLUE}  $1${NC}"; echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# ─── 默认配置（可通过环境变量覆盖）───
DEPLOY_DIR="${DEPLOY_DIR:-/opt/green-campus}"
DEPLOY_USER="${DEPLOY_USER:-www-data}"
VENV_DIR="${DEPLOY_DIR}/venv"
BACKEND_DIR="${DEPLOY_DIR}/backend"
FRONTEND_DIR="${DEPLOY_DIR}/frontend"
SERVICE_NAME="green_campus"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
NGINX_CONF_SRC="${DEPLOY_DIR}/deploy/nginx_green_campus.conf"
NGINX_CONF_DEST="/etc/nginx/sites-available/green_campus"
NGINX_LINK="/etc/nginx/sites-enabled/green_campus"

# ─── 项目根目录（脚本在 deploy/ 下，根目录是上一级）───
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ═══════════════════════════════════════════════════════════════
# 函数定义
# ═══════════════════════════════════════════════════════════════

check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "请使用 root 或 sudo 权限运行此脚本"
        exit 1
    fi
}

check_system() {
    step "检查系统环境"

    # 检查 Python
    if command -v python3 &>/dev/null; then
        PYTHON=python3
        info "Python3: $($PYTHON --version)"
    else
        error "未找到 python3，请先安装: apt install python3 python3-venv python3-pip"
        exit 1
    fi

    # 确保 python3-venv 和 python3-pip 已安装（venv 创建失败最常见原因）
    if ! $PYTHON -m venv --help &>/dev/null; then
        warn "python3-venv 模块缺失，正在安装..."
        apt update -qq && apt install -y -qq python3-venv python3-pip python3-dev
    fi

    # 检查 Nginx
    if ! command -v nginx &>/dev/null; then
        warn "未找到 nginx，正在安装..."
        apt update -qq && apt install -y -qq nginx
    fi
    info "Nginx: $(nginx -v 2>&1)"

    # 检查 rsync（没有则安装，安装失败则用 cp 回退）
    if ! command -v rsync &>/dev/null; then
        warn "未找到 rsync，正在安装..."
        apt update -qq && apt install -y -qq rsync 2>/dev/null || warn "rsync 安装失败，将使用 cp 回退"
    fi

    # 确保部署用户存在
    if ! id "$DEPLOY_USER" &>/dev/null; then
        warn "用户 $DEPLOY_USER 不存在，创建中..."
        useradd --system --no-create-home --shell /usr/sbin/nologin "$DEPLOY_USER"
    fi
    info "运行用户: $DEPLOY_USER"
}

# ─── 安全复制函数（优先 rsync，回退 cp）───
safe_copy() {
    local src="$1"
    local dst="$2"
    local exclude_args=()
    # 剩余参数为排除模式
    shift 2
    while [ $# -gt 0 ]; do
        exclude_args+=("--exclude=$1")
        shift
    done

    if command -v rsync &>/dev/null; then
        rsync -a --delete "${exclude_args[@]}" "$src" "$dst"
    else
        # cp 回退：先清空目标，再复制
        rm -rf "${dst:?}/"*  2>/dev/null || true
        cp -a "${src:?}/"* "$dst" 2>/dev/null || true
        # cp 不支持 exclude，手动清理
        for pattern in __pycache__ '*.pyc' db.sqlite3; do
            find "$dst" -name "$pattern" -exec rm -rf {} + 2>/dev/null || true
        done
        rm -rf "${dst}/logs" "${dst}/.env" 2>/dev/null || true
    fi
}

# ─── 部署前备份 SQLite 数据库（若存在）───
backup_database() {
    local db_file="${BACKEND_DIR}/db.sqlite3"
    if [ -f "$db_file" ]; then
        local ts
        ts=$(date +%Y%m%d_%H%M%S)
        cp -a "$db_file" "${db_file}.bak.${ts}"
        info "已备份数据库: db.sqlite3.bak.${ts}"
    fi
}

copy_project() {
    step "复制项目文件到 ${DEPLOY_DIR}"

    mkdir -p "$DEPLOY_DIR"

    # 部署前备份现有数据库（在覆盖后端代码前）
    backup_database

    # 复制后端
    info "复制后端代码..."
    safe_copy "${SCRIPT_DIR}/backend/" "${BACKEND_DIR}/" \
        '__pycache__' '*.pyc' 'db.sqlite3' 'logs/' '.env'

    # 复制前端
    info "复制前端代码..."
    safe_copy "${SCRIPT_DIR}/frontend/" "${FRONTEND_DIR}/"

    # 复制部署配置
    info "复制部署配置..."
    mkdir -p "${DEPLOY_DIR}/deploy"
    cp -f "${SCRIPT_DIR}/deploy/"* "${DEPLOY_DIR}/deploy/" 2>/dev/null || true

    # 创建日志目录
    mkdir -p "${BACKEND_DIR}/logs"
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR"

    info "项目文件已复制到 ${DEPLOY_DIR}"
}

setup_virtualenv() {
    step "配置 Python 虚拟环境"

    # 如果 venv 存在但损坏（没有 pip），删除重建
    if [ -d "$VENV_DIR" ] && [ ! -f "$VENV_DIR/bin/pip" ]; then
        warn "虚拟环境损坏，删除重建..."
        rm -rf "$VENV_DIR"
    fi

    if [ ! -d "$VENV_DIR" ]; then
        info "创建虚拟环境..."
        $PYTHON -m venv "$VENV_DIR"
        # 验证 venv 创建成功
        if [ ! -f "$VENV_DIR/bin/pip" ]; then
            error "虚拟环境创建失败，尝试安装 python3-venv..."
            apt update -qq && apt install -y -qq python3-venv python3-pip python3-dev
            rm -rf "$VENV_DIR"
            $PYTHON -m venv "$VENV_DIR"
            if [ ! -f "$VENV_DIR/bin/pip" ]; then
                error "虚拟环境仍创建失败，请手动运行: apt install python3-venv python3-pip"
                exit 1
            fi
        fi
    fi

    info "安装依赖..."
    "$VENV_DIR/bin/pip" install --upgrade pip -q
    "$VENV_DIR/bin/pip" install -r "${BACKEND_DIR}/requirements.txt" -q

    info "依赖安装完成"
}

setup_env_file() {
    step "配置环境变量"

    ENV_FILE="${BACKEND_DIR}/.env"

    if [ ! -f "$ENV_FILE" ]; then
        info "从模板创建 .env 文件..."
        cp "${BACKEND_DIR}/.env.example" "$ENV_FILE"

        # 生成随机密钥
        SECRET_KEY=$("$VENV_DIR/bin/python" -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
        sed -i "s|change-me-to-a-random-secret-key|${SECRET_KEY}|g" "$ENV_FILE"

        # 设置调试模式为 False
        sed -i 's|DJANGO_DEBUG=True|DJANGO_DEBUG=False|g' "$ENV_FILE"

        # 清理 .env：移除注释行和空行（systemd EnvironmentFile 要求纯 KEY=VALUE）
        sed -i '/^#/d; /^$/d' "$ENV_FILE"

        info "已生成随机密钥并配置生产环境"
    else
        warn ".env 文件已存在，跳过（如需重新生成请先删除）"
    fi

    chown "$DEPLOY_USER:$DEPLOY_USER" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
}

setup_database() {
    step "初始化数据库"

    cd "$BACKEND_DIR"

    info "生成迁移文件..."
    "$VENV_DIR/bin/python" manage.py makemigrations users core --noinput 2>&1 | tail -5

    info "应用数据库迁移..."
    "$VENV_DIR/bin/python" manage.py migrate --noinput 2>&1 | tail -10

    # 仅当数据库为空（无任何用户）时初始化演示数据，避免覆盖已有数据
    USER_COUNT=$("$VENV_DIR/bin/python" manage.py shell -c "
from django.contrib.auth import get_user_model
print(get_user_model().objects.count())
" 2>/dev/null | tail -1)

    if [ "${USER_COUNT:-0}" = "0" ] || [ "${INIT_DEMO_DATA:-0}" = "1" ]; then
        info "数据库为空，初始化演示数据..."
        "$VENV_DIR/bin/python" manage.py init_data 2>&1 | tail -15
    else
        info "检测到已有 ${USER_COUNT} 个用户，跳过数据初始化（保留现有数据）"
    fi

    info "收集静态文件..."
    "$VENV_DIR/bin/python" manage.py collectstatic --noinput 2>&1 | tail -3

    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$BACKEND_DIR"
}

setup_superuser() {
    step "创建超级管理员"

    cd "$BACKEND_DIR"

    # 检查是否已有超级用户
    HAS_SUPERUSER=$("$VENV_DIR/bin/python" manage.py shell -c "
from django.contrib.auth import get_user_model
print('yes' if get_user_model().objects.filter(is_superuser=True).exists() else 'no')
" 2>/dev/null | tail -1)

    if [ "$HAS_SUPERUSER" = "yes" ]; then
        info "超级管理员已存在，跳过"
        return
    fi

    # 优先用环境变量非交互式创建（通过 env 传递凭据，避免 shell 插值转义问题）
    if [ -n "${ADMIN_USERNAME:-}" ] && [ -n "${ADMIN_PASSWORD:-}" ]; then
        info "通过环境变量创建超级管理员: ${ADMIN_USERNAME}"
        ADMIN_USERNAME="${ADMIN_USERNAME}" ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
            "$VENV_DIR/bin/python" manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.create_superuser(username=os.environ['ADMIN_USERNAME'], password=os.environ['ADMIN_PASSWORD'])
u.nickname = '管理员'
u.save()
print('ok')
" 2>&1 | tail -3
        info "超级管理员创建成功"
        return
    fi

    # 未提供凭据则跳过，给出命令提示，不打断部署流程
    warn "未创建超级管理员（未提供 ADMIN_USERNAME/ADMIN_PASSWORD）"
    echo "  稍后可手动创建:"
    echo "    ${VENV_DIR}/bin/python ${BACKEND_DIR}/manage.py createsuperuser"
}

setup_systemd() {
    step "配置 Systemd 服务"

    # 更新 service 文件中的路径
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Green Campus (绿动校园) Gunicorn Service
After=network.target

[Service]
Type=simple
User=${DEPLOY_USER}
Group=${DEPLOY_USER}
WorkingDirectory=${BACKEND_DIR}
EnvironmentFile=${BACKEND_DIR}/.env
ExecStart=${VENV_DIR}/bin/gunicorn --config gunicorn_conf.py green_campus.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=10
PrivateTmp=true
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    info "Systemd 服务已配置并设置开机自启"
}

setup_nginx() {
    step "配置 Nginx"

    # 确保目录存在
    mkdir -p /etc/nginx/sites-available
    mkdir -p /etc/nginx/sites-enabled

    # 复制 Nginx 配置
    cp -f "$NGINX_CONF_SRC" "$NGINX_CONF_DEST"

    # 更新配置中的路径
    sed -i "s|/opt/green-campus|${DEPLOY_DIR}|g" "$NGINX_CONF_DEST"

    # 创建软链接
    ln -sf "$NGINX_CONF_DEST" "$NGINX_LINK"

    # 移除默认站点（避免冲突）
    rm -f /etc/nginx/sites-enabled/default

    # 测试 Nginx 配置
    if nginx -t 2>&1; then
        info "Nginx 配置测试通过"
    else
        error "Nginx 配置测试失败，请检查 $NGINX_CONF_DEST"
        exit 1
    fi

    systemctl enable nginx
    info "Nginx 已配置"
}

start_services() {
    step "启动服务"

    # 启动 Gunicorn
    systemctl restart "$SERVICE_NAME"
    sleep 3

    # 检查服务状态
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        info "✅ Gunicorn 运行中"
    else
        error "❌ Gunicorn 启动失败"
        echo ""
        echo -e "${YELLOW}─── 最近 30 行日志 ───${NC}"
        journalctl -u "$SERVICE_NAME" -n 30 --no-pager 2>/dev/null || true
        echo ""
        echo -e "${YELLOW}─── 手动测试命令 ───${NC}"
        echo "  cd ${BACKEND_DIR} && sudo -u ${DEPLOY_USER} ${VENV_DIR}/bin/gunicorn --config gunicorn_conf.py green_campus.wsgi:application"
        exit 1
    fi

    # 启动 Nginx
    systemctl restart nginx
    sleep 1

    if systemctl is-active --quiet nginx; then
        info "✅ Nginx 运行中"
    else
        error "❌ Nginx 启动失败"
        echo ""
        echo -e "${YELLOW}─── 最近 20 行日志 ───${NC}"
        journalctl -u nginx -n 20 --no-pager 2>/dev/null || true
        echo ""
        nginx -t 2>&1 || true
        exit 1
    fi
}

show_status() {
    step "服务状态"

    echo ""
    systemctl status "$SERVICE_NAME" --no-pager -l 2>/dev/null | head -15
    echo ""
    systemctl status nginx --no-pager -l 2>/dev/null | head -10
    echo ""

    # 真实 API 健康检查（请求实际接口而非仅看进程）
    step "API 连通性测试"

    # Gunicorn 直连（127.0.0.1:8000）
    API_DIRECT=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/api/" --max-time 5 2>/dev/null || echo "000")
    if [ "$API_DIRECT" != "000" ]; then
        info "后端 Gunicorn 直连: HTTP ${API_DIRECT}"
    else
        warn "后端 Gunicorn 直连失败（服务可能未启动）"
    fi

    # Nginx 代理（80 端口）
    API_PROXY=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1/api/" --max-time 5 2>/dev/null || echo "000")
    if [ "$API_PROXY" != "000" ]; then
        info "Nginx 代理 API: HTTP ${API_PROXY}"
    else
        warn "Nginx 代理测试失败"
    fi

    # 前端页面
    FRONTEND=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1/" --max-time 5 2>/dev/null || echo "000")
    if [ "$FRONTEND" = "200" ]; then
        info "前端页面: HTTP 200 ✓"
    else
        warn "前端页面返回 HTTP ${FRONTEND}"
    fi

    echo ""
    echo -e "${BLUE}提示:${NC} 若 API 返回 401/403 属正常（需登录鉴权），返回 200/502 才需关注"
}

show_summary() {
    step "部署完成 🎉"

    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "服务器IP")

    cat << EOF

${GREEN}╔══════════════════════════════════════════════╗${NC}
${GREEN}║        绿动校园部署成功！                      ║${NC}
${GREEN}╠══════════════════════════════════════════════╣${NC}
${GREEN}║                                              ║${NC}
${GREEN}║  前端地址:  http://${SERVER_IP}              ${NC}
${GREEN}║  后端API:   http://${SERVER_IP}/api/         ${NC}
${GREEN}║  管理后台:  http://${SERVER_IP}/admin/       ${NC}
${GREEN}║                                              ║${NC}
${GREEN}║  演示账号:  demo / demo123456                ${NC}
${GREEN}║                                              ║${NC}
${GREEN}╚══════════════════════════════════════════════╝${NC}

${BLUE}常用命令:${NC}
  更新代码:    sudo bash deploy.sh --update
  查看状态:    sudo bash deploy.sh --status
  重启服务:    sudo bash deploy.sh --restart
  查看日志:    sudo bash deploy.sh --logs
  清空数据:    sudo bash deploy.sh --flush
  Nginx日志:   sudo tail -f /var/log/nginx/green_campus_error.log

${BLUE}配置文件位置:${NC}
  环境变量:    ${BACKEND_DIR}/.env
  Nginx配置:   ${NGINX_CONF_DEST}
  Systemd:     ${SERVICE_FILE}
  项目目录:    ${DEPLOY_DIR}

EOF
}

flush_data_only() {
    step "⚠ 清除所有业务数据"

    echo -e "${RED}  这将删除所有用户、任务记录、积分等业务数据并重新初始化！${NC}"
    echo -e "${RED}  超级管理员账号会保留。${NC}"
    echo -n "  确认清空？输入 yes 继续，其他取消: "
    read -r CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        info "已取消"
        exit 0
    fi

    cd "$BACKEND_DIR"

    # 清空前备份
    backup_database

    info "正在清除数据并重新初始化..."
    "$VENV_DIR/bin/python" manage.py flush_test_data

    # 重启服务
    systemctl restart "$SERVICE_NAME"
    info "服务已重启"

    step "数据清除完成 🎉"
    echo -e "  ${GREEN}演示账号: demo / demo123456${NC}"
}

# ─── 仅更新代码（快速迭代，不碰 nginx/systemd 配置）───
update_only() {
    step "快速更新模式"

    check_root

    # 备份 + 复制代码
    backup_database
    info "复制后端代码..."
    safe_copy "${SCRIPT_DIR}/backend/" "${BACKEND_DIR}/" \
        '__pycache__' '*.pyc' 'db.sqlite3' 'logs/' '.env'
    info "复制前端代码..."
    safe_copy "${SCRIPT_DIR}/frontend/" "${FRONTEND_DIR}/"
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR"

    # 更新依赖（requirements 变化时）
    info "检查依赖..."
    "$VENV_DIR/bin/pip" install -r "${BACKEND_DIR}/requirements.txt" -q 2>&1 | tail -3

    # 迁移（数据安全，只增不改不删）
    cd "$BACKEND_DIR"
    info "应用数据库迁移..."
    "$VENV_DIR/bin/python" manage.py makemigrations users core --noinput 2>&1 | tail -3
    "$VENV_DIR/bin/python" manage.py migrate --noinput 2>&1 | tail -5
    "$VENV_DIR/bin/python" manage.py collectstatic --noinput 2>&1 | tail -2
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$BACKEND_DIR"

    # 重启
    systemctl restart "$SERVICE_NAME"
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        info "✅ 更新完成，服务运行中"
    else
        error "❌ 服务启动失败，查看日志: journalctl -u $SERVICE_NAME -n 30"
        exit 1
    fi
}

# ─── 实时查看日志 ───
show_logs() {
    step "实时日志（Ctrl+C 退出）"
    echo "  Gunicorn:  ${BACKEND_DIR}/logs/gunicorn_error.log"
    echo "  Django:    ${BACKEND_DIR}/logs/django.log"
    echo "  Nginx:     /var/log/nginx/green_campus_error.log"
    echo ""
    echo -e "${BLUE}─── Gunicorn 错误日志（最近 50 行 + 实时跟踪）───${NC}"
    journalctl -u "$SERVICE_NAME" -n 50 --no-pager 2>/dev/null
    echo ""
    echo -e "${BLUE}─── 开始实时跟踪（Ctrl+C 退出）───${NC}"
    journalctl -u "$SERVICE_NAME" -f
}

restart_services() {
    step "重启服务"
    systemctl restart "$SERVICE_NAME"
    systemctl restart nginx
    sleep 2
    info "服务已重启"
    show_status
}

uninstall() {
    step "卸载绿动校园服务"

    echo -e "${YELLOW}  这将停止并删除服务配置，但不会删除项目文件。${NC}"
    echo -n "  确认卸载？(y/n): "
    read -r CONFIRM

    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        info "已取消"
        exit 0
    fi

    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "$SERVICE_FILE"
    rm -f "$NGINX_LINK"
    rm -f "$NGINX_CONF_DEST"
    systemctl daemon-reload
    systemctl restart nginx

    info "服务已卸载"
    warn "项目文件仍保留在 ${DEPLOY_DIR}，如需删除请手动执行:"
    echo "  rm -rf ${DEPLOY_DIR}"
}

# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

main() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════╗"
    echo "║     绿动校园 · 一键部署脚本 v2.0            ║"
    echo "║     Green Campus Deploy Script              ║"
    echo "╚══════════════════════════════════════════════╝"
    echo -e "${NC}"

    case "${1:-}" in
        --flush)
            check_root
            flush_data_only
            exit 0
            ;;
        --update)
            update_only
            exit 0
            ;;
        --restart)
            check_root
            restart_services
            exit 0
            ;;
        --status)
            show_status
            exit 0
            ;;
        --logs)
            show_logs
            exit 0
            ;;
        --uninstall)
            check_root
            uninstall
            exit 0
            ;;
        --help|-h)
            echo "用法: sudo bash deploy.sh [选项]"
            echo ""
            echo "选项:"
            echo "  (无参数)    完整部署（首次安装或更新代码，数据安全）"
            echo "  --update    快速更新：仅复制代码+依赖+迁移+重启（不碰配置）"
            echo "  --flush     清空所有业务数据并重新初始化（会丢数据！）"
            echo "  --restart   重启服务"
            echo "  --status    查看服务状态 + API 健康检查"
            echo "  --logs      实时查看日志（Ctrl+C 退出）"
            echo "  --uninstall 卸载服务（保留项目文件）"
            echo "  --help      显示帮助"
            echo ""
            echo "可选环境变量:"
            echo "  ADMIN_USERNAME / ADMIN_PASSWORD  首次部署自动创建超管"
            echo "  INIT_DEMO_DATA=1                 强制初始化演示数据"
            echo "  DEPLOY_DIR=/opt/green-campus     自定义部署路径"
            exit 0
            ;;
    esac

    # 完整部署流程
    check_root
    check_system
    copy_project
    setup_virtualenv
    setup_env_file
    setup_database
    setup_superuser
    setup_systemd
    setup_nginx
    start_services
    show_summary
}

main "$@"
