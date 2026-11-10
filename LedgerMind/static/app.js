/**
 * LedgerMind — Client Application Logic
 * Integrates with FastAPI backend:
 *   - GET  /api/dashboard
 *   - GET  /api/issues
 *   - GET  /api/vendors
 *   - GET  /api/actions
 *   - GET  /api/integrations
 *   - POST /api/run-agent
 *   - POST /api/actions/{id}/sent
 *   - POST /api/upload/{kind}
 *   - POST /api/gst/calculate
 */

let currentIssues = [];
let allVendors = [];
let allActions = [];
let latestTrend = [];

const fmt = n => '₹' + Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });
const fmtDecimal = n => '₹' + Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function toast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3400);
}

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[c]));
}

async function get(url) {
  const r = await fetch(url);
  if (!r.ok) {
    const errText = await r.text();
    throw new Error(errText || 'Network request failed');
  }
  return r.json();
}

/* ==========================================================================
   Navigation & Tab Management (shadcn/ui Sidebar & Smooth Transitions)
   ========================================================================== */
function showTab(tab) {
  // Hide all tab views
  document.querySelectorAll('.tab-view').forEach(el => {
    el.classList.add('hidden');
    el.classList.remove('view-active-enter');
  });

  // Show target tab
  const target = document.getElementById(tab);
  if (target) {
    target.classList.remove('hidden');
    // Double rAF ensures the browser has painted the hidden→visible change
    // before adding the entrance class so the animation actually fires
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        target.classList.add('view-active-enter');
      });
    });
  }

  // Update sidebar active buttons
  document.querySelectorAll('.nav-button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });

  // Dynamic page titles — fade the old title out, swap, fade in
  const meta = {
    overview:     ['Overview',       'FINANCE WORKSPACE / GST INTELLIGENCE'],
    exceptions:   ['Reconciliation', 'FINANCE WORKSPACE / GSTR-2B AUDIT'],
    gstcalc:      ['GST Calculator', 'FINANCE WORKSPACE / TAX ENGINE'],
    vendors:      ['Vendor Memory',  'INTELLIGENCE / HINDSIGHT PROFILES'],
    actions:      ['Action Drafts',  'INTELLIGENCE / GROQ AI FOLLOW-UPS'],
    integrations: ['Integrations',   'SYSTEM / LIVE CONNECTIONS']
  };

  const titleEl = document.getElementById('pageTitle');
  const breadcrumbEl = document.getElementById('headerBreadcrumb');
  if (meta[tab]) {
    if (titleEl) {
      titleEl.style.opacity = '0.3';
      titleEl.style.transform = 'translateY(-3px)';
      setTimeout(() => {
        titleEl.textContent = meta[tab][0];
        titleEl.style.transition = 'opacity 0.22s ease, transform 0.22s cubic-bezier(0.16, 1, 0.3, 1)';
        titleEl.style.opacity = '1';
        titleEl.style.transform = 'translateY(0)';
      }, 85);
    }
    if (breadcrumbEl) breadcrumbEl.textContent = meta[tab][1];
  }

  // Load section-specific data
  if (tab === 'overview' && latestTrend.length) {
    renderPulseChart(latestTrend);
  }
  if (tab === 'exceptions') loadIssues();
  if (tab === 'vendors') loadVendors();
  if (tab === 'actions') loadActions();
  if (tab === 'integrations') loadIntegrations();
  if (tab === 'gstcalc') calculateGstLive();

  // Close mobile sidebar if open
  const sidebar = document.getElementById('sidebar');
  if (sidebar && sidebar.classList.contains('mobile-open')) {
    sidebar.classList.remove('mobile-open');
  }
}

// Bind nav buttons
document.querySelectorAll('.nav-button').forEach(btn => {
  btn.addEventListener('click', () => {
    if (btn.dataset.tab) {
      showTab(btn.dataset.tab);
    }
  });
});

function toggleSidebarCollapse() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;
  if (window.innerWidth <= 900) {
    sidebar.classList.toggle('mobile-open');
  } else {
    sidebar.classList.toggle('collapsed');
  }
}

/* ==========================================================================
   KPI Count-Up Animation (Cinematic fintech number reveal)
   ========================================================================== */
function animateCountUp(el, targetVal, isCurrency) {
  if (!el) return;

  const duration = 900;
  const startTime = performance.now();

  function tick(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(targetVal * eased);
    el.textContent = isCurrency ? fmt(current) : current.toLocaleString('en-IN');
    if (progress < 1) requestAnimationFrame(tick);
  }

  requestAnimationFrame(tick);
}

/* ==========================================================================
   Executive Dashboard (Finovex) & Trend Curves (Pulse)
   ========================================================================== */
async function refresh() {
  try {
    const d = await get('/api/dashboard');

    // KPI Cards — animated count-up on first load
    const elInvoices = document.getElementById('mInvoices');
    const elVendors = document.getElementById('mVendors');
    const elRisk = document.getElementById('mRisk');
    const elIssues = document.getElementById('mIssues');
    const elHigh = document.getElementById('mHigh');
    const elNavCount = document.getElementById('navCount');
    const elMatchedPill = document.getElementById('mMatchedPill');

    animateCountUp(elInvoices, d.total_invoices, false);
    animateCountUp(elVendors, d.vendors, false);
    animateCountUp(elRisk, d.risk, true);
    animateCountUp(elIssues, d.issues, false);
    if (elHigh) elHigh.textContent = `${d.high_priority} High Priority`;
    if (elNavCount) elNavCount.textContent = d.issues;
    if (elMatchedPill) elMatchedPill.textContent = `${d.matched} Matched Invoices`;

    latestTrend = d.trend || [];

    // Render Pulse Spline Area Chart with line drawing animation
    renderPulseChart(latestTrend);

    // Render Live Activity
    renderActivityStream(d);

    // Render Priority Exceptions on Overview
    const issues = await get('/api/issues');
    currentIssues = issues;
    const topIssuesEl = document.getElementById('topIssues');
    if (topIssuesEl) {
      topIssuesEl.innerHTML = issueTable(issues.slice(0, 6));
    }

    // Populate filing period selectors
    await fillMonths(latestTrend);

  } catch (err) {
    console.error('Refresh error:', err);
    toast('Could not refresh dashboard: ' + err.message);
  }
}

/* ==========================================================================
   Pulse High-Contrast Curve Renderer (Line Drawing & Gradual Area Fill)
   Uses double-rAF to guarantee Chromium applies the reset before animating.
   ========================================================================== */
function renderPulseChart(trend) {
  if (!trend || !trend.length) return;

  const totalExposure = trend.reduce((sum, item) => sum + (item.risk || 0), 0);
  const heroRiskEl = document.getElementById('chartTotalRisk');
  if (heroRiskEl) {
    heroRiskEl.innerHTML = `${fmt(totalExposure)} <small>Total 6-Month Exposure</small>`;
  }

  const svg = document.getElementById('pulseSvg');
  const curvePath = document.getElementById('pulseCurvePath');
  const areaPath = document.getElementById('pulseAreaPath');
  const pointsGroup = document.getElementById('pulsePointsGroup');
  const xLabels = document.getElementById('chartXLabels');
  const tooltip = document.getElementById('chartTooltip');

  if (!svg || !curvePath || !areaPath || !pointsGroup) return;

  const width = 600;
  const height = 150;
  const paddingX = 40;
  const paddingTop = 20;
  const paddingBottom = 25;

  const maxVal = Math.max(1, ...trend.map(t => t.risk));
  const usableW = width - paddingX * 2;
  const usableH = height - paddingTop - paddingBottom;

  // Compute coordinate points
  const points = trend.map((item, idx) => {
    const x = paddingX + (idx / (trend.length - 1)) * usableW;
    const y = height - paddingBottom - (item.risk / maxVal) * usableH;
    return { x, y, data: item };
  });

  // Generate cubic bezier spline path
  function getSplinePath(pts) {
    if (pts.length === 0) return '';
    if (pts.length === 1) return `M ${pts[0].x} ${pts[0].y}`;

    let path = `M ${pts[0].x} ${pts[0].y}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[i === 0 ? 0 : i - 1];
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const p3 = pts[i + 2] || p2;

      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;

      path += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
    }
    return path;
  }

  const curveD = getSplinePath(points);
  curvePath.setAttribute('d', curveD);

  // Area path closing at the bottom baseline
  const firstPt = points[0];
  const lastPt = points[points.length - 1];
  const baselineY = height - paddingBottom + 5;
  const areaD = `${curveD} L ${lastPt.x} ${baselineY} L ${firstPt.x} ${baselineY} Z`;
  areaPath.setAttribute('d', areaD);

  // Always animate — no reduced-motion guard on chart
  let pathLength = 800;
  try { pathLength = curvePath.getTotalLength(); } catch (e) {}

  // Reset state with no transition
  curvePath.style.transition = 'none';
  curvePath.style.strokeDasharray = `${pathLength}`;
  curvePath.style.strokeDashoffset = `${pathLength}`;
  areaPath.classList.remove('drawn');

  // Double rAF: let browser paint the reset before animating
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      curvePath.style.transition = 'stroke-dashoffset 1.3s cubic-bezier(0.16, 1, 0.3, 1)';
      curvePath.style.strokeDashoffset = '0';
      setTimeout(() => areaPath.classList.add('drawn'), 300);
    });
  });

  // Staggered point entrance
  pointsGroup.innerHTML = '';
  points.forEach((pt, idx) => {
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', pt.x);
    circle.setAttribute('cy', pt.y);
    circle.setAttribute('r', '4.5');
    circle.setAttribute('class', 'chart-point');
    circle.style.opacity = '0';
    circle.style.transform = 'scale(0)';
    circle.style.transformOrigin = `${pt.x}px ${pt.y}px`;
    circle.style.transition = `opacity 0.3s ease ${380 + idx * 80}ms, transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) ${380 + idx * 80}ms`;

    pointsGroup.appendChild(circle);

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        circle.style.opacity = '1';
        circle.style.transform = 'scale(1)';
      });
    });

    circle.addEventListener('mouseenter', () => {
      if (tooltip) {
        tooltip.innerHTML = `<strong>${pt.data.month}</strong><br>Credit Risk: <span style="color:var(--soft-pink);font-weight:700;">${fmt(pt.data.risk)}</span><br>${pt.data.issues} exception${pt.data.issues === 1 ? '' : 's'}`;
        const cr = svg.parentElement.getBoundingClientRect();
        const pr = circle.getBoundingClientRect();
        tooltip.style.left = `${pr.left - cr.left + pr.width / 2}px`;
        tooltip.style.top = `${pr.top - cr.top}px`;
        tooltip.classList.add('visible');
      }
    });
    circle.addEventListener('mouseleave', () => {
      if (tooltip) tooltip.classList.remove('visible');
    });
  });

  // Render X-Axis month labels
  if (xLabels) {
    xLabels.innerHTML = trend.map(t => `<span class="chart-x-label">${t.month.slice(5)}/${t.month.slice(2, 4)}</span>`).join('');
  }
}

function renderActivityStream(d) {
  const el = document.getElementById('activity');
  if (!el) return;

  const events = [
    {
      icon: '✓',
      type: 'green',
      title: 'Reconciliation Engine Operational',
      desc: `${d.total_invoices} purchase records mapped with synthetic GSTR-2B ledger.`
    },
    {
      icon: '♙',
      type: 'pink',
      title: `${d.vendors} Vendor Profiles Retained`,
      desc: 'Hindsight persistent memory bank actively tracking late filings and GSTIN typo patterns.'
    },
    {
      icon: '⚠',
      type: 'amber',
      title: `${fmt(d.risk)} Total Credit Exposure`,
      desc: `${d.issues} reconciliation exceptions requiring supplier clarification or correction.`
    }
  ];

  el.innerHTML = events.map(e => `
    <div class="activity-event">
      <div class="event-icon-box ${e.type}">${e.icon}</div>
      <div class="event-details">
        <div class="event-title">${esc(e.title)}</div>
        <div class="event-desc">${esc(e.desc)}</div>
      </div>
    </div>
  `).join('');
}

/* ==========================================================================
   Reconciliation & Exceptions Table (Finovex Aesthetic)
   ========================================================================== */
function issueTable(rows) {
  if (!rows || !rows.length) {
    return `<div style="padding: 32px; text-align: center; color: var(--charcoal-muted);">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin: 0 auto 8px; display: block; color: var(--forest-green);"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
      <strong>No reconciliation exceptions found for this period.</strong><br>
      <span style="font-size: 11px;">Upload fresh purchase registers or supplier filings to audit.</span>
    </div>`;
  }

  return `<table class="data-table">
    <thead>
      <tr>
        <th>Vendor / Invoice</th>
        <th>Period</th>
        <th>Audit Exception</th>
        <th>Priority</th>
        <th>Taxable Value</th>
        <th>Credit at Risk</th>
      </tr>
    </thead>
    <tbody>
      ${rows.map(x => {
        const pClass = (x.priority || 'medium').toLowerCase();
        return `<tr>
          <td>
            <div class="vendor-cell">
              <span class="vendor-name">${esc(x.vendor)}</span>
              <span class="vendor-sub">Inv: ${esc(x.invoice)} · GSTIN: ${esc(x.gstin)}</span>
            </div>
          </td>
          <td><span style="font-family: var(--font-mono); font-size: 11px; font-weight: 600;">${esc(x.month)}</span></td>
          <td>
            <div style="font-weight: 600; color: var(--charcoal);">${esc(x.issue)}</div>
            <div style="font-size: 10.5px; color: var(--charcoal-muted);">${esc(x.detail)}</div>
          </td>
          <td>
            <span class="badge-pill ${pClass}">
              <span style="display:inline-block;width:5px;height:5px;border-radius:50%;background:currentColor;"></span>
              ${esc(x.priority)}
            </span>
          </td>
          <td><span class="amount-cell">${fmt(x.taxable)}</span></td>
          <td><span class="amount-cell risk-highlight">${fmt(x.risk)}</span></td>
        </tr>`;
      }).join('')}
    </tbody>
  </table>`;
}

async function fillMonths(trend) {
  const selects = [document.getElementById('monthFilter'), document.getElementById('periodFilter')];
  
  selects.forEach(sel => {
    if (!sel) return;
    const currentVal = sel.value;
    sel.innerHTML = '<option value="">All Periods</option>' + 
      trend.map(t => `<option value="${t.month}">${t.month} (${fmt(t.risk)} risk)</option>`).join('');
    sel.value = currentVal;
  });
}

function onPeriodChange(val) {
  const monthFilter = document.getElementById('monthFilter');
  if (monthFilter) monthFilter.value = val;
  loadIssues();
}

async function loadIssues() {
  const monthFilter = document.getElementById('monthFilter');
  const month = monthFilter ? monthFilter.value : '';
  
  const periodFilter = document.getElementById('periodFilter');
  if (periodFilter && periodFilter.value !== month) {
    periodFilter.value = month;
  }

  try {
    currentIssues = await get('/api/issues' + (month ? '?month=' + encodeURIComponent(month) : ''));
    filterIssueTable();
  } catch (err) {
    toast('Could not load exceptions: ' + err.message);
  }
}

function filterIssueTable() {
  const searchInput = document.getElementById('issueSearchInput');
  const query = (searchInput ? searchInput.value : '').toLowerCase().trim();

  let filtered = currentIssues;
  if (query) {
    filtered = currentIssues.filter(x => 
      (x.vendor && x.vendor.toLowerCase().includes(query)) ||
      (x.invoice && x.invoice.toLowerCase().includes(query)) ||
      (x.issue && x.issue.toLowerCase().includes(query)) ||
      (x.gstin && x.gstin.toLowerCase().includes(query))
    );
  }

  const el = document.getElementById('issueTable');
  if (el) {
    el.innerHTML = issueTable(filtered);
  }
}

/* ==========================================================================
   Vendor Memory View (Hindsight Behavioral Profiles)
   ========================================================================== */
async function loadVendors() {
  try {
    allVendors = await get('/api/vendors');
    filterVendorTable();
  } catch (err) {
    toast('Could not load vendor memories: ' + err.message);
  }
}

function filterVendorTable() {
  const searchInput = document.getElementById('vendorSearchInput');
  const query = (searchInput ? searchInput.value : '').toLowerCase().trim();

  let filtered = allVendors;
  if (query) {
    filtered = allVendors.filter(v => 
      (v.vendor && v.vendor.toLowerCase().includes(query)) ||
      (v.gstin && v.gstin.toLowerCase().includes(query)) ||
      (v.notes && v.notes.toLowerCase().includes(query))
    );
  }

  const el = document.getElementById('vendorTable');
  if (!el) return;

  if (!filtered.length) {
    el.innerHTML = `<div style="padding: 32px; text-align: center; color: var(--charcoal-muted);">No vendor memories matching "${esc(query)}".</div>`;
    return;
  }

  el.innerHTML = `<table class="data-table">
    <thead>
      <tr>
        <th>Vendor / Behavioral Pattern</th>
        <th>GSTIN</th>
        <th>Late Filing Frequency</th>
        <th>GSTIN Typos</th>
        <th>Preferred Channel</th>
        <th>Last Resolution Outcome</th>
      </tr>
    </thead>
    <tbody>
      ${filtered.map(v => {
        const isLateHabit = v.late_count >= 3;
        const isTypoHabit = v.typo_count > 0;
        return `<tr>
          <td>
            <div class="vendor-cell">
              <span class="vendor-name">${esc(v.vendor)}</span>
              <span class="vendor-sub">${esc(v.notes || 'Normal filing compliance')}</span>
            </div>
          </td>
          <td><span style="font-family: var(--font-mono); font-size: 11px;">${esc(v.gstin)}</span></td>
          <td>
            <span class="badge-pill ${isLateHabit ? 'high' : 'match'}">
              ${v.late_count} / ${v.months_seen} cycles
            </span>
          </td>
          <td>
            <span class="badge-pill ${isTypoHabit ? 'medium' : 'match'}">
              ${v.typo_count} occurrence${v.typo_count === 1 ? '' : 's'}
            </span>
          </td>
          <td>
            <span style="font-weight: 600; color: var(--charcoal); font-size: 11.5px;">${esc(v.preferred_channel)}</span>
          </td>
          <td>
            <span style="font-size: 11px; color: var(--charcoal-muted);">${esc(v.last_outcome)}</span>
          </td>
        </tr>`;
      }).join('')}
    </tbody>
  </table>`;
}

/* ==========================================================================
   AI Action Drafts View (Groq LLM + Hindsight Follow-ups)
   ========================================================================== */
async function loadActions() {
  try {
    allActions = await get('/api/actions');
    const el = document.getElementById('actionList');
    const navDraftCount = document.getElementById('navDraftCount');
    
    if (navDraftCount) {
      navDraftCount.textContent = allActions.length || 'AI';
    }

    if (!el) return;

    if (!allActions.length) {
      el.innerHTML = `<div style="grid-column: 1 / -1; padding: 48px 24px; text-align: center;" class="card">
        <div class="banner-icon-box" style="margin: 0 auto 12px; background-color: var(--forest-green-subtle); color: var(--forest-green);">✦</div>
        <h4 style="font-family: var(--font-heading); font-size: 15px; font-weight: 700; margin-bottom: 6px;">No Action Drafts Generated Yet</h4>
        <p style="font-size: 12px; color: var(--charcoal-muted); max-width: 420px; margin: 0 auto 16px;">Run the autonomous reconciliation agent to formulate supplier follow-up messages using Groq and recalled vendor history.</p>
        <button class="btn btn-primary btn-sm" onclick="runAgent()">✦ Generate Drafts Now</button>
      </div>`;
      return;
    }

    el.innerHTML = allActions.map(x => `
      <article class="draft-card">
        <div class="draft-header">
          <div>
            <h4 class="draft-vendor-name">${esc(x.vendor)}</h4>
            <div class="draft-meta">${esc(x.issue)} · via ${esc(x.channel)} · ${x.created_at || 'Just now'}</div>
          </div>
          <span class="badge-pill ${x.status === 'Draft' ? 'medium' : 'match'}">
            ${esc(x.status)}
          </span>
        </div>
        <pre class="draft-body">${esc(x.draft)}</pre>
        <div class="draft-actions">
          <button class="btn btn-secondary btn-sm" onclick="copyDraft(${x.id})">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
            <span>Copy Text</span>
          </button>
          ${x.status === 'Draft' ? `
            <button class="btn btn-primary btn-sm" onclick="markSent(${x.id})">
              <span>Mark as Sent</span>
            </button>
          ` : ''}
        </div>
      </article>
    `).join('');

  } catch (err) {
    toast('Could not load action drafts: ' + err.message);
  }
}

async function runAgent() {
  const btn = document.getElementById('btnRunAgent');
  const originalText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span>✦ Running Agent…</span>';
  }

  try {
    const r = await fetch('/api/run-agent', { method: 'POST' });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'Agent execution failed');

    toast(d.message || 'Reconciliation agent completed successfully.');
    await refresh();

    const actionsTab = document.getElementById('actions');
    if (actionsTab && !actionsTab.classList.contains('hidden')) {
      loadActions();
    }
  } catch (err) {
    toast('Agent failed: ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  }
}

async function markSent(id) {
  try {
    await fetch(`/api/actions/${id}/sent`, { method: 'POST' });
    toast('Action draft marked as sent.');
    loadActions();
  } catch (err) {
    toast('Error updating draft: ' + err.message);
  }
}

async function copyDraft(id) {
  const x = allActions.find(z => z.id === id);
  if (x && x.draft) {
    try {
      await navigator.clipboard.writeText(x.draft);
      toast('Draft copied to clipboard.');
    } catch {
      toast('Clipboard permission denied.');
    }
  }
}

/* ==========================================================================
   CSV Upload Handlers (Phase 3)
   ========================================================================== */
async function uploadFile(kind, file) {
  if (!file) return;

  const fd = new FormData();
  fd.append('file', file);

  try {
    toast(`Uploading ${kind} CSV…`);
    const r = await fetch('/api/upload/' + kind, {
      method: 'POST',
      body: fd
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'Upload failed');

    toast(`Success: ${d.inserted} ${kind} rows imported.`);
    await refresh();
    loadIssues();
  } catch (err) {
    toast('Upload error: ' + err.message);
  }
}

// Drag & Drop event bindings
['dropzonePurchase', 'dropzoneGstr2b'].forEach(id => {
  const dz = document.getElementById(id);
  if (!dz) return;

  ['dragenter', 'dragover'].forEach(name => {
    dz.addEventListener(name, e => {
      e.preventDefault();
      dz.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(name => {
    dz.addEventListener(name, e => {
      e.preventDefault();
      dz.classList.remove('dragover');
    });
  });

  dz.addEventListener('drop', e => {
    const files = e.dataTransfer.files;
    if (files.length) {
      const kind = id === 'dropzonePurchase' ? 'purchase' : 'gstr2b';
      uploadFile(kind, files[0]);
    }
  });
});

/* ==========================================================================
   Interactive GST Calculator Module (Phase 3)
   Connected to POST /api/gst/calculate
   ========================================================================== */
function autoDetectState() {
  const gstinInput = document.getElementById('calcSupplierGstin');
  const posSelect = document.getElementById('calcPlaceOfSupply');
  if (!gstinInput || !posSelect) return;

  const val = gstinInput.value.trim().toUpperCase();
  if (val.length >= 2) {
    const code = val.slice(0, 2);
    // If option exists in place of supply, sync it
    const opt = Array.from(posSelect.options).find(o => o.value === code);
    if (opt) {
      posSelect.value = code;
    }
  }
  calculateGstLive();
}

function addCalcItemRow() {
  const tbody = document.getElementById('calcItemsBody');
  if (!tbody) return;

  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><input type="text" class="c-name" value="Consulting Services" oninput="calculateGstLive()"></td>
    <td><input type="number" class="c-qty" value="1" min="1" oninput="calculateGstLive()"></td>
    <td><input type="number" class="c-price" value="10000" min="0" oninput="calculateGstLive()"></td>
    <td><input type="number" class="c-disc" value="0" min="0" oninput="calculateGstLive()"></td>
    <td>
      <select class="c-rate" onchange="calculateGstLive()">
        <option value="0">0%</option>
        <option value="5">5%</option>
        <option value="12">12%</option>
        <option value="18" selected>18%</option>
        <option value="28">28%</option>
      </select>
    </td>
    <td><button class="btn btn-ghost btn-sm" onclick="removeCalcRow(this)" title="Remove item" style="color: var(--risk-high); padding: 4px;">✕</button></td>
  `;
  tbody.appendChild(tr);
  calculateGstLive();
}

function removeCalcRow(btn) {
  const tr = btn.closest('tr');
  const tbody = document.getElementById('calcItemsBody');
  if (tbody && tbody.children.length > 1) {
    tr.remove();
    calculateGstLive();
  } else {
    toast('At least one item line is required.');
  }
}

function resetCalcForm() {
  const gstin = document.getElementById('calcSupplierGstin');
  const inv = document.getElementById('calcInvoiceNumber');
  const pos = document.getElementById('calcPlaceOfSupply');
  if (gstin) gstin.value = '29ABCDE1234F1Z5';
  if (inv) inv.value = 'INV-2026-001';
  if (pos) pos.value = '29';
  calculateGstLive();
}

async function calculateGstLive() {
  const gstin = (document.getElementById('calcSupplierGstin')?.value || '29ABCDE1234F1Z5').trim().toUpperCase();
  const pos = document.getElementById('calcPlaceOfSupply')?.value || '29';
  const inv = document.getElementById('calcInvoiceNumber')?.value || 'INV-001';

  const rows = document.querySelectorAll('#calcItemsBody tr');
  const items = [];

  rows.forEach((r, idx) => {
    const name = r.querySelector('.c-name')?.value || `Item ${idx + 1}`;
    const qty = parseFloat(r.querySelector('.c-qty')?.value) || 1;
    const price = parseFloat(r.querySelector('.c-price')?.value) || 0;
    const disc = parseFloat(r.querySelector('.c-disc')?.value) || 0;
    const rate = parseFloat(r.querySelector('.c-rate')?.value) || 18;

    items.push({
      item_name: name,
      quantity: qty,
      unit_price: price,
      discount: disc,
      gst_rate: rate
    });
  });

  const payload = {
    supplier_gstin: gstin.length === 15 ? gstin : '29ABCDE1234F1Z5',
    place_of_supply: pos,
    invoice_number: inv,
    items: items
  };

  try {
    const r = await fetch('/api/gst/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const res = await r.json();

    if (!r.ok) {
      console.warn('GST calc error:', res.detail);
      return;
    }

    const data = res.data;
    
    // Update summary outputs
    const elTaxable = document.getElementById('resTaxable');
    const elCgst = document.getElementById('resCgst');
    const elSgst = document.getElementById('resSgst');
    const elIgst = document.getElementById('resIgst');
    const elTotalTax = document.getElementById('resTotalTax');
    const elGrandTotal = document.getElementById('resGrandTotal');
    const badge = document.getElementById('calcSupplyBadge');

    const rowCgst = document.getElementById('rowCgst');
    const rowSgst = document.getElementById('rowSgst');
    const rowIgst = document.getElementById('rowIgst');

    if (elTaxable) elTaxable.textContent = fmtDecimal(data.total_taxable_value);
    if (elCgst) elCgst.textContent = fmtDecimal(data.total_cgst);
    if (elSgst) elSgst.textContent = fmtDecimal(data.total_sgst);
    if (elIgst) elIgst.textContent = fmtDecimal(data.total_igst);
    if (elTotalTax) elTotalTax.textContent = fmtDecimal(data.total_tax);
    if (elGrandTotal) elGrandTotal.textContent = fmtDecimal(data.grand_total);

    if (data.is_intra_state) {
      if (badge) {
        badge.textContent = 'INTRA-STATE (CGST + SGST)';
        badge.className = 'kpi-badge success';
      }
      if (rowCgst) rowCgst.style.display = 'flex';
      if (rowSgst) rowSgst.style.display = 'flex';
      if (rowIgst) rowIgst.style.display = 'none';
    } else {
      if (badge) {
        badge.textContent = 'INTER-STATE (IGST)';
        badge.className = 'kpi-badge pink';
      }
      if (rowCgst) rowCgst.style.display = 'none';
      if (rowSgst) rowSgst.style.display = 'none';
      if (rowIgst) rowIgst.style.display = 'flex';
    }

  } catch (err) {
    console.warn('Calculator error:', err);
  }
}

/* ==========================================================================
   Integrations Status
   ========================================================================== */
async function loadIntegrations() {
  try {
    const d = await get('/api/integrations');
    const el = document.getElementById('integrationStatus');
    if (!el) return;

    const items = [
      {
        name: 'Hindsight Persistent Memory',
        status: d.hindsight.connected ? 'Connected · Active Bank' : (d.hindsight.configured ? 'Configured · Connection Error' : 'Local Fallback · API Key Not Configured'),
        ok: d.hindsight.connected,
        icon: '♙',
        type: d.hindsight.connected ? 'green' : 'pink'
      },
      {
        name: 'Groq LLM Acceleration',
        status: d.groq.configured ? `Configured (${d.groq.model})` : 'Deterministic Local Fallback Active',
        ok: d.groq.configured,
        icon: '✦',
        type: d.groq.configured ? 'green' : 'pink'
      },
      {
        name: 'Band AI Desktop Client',
        status: d.band_ai.status || 'Standalone Desktop App Required',
        ok: true,
        icon: '💻',
        type: 'green'
      },
      {
        name: 'OpenClaw Workflow Automator',
        status: d.openclaw.status || 'Ready for Automation',
        ok: true,
        icon: '⚙',
        type: 'green'
      }
    ];

    el.innerHTML = items.map(x => `
      <div class="integration-card">
        <div class="event-icon-box ${x.type}">${x.icon}</div>
        <div class="event-details">
          <div class="event-title">${esc(x.name)}</div>
          <div class="event-desc">${esc(x.status)}</div>
        </div>
      </div>
    `).join('');

  } catch (err) {
    const el = document.getElementById('integrationStatus');
    if (el) el.innerHTML = '<div style="color: var(--risk-high); padding: 12px;">Could not read integration status.</div>';
  }
}

// Initial bootstrap — show overview tab first to fire entrance animations,
// then load data. The chart and KPI count-ups trigger inside refresh().
showTab('overview');
refresh();
loadIntegrations();
setInterval(refresh, 30000);
