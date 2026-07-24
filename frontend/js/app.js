/* ════════════════════════════════════════════════════════
   绿动校园 · 前端交互逻辑
════════════════════════════════════════════════════════ */

// ─── 配置 ───
// 开发环境指向本地后端；生产环境用相对路径（由 Nginx 反代 /api/ → Gunicorn）
const API_BASE = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost'
  ? 'http://127.0.0.1:8000/api'
  : '/api';

// ─── 状态 ───
let TOKEN = localStorage.getItem('gc_token') || '';
let REFRESH = localStorage.getItem('gc_refresh') || '';
let USER = null;
let currentPage = 'home';
let selectedCharity = null;
let pendingAction = null;

// ─── 工具函数 ───
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function getToken() { return TOKEN; }

async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (TOKEN) headers['Authorization'] = `Bearer ${TOKEN}`;
  try {
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    // token 过期尝试刷新
    if (res.status === 401 && REFRESH) {
      const ok = await refreshToken();
      if (ok) {
        headers['Authorization'] = `Bearer ${TOKEN}`;
        const res2 = await fetch(`${API_BASE}${path}`, { ...options, headers });
        return handleRes(res2);
      }
      logout();
      throw new Error('登录已过期');
    }
    return handleRes(res);
  } catch (e) {
    showToast('网络错误，请检查后端服务');
    throw e;
  }
}

async function handleRes(res) {
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || '请求失败');
  }
  return data;
}

async function refreshToken() {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: REFRESH }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    TOKEN = data.access;
    localStorage.setItem('gc_token', TOKEN);
    return true;
  } catch { return false; }
}

function showToast(msg) {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
}

function saveAuth(data) {
  TOKEN = data.token.access;
  REFRESH = data.token.refresh;
  USER = data.user;
  localStorage.setItem('gc_token', TOKEN);
  localStorage.setItem('gc_refresh', REFRESH);
  localStorage.setItem('gc_user', JSON.stringify(USER));
}

function logout() {
  TOKEN = ''; REFRESH = ''; USER = null;
  localStorage.removeItem('gc_token');
  localStorage.removeItem('gc_refresh');
  localStorage.removeItem('gc_user');
  $('#app').style.display = 'none';
  $('#auth-page').style.display = 'flex';
}

// ─── 初始化 ───
document.addEventListener('DOMContentLoaded', () => {
  // 恢复登录态
  const savedUser = localStorage.getItem('gc_user');
  if (TOKEN && savedUser) {
    USER = JSON.parse(savedUser);
    showApp();
  }

  bindAuthEvents();
  bindNavEvents();
  bindModalEvents();
  bindSettingEvents();
  bindMonopolyEvents();
});

// ─── 认证事件 ───
function bindAuthEvents() {
  // Tab 切换
  $$('.auth-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      $$('.auth-tab').forEach(t => t.classList.remove('active'));
      $$('.auth-form').forEach(f => f.classList.remove('active'));
      tab.classList.add('active');
      $(`#${tab.dataset.tab}-form`).classList.add('active');
    });
  });

  // 登录
  $('#login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const data = await api('/auth/login/', {
        method: 'POST',
        body: JSON.stringify({
          username: $('#login-username').value,
          password: $('#login-password').value,
        }),
      });
      saveAuth(data);
      showApp();
      showToast('登录成功');
    } catch (err) {
      showToast(err.message);
    }
  });

  // 注册
  $('#register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const data = await api('/auth/register/', {
        method: 'POST',
        body: JSON.stringify({
          username: $('#reg-username').value,
          nickname: $('#reg-nickname').value || '低碳新人',
          student_id: $('#reg-studentid').value,
          college: $('#reg-college').value,
          major: $('#reg-major').value,
          password: $('#reg-password').value,
          password2: $('#reg-password2').value,
        }),
      });
      saveAuth(data);
      showApp();
      showToast('注册成功，欢迎加入！');
    } catch (err) {
      showToast(err.message);
    }
  });
}

// ─── 显示主应用 ───
function showApp() {
  $('#auth-page').style.display = 'none';
  $('#app').style.display = 'flex';
  updateUserUI();
  switchPage('home');
}

function updateUserUI() {
  if (!USER) return;
  $('#side-name').textContent = USER.nickname;
  $('#side-pts').textContent = `${USER.available_points} 积分`;
  $('#side-avatar').textContent = USER.avatar_emoji || '🌱';
  $('#topbar-pts span').textContent = USER.available_points;
  $('#mb-pts').textContent = `🌱 ${USER.available_points}`;
}

// ─── 导航 ───
function bindNavEvents() {
  // 侧边栏 + Tab 共用
  $$('[data-page]').forEach(el => {
    el.addEventListener('click', (e) => {
      if (el.classList.contains('section-more')) return; // 让默认跳转
      e.preventDefault();
      switchPage(el.dataset.page);
    });
  });

  // 移动端菜单
  $('#mb-menu-btn').addEventListener('click', () => {
    $('#sidebar').classList.toggle('open');
    $('#sidebar-overlay').classList.toggle('open');
  });
  $('#sidebar-overlay').addEventListener('click', () => {
    $('#sidebar').classList.remove('open');
    $('#sidebar-overlay').classList.remove('open');
  });
}

function switchPage(page) {
  currentPage = page;
  $$('.page').forEach(p => p.classList.remove('active'));
  $(`#page-${page}`).classList.add('active');
  // 导航高亮
  $$('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.page === page));
  $$('.tab-item').forEach(n => n.classList.toggle('active', n.dataset.page === page));

  const titles = { home:'首页', challenge:'校园挑战', shop:'积分商城', rank:'排行榜', monopoly:'绿色大富翁', profile:'我的' };
  $('#topbar-title').textContent = titles[page];
  $('#mb-title').textContent = titles[page];

  // 关闭移动端侧边栏
  $('#sidebar').classList.remove('open');
  $('#sidebar-overlay').classList.remove('open');
  // 滚动到顶
  $('#app-scroll').scrollTop = 0;

  // 加载对应数据
  const loaders = {
    home: loadHome, challenge: loadChallenges, shop: loadShop,
    rank: loadLeaderboard, monopoly: loadMonopoly, profile: loadProfile,
  };
  if (loaders[page]) loaders[page]();
}

// ─── 首页 ───
async function loadHome() {
  try {
    const data = await api('/home/');
    const u = data.user;
    USER = { ...USER, ...u };
    localStorage.setItem('gc_user', JSON.stringify(USER));
    updateUserUI();

    $('#hero-greeting').textContent = greeting();
    $('#hero-name').textContent = u.nickname;
    $('#hero-points').textContent = u.total_points;
    $('#hero-streak').textContent = u.streak_days;
    $('#hero-carbon').textContent = u.total_carbon_reduction.toFixed(1);
    $('#hero-tasks').textContent = u.total_tasks_done;
    $('#hero-level').textContent = `Lv.${u.level}`;

    const t = data.today;
    $('#prog-count').textContent = `${t.done_tasks}/${t.total_tasks}`;
    $('#prog-fill').style.width = `${t.progress}%`;
    $('#prog-note').textContent = `今日已获 ${t.points} 积分，${t.done_tasks >= t.total_tasks ? '全部完成，太棒了！' : '继续加油！'}`;

    // 任务列表
    $('#task-list').innerHTML = data.tasks.map(task => `
      <div class="task-card ${task.is_done ? 'done' : ''}" data-id="${task.id}" ${task.is_done ? '' : 'role="button" tabindex="0"'}>
        <div class="t-icon">${task.icon}</div>
        <div class="t-info">
          <div class="t-name">${task.name}</div>
          <div class="t-desc">${task.description || task.category_label} · 今日 ${task.done_count}/${task.daily_limit}</div>
        </div>
        <div class="t-right">
          <span class="t-pts ${task.is_done ? 'earned' : ''}">+${task.points}</span>
          <button class="t-check ${task.is_done ? 'done' : ''}" data-task="${task.id}" ${task.is_done ? 'disabled' : ''}>${task.is_done ? '✓' : ''}</button>
        </div>
      </div>
    `).join('');

    // 任务点击（事件委托到列表容器，整卡可点，避免小按钮难以命中）
    $('#task-list').onclick = async (e) => {
      const card = e.target.closest('.task-card');
      if (!card || card.classList.contains('done') || card.dataset.busy === '1') return;
      const id = card.dataset.id;
      const btn = card.querySelector('.t-check');
      card.dataset.busy = '1';
      // 立即打勾反馈
      btn.classList.add('done');
      btn.textContent = '✓';
      card.classList.add('done');
      btn.disabled = true;
      try {
        const res = await api(`/tasks/${id}/complete/`, { method: 'POST' });
        showToast(res.message);
        USER = { ...USER, ...res.user };
        localStorage.setItem('gc_user', JSON.stringify(USER));
        updateUserUI();
        loadHome();
      } catch (err) {
        // 失败则回退
        btn.classList.remove('done');
        btn.textContent = '';
        card.classList.remove('done');
        btn.disabled = false;
        showToast(err.message);
      } finally {
        card.dataset.busy = '0';
      }
    };

    // 排行速览
    $('#rank-mini').innerHTML = data.rank_mini.map(r => `
      <div class="rank-row ${r.is_me ? 'me' : ''}">
        <div class="rk-num ${r.rank<=3 ? 'g'+r.rank : ''}">${r.rank}</div>
        <div class="rk-ava">${r.avatar}</div>
        <div class="rk-name">${r.nickname}${r.is_me ? '（我）' : ''}</div>
        <div class="rk-pts">${r.points}</div>
      </div>
    `).join('');

  } catch (err) { showToast(err.message); }
}

function greeting() {
  const h = new Date().getHours();
  if (h < 6) return '凌晨好'; if (h < 9) return '早上好';
  if (h < 12) return '上午好'; if (h < 14) return '中午好';
  if (h < 18) return '下午好'; return '晚上好';
}

// ─── 挑战 ───
let challengeStatus = '';
async function loadChallenges() {
  try {
    const data = await api(`/challenges/${challengeStatus ? '?status=' + challengeStatus : ''}`);
    $('#challenge-list').innerHTML = data.length ? data.map(c => `
      <div class="ch-card">
        <div class="ch-thumb">${c.cover}
          <span class="ch-tag">${c.tag || c.status_label}</span>
        </div>
        <div class="ch-body">
          <div class="ch-name">${c.title}</div>
          <div class="ch-desc">${c.description}</div>
          <div class="ch-footer">
            <div>
              <div class="ch-pts-badge">+${c.points} 积分</div>
              <div class="ch-meta">${c.participants_count} 人参与</div>
            </div>
            <button class="btn-join" data-challenge="${c.id}">加入挑战</button>
          </div>
        </div>
      </div>
    `).join('') : '<div style="text-align:center;padding:40px;color:var(--text-lt)">暂无挑战</div>';

    $$('.btn-join').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          const res = await api(`/challenges/${btn.dataset.challenge}/join/`, { method: 'POST' });
          showToast(res.message);
          btn.classList.add('joined');
          btn.textContent = '已加入';
        } catch (err) { showToast(err.message); }
      });
    });
  } catch (err) { showToast(err.message); }
}

// 挑战筛选
document.addEventListener('click', (e) => {
  if (e.target.closest('#challenge-chips .chip')) {
    $$('#challenge-chips .chip').forEach(c => c.classList.remove('active'));
    e.target.classList.add('active');
    challengeStatus = e.target.dataset.status;
    loadChallenges();
  }
  if (e.target.closest('#rank-chips .chip')) {
    $$('#rank-chips .chip').forEach(c => c.classList.remove('active'));
    e.target.classList.add('active');
    loadLeaderboard(e.target.dataset.period);
  }
});

// ─── 商城 ───
async function loadShop() {
  try {
    const [items, charity] = await Promise.all([
      api('/shop/'), api('/charity/')
    ]);
    $('#shop-pts').textContent = USER?.available_points || 0;

    $('#shop-grid').innerHTML = items.map(item => `
      <div class="item-card">
        <div class="item-img">${item.image}
          ${item.tag ? `<span class="item-sticker ${item.tag}">${item.tag_label}</span>` : ''}
        </div>
        <div class="item-body">
          <div class="item-name">${item.name}</div>
          <div class="item-stock">库存 ${item.stock}</div>
          <div class="item-bottom">
            <span class="item-cost">${item.cost}</span>
            <button class="btn-redeem" data-item="${item.id}" ${item.stock<=0?'disabled':''}>兑换</button>
          </div>
        </div>
      </div>
    `).join('');

    $$('.btn-redeem').forEach(btn => {
      btn.addEventListener('click', () => {
        const item = items.find(i => i.id == btn.dataset.item);
        openModal('确认兑换', `兑换「${item.name}」`, item.cost, async () => {
          try {
            const res = await api(`/shop/${item.id}/redeem/`, { method: 'POST' });
            showToast(res.message);
            USER.available_points = res.available_points;
            localStorage.setItem('gc_user', JSON.stringify(USER));
            updateUserUI();
            loadShop();
          } catch (err) { showToast(err.message); }
        });
      });
    });

    // 公益
    $('#charity-list').innerHTML = charity.map(p => `
      <div class="ch-opt" data-charity="${p.id}">
        <div class="ch-opt-icon">${p.icon}</div>
        <div class="ch-opt-name">${p.name}</div>
        <div class="ch-opt-pts">${p.cost} 积分</div>
      </div>
    `).join('');

    $$('.ch-opt').forEach(opt => {
      opt.addEventListener('click', () => {
        $$('.ch-opt').forEach(o => o.classList.remove('selected'));
        opt.classList.add('selected');
        selectedCharity = charity.find(p => p.id == opt.dataset.charity);
      });
    });

    // 捐赠按钮（动态添加）
    let donateBtn = $('#donate-btn');
    if (!donateBtn) {
      donateBtn = document.createElement('button');
      donateBtn.id = 'donate-btn';
      donateBtn.className = 'btn-donate';
      donateBtn.textContent = '立即捐赠';
      donateBtn.addEventListener('click', () => {
        if (!selectedCharity) { showToast('请选择公益项目'); return; }
        openModal('确认捐赠', `捐赠「${selectedCharity.name}」`, selectedCharity.cost, async () => {
          try {
            const res = await api(`/charity/${selectedCharity.id}/donate/`, { method: 'POST' });
            showToast(res.message);
            USER.available_points = res.available_points;
            localStorage.setItem('gc_user', JSON.stringify(USER));
            updateUserUI();
            loadShop();
          } catch (err) { showToast(err.message); }
        });
      });
      $('.charity-section').appendChild(donateBtn);
    }
  } catch (err) { showToast(err.message); }
}

// ─── 排行榜 ───
async function loadLeaderboard(period = 'week') {
  try {
    const data = await api(`/leaderboard/?period=${period}`);
    // 领奖台
    const top3 = data.slice(0, 3);
    const order = [top3[1], top3[0], top3[2]].filter(Boolean);
    $('#rank-podium').innerHTML = order.map((u, i) => {
      const isFirst = u && top3[0] && u.id === top3[0].id;
      return `
        <div class="podium-item ${isFirst ? 'first' : ''}">
          ${isFirst ? '<div class="podium-crown">👑</div>' : ''}
          <div class="podium-ava">${u.avatar}</div>
          <div class="podium-name">${u.nickname}</div>
          <div class="podium-pts">${u.points} 分</div>
        </div>
      `;
    }).join('');

    // 完整列表
    $('#lb-full').innerHTML = data.map(u => `
      <div class="lb-row ${u.is_me ? 'me' : ''}">
        <div class="lb-rank-n">${u.rank}</div>
        <div class="lb-ava">${u.avatar}</div>
        <div class="lb-info">
          <div class="lb-name">${u.nickname}${u.is_me ? '（我）' : ''}</div>
          <div class="lb-dept">${u.college || ''} ${u.major || ''}</div>
        </div>
        <div class="lb-right">
          <div class="lb-pts-val">${u.points}</div>
          <div class="lb-week">累计 ${u.total_points}</div>
        </div>
      </div>
    `).join('');
  } catch (err) { showToast(err.message); }
}

// ─── 我的 ───
async function loadProfile() {
  try {
    // 刷新用户信息
    const me = await api('/auth/me/');
    USER = { ...USER, ...me };
    localStorage.setItem('gc_user', JSON.stringify(USER));
    updateUserUI();

    $('#prof-avatar').textContent = me.avatar_emoji || '🌱';
    $('#prof-name').textContent = me.nickname;
    $('#prof-school').textContent = `${me.college || '学院'} · ${me.major || '专业'}`;
    $('#prof-level').textContent = `Lv.${me.level} ${me.level_title}`;
    $('#prof-total-pts').textContent = me.total_points;
    $('#prof-carbon').textContent = me.total_carbon_reduction.toFixed(1);
    $('#prof-streak').textContent = me.streak_days;

    // 徽章
    const badges = await api('/badges/');
    $('#badges-row').innerHTML = badges.map(b => `
      <div class="badge-item ${b.earned ? '' : 'locked'}">
        <div class="badge-icon">${b.icon}</div>
        <div class="badge-name">${b.name}</div>
      </div>
    `).join('');

    // 绿色记录
    const records = await api('/green-records/');
    $('#green-records').innerHTML = records.length ? records.map(r => `
      <div class="gr-row">
        <div class="gr-icon">${r.icon}</div>
        <div class="gr-info">
          <div class="gr-name">${r.name}</div>
          <div class="gr-date">${r.date}</div>
        </div>
        <div class="gr-pts ${r.sign === '+' ? 'plus' : 'minus'}">${r.sign}${r.points}</div>
      </div>
    `).join('') : '<div style="padding:30px;text-align:center;color:var(--text-lt)">暂无记录</div>';

    // 小组
    const groups = await api('/groups/');
    $('#group-list').innerHTML = groups.map(g => `
      <div class="group-row">
        <div class="group-icon-box">${g.icon}</div>
        <div class="group-info">
          <div class="group-name">${g.name}</div>
          <div class="group-sub">${g.description || ''} · ${g.member_count}人</div>
        </div>
        <button class="btn-checkin" data-group="${g.id}">签到</button>
      </div>
    `).join('');

    $$('.btn-checkin').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          const res = await api(`/groups/${btn.dataset.group}/checkin/`, { method: 'POST' });
          showToast(res.message);
          btn.classList.add('done');
          btn.textContent = '已签到';
          loadProfile();
        } catch (err) {
          showToast(err.message);
          btn.classList.add('done');
          btn.textContent = '已签到';
        }
      });
    });
  } catch (err) { showToast(err.message); }
}

// ─── 绿色大富翁 ───
let mpState = null; // 缓存棋盘全景

async function loadMonopoly() {
  try {
    const data = await api('/monopoly/');
    mpState = data;
    renderMonopolyBoard(data);
    renderMonopolyStatus(data);
    renderMonopolyProps(data);
    renderMonopolyRank(data.rank_mini || []);
    // 加载日志
    try {
      const logs = await api('/monopoly/logs/');
      renderMonopolyLogs(logs);
    } catch { renderMonopolyLogs([]); }
    $('#mp-action-btns').innerHTML = '';
  } catch (err) { showToast(err.message); }
}

function renderMonopolyStatus(data) {
  const p = data.player;
  $('#mp-points').textContent = p.available_points;
  $('#mp-dice').textContent = `🎲 ${p.dice_count}`;
  const tile = (data.board || []).find(t => t.position === p.position);
  $('#mp-pos').textContent = tile ? `${tile.icon} ${tile.name}` : `第${p.position}格`;
  $('#mp-asset').textContent = data.asset_value || 0;
  $('#mp-props-count').textContent = `${(data.assets || []).length}/3`;
  // 掷骰按钮状态
  const btn = $('#mp-btn-roll');
  if (p.is_trapped) {
    btn.disabled = true; btn.classList.add('disabled');
    btn.innerHTML = '<span class="mp-dice-emoji">⛽</span><span>被困中·答题脱困</span>';
  } else if (p.dice_count <= 0) {
    btn.disabled = true; btn.classList.add('disabled');
    btn.innerHTML = '<span class="mp-dice-emoji">🎲</span><span>无骰子·去完成任务</span>';
  } else {
    btn.disabled = false; btn.classList.remove('disabled');
    btn.innerHTML = '<span class="mp-dice-emoji">🎲</span><span>掷骰子</span>';
  }
}

function renderMonopolyBoard(data) {
  const board = data.board || [];
  const p = data.player;
  const layout = buildBoardLayout();
  // 从 board 中提取所有权信息（tile_detail 已含 owner/level）
  const tileMap = {};
  board.forEach(t => { tileMap[t.position] = t; });

  let html = '';
  for (let r = 0; r < 7; r++) {
    for (let c = 0; c < 7; c++) {
      const pos = layout[r][c];
      if (pos === 0) {
        if (r >= 2 && r <= 4 && c >= 2 && c <= 4) {
          html += '<div class="mp-cell mp-cell-center"></div>';
        } else {
          html += '<div class="mp-cell mp-cell-empty"></div>';
        }
      } else {
        const tile = tileMap[pos];
        if (!tile) { html += '<div class="mp-cell mp-cell-empty"></div>'; continue; }
        const isHere = pos === p.position;
        const ownerInfo = tile.owner ? `${tile.owner.avatar} ${'⭐'.repeat(tile.level || 1)}` : '';
        html += `
          <div class="mp-cell mp-type-${tile.tile_type} ${isHere ? 'mp-here' : ''}" data-pos="${pos}">
            <div class="mp-cell-pos">${pos}</div>
            <div class="mp-cell-icon">${tile.icon}</div>
            <div class="mp-cell-name">${tile.name}</div>
            ${ownerInfo ? `<div class="mp-cell-owner">${ownerInfo}</div>` : ''}
            ${isHere ? '<div class="mp-cell-pin">📍</div>' : ''}
          </div>`;
      }
    }
  }
  $('#mp-board').innerHTML = html;
}

// 构建 7×7 环形布局矩阵，外圈24格，中心9格留空
function buildBoardLayout() {
  const grid = Array.from({length:7}, () => Array(7).fill(0));
  let pos = 1;
  for (let c = 0; c < 6; c++) grid[0][c] = pos++;       // 1-6 上排
  for (let r = 1; r < 7; r++) grid[r][6] = pos++;       // 7-12 右列
  for (let c = 5; c >= 0; c--) grid[6][c] = pos++;      // 13-18 下排
  for (let r = 5; r >= 1; r--) grid[r][0] = pos++;      // 19-24 左列
  return grid;
}

function renderMonopolyProps(data) {
  const props = data.assets || [];
  if (props.length === 0) {
    $('#mp-props').innerHTML = '<div class="mp-empty">暂未认领任何低碳场景</div>';
    return;
  }
  $('#mp-props').innerHTML = props.map(pr => `
    <div class="mp-prop-card">
      <div class="mp-prop-icon">${pr.icon}</div>
      <div class="mp-prop-info">
        <div class="mp-prop-name">${pr.name}</div>
        <div class="mp-prop-meta">Lv.${pr.level} · 过路费 ${pr.toll}</div>
      </div>
      <div class="mp-prop-val">${pr.value}</div>
    </div>
  `).join('');
}

function renderMonopolyLogs(logs) {
  if (!logs || logs.length === 0) {
    $('#mp-logs').innerHTML = '<div class="mp-empty">暂无游戏日志</div>';
    return;
  }
  $('#mp-logs').innerHTML = logs.map(l => `
    <div class="mp-log-row">
      <div class="mp-log-act">${l.action_label}</div>
      <div class="mp-log-desc">${l.description}</div>
      <div class="mp-log-pts ${l.points_change >= 0 ? 'plus' : 'minus'}">${l.points_change >= 0 ? '+' : ''}${l.points_change}</div>
    </div>
  `).join('');
}

function renderMonopolyRank(rank) {
  if (!rank || rank.length === 0) {
    $('#mp-rank').innerHTML = '<div class="mp-empty">暂无排行数据</div>';
    return;
  }
  $('#mp-rank').innerHTML = rank.map(u => `
    <div class="mp-rank-row ${u.is_me ? 'me' : ''}">
      <div class="mp-rank-n">${u.rank}</div>
      <div class="mp-rank-ava">${u.avatar || '🌱'}</div>
      <div class="mp-rank-name">${u.nickname}${u.is_me ? '（我）' : ''}</div>
      <div class="mp-rank-val">${u.asset_value}</div>
    </div>
  `).join('');
}

// 掷骰子
async function mpRoll() {
  const btn = $('#mp-btn-roll');
  btn.disabled = true;
  btn.innerHTML = '<span class="mp-dice-emoji mp-rolling">🎲</span><span>掷骰中...</span>';
  try {
    const res = await api('/monopoly/roll/', { method: 'POST' });
    await mpDiceAnimation(res.dice_value || 1);
    // 更新缓存的玩家状态
    if (mpState) {
      mpState.player = res.player;
    }
    renderMonopolyStatus({ ...mpState, player: res.player });
    renderMonopolyBoard({ ...mpState, player: res.player });
    // 刷新顶部积分
    if (USER && res.player) {
      USER.available_points = res.player.available_points;
      localStorage.setItem('gc_user', JSON.stringify(USER));
      updateUserUI();
    }
    // 处理事件结果
    const ev = res.tile_event;
    if (ev) {
      if (ev.type === 'trap') {
        showMpTrapModal(res);
      } else if (ev.type === 'trap_released') {
        showToast(ev.message);
        loadMonopoly();
      } else {
        showMpEventModal(res, ev);
      }
    } else {
      showToast(`掷出 ${res.dice_value} 点，到达「${res.tile?.name || ''}」`);
      mpShowActionBtns(res);
    }
    // 徽章提示
    (res.new_badges || []).forEach(b => showToast(`🏅 获得徽章：${b.name}`));
    // 刷新日志
    try { renderMonopolyLogs(await api('/monopoly/logs/')); } catch {}
  } catch (err) {
    showToast(err.message);
    renderMonopolyStatus(mpState);
  }
}

function mpDiceAnimation(steps) {
  return new Promise(resolve => {
    const emoji = $('#mp-btn-roll .mp-dice-emoji');
    if (!emoji) { setTimeout(resolve, 300); return; }
    let count = 0;
    const faces = ['⚀','⚁','⚂','⚃','⚄','⚅'];
    const timer = setInterval(() => {
      emoji.textContent = faces[count % 6];
      count++;
      if (count > 8) {
        clearInterval(timer);
        emoji.textContent = faces[steps - 1] || '🎲';
        setTimeout(resolve, 300);
      }
    }, 80);
  });
}

// 显示认领/升级按钮（基于当前格子状态）
function mpShowActionBtns(res) {
  const area = $('#mp-action-btns');
  area.innerHTML = '';
  // 从全景获取当前格子详情
  if (!mpState) return;
  const tile = (mpState.board || []).find(t => t.position === res.new_position);
  if (!tile || tile.tile_type !== 'scene') return;
  if (!tile.owner) {
    // 可认领
    const btn = document.createElement('button');
    btn.className = 'mp-btn-action mp-btn-claim';
    btn.innerHTML = `🏠 认领（${tile.claim_cost}积分）`;
    btn.addEventListener('click', () => mpClaim());
    area.appendChild(btn);
  } else if (tile.owner.id === USER?.id && (tile.level || 1) < 3) {
    // 可升级
    const btn = document.createElement('button');
    btn.className = 'mp-btn-action mp-btn-upgrade';
    btn.innerHTML = `⭐ 升级至Lv.${(tile.level || 1) + 1}（${tile.upgrade_cost}积分）`;
    btn.addEventListener('click', () => mpUpgrade());
    area.appendChild(btn);
  }
}

async function mpClaim() {
  try {
    const res = await api('/monopoly/claim/', { method: 'POST' });
    $('#mp-action-btns').innerHTML = '';
    showToast(res.message);
    (res.new_badges || []).forEach(b => showToast(`🏅 获得徽章：${b.name}`));
    if (USER) { USER.available_points = res.available_points; localStorage.setItem('gc_user', JSON.stringify(USER)); updateUserUI(); }
    loadMonopoly();
  } catch (err) { showToast(err.message); }
}

async function mpUpgrade() {
  try {
    const res = await api('/monopoly/upgrade/', { method: 'POST' });
    $('#mp-action-btns').innerHTML = '';
    showToast(res.message);
    (res.new_badges || []).forEach(b => showToast(`🏅 获得徽章：${b.name}`));
    if (USER) { USER.available_points = res.available_points; localStorage.setItem('gc_user', JSON.stringify(USER)); updateUserUI(); }
    loadMonopoly();
  } catch (err) { showToast(err.message); }
}

// 事件弹窗（机遇/危机/过路费/任务/公益/起点）
function showMpEventModal(res, ev) {
  let icon = '🎲', title = '事件', ptsText = '', ptsClass = '';
  switch (ev.type) {
    case 'chance': icon = '🎉'; title = '绿色机遇'; break;
    case 'crisis': icon = '🌪️'; title = '碳危机'; break;
    case 'toll': icon = '💸'; title = '支付过路费'; break;
    case 'own_scene': icon = '🏠'; title = '回到自家场景'; break;
    case 'task': icon = '📋'; title = '任务格'; break;
    case 'charity': icon = '🌳'; title = '公益格'; break;
    case 'start': icon = '🏁'; title = '经过起点'; break;
    default: icon = '🎲'; title = '事件';
  }
  if (ev.points_change !== undefined && ev.points_change !== 0) {
    ptsText = `${ev.points_change >= 0 ? '+' : ''}${ev.points_change} 积分`;
    ptsClass = ev.points_change >= 0 ? 'plus' : 'minus';
  } else if (ev.toll) {
    ptsText = `-${ev.toll} 积分`;
    ptsClass = 'minus';
  }
  $('#mp-modal-icon').textContent = icon;
  $('#mp-modal-title').textContent = title;
  $('#mp-modal-desc').textContent = ev.message || ev.description || '';
  $('#mp-modal-pts').textContent = ptsText;
  $('#mp-modal-pts').className = `mp-modal-pts ${ptsClass}`;
  $('#mp-quiz-area').style.display = 'none';
  $('#mp-modal-actions').innerHTML = '<button class="btn-confirm" id="mp-modal-ok">确定</button>';
  $('#mp-modal-overlay').classList.add('open');
  $('#mp-modal-ok').addEventListener('click', () => {
    $('#mp-modal-overlay').classList.remove('open');
    mpShowActionBtns(res);
    loadMonopoly();
  });
}

// 陷阱答题弹窗
function showMpTrapModal(res) {
  const quiz = res.tile_event?.quiz;
  if (!quiz) { showToast('陷阱触发但无题目'); return; }
  $('#mp-modal-icon').textContent = '⛽';
  $('#mp-modal-title').textContent = '高碳陷阱';
  $('#mp-modal-desc').textContent = '被困住了！答对低碳知识题即可脱困';
  $('#mp-modal-pts').textContent = '';
  $('#mp-quiz-area').style.display = 'block';
  $('#mp-quiz-q').textContent = quiz.question;
  $('#mp-quiz-opts').innerHTML = quiz.options.map((opt, i) => `
    <button class="mp-quiz-opt" data-idx="${i}">${opt}</button>
  `).join('');
  $('#mp-modal-actions').innerHTML = '';
  $('#mp-modal-overlay').classList.add('open');
  $$('.mp-quiz-opt').forEach(btn => {
    btn.addEventListener('click', async () => {
      const idx = parseInt(btn.dataset.idx);
      try {
        const r = await api('/monopoly/resolve-event/', {
          method: 'POST',
          body: JSON.stringify({ action: 'trap_answer', answer: idx }),
        });
        if (r.released) {
          $('#mp-quiz-area').style.display = 'none';
          $('#mp-modal-icon').textContent = r.correct === false ? '🔓' : '✅';
          $('#mp-modal-title').textContent = r.correct === false ? '已强制释放' : '答对了！';
          $('#mp-modal-desc').textContent = r.message;
          $('#mp-modal-actions').innerHTML = '<button class="btn-confirm" id="mp-modal-ok">好的</button>';
          $('#mp-modal-ok').addEventListener('click', () => {
            $('#mp-modal-overlay').classList.remove('open');
            loadMonopoly();
          });
        } else {
          btn.classList.add('wrong');
          showToast(r.message);
        }
      } catch (err) { showToast(err.message); }
    });
  });
}

function bindMonopolyEvents() {
  $('#mp-btn-roll').addEventListener('click', mpRoll);
  $('#mp-modal-overlay').addEventListener('click', (e) => {
    if (e.target === $('#mp-modal-overlay')) {
      // 陷阱答题时不允许点击外部关闭
      if ($('#mp-quiz-area').style.display === 'none') {
        $('#mp-modal-overlay').classList.remove('open');
      }
    }
  });
}

// ─── 弹窗 ───
function bindModalEvents() {
  $('#modal-cancel').addEventListener('click', closeModal);
  $('#modal-overlay').addEventListener('click', (e) => {
    if (e.target === $('#modal-overlay')) closeModal();
  });
  $('#modal-confirm').addEventListener('click', () => {
    if (pendingAction) pendingAction();
    closeModal();
  });
}

function openModal(title, sub, pts, onConfirm) {
  $('#modal-title').textContent = title;
  $('#modal-sub').textContent = sub;
  $('#modal-pts').textContent = pts;
  pendingAction = onConfirm;
  $('#modal-overlay').classList.add('open');
}

function closeModal() {
  $('#modal-overlay').classList.remove('open');
  pendingAction = null;
}

// ─── 设置 ───
function bindSettingEvents() {
  $('#setting-logout').addEventListener('click', () => {
    if (confirm('确定退出登录？')) { logout(); showToast('已退出登录'); }
  });
  $('#setting-about').addEventListener('click', () => {
    showToast('绿动校园 V1.0 · 让低碳成为习惯');
  });
  $('#setting-profile').addEventListener('click', () => {
    const nickname = prompt('请输入新昵称', USER?.nickname || '');
    if (nickname) updateProfile({ nickname });
  });
  $('#setting-notify').addEventListener('click', async () => {
    try {
      const data = await api('/notifications/');
      if (data.length === 0) { showToast('暂无通知'); return; }
      showToast(data[0].title);
    } catch (err) { showToast('暂无通知'); }
  });
}

async function updateProfile(payload) {
  try {
    const res = await api('/auth/profile/', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    USER = { ...USER, ...res.user };
    localStorage.setItem('gc_user', JSON.stringify(USER));
    updateUserUI();
    loadProfile();
    showToast('更新成功');
  } catch (err) { showToast(err.message); }
}
