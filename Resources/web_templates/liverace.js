// Carica dinamicamente i loghi sponsor se presenti

fetch('/assets/sponsors')
  .then(r => r.ok ? r.json() : [])
  .then(list => {
    const bar = document.getElementById('sponsor-bar');
    const track = bar ? bar.querySelector('.sponsor-track') : null;
    if (!bar || !track) return;
    if (Array.isArray(list) && list.length) {
      // Crea i loghi una volta
      list.forEach(src => {
        const img = document.createElement('img');
        img.src = src;
        img.alt = 'Sponsor';
        img.onerror = () => { img.style.display = 'none'; };
        track.appendChild(img);
      });
      // Duplica i loghi per effetto loop
      list.forEach(src => {
        const img = document.createElement('img');
        img.src = src;
        img.alt = 'Sponsor';
        img.onerror = () => { img.style.display = 'none'; };
        track.appendChild(img);
      });
      // Calcola larghezza per animazione fluida
      setTimeout(() => {
        const trackWidth = track.scrollWidth / 2;
        track.style.width = (trackWidth * 2) + 'px';
      }, 100);
    } else {
      bar.style.display = 'none';
    }
  })
  .catch(() => {
    const bar = document.getElementById('sponsor-bar');
    if (bar) bar.style.display = 'none';
  });

const host = window.location.host;
const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const httpProto = window.location.protocol;

const apiBase = `${httpProto}//${host}`;
const wsBase  = `${protocol}://${host}`;

const elRows = document.getElementById("rows");
const elTimer = document.getElementById("timer");
const elMeta = document.getElementById("sessionMeta");
const elBestLastA = document.getElementById("colBestLastA");
const elBestLastB = document.getElementById("colBestLastB");

const state = { rows: new Map(), isRace: false };

function detectIsRace(session) {
    if (!session || typeof session !== 'object') return false;

    const direct = session.is_race ?? session.isRace ?? session.race;
    if (typeof direct === 'boolean') return direct;
    if (typeof direct === 'number') return direct !== 0;
    if (typeof direct === 'string') {
        const v = direct.trim().toLowerCase();
        if (['1', 'true', 'yes', 'on', 'race', 'gara'].includes(v)) return true;
        if (['0', 'false', 'no', 'off', 'practice', 'qualifying', 'qualifica'].includes(v)) return false;
    }

    const st = String(session.sessionType ?? '').toLowerCase();
    return st.includes('race') || st.includes('gara');
}

function syncBestLastHeaders() {
    if (!elBestLastA || !elBestLastB) return;
    if (state.isRace) {
        elBestLastA.textContent = 'Last';
        elBestLastB.textContent = 'Best';
    } else {
        elBestLastA.textContent = 'Best';
        elBestLastB.textContent = 'Last';
    }
}

function render(drivers) {
  if (!Array.isArray(drivers)) return;

  drivers.sort((a,b) => (a.position || 999) - (b.position || 999));

  elRows.innerHTML = drivers.map(d => `
    <tr class="row" data-key="${d.number ?? d.driverId ?? d.raceNumber ?? ''}">
      <td>${d.position ?? ''}</td>
      <td>${d.name_surname ?? ''}</td>
      <td>${d.team ?? ''}</td>
      <td>${d.sector1 ?? ''}</td>
      <td>${d.sector2 ?? ''}</td>
      <td>${d.sector3 ?? ''}</td>
            <td>${state.isRace ? (d.lastLap ?? '') : (d.fastLap ?? '')}</td>
      <td>${d.laps ?? ''}</td>
      <td><span class="badge">${d.status ?? ''}</span></td>
      <td>${d.gap ?? ''}</td>
      <td>${d.interval ?? ''}</td>
            <td>${state.isRace ? (d.fastLap ?? '') : (d.lastLap ?? '')}</td>
    </tr>`).join("");

  state.rows.clear();
  elRows.querySelectorAll("tr").forEach(tr => state.rows.set(String(tr.dataset.key), tr));
}

function flash(key, kind) {
  const row = state.rows.get(String(key));
  if (!row || !kind) return;

  const cls = "flash-" + String(kind).toLowerCase();
  row.classList.add(cls);
  setTimeout(() => row.classList.remove(cls), 800);
}

function updateSession(data) {
  if (!data || typeof data !== 'object') return;
    if (elTimer) elTimer.textContent = data.sessionTime || '--:--:--';

    state.isRace = detectIsRace(data);
    syncBestLastHeaders();

  const type = data.sessionType || 'Session';
  const status = data.sessionStatus || 'N/A';
  const idx = data.index != null ? ` #${data.index + 1}` : '';
  elMeta.textContent = `${type}${idx} - ${status}`;
}

async function boot() {
  try {
    const res = await fetch(`${apiBase}/api/snapshot`);
    const snap = await res.json();
    updateSession(snap.session);
    render(snap.drivers || []);
  } catch (_) {}

  const ws = new WebSocket(`${wsBase}/ws/timing`);
  ws.onmessage = e => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'snapshot') {
      updateSession(msg.data.session);
      render(msg.data.drivers || []);
    }
    if (msg.type === 'drivers') render(msg.data || []);
    if (msg.type === 'session') updateSession(msg.data);
  };

  const we = new WebSocket(`${wsBase}/ws/event`);
  we.onmessage = e => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'event') flash(msg.data.key, msg.data.kind);
  };
}

boot();
