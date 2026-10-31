const COLORS = ['#2563eb', '#d97706', '#059669', '#9333ea'];
const STATUS = { ok: 'Normal', half: 'À moitié', full: 'Pleine', offline: 'Hors ligne', unknown: 'Aucune donnée' };

function ago(ts) {
  if (!ts) return 'jamais';
  const s = Math.round((Date.now() - Date.parse(ts)) / 1000);
  if (s < 60) return `il y a ${s} s`;
  if (s < 3600) return `il y a ${Math.round(s / 60)} min`;
  return `il y a ${Math.round(s / 3600)} h`;
}

function binCard(b, i) {
  const lvl = b.level ?? 0;
  return `
  <article class="bin ${b.status}">
    <div class="gauge"><div class="fill" style="height:${lvl}%"></div><span>${b.level === null ? '—' : lvl + '%'}</span></div>
    <div class="info">
      <div class="title"><i style="background:${COLORS[i % COLORS.length]}"></i><h3>${b.name}</h3></div>
      <p class="loc">${b.location}</p>
      <span class="badge ${b.status}">${STATUS[b.status]}</span>
      <dl>
        <dt>Couvercle</dt><dd>${b.lid_open ? 'ouvert' : 'fermé'}</dd>
        <dt>Signal Wi-Fi</dt><dd>${b.rssi ?? '—'} dBm</dd>
        <dt>Dernière mesure</dt><dd>${ago(b.last_seen)}</dd>
        <dt>Alerte WhatsApp</dt><dd>${b.alert_sent ? 'envoyée' : '—'}</dd>
      </dl>
    </div>
  </article>`;
}

function drawChart(series) {
  const svg = document.getElementById('chart');
  const W = 800, H = 240, P = 28;
  const all = series.flatMap(s => s.points.map(p => Date.parse(p.ts)));
  const now = Date.now(), t0 = all.length ? Math.min(...all) : now - 3600e3;
  const x = t => P + (W - 2 * P) * (t - t0) / Math.max(1, now - t0);
  const y = v => H - P - (H - 2 * P) * v / 100;
  let g = '';
  for (const v of [0, 25, 50, 75, 100]) {
    g += `<line x1="${P}" x2="${W - P}" y1="${y(v)}" y2="${y(v)}" class="grid"/>`;
    g += `<text x="4" y="${y(v) + 4}" class="axis">${v}</text>`;
  }
  for (let k = 0; k <= 4; k++) {
    const t = t0 + (now - t0) * k / 4;
    const label = new Date(t).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    g += `<text x="${x(t)}" y="${H - 6}" text-anchor="${k === 0 ? 'start' : k === 4 ? 'end' : 'middle'}" class="axis">${label}</text>`;
  }
  series.forEach((s, i) => {
    if (!s.points.length) return;
    const d = s.points.map((p, j) => `${j ? 'L' : 'M'}${x(Date.parse(p.ts)).toFixed(1)},${y(p.level).toFixed(1)}`).join('');
    g += `<path d="${d}" fill="none" stroke="${COLORS[i % COLORS.length]}" stroke-width="2"/>`;
  });
  svg.innerHTML = g;
  document.getElementById('legend').innerHTML =
    series.map((s, i) => `<span><i style="background:${COLORS[i % COLORS.length]}"></i>${s.name}</span>`).join('');
}

async function refresh() {
  const bins = await (await fetch('/api/bins')).json();
  document.getElementById('bins').innerHTML = bins.map(binCard).join('');
  const series = await Promise.all(bins.map(async b => ({
    name: b.name, points: await (await fetch(`/api/bins/${b.id}/history?hours=24`)).json()
  })));
  drawChart(series);
  const events = await (await fetch('/api/events')).json();
  document.getElementById('events').innerHTML = events.length ? events.map(e => `
    <li class="${e.kind}"><time>${new Date(e.ts).toLocaleString('fr-FR')}</time>
    <b>${e.name}</b> ${e.kind === 'FULL_ALERT' ? `pleine à ${e.level} %` : `vidée (${e.level} %)`}
    <small>${e.detail ?? ''}</small></li>`).join('') : '<li class="empty">Aucun événement</li>';
}

refresh();
setInterval(refresh, 5000);
