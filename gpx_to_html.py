#!/usr/bin/env python3
"""Convertisseur GPX → HTML pour MIUT 2026"""

import xml.etree.ElementTree as ET
import math
import json
from pathlib import Path

NS = {'gpx': 'http://www.topografix.com/GPX/1/1'}

STAGES = [
    {'file': 'J1MIUT2026.gpx',       'label': 'J1', 'color': '#e74c3c'},
    {'file': 'J2MIUT2026.gpx',       'label': 'J2', 'color': '#e67e22'},
    {'file': 'J3MIUT2026.gpx',       'label': 'J3', 'color': '#27ae60'},
    {'file': 'J4varianteMIUT2026.gpx','label': 'J4 Variante', 'color': '#8e44ad'},
]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def parse_gpx(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()

    meta = root.find('gpx:metadata', NS)
    name = ''
    if meta is not None:
        n = meta.find('gpx:name', NS)
        if n is not None:
            name = n.text or ''

    points = []
    for rte in root.findall('gpx:rte', NS):
        for pt in rte.findall('gpx:rtept', NS):
            lat = float(pt.get('lat'))
            lon = float(pt.get('lon'))
            e = pt.find('gpx:ele', NS)
            ele = float(e.text) if e is not None else 0
            points.append((lat, lon, ele))

    waypoints = []
    for wpt in root.findall('gpx:wpt', NS):
        lat = float(wpt.get('lat'))
        lon = float(wpt.get('lon'))
        n = wpt.find('gpx:name', NS)
        t = wpt.find('gpx:type', NS)
        wpt_name = n.text if n is not None else ''
        wpt_type = t.text if t is not None else ''
        waypoints.append({'lat': lat, 'lon': lon, 'name': wpt_name or '', 'type': wpt_type or ''})

    return name, points, waypoints

def compute_stats(points):
    dist, gain, loss = 0.0, 0.0, 0.0
    cum = [0.0]
    for i in range(1, len(points)):
        d = haversine(points[i-1][0], points[i-1][1], points[i][0], points[i][1])
        dist += d
        cum.append(dist)
        de = points[i][2] - points[i-1][2]
        if de > 0:
            gain += de
        else:
            loss += abs(de)
    min_e = min(p[2] for p in points) if points else 0
    max_e = max(p[2] for p in points) if points else 0
    return dist, gain, loss, min_e, max_e, cum

def sample(lst, max_pts):
    if len(lst) <= max_pts:
        return lst
    step = len(lst) / max_pts
    return [lst[int(i * step)] for i in range(max_pts)] + [lst[-1]]

def build_stage_data(base_dir):
    data = []
    for s in STAGES:
        path = base_dir / s['file']
        if not path.exists():
            print(f"⚠ Fichier manquant : {path}")
            continue
        name, points, waypoints = parse_gpx(path)
        dist, gain, loss, min_e, max_e, cum = compute_stats(points)

        # Sous-échantillonnage pour la carte (max 1500 pts) et profil (max 600 pts)
        coords = sample([(p[0], p[1]) for p in points], 1500)
        elev_pts = sample(points, 600)
        elev_cum  = sample(cum, 600)

        # Filtrage des waypoints : Begin, End, Waypoint nommés, forks nommés
        important_wpts = []
        for w in waypoints:
            t = w['type']
            nm = w['name']
            if t in ('Begin', 'End'):
                important_wpts.append(w)
            elif t == 'Waypoint' and nm:
                important_wpts.append(w)
            elif 'fork' in t.lower() and nm:
                important_wpts.append(w)

        data.append({
            'label':    s['label'],
            'name':     name,
            'color':    s['color'],
            'coords':   [[c[0], c[1]] for c in coords],
            'elevPts':  [round(p[2], 1) for p in elev_pts],
            'elevKm':   [round(d/1000, 2) for d in elev_cum],
            'waypoints': important_wpts,
            'stats': {
                'dist_km':  round(dist / 1000, 1),
                'gain_m':   round(gain),
                'loss_m':   round(loss),
                'min_ele':  round(min_e),
                'max_ele':  round(max_e),
            }
        })
    return data

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MIUT 2026 – Parcours</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #eee; height: 100vh; display: flex; flex-direction: column; }

/* ── Header ── */
#header {
  background: linear-gradient(135deg, #16213e 0%, #0f3460 100%);
  padding: 14px 20px;
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
  box-shadow: 0 2px 8px rgba(0,0,0,.5);
  flex-shrink: 0;
}
#header h1 { font-size: 1.4rem; letter-spacing: 2px; color: #e2b96f; white-space: nowrap; }
#header h1 small { font-size: .75rem; color: #aaa; display: block; letter-spacing: 0; }
#legend { display: flex; gap: 10px; flex-wrap: wrap; }
.legend-item {
  display: flex; align-items: center; gap: 7px;
  background: rgba(255,255,255,.07);
  border-radius: 20px; padding: 5px 12px;
  cursor: pointer; transition: background .2s;
  border: 2px solid transparent;
  user-select: none;
}
.legend-item:hover { background: rgba(255,255,255,.14); }
.legend-item.active { border-color: #fff; }
.legend-dot { width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0; }
.legend-label { font-size: .82rem; font-weight: 600; }
.legend-dist { font-size: .75rem; color: #bbb; }

/* ── Main layout ── */
#main { display: flex; flex: 1; overflow: hidden; }
#map { flex: 1; }

/* ── Side panel ── */
#panel {
  width: 320px; flex-shrink: 0;
  background: #16213e;
  display: flex; flex-direction: column;
  overflow: hidden;
  border-left: 1px solid #2a3a5e;
}
#panel-tabs { display: flex; border-bottom: 1px solid #2a3a5e; }
.tab-btn {
  flex: 1; padding: 10px 4px; font-size: .78rem; font-weight: 700;
  background: transparent; color: #888; border: none; cursor: pointer;
  border-bottom: 3px solid transparent; transition: all .2s;
}
.tab-btn:hover { color: #ccc; }
.tab-btn.active { color: #fff; border-bottom-color: var(--stage-color, #e2b96f); }
.tab-content { display: none; flex: 1; flex-direction: column; overflow-y: auto; padding: 14px; }
.tab-content.active { display: flex; }

/* ── Stats cards ── */
.stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }
.stat-card {
  background: rgba(255,255,255,.06); border-radius: 8px; padding: 10px;
  text-align: center;
}
.stat-card .val { font-size: 1.3rem; font-weight: 700; color: var(--stage-color, #e2b96f); }
.stat-card .lbl { font-size: .68rem; color: #999; text-transform: uppercase; letter-spacing: .5px; margin-top: 2px; }
.stat-card.full { grid-column: 1 / -1; }

/* ── Elevation chart ── */
.chart-wrap { flex: 1; min-height: 160px; position: relative; }

/* ── Waypoints list ── */
.wpt-list { list-style: none; }
.wpt-item {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,.06);
}
.wpt-icon {
  width: 24px; height: 24px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: .9rem; flex-shrink: 0; margin-top: 1px;
}
.wpt-text .wpt-name { font-size: .84rem; font-weight: 600; }
.wpt-text .wpt-type { font-size: .72rem; color: #888; }
.section-title {
  font-size: .72rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1px; color: #aaa; margin: 10px 0 6px;
}

/* ── Scrollbar ── */
#panel ::-webkit-scrollbar { width: 5px; }
#panel ::-webkit-scrollbar-track { background: transparent; }
#panel ::-webkit-scrollbar-thumb { background: #2a3a5e; border-radius: 4px; }
</style>
</head>
<body>

<div id="header">
  <h1>MIUT 2026 <small>Madère Ultra-Trail</small></h1>
  <div id="legend"></div>
</div>

<div id="main">
  <div id="map"></div>
  <div id="panel">
    <div id="panel-tabs"></div>
    <div id="panel-body"></div>
  </div>
</div>

<script>
const STAGES = __STAGES_JSON__;

// ── Map ────────────────────────────────────────────────────────────────────
const map = L.map('map', { zoomControl: true });
L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenTopoMap',
  maxZoom: 17
}).addTo(map);

const allBounds = [];

// ── Waypoint icons ─────────────────────────────────────────────────────────
function wptIcon(type, color) {
  const isBegin = type === 'Begin';
  const isEnd   = type === 'End';
  const isFork  = type.toLowerCase().includes('fork');
  const emoji   = isBegin ? '🏁' : isEnd ? '🏆' : isFork ? '⚠' : '📍';
  const bg      = isBegin ? '#27ae60' : isEnd ? '#e74c3c' : color;
  return L.divIcon({
    className: '',
    html: `<div style="background:${bg};width:28px;height:28px;border-radius:50%;border:2px solid #fff;
           display:flex;align-items:center;justify-content:center;font-size:14px;
           box-shadow:0 2px 6px rgba(0,0,0,.5)">${emoji}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

// ── Draw tracks & waypoints ────────────────────────────────────────────────
const polylines = [];
STAGES.forEach((s, i) => {
  const poly = L.polyline(s.coords, {
    color: s.color, weight: 4, opacity: 0.85, smoothFactor: 1
  }).addTo(map);
  poly.bindTooltip(`<b>${s.label}</b> – ${s.name}<br>${s.stats.dist_km} km • +${s.stats.gain_m}m`, {sticky: true});
  polylines.push(poly);
  allBounds.push(...s.coords);

  s.waypoints.forEach(w => {
    L.marker([w.lat, w.lon], { icon: wptIcon(w.type, s.color) })
      .bindPopup(`<b>${w.name || w.type}</b><br><small style="color:#888">${s.label} – ${s.name}</small>`)
      .addTo(map);
  });
});

if (allBounds.length) map.fitBounds(allBounds);

// ── Number labels on track (start of each stage) ───────────────────────────
STAGES.forEach(s => {
  if (!s.coords.length) return;
  const [lat, lon] = s.coords[0];
  L.marker([lat, lon], {
    icon: L.divIcon({
      className: '',
      html: `<div style="background:${s.color};color:#fff;font-weight:900;font-size:13px;
             padding:3px 9px;border-radius:12px;border:2px solid #fff;
             box-shadow:0 2px 6px rgba(0,0,0,.6);white-space:nowrap">${s.label}</div>`,
      iconAnchor: [0, 14],
    }),
    zIndexOffset: 1000,
    interactive: false,
  }).addTo(map);
});

// ── Legend ─────────────────────────────────────────────────────────────────
const legendEl = document.getElementById('legend');
let activeStage = 0;

function setActive(idx) {
  activeStage = idx;
  document.querySelectorAll('.legend-item').forEach((el, i) => el.classList.toggle('active', i === idx));
  document.querySelectorAll('.tab-btn').forEach((el, i)  => el.classList.toggle('active', i === idx));
  document.querySelectorAll('.tab-content').forEach((el, i) => el.classList.toggle('active', i === idx));
  polylines.forEach((p, i) => p.setStyle({ weight: i === idx ? 6 : 4, opacity: i === idx ? 1 : 0.55 }));
  if (polylines[idx] && polylines[idx].getBounds().isValid()) map.fitBounds(polylines[idx].getBounds(), {padding:[20,20]});
}

STAGES.forEach((s, i) => {
  const item = document.createElement('div');
  item.className = 'legend-item' + (i === 0 ? ' active' : '');
  item.innerHTML = `<div class="legend-dot" style="background:${s.color}"></div>
    <div><div class="legend-label">${s.label}</div>
    <div class="legend-dist">${s.stats.dist_km} km · +${s.stats.gain_m}m</div></div>`;
  item.addEventListener('click', () => setActive(i));
  legendEl.appendChild(item);
});

// ── Panel tabs ─────────────────────────────────────────────────────────────
const tabsEl = document.getElementById('panel-tabs');
const bodyEl = document.getElementById('panel-body');
bodyEl.style.cssText = 'flex:1;display:flex;flex-direction:column;overflow:hidden';

const charts = [];

STAGES.forEach((s, i) => {
  // Tab button
  const btn = document.createElement('button');
  btn.className = 'tab-btn' + (i === 0 ? ' active' : '');
  btn.textContent = s.label;
  btn.style.setProperty('--stage-color', s.color);
  btn.addEventListener('click', () => setActive(i));
  tabsEl.appendChild(btn);

  // Tab content
  const content = document.createElement('div');
  content.className = 'tab-content' + (i === 0 ? ' active' : '');
  content.style.flexDirection = 'column';

  // Stats
  const st = s.stats;
  content.innerHTML = `
    <p class="section-title">Statistiques</p>
    <div class="stat-grid" style="--stage-color:${s.color}">
      <div class="stat-card"><div class="val">${st.dist_km} km</div><div class="lbl">Distance</div></div>
      <div class="stat-card"><div class="val">${st.gain_m} m</div><div class="lbl">Dénivelé +</div></div>
      <div class="stat-card"><div class="val">${st.loss_m} m</div><div class="lbl">Dénivelé −</div></div>
      <div class="stat-card"><div class="val">${st.max_ele} m</div><div class="lbl">Alt. max</div></div>
      <div class="stat-card full"><div class="val">${st.min_ele} m → ${st.max_ele} m</div><div class="lbl">Altitude min / max</div></div>
    </div>
    <p class="section-title">Profil altimétrique</p>
    <div class="chart-wrap"><canvas id="chart-${i}"></canvas></div>
    <p class="section-title" style="margin-top:14px">Points clés</p>
    <ul class="wpt-list" id="wpts-${i}"></ul>
  `;
  bodyEl.appendChild(content);

  // Waypoints list
  const wptList = content.querySelector(`#wpts-${i}`);
  const wptFiltered = s.waypoints.filter(w => w.name);
  if (wptFiltered.length === 0) {
    wptList.innerHTML = '<li style="color:#666;font-size:.8rem;padding:6px 0">Aucun point nommé</li>';
  }
  wptFiltered.forEach(w => {
    const isBegin = w.type === 'Begin', isEnd = w.type === 'End';
    const emoji   = isBegin ? '🏁' : isEnd ? '🏆' : w.type.toLowerCase().includes('fork') ? '⚠' : '📍';
    const bg      = isBegin ? '#27ae60' : isEnd ? '#c0392b' : s.color;
    const li = document.createElement('li');
    li.className = 'wpt-item';
    li.innerHTML = `<div class="wpt-icon" style="background:${bg}">${emoji}</div>
      <div class="wpt-text">
        <div class="wpt-name">${w.name}</div>
        <div class="wpt-type">${w.type.replace(/_/g,' ')}</div>
      </div>`;
    li.style.cursor = 'pointer';
    li.addEventListener('click', () => map.setView([w.lat, w.lon], 15));
    wptList.appendChild(li);
  });
});

// ── Elevation charts (deferred to avoid layout issue) ─────────────────────
setTimeout(() => {
  STAGES.forEach((s, i) => {
    const canvas = document.getElementById(`chart-${i}`);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    charts.push(new Chart(ctx, {
      type: 'line',
      data: {
        labels: s.elevKm,
        datasets: [{
          data: s.elevPts,
          borderColor: s.color,
          backgroundColor: s.color + '33',
          borderWidth: 1.5,
          fill: true,
          pointRadius: 0,
          tension: 0.3,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false }, tooltip: {
          callbacks: {
            title: ctx => ctx[0].label + ' km',
            label: ctx => ctx.parsed.y + ' m',
          }
        }},
        scales: {
          x: {
            ticks: { color: '#888', maxTicksLimit: 6, callback: v => s.elevKm[v] + ' km' },
            grid: { color: 'rgba(255,255,255,.05)' },
          },
          y: {
            ticks: { color: '#888', callback: v => v + ' m' },
            grid: { color: 'rgba(255,255,255,.08)' },
          }
        }
      }
    }));
  });
}, 100);
</script>
</body>
</html>
'''

def main():
    base = Path(__file__).parent
    data = build_stage_data(base)
    if not data:
        print("Aucun fichier GPX trouvé.")
        return

    html = HTML_TEMPLATE.replace('__STAGES_JSON__', json.dumps(data, ensure_ascii=False))
    out = base / 'MIUT2026_carte.html'
    out.write_text(html, encoding='utf-8')
    print(f"✅ Carte générée : {out}")
    for s in data:
        st = s['stats']
        print(f"  {s['label']:12s} {st['dist_km']} km  +{st['gain_m']}m  -{st['loss_m']}m  alt {st['min_ele']}–{st['max_ele']}m")

if __name__ == '__main__':
    main()
