/**
 * StartApp PhishGuard — Admin Web Dashboard Logic
 * High-performance, reactive cybersec monitoring & threat forensics client.
 */

// Global State
let currentTab = 'overview';
let currentScanPage = 1;
const scanPageSize = 15;
let currentScanVerdict = '';
let currentScanSearch = '';
let searchDebounceTimer = null;
let currentDrawerUrlId = null;
let currentDrawerUrl = null;

// Initialization on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initDashboard();
});

function initDashboard() {
  fetchDashboardStats();
  fetchRecentOverviewScans();

  // Background Live Polling every 15 seconds
  setInterval(() => {
    fetchDashboardStats(true);
  }, 15000);
}

/**
 * Tab Switching Logic
 */
function switchTab(tabId) {
  currentTab = tabId;

  // Update Nav Buttons
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.classList.remove('active');
  });
  const activeNavBtn = document.getElementById(`nav-tab-${tabId}`);
  if (activeNavBtn) activeNavBtn.classList.add('active');

  // Update Panes
  document.querySelectorAll('.tab-pane').forEach(pane => {
    pane.classList.remove('active');
  });
  const activePane = document.getElementById(`pane-${tabId}`);
  if (activePane) activePane.classList.add('active');

  // Update Headings
  const heading = document.getElementById('page-heading');
  const subheading = document.getElementById('page-subheading');

  switch (tabId) {
    case 'overview':
      heading.innerText = 'Boshqaruv Paneli & Tizim Holati';
      subheading.innerText = 'Telegram xabarlari orqali aniqlangan xavflar va monitoring statistikasi';
      fetchDashboardStats();
      fetchRecentOverviewScans();
      break;
    case 'scans':
      heading.innerText = 'Skanerlangan Barcha Saytlar';
      subheading.innerText = 'Tizim aniqlagan fishing, firibgarlik (qimor), shubhali va toza havolalar arxivi';
      fetchScans();
      break;
    case 'accounts':
      heading.innerText = 'Telegram Monitoring Hisoblari';
      subheading.innerText = 'Ulangan, chiqarib yuborilgan yoki bekor qilingan foydalanuvchi hisoblari ro\'yxati';
      fetchAccounts();
      break;
    case 'notifications':
      heading.innerText = 'Ogohlantirish Xabarlari Jurnali';
      subheading.innerText = 'Telegram bot orqali foydalanuvchilarga yuborilgan xavfsizlik ogohlantirishlari';
      fetchNotifications();
      break;
    case 'sandbox':
      heading.innerText = 'Kiber Razvedka Sandboxi';
      subheading.innerText = 'Yangi havolalarni sun\'iy intellekt va texnik tahlil orqali real vaqtda tekshirish';
      break;
  }
}

/**
 * Manual Refresh Action
 */
function refreshDashboardData() {
  const btn = document.getElementById('btn-manual-refresh');
  if (btn) btn.classList.add('loading');

  fetchDashboardStats();

  if (currentTab === 'overview') {
    fetchRecentOverviewScans();
  } else if (currentTab === 'scans') {
    fetchScans();
  } else if (currentTab === 'accounts') {
    fetchAccounts();
  } else if (currentTab === 'notifications') {
    fetchNotifications();
  }

  setTimeout(() => {
    if (btn) btn.classList.remove('loading');
    showToast('Ma\'lumotlar yangilandi', 'success');
  }, 600);
}

/**
 * Fetch Aggregated Platform Statistics & System Health
 */
async function fetchDashboardStats(isSilent = false) {
  try {
    const res = await fetch('/api/v1/admin/stats');
    if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
    const data = await res.json();
    if (!data.success) throw new Error('API reported failure');

    const stats = data.stats;
    const health = data.system_health;

    // 1. Update KPI Values
    setText('stat-connected-accounts', stats.connected_accounts);
    setText('stat-disconnected-accounts', stats.disconnected_accounts);
    setText('stat-bot-users', stats.bot_users_count);
    setText('stat-total-scans', stats.total_scans);

    const threatsTotal = (stats.verdict_distribution.PHISHING || 0) + (stats.verdict_distribution.SCAM || 0);
    setText('stat-threat-ratio', `${threatsTotal} ta xavfli / scam aniqlangan`);
    setText('nav-threats-badge', threatsTotal);

    // 2. Verdict Distribution Progress Bars & Counts
    const dist = stats.verdict_distribution;
    const totalV = (dist.PHISHING + dist.SCAM + dist.SUSPICIOUS + dist.BENIGN) || 1;

    setText('count-phishing', dist.PHISHING);
    setBarWidth('bar-phishing', (dist.PHISHING / totalV) * 100);

    setText('count-scam', dist.SCAM);
    setBarWidth('bar-scam', (dist.SCAM / totalV) * 100);

    setText('count-suspicious', dist.SUSPICIOUS);
    setBarWidth('bar-suspicious', (dist.SUSPICIOUS / totalV) * 100);

    setText('count-benign', dist.BENIGN);
    setBarWidth('bar-benign', (dist.BENIGN / totalV) * 100);

    // 3. Notifications Summary
    setText('notif-sent-count', stats.notifications.SENT || 0);
    setText('notif-throttled-count', stats.notifications.THROTTLED || 0);
    setText('monitored-chats-count', stats.monitored_chats_count || 0);

    // 4. Daemons Health
    updateDaemonStatus('daemon-telethon-status', health.telethon_monitor?.status);
    updateDaemonStatus('daemon-celery-status', health.celery?.status);
    updateDaemonStatus('daemon-bot-status', health.telegram_bot?.status);
    updateDaemonStatus('daemon-db-status', health.postgres?.status);
    updateDaemonStatus('daemon-redis-status', health.redis?.status);

  } catch (err) {
    if (!isSilent) {
      console.error('Failed to fetch dashboard stats:', err);
      showToast('Statistika yuklanishida xatolik yuz berdi', 'error');
    }
  }
}

/**
 * Fetch Recent 5 Scans for Overview Tab Mini-Table
 */
async function fetchRecentOverviewScans() {
  const tbody = document.getElementById('overview-recent-scans-tbody');
  if (!tbody) return;

  try {
    const res = await fetch('/api/v1/admin/scans?page=1&page_size=5');
    const data = await res.json();
    if (!data.success || !data.items || data.items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty-cell">Hozircha tekshirilgan saytlar mavjud emas</td></tr>';
      return;
    }

    tbody.innerHTML = data.items.map(item => `
      <tr class="table-row-clickable" onclick="openForensicDrawer('${item.id}')">
        <td>
          <div class="domain-cell">
            <span class="domain-main">${escapeHtml(item.domain)}</span>
            <span class="url-sub">${escapeHtml(truncateString(item.canonical_url, 45))}</span>
          </div>
        </td>
        <td>
          <div class="risk-pill ${getRiskScoreClass(item.risk_score)}">
            <span class="rp-score">${item.risk_score}</span>
            <span class="rp-max">/100</span>
          </div>
        </td>
        <td>${getVerdictBadgeHtml(item.verdict)}</td>
        <td>
          <span class="brand-tag">${item.impersonated_brand ? escapeHtml(item.impersonated_brand) : '<span class="text-dim">Yo\'q</span>'}</span>
        </td>
        <td>
          <span class="engine-badge">${escapeHtml(item.evaluated_by || 'RiskEngine')}</span>
        </td>
        <td class="text-muted text-sm">${formatDate(item.created_at)}</td>
        <td style="text-align: right;">
          <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); openForensicDrawer('${item.id}')">
            Batafsil →
          </button>
        </td>
      </tr>
    `).join('');

  } catch (err) {
    console.error('Failed to fetch recent scans:', err);
    tbody.innerHTML = '<tr><td colspan="7" class="empty-cell text-crimson">Ma\'lumotlarni yuklab bo\'lmadi</td></tr>';
  }
}

/**
 * Fetch Scanned Sites with Pagination, Filter & Search
 */
async function fetchScans() {
  const tbody = document.getElementById('full-scans-tbody');
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">Saytlar ro\'yxati yuklanmoqda...</td></tr>';

  let url = `/api/v1/admin/scans?page=${currentScanPage}&page_size=${scanPageSize}`;
  if (currentScanVerdict) {
    url += `&verdict=${encodeURIComponent(currentScanVerdict)}`;
  }
  if (currentScanSearch) {
    url += `&search=${encodeURIComponent(currentScanSearch)}`;
  }

  try {
    const res = await fetch(url);
    const data = await res.json();

    if (!data.success || !data.items || data.items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty-cell">Hech qanday sayt topilmadi</td></tr>';
      updatePaginationControls(0, 0, 1, 1);
      return;
    }

    tbody.innerHTML = data.items.map(item => `
      <tr class="table-row-clickable" onclick="openForensicDrawer('${item.id}')">
        <td>
          <div class="domain-cell">
            <span class="domain-main">${escapeHtml(item.domain)}</span>
            <span class="url-sub">${escapeHtml(truncateString(item.canonical_url, 60))}</span>
          </div>
        </td>
        <td>
          <div class="risk-pill ${getRiskScoreClass(item.risk_score)}">
            <span class="rp-score">${item.risk_score}</span>
            <span class="rp-max">/100</span>
          </div>
        </td>
        <td>${getVerdictBadgeHtml(item.verdict)}</td>
        <td>
          <span class="brand-tag">${item.impersonated_brand ? escapeHtml(item.impersonated_brand) : '<span class="text-dim">Aniqlanmadi</span>'}</span>
        </td>
        <td>
          <div class="tech-snippet">
            <span class="ssl-indicator ${item.ssl_valid ? 'text-emerald' : 'text-crimson'}">
              ${item.ssl_valid ? '🔒 SSL Bor' : '⚠️ SSL Yo\'q'}
            </span>
            <span class="http-badge">HTTP ${item.http_status || '-'}</span>
          </div>
        </td>
        <td class="text-muted text-sm">${formatDate(item.created_at)}</td>
        <td style="text-align: right;">
          <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); openForensicDrawer('${item.id}')">
            Tekshiruv →
          </button>
        </td>
      </tr>
    `).join('');

    updatePaginationControls(data.total, data.items.length, data.page, data.total_pages);

  } catch (err) {
    console.error('Failed to fetch scans:', err);
    tbody.innerHTML = '<tr><td colspan="7" class="empty-cell text-crimson">Xatolik yuz berdi</td></tr>';
  }
}

/**
 * Filter Chip Handling
 */
function setScanFilter(btn, verdict) {
  document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  currentScanVerdict = verdict;
  currentScanPage = 1;
  fetchScans();
}

/**
 * Search Debounce
 */
function debounceScanSearch() {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(() => {
    const input = document.getElementById('scan-search-input');
    currentScanSearch = input ? input.value.trim() : '';
    currentScanPage = 1;
    fetchScans();
  }, 350);
}

/**
 * Pagination Controls Update & Change
 */
function updatePaginationControls(total, pageItemsCount, page, totalPages) {
  const infoText = document.getElementById('pagination-info-text');
  const pageDisplay = document.getElementById('page-number-display');
  const prevBtn = document.getElementById('btn-prev-page');
  const nextBtn = document.getElementById('btn-next-page');

  if (infoText) {
    const start = total === 0 ? 0 : (page - 1) * scanPageSize + 1;
    const end = (page - 1) * scanPageSize + pageItemsCount;
    infoText.innerText = `Ko'rsatilmoqda: ${start}-${end} / Jami: ${total} ta`;
  }

  if (pageDisplay) {
    pageDisplay.innerText = `${page} / ${totalPages || 1}`;
  }

  if (prevBtn) prevBtn.disabled = page <= 1;
  if (nextBtn) nextBtn.disabled = page >= totalPages;
}

function changeScanPage(delta) {
  currentScanPage += delta;
  if (currentScanPage < 1) currentScanPage = 1;
  fetchScans();
}

/**
 * Open Slide-over Forensic Drawer for a URL
 */
async function openForensicDrawer(urlId) {
  currentDrawerUrlId = urlId;

  const drawer = document.getElementById('forensic-drawer');
  const overlay = document.getElementById('drawer-overlay');

  if (!drawer || !overlay) return;

  // Open drawer immediately with loading placeholders
  drawer.classList.add('active');
  overlay.classList.add('active');
  document.body.style.overflow = 'hidden';

  setText('drawer-domain-name', 'Yuklanmoqda...');
  setText('drawer-risk-score-number', '- / 100');
  setBarWidth('drawer-risk-meter-fill', 0);
  setText('drawer-impersonated-brand-tag', 'Nishon: Tekshirilmoqda...');
  setText('drawer-evaluator-tag', 'Dvigatel: ...');

  const reasonsList = document.getElementById('drawer-reasons-list');
  if (reasonsList) {
    reasonsList.innerHTML = '<div class="loading-cell">Forensic tahlil xulosasi yuklanmoqda...</div>';
  }

  try {
    const res = await fetch(`/api/v1/admin/scans/${urlId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data.success || !data.scan) throw new Error('Data format error');

    const scan = data.scan;
    currentDrawerUrl = scan.canonical_url;
    const assessment = scan.assessment || {};
    const intel = scan.intelligence || {};

    // 1. Header & Domain
    setText('drawer-domain-name', scan.domain);
    const badgeEl = document.getElementById('drawer-verdict-badge');
    if (badgeEl) {
      badgeEl.className = 'dh-badge ' + getVerdictBadgeClass(assessment.verdict);
      badgeEl.innerText = getVerdictLabelUz(assessment.verdict);
    }

    // 2. Risk Score & Meter
    const score = assessment.risk_score || 0;
    setText('drawer-risk-score-number', `${score} / 100`);
    const meterFill = document.getElementById('drawer-risk-meter-fill');
    if (meterFill) {
      meterFill.style.width = `${score}%`;
      meterFill.style.backgroundColor = getScoreColor(score);
    }

    // 3. Meta Tags
    setText(
      'drawer-impersonated-brand-tag',
      `Nishon Brend: ${assessment.impersonated_brand || 'Aniqlanmadi'}`
    );
    setText(
      'drawer-evaluator-tag',
      `Tahlilchi: ${assessment.evaluated_by || 'Gemini 3.5 Flash'}`
    );

    // 4. Forensic Reasons (Nega bunday xulosa berildi?)
    if (reasonsList) {
      const reasons = assessment.reasons || [];
      if (reasons.length === 0) {
        reasonsList.innerHTML = '<div class="reason-empty">Hech qanday maxsus xavfli parametrlar aniqlanmadi (Sayt toza yoki tekshiruv davomida xato yo\'q).</div>';
      } else {
        reasonsList.innerHTML = reasons.map(r => `
          <div class="reason-item ${getReasonItemClass(assessment.verdict)}">
            <div class="reason-icon">${getReasonIconSvg(assessment.verdict)}</div>
            <div class="reason-text">${escapeHtml(r)}</div>
          </div>
        `).join('');
      }
    }

    // 5. Technical Evidence Grid
    setText(
      'drawer-tech-domain-age',
      intel.domain_age_days != null ? `${intel.domain_age_days} kun oldin` : 'Noma\'lum'
    );
    setText(
      'drawer-tech-ssl',
      intel.ssl_valid ? `Yaroqli (${escapeHtml(intel.ssl_issuer || 'TLS')})` : 'Mavjud emas / Xavfli'
    );
    setText(
      'drawer-tech-http-status',
      intel.http_status ? `${intel.http_status}` : 'Bog\'lanib bo\'lmadi'
    );
    setText(
      'drawer-tech-latency',
      intel.response_time_ms ? `${intel.response_time_ms} ms` : '-'
    );
    setText(
      'drawer-tech-login-form',
      intel.has_password_input ? '🔴 Parol kiritish formasi mavjud!' : (intel.has_login_form ? '🟡 Login formasi bor' : 'Yo\'q')
    );
    setText(
      'drawer-tech-redirects',
      intel.redirect_chain && intel.redirect_chain.length > 1
        ? `${intel.redirect_chain.length - 1} ta qayta yo'naltirish`
        : 'To\'g\'ridan-to\'g\'ri'
    );

    // 6. DNS Records
    const dnsBox = document.getElementById('drawer-dns-records');
    if (dnsBox) {
      if (intel.dns_records && Object.keys(intel.dns_records).length > 0) {
        dnsBox.innerText = JSON.stringify(intel.dns_records, null, 2);
      } else {
        dnsBox.innerText = 'DNS yozuvlari keshda mavjud emas';
      }
    }

    // 7. Page Text Excerpt
    const textExcerptBox = document.getElementById('drawer-text-excerpt');
    if (textExcerptBox) {
      textExcerptBox.innerText = intel.text_excerpt || 'Sayt matnidan parcha topilmadi yoki HTML bo\'sh.';
    }

  } catch (err) {
    console.error('Failed to load scan forensic detail:', err);
    showToast('Tafsilotlarni yuklashda xatolik yuz berdi', 'error');
  }
}

/**
 * Close Slide-over Forensic Drawer
 */
function closeForensicDrawer() {
  const drawer = document.getElementById('forensic-drawer');
  const overlay = document.getElementById('drawer-overlay');
  if (drawer) drawer.classList.remove('active');
  if (overlay) overlay.classList.remove('active');
  document.body.style.overflow = '';
  currentDrawerUrlId = null;
  currentDrawerUrl = null;
}

/**
 * Trigger Rescan from Drawer
 */
async function triggerDrawerRescan() {
  if (!currentDrawerUrl) {
    showToast('Havola manzili topilmadi', 'error');
    return;
  }

  const btn = document.getElementById('btn-drawer-rescan');
  if (btn) btn.classList.add('loading');

  try {
    const res = await fetch('/api/v1/admin/rescan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: currentDrawerUrl }),
    });

    const data = await res.json();
    if (!data.success) throw new Error('Rescan error');

    showToast('Havola yangidan to\'liq tekshirildi!', 'success');
    await openForensicDrawer(data.url_id);
    fetchDashboardStats(true);
    fetchScans();

  } catch (err) {
    console.error('Failed to trigger rescan:', err);
    showToast('Qayta skanerlashda xatolik yuz berdi', 'error');
  } finally {
    if (btn) btn.classList.remove('loading');
  }
}

/**
 * Fetch Telegram Accounts
 */
async function fetchAccounts() {
  const tbody = document.getElementById('accounts-tbody');
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">Hisoblar yuklanmoqda...</td></tr>';

  try {
    const res = await fetch('/api/v1/admin/accounts');
    const data = await res.json();

    if (!data.success || !data.items || data.items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty-cell">Hozircha ulangan Telegram hisoblar yo\'q</td></tr>';
      setText('accounts-count-badge', 'Jami: 0 hisob');
      return;
    }

    setText('accounts-count-badge', `Jami: ${data.total} hisob`);

    tbody.innerHTML = data.items.map(acc => `
      <tr>
        <td>
          <div class="user-id-cell">
            <span class="uid-tag">TG-${escapeHtml(String(acc.telegram_user_id))}</span>
          </div>
        </td>
        <td>
          <code class="code-sm">${escapeHtml(acc.phone_number_hash || '-')}</code>
        </td>
        <td>${getAccountStatusBadge(acc.status)}</td>
        <td>
          <span class="auth-tag">${escapeHtml(acc.auth_state || 'AUTHORIZED')}</span>
        </td>
        <td>
          <span class="chats-counter">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            ${acc.chats_count || 0} ta guruh/kanal
          </span>
        </td>
        <td class="text-muted text-sm">${formatDate(acc.last_connected_at)}</td>
        <td class="text-muted text-sm">${formatDate(acc.created_at)}</td>
      </tr>
    `).join('');

  } catch (err) {
    console.error('Failed to fetch accounts:', err);
    tbody.innerHTML = '<tr><td colspan="7" class="empty-cell text-crimson">Hisoblarni yuklab bo\'lmadi</td></tr>';
  }
}

/**
 * Fetch Notifications Logs
 */
async function fetchNotifications() {
  const tbody = document.getElementById('notifications-tbody');
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="6" class="loading-cell">Ogohlantirishlar jurnali yuklanmoqda...</td></tr>';

  try {
    const res = await fetch('/api/v1/admin/notifications?limit=50');
    const data = await res.json();

    if (!data.success || !data.items || data.items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-cell">Hozircha yuborilgan ogohlantirishlar mavjud emas</td></tr>';
      setText('notifications-count-badge', 'Jami: 0 ta');
      return;
    }

    setText('notifications-count-badge', `Oxirgi ${data.total} ta`);

    tbody.innerHTML = data.items.map(n => `
      <tr>
        <td>
          <span class="chat-id-tag">TG: ${escapeHtml(String(n.telegram_chat_id))}</span>
        </td>
        <td>
          <div class="domain-cell">
            <span class="domain-main">${escapeHtml(n.domain)}</span>
            <span class="url-sub">${escapeHtml(truncateString(n.url, 45))}</span>
          </div>
        </td>
        <td>
          <span class="badge ${n.alert_type === 'PHISHING_ALERT' ? 'badge-danger' : 'badge-warning'}">
            ${escapeHtml(n.alert_type)}
          </span>
        </td>
        <td>
          <span class="badge ${n.delivery_status === 'SENT' ? 'badge-success' : 'badge-secondary'}">
            ${n.delivery_status === 'SENT' ? '✓ YETKAZILDI' : escapeHtml(n.delivery_status)}
          </span>
        </td>
        <td class="text-center">${n.attempts}</td>
        <td class="text-muted text-sm">${formatDate(n.sent_at || n.created_at)}</td>
      </tr>
    `).join('');

  } catch (err) {
    console.error('Failed to fetch notifications:', err);
    tbody.innerHTML = '<tr><td colspan="6" class="empty-cell text-crimson">Jurnalni yuklab bo\'lmadi</td></tr>';
  }
}

/**
 * Execute Sandbox Live Scan
 */
async function executeSandboxScan() {
  const input = document.getElementById('sandbox-url-input');
  const btn = document.getElementById('btn-run-sandbox');
  const resultBox = document.getElementById('sandbox-result-box');

  if (!input || !input.value.trim()) {
    showToast('Iltimos, havolani kiriting', 'error');
    if (input) input.focus();
    return;
  }

  const url = input.value.trim();
  if (btn) btn.classList.add('loading');

  try {
    const res = await fetch('/api/v1/admin/rescan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url }),
    });

    const data = await res.json();
    if (!data.success) throw new Error(data.detail || 'Xatolik');

    resultBox.style.display = 'block';
    resultBox.innerHTML = `
      <div class="sandbox-result-card border-${getVerdictBorderClass(data.verdict)}">
        <div class="src-header">
          <div>
            <div class="src-verdict">${getVerdictBadgeHtml(data.verdict)}</div>
            <h3 class="src-domain">${escapeHtml(data.domain)}</h3>
            <p class="src-url">${escapeHtml(data.canonical_url)}</p>
          </div>
          <div class="src-score-box">
            <div class="src-score ${getRiskScoreClass(data.risk_score)}">${data.risk_score}<span>/100</span></div>
            <div class="src-score-label">Xavf Bali</div>
          </div>
        </div>

        <div class="src-brand">
          <strong>Nishon Brend:</strong> ${data.impersonated_brand ? escapeHtml(data.impersonated_brand) : 'Yo\'q / Aniqlanmadi'}
        </div>

        <div class="src-reasons">
          <strong>Ekspertiza Dalillari:</strong>
          <ul>
            ${(data.reasons || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}
          </ul>
        </div>

        <div class="src-footer">
          <button class="btn btn-primary" onclick="openForensicDrawer('${data.url_id}')">
            Yon Paneldan To'liq Texnik Razvedkani Ochish →
          </button>
        </div>
      </div>
    `;

    showToast('Tahlil yakunlandi!', 'success');
    fetchDashboardStats(true);

  } catch (err) {
    console.error('Sandbox scan error:', err);
    showToast('Havolani tekshirib bo\'lmadi: ' + err.message, 'error');
  } finally {
    if (btn) btn.classList.remove('loading');
  }
}

/**
 * Quick Test Modal
 */
function openTestModal() {
  const modal = document.getElementById('quick-test-modal');
  if (modal) modal.style.display = 'flex';
  const input = document.getElementById('modal-url-input');
  if (input) {
    input.value = '';
    setTimeout(() => input.focus(), 100);
  }
}

function closeTestModal() {
  const modal = document.getElementById('quick-test-modal');
  if (modal) modal.style.display = 'none';
}

function submitModalScan() {
  const input = document.getElementById('modal-url-input');
  if (!input || !input.value.trim()) return;

  const url = input.value.trim();
  closeTestModal();

  switchTab('sandbox');
  const sbInput = document.getElementById('sandbox-url-input');
  if (sbInput) {
    sbInput.value = url;
    executeSandboxScan();
  }
}

/**
 * Toast Notifications
 */
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `cyber-toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-dot dot-${type}"></span>
    <span class="toast-msg">${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('fading');
    setTimeout(() => toast.remove(), 400);
  }, 3500);
}

/**
 * Helpers & UI Formatters
 */
function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.innerText = text;
}

function setBarWidth(id, pct) {
  const el = document.getElementById(id);
  if (el) el.style.width = `${Math.min(100, Math.max(0, pct))}%`;
}

function updateDaemonStatus(id, status) {
  const el = document.getElementById(id);
  if (!el) return;

  if (status === 'HEALTHY' || status === 'CONNECTED') {
    el.className = 'daemon-badge badge-success';
    el.innerText = 'FAOL ISHLAYAPTI';
  } else {
    el.className = 'daemon-badge badge-danger';
    el.innerText = 'NOFAOL / XATO';
  }
}

function getVerdictBadgeHtml(verdict) {
  const v = (verdict || '').toUpperCase();
  switch (v) {
    case 'PHISHING':
      return '<span class="badge badge-phishing">🔴 FISHING</span>';
    case 'SCAM':
      return '<span class="badge badge-scam">🟠 FIRIBGARLIK & QIMOR</span>';
    case 'SUSPICIOUS':
      return '<span class="badge badge-suspicious">🟡 SHUBHALI</span>';
    case 'BENIGN':
      return '<span class="badge badge-benign">🟢 XAVFSIZ / TOZA</span>';
    default:
      return `<span class="badge badge-secondary">${escapeHtml(v || 'NOMA\'LUM')}</span>`;
  }
}

function getVerdictBadgeClass(verdict) {
  const v = (verdict || '').toUpperCase();
  switch (v) {
    case 'PHISHING': return 'badge-phishing';
    case 'SCAM': return 'badge-scam';
    case 'SUSPICIOUS': return 'badge-suspicious';
    case 'BENIGN': return 'badge-benign';
    default: return 'badge-secondary';
  }
}

function getVerdictBorderClass(verdict) {
  const v = (verdict || '').toUpperCase();
  switch (v) {
    case 'PHISHING': return 'phishing';
    case 'SCAM': return 'scam';
    case 'SUSPICIOUS': return 'suspicious';
    case 'BENIGN': return 'benign';
    default: return 'secondary';
  }
}

function getVerdictLabelUz(verdict) {
  const v = (verdict || '').toUpperCase();
  switch (v) {
    case 'PHISHING': return '🔴 O\'TA XAVFLI FISHING';
    case 'SCAM': return '🟠 FIRIBGARLIK / KAZINO (SCAM)';
    case 'SUSPICIOUS': return '🟡 SHUBHALI HAVOLA';
    case 'BENIGN': return '🟢 TOZA VA XAVFSIZ SAYT';
    default: return 'NOMA\'LUM';
  }
}

function getRiskScoreClass(score) {
  if (score >= 70) return 'risk-high';
  if (score >= 35) return 'risk-med';
  return 'risk-low';
}

function getScoreColor(score) {
  if (score >= 70) return '#ef4444';
  if (score >= 35) return '#eab308';
  return '#10b981';
}

function getReasonItemClass(verdict) {
  const v = (verdict || '').toUpperCase();
  if (v === 'PHISHING' || v === 'SCAM') return 'reason-danger';
  if (v === 'SUSPICIOUS') return 'reason-warning';
  return 'reason-success';
}

function getReasonIconSvg(verdict) {
  const v = (verdict || '').toUpperCase();
  if (v === 'PHISHING' || v === 'SCAM') {
    return `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2">
        <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
    `;
  }
  if (v === 'SUSPICIOUS') {
    return `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#eab308" stroke-width="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
    `;
  }
  return `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
      <polyline points="22 4 12 14.01 9 11.01"/>
    </svg>
  `;
}

function getAccountStatusBadge(status) {
  const s = (status || '').toUpperCase();
  if (s === 'CONNECTED') {
    return '<span class="badge badge-success"><span class="status-dot-sm pulse-emerald"></span> FAOL ULANGAN</span>';
  }
  if (s === 'DISCONNECTED' || s === 'REVOKED') {
    return '<span class="badge badge-danger">UZILGAN / BEKOR</span>';
  }
  return `<span class="badge badge-secondary">${escapeHtml(s)}</span>`;
}

function truncateString(str, maxLen) {
  if (!str) return '';
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen) + '...';
}

function formatDate(isoStr) {
  if (!isoStr) return '-';
  try {
    const d = new Date(isoStr);
    return d.toLocaleString('uz-UZ', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoStr;
  }
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
