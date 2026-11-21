import * as THREE from 'three';
import { GLTFLoader } from './vendor/GLTFLoader.js';
import { RGBELoader } from './vendor/RGBELoader.js';

const $ = (selector) => document.querySelector(selector);
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const params = new URLSearchParams(location.search);
if (params.has('api')) {
  localStorage.setItem('arbscout_api', params.get('api').replace(/\/$/, ''));
}
const API_BASE = localStorage.getItem('arbscout_api') || '';

const MODE_NOTES = {
  research: 'Read-only. The agent never logs in or transacts.',
  semi: 'Plans are prepared, but every step needs your approval.',
  full: 'Unattended execution, only through permitted official APIs.',
};

const DEMO_OPPORTUNITIES = [
  {
    id: 'demo-1', item_key: 'demo:gold', buy_venue: 'example_api', buy_price: '96.40',
    sell_venue: 'example_browser', sell_price: '101.80', net_profit: '4.12',
    roi_pct: '4.27', confidence: 0.62, risk_flags: ['demo data'],
  },
  {
    id: 'demo-2', item_key: 'demo:gold', buy_venue: 'venue_b', buy_price: '97.10',
    sell_venue: 'venue_c', sell_price: '99.60', net_profit: '1.84',
    roi_pct: '1.89', confidence: 0.51, risk_flags: ['demo data'],
  },
];

const state = {
  mode: 'research',
  kill: true,
  items: [],
  opportunities: [],
  plans: new Map(),
  demo: false,
};

/* ---------------- 3D scene ---------------- */

let renderer, scene, camera, model;
let scrollProgress = 0;
const pointer = { x: 0, y: 0 };

function initScene() {
  const canvas = $('#scene');
  if (!canvas) return;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  } catch (error) {
    console.warn('WebGL unavailable:', error);
    return;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  camera.position.set(0, 0, 6.4);

  const pmrem = new THREE.PMREMGenerator(renderer);
  new RGBELoader().load(
    './assets/hdri/blocky_photo_studio_1k.hdr',
    (hdr) => {
      hdr.mapping = THREE.EquirectangularReflectionMapping;
      scene.environment = pmrem.fromEquirectangular(hdr).texture;
      hdr.dispose();
      pmrem.dispose();
    },
    undefined,
    () => pmrem.dispose()
  );

  new GLTFLoader().load(
    './assets/models/camera/Camera_01_1k.gltf',
    (gltf) => {
      const pivot = new THREE.Group();
      const asset = gltf.scene;
      const box = new THREE.Box3().setFromObject(asset);
      const size = box.getSize(new THREE.Vector3());
      const scale = 2.4 / (Math.max(size.x, size.y, size.z) || 1);
      asset.scale.setScalar(scale);
      asset.position.sub(box.getCenter(new THREE.Vector3()).multiplyScalar(scale));
      pivot.add(asset);
      model = pivot;
      scene.add(model);
    },
    undefined,
    () => {
      const geometry = new THREE.IcosahedronGeometry(1.35, 5);
      const material = new THREE.MeshPhysicalMaterial({
        color: 0x9fb4ff, metalness: 0.95, roughness: 0.18, clearcoat: 0.6,
      });
      model = new THREE.Mesh(geometry, material);
      scene.add(model);
    }
  );

  const key = new THREE.DirectionalLight(0xdce8ff, 2.4);
  key.position.set(3, 4, 5);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x7cf7d4, 1.8);
  rim.position.set(-4, -1, -4);
  scene.add(rim);
  scene.add(new THREE.AmbientLight(0xffffff, 0.35));

  window.addEventListener('resize', resize);
  window.addEventListener('pointermove', (event) => {
    pointer.x = event.clientX / window.innerWidth - 0.5;
    pointer.y = event.clientY / window.innerHeight - 0.5;
  });
  resize();
  requestAnimationFrame(loop);
}

function resize() {
  if (!renderer || !camera) return;
  const width = window.innerWidth;
  const height = window.innerHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function loop() {
  requestAnimationFrame(loop);
  if (!renderer || !scene || !camera) return;

  const hero = $('#hero');
  if (hero) {
    const rect = hero.getBoundingClientRect();
    const distance = Math.max(1, hero.offsetHeight - window.innerHeight);
    scrollProgress = Math.min(1, Math.max(0, -rect.top / distance));
  }

  if (model) {
    const wide = window.innerWidth > 900;
    model.position.x = wide ? 1.75 : 0;
    if (!reduced) {
      model.rotation.y = scrollProgress * Math.PI * 2.3 + pointer.x * 0.4;
      model.rotation.x = -0.12 + scrollProgress * 0.55 + pointer.y * 0.18;
      model.position.y = Math.sin(scrollProgress * Math.PI) * 0.32;
      camera.position.z = 6.4 - scrollProgress * 1.1;
    } else {
      model.rotation.y = 0.5;
    }
  }
  renderer.render(scene, camera);
}

function initSteps() {
  const observer = new IntersectionObserver(
    (entries) => entries.forEach((entry) => entry.target.classList.toggle('visible', entry.isIntersecting)),
    { threshold: 0.35 }
  );
  document.querySelectorAll('.step').forEach((step) => observer.observe(step));
}

/* ---------------- API ---------------- */

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json();
}

function toast(message) {
  const el = $('#toast');
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove('show'), 3200);
}

const money = (value) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(number);
};
const pct = (value) => `${Number(value).toFixed(2)}%`;
const shortTime = (iso) => {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

function setConnection(online) {
  const el = $('#connection');
  el.classList.toggle('online', online);
  el.classList.toggle('offline', !online);
  el.innerHTML = `<i></i> ${online ? (state.demo ? 'offline demo' : 'connected') : 'backend offline'}`;
}

function renderOpportunities() {
  const tbody = $('#opportunity-list');
  const list = state.opportunities;
  if (!list.length) {
    tbody.innerHTML = '<tr class="empty"><td colspan="7">No qualifying spreads yet. Add venues, then run a scan.</td></tr>';
    return;
  }
  tbody.innerHTML = list.map((opp) => {
    const saved = state.plans.get(opp.id);
    let label = 'Plan';
    let disabled = state.demo;
    if (saved?.executed) { label = 'Done'; disabled = true; }
    else if (saved?.approved) label = 'Execute';
    else if (saved?.plan) label = 'Approve';
    const tags = (opp.risk_flags || []).map((flag) => `<span class="tag">${flag}</span>`).join('');
    return `<tr>
      <td><div>${opp.item_key}</div>${tags ? `<div class="tags">${tags}</div>` : ''}</td>
      <td>${opp.buy_venue}<br><span class="muted">${money(opp.buy_price)}</span></td>
      <td>${opp.sell_venue}<br><span class="muted">${money(opp.sell_price)}</span></td>
      <td class="pos">${money(opp.net_profit)}</td>
      <td class="pos">${pct(opp.roi_pct)}</td>
      <td>${Math.round(Number(opp.confidence) * 100)}%</td>
      <td><button class="row-btn" data-opp="${opp.id}" ${disabled ? 'disabled' : ''}>${label}</button></td>
    </tr>`;
  }).join('');

  tbody.querySelectorAll('button[data-opp]').forEach((button) => {
    button.addEventListener('click', () => handleOpportunity(button.dataset.opp));
  });
}

async function handleOpportunity(id) {
  const opp = state.opportunities.find((item) => item.id === id);
  if (!opp) return;
  let saved = state.plans.get(id);

  try {
    if (!saved?.plan) {
      const plan = await api(`/opportunities/${id}/plan`, { method: 'POST' });
      saved = { plan, approved: false, executed: false };
      state.plans.set(id, saved);
      if (plan.approval_required) {
        toast('Plan created. Review and approve each step.');
      } else {
        await executePlan(id);
        return;
      }
    } else if (!saved.approved) {
      await api(`/plans/${saved.plan.id}/approve`, { method: 'POST' });
      saved.approved = true;
      toast('Approved. Ready to execute.');
    } else if (!saved.executed) {
      await executePlan(id);
      return;
    }
    renderOpportunities();
  } catch (error) {
    toast(error.message);
  }
}

async function executePlan(id) {
  const saved = state.plans.get(id);
  if (!saved) return;
  const result = await api(`/plans/${saved.plan.id}/execute`, { method: 'POST' });
  if (result.ok) {
    saved.executed = true;
    toast('Execution completed.');
  } else {
    toast(result.reason || 'Execution blocked.');
  }
  renderOpportunities();
}

function renderAudit(entries) {
  const list = $('#audit-list');
  if (!entries.length) {
    list.innerHTML = '<li><span class="detail">No recorded activity yet.</span></li>';
    return;
  }
  list.innerHTML = entries.map((entry) => `<li>
    <span><span class="event ${entry.allowed ? '' : 'denied'}">${entry.event}</span>
    <span class="detail">${entry.detail || ''}</span></span>
    <time>${shortTime(entry.timestamp)}</time>
  </li>`).join('');
}

function renderItems(items) {
  state.items = items;
  const select = $('#research-select');
  const current = select.value;
  select.innerHTML = items.length
    ? items.map((item) => `<option value="${item.key}">${item.game ? `${item.game} · ` : ''}${item.name || item.key}</option>`).join('')
    : '<option value="">No items configured</option>';
  if (current && items.some((item) => item.key === current)) select.value = current;
  if (items.length) loadValuation(select.value);
}

async function loadValuation(key) {
  const body = $('#research-body');
  if (!key) return;
  try {
    const valuation = await api(`/valuation/${encodeURIComponent(key)}`);
    const value = (v) => (v === null || v === undefined ? '—' : money(v));
    body.innerHTML = `<div class="metric-row">
      <div class="metric"><span>Fair value</span><strong>${value(valuation.fair_value)}</strong></div>
      <div class="metric"><span>Likely sell</span><strong>${value(valuation.likely_sell_price)}</strong></div>
      <div class="metric"><span>Confidence</span><strong>${Math.round(valuation.confidence * 100)}%</strong></div>
    </div>
    <p class="muted">${valuation.sample_count} quotes · volatility ${Number(valuation.volatility).toFixed(3)} · trend ${Number(valuation.trend_pct_per_day).toFixed(2)}%/day</p>
    <div class="tags">${(valuation.notes || []).map((note) => `<span class="tag">${note}</span>`).join('')}</div>`;
  } catch (error) {
    body.innerHTML = `<p class="muted">Valuation unavailable: ${error.message}</p>`;
  }
}

function applySettings(snapshot) {
  if (!snapshot) return;
  state.mode = snapshot.mode;
  state.kill = snapshot.kill_switch;
  document.querySelectorAll('#mode-buttons button').forEach((button) => {
    button.classList.toggle('active', button.dataset.mode === state.mode);
  });
  const pill = $('#mode-pill');
  pill.textContent = state.mode;
  pill.className = `pill ${state.mode}`;
  $('#mode-note').textContent = MODE_NOTES[state.mode] || '';
  const kill = $('#kill-switch');
  kill.classList.toggle('off', !state.kill);
  kill.setAttribute('aria-pressed', String(state.kill));
  $('#kill-state').textContent = state.kill ? 'Kill switch on' : 'Kill switch off';
}

async function refresh() {
  try {
    const [status, opportunities, audit, items] = await Promise.all([
      api('/status'), api('/opportunities'), api('/audit'), api('/items'),
    ]);
    state.demo = false;
    setConnection(true);
    applySettings(status.settings);
    state.opportunities = opportunities;
    renderOpportunities();
    renderAudit(audit);
    renderItems(items);
    $('#stat-quotes').textContent = money(status.last_scan?.quote_count ?? '—');
    $('#stat-opps').textContent = money(status.last_scan?.opportunity_count ?? opportunities.length);
    $('#stat-venues').textContent = `${status.venue_count}`;
    $('#stat-confidence').textContent = opportunities.length
      ? `${Math.round(Math.max(...opportunities.map((o) => o.confidence)) * 100)}%` : '—';
    $('#last-scan').textContent = status.last_scan
      ? `last scan ${shortTime(status.last_scan.scanned_at)}` : 'not scanned yet';
  } catch (error) {
    state.demo = true;
    setConnection(false);
    state.opportunities = DEMO_OPPORTUNITIES;
    renderOpportunities();
    renderAudit([]);
    $('#stat-quotes').textContent = '—';
    $('#stat-opps').textContent = `${DEMO_OPPORTUNITIES.length}`;
    $('#stat-venues').textContent = '—';
    $('#stat-confidence').textContent = '62%';
    $('#last-scan').textContent = 'offline demo · connect a backend';
  }
}

function wireControls() {
  $('#mode-buttons').addEventListener('click', async (event) => {
    const button = event.target.closest('button[data-mode]');
    if (!button) return;
    try {
      const result = await api('/mode', { method: 'PUT', body: JSON.stringify({ mode: button.dataset.mode }) });
      applySettings({ mode: result.mode, kill_switch: state.kill });
      toast(`Mode set to ${result.mode}`);
    } catch (error) { toast(error.message); }
  });

  $('#kill-switch').addEventListener('click', async () => {
    try {
      const next = !state.kill;
      const result = await api('/settings', {
        method: 'PATCH',
        body: JSON.stringify({ values: { kill_switch: String(next) } }),
      });
      applySettings(result);
      toast(next ? 'Kill switch engaged.' : 'Kill switch released — execution gates still apply.');
    } catch (error) { toast(error.message); }
  });

  $('#scan-btn').addEventListener('click', async () => {
    try {
      const result = await api('/scan', { method: 'POST' });
      toast(`Scan complete: ${result.quote_count} quotes, ${result.opportunity_count} spreads.`);
      await refresh();
    } catch (error) { toast(error.message); }
  });

  $('#research-select').addEventListener('change', (event) => loadValuation(event.target.value));
}

initScene();
initSteps();
wireControls();
refresh();
setInterval(refresh, 8000);

if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
  navigator.serviceWorker.register('./sw.js').catch(() => {});
}
