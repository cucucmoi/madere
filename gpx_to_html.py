#!/usr/bin/env python3
"""
MIUT 2026 – deux cartes :
  1. MIUT2026_carte.html    : MIUT + PR1.1 (tracé exact IFCN)
  2. MIUT2026_PR_carte.html : MIUT + TOUS les PR Madère via Overpass/OSM (browser-side)
"""

import xml.etree.ElementTree as ET
import math
import json
from pathlib import Path

NS = {'gpx': 'http://www.topografix.com/GPX/1/1'}

STAGES = [
    {'file': 'J1MIUT2026.gpx',         'label': 'J1',          'color': '#e74c3c'},
    {'file': 'J2MIUT2026.gpx',         'label': 'J2',          'color': '#e67e22'},
    {'file': 'J3MIUT2026.gpx',         'label': 'J3',          'color': '#27ae60'},
    {'file': 'J4varianteMIUT2026.gpx', 'label': 'J4 Variante', 'color': '#8e44ad'},
]

PR11_START    = (32.760211, -16.941575)
PR11_END      = (32.805950, -16.944994)
PR11_BUFFER_M = 280


# ── Utilitaires ───────────────────────────────────────────────────────────────

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def dist_to_segment(lat, lon, lat1, lon1, lat2, lon2):
    n = 200
    min_d = float('inf')
    for i in range(n + 1):
        t = i / n
        slat = lat1 + t * (lat2 - lat1)
        slon = lon1 + t * (lon2 - lon1)
        d = haversine(lat, lon, slat, slon)
        if d < min_d:
            min_d = d
    return min_d


def parse_gpx(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    points = []
    for rte in root.findall('gpx:rte', NS):
        for pt in rte.findall('gpx:rtept', NS):
            points.append((float(pt.get('lat')), float(pt.get('lon'))))
    return points


def sample(lst, max_pts):
    if len(lst) <= max_pts:
        return lst
    step = len(lst) / max_pts
    return [lst[int(i * step)] for i in range(max_pts)] + [lst[-1]]


def extract_pr11_overlap(pts):
    lat1, lon1 = PR11_START
    lat2, lon2 = PR11_END
    in_pr = [dist_to_segment(lat, lon, lat1, lon1, lat2, lon2) <= PR11_BUFFER_M
             for lat, lon in pts]
    segments = []
    i = 0
    while i < len(pts):
        if in_pr[i]:
            j = i
            while j < len(pts) and in_pr[j]:
                j += 1
            seg = [[pts[k][0], pts[k][1]] for k in range(i, j)]
            if len(seg) >= 2:
                segments.append(seg)
            i = j
        else:
            i += 1
    return segments


def build_data(base_dir):
    stages_js = []
    pr11_all  = []
    for s in STAGES:
        path = base_dir / s['file']
        if not path.exists():
            print(f"  ⚠ {path} manquant"); continue
        pts = parse_gpx(path)
        coords_map = sample(pts, 1500)
        segs = extract_pr11_overlap(pts)
        for seg in segs:
            pr11_all.append({'stage': s['label'], 'color': s['color'], 'coords': seg})
        stages_js.append({
            'label':  s['label'],
            'color':  s['color'],
            'coords': [[c[0], c[1]] for c in coords_map],
        })
        n_pts = sum(len(sg) for sg in segs)
        print(f"  {s['label']:12s} {len(pts)} pts GPX  →  PR1.1 overlap : {n_pts} pts ({len(segs)} seg.)")
    return stages_js, pr11_all


def build_stages_full(base_dir):
    """Retourne les étapes MIUT avec points full-res (pour la carte PR complète)."""
    stages = []
    for s in STAGES:
        path = base_dir / s['file']
        if not path.exists():
            print(f"  ⚠ {path} manquant"); continue
        pts = parse_gpx(path)
        print(f"  {s['label']:12s} → {len(pts)} points GPX")
        stages.append({
            'label':  s['label'],
            'color':  s['color'],
            'coords': [[p[0], p[1]] for p in sample(pts, 2000)],
        })
    return stages


# ── HTML 1 : MIUT + PR1.1 exact ──────────────────────────────────────────────

HTML_PR11 = r'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MIUT 2026 – PR1.1 Vereda da Ilha</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #eee;
       height: 100vh; display: flex; flex-direction: column; }
#header {
  background: linear-gradient(135deg, #16213e, #0f3460);
  padding: 10px 20px; display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
  box-shadow: 0 2px 8px rgba(0,0,0,.5); flex-shrink: 0;
}
#header h1 { font-size: 1.2rem; letter-spacing: 2px; color: #e2b96f; white-space: nowrap; }
#header h1 small { font-size: .7rem; color: #aaa; display: block; letter-spacing: 0; }
#legend { display: flex; gap: 8px; flex-wrap: wrap; }
.leg {
  display: flex; align-items: center; gap: 6px;
  background: rgba(255,255,255,.08); border-radius: 20px; padding: 4px 11px;
  cursor: pointer; border: 2px solid transparent; transition: .2s; user-select: none;
}
.leg:hover { background: rgba(255,255,255,.15); }
.leg.active { border-color: #fff; }
.dot { width: 12px; height: 12px; border-radius: 50%; }
.leg-label { font-size: .78rem; font-weight: 700; }
#pr-badge {
  background: rgba(231,76,60,.18); border: 2px solid rgba(231,76,60,.5);
  border-radius: 20px; padding: 4px 13px; font-size: .78rem; font-weight: 700;
  color: #e74c3c; white-space: nowrap;
}
#map { flex: 1; }
</style>
</head>
<body>
<div id="header">
  <h1>MIUT 2026 <small>Madère Ultra-Trail</small></h1>
  <div id="legend"></div>
  <div id="pr-badge">🔴 PR1.1 Vereda da Ilha — sections communes</div>
</div>
<div id="map"></div>
<script>
const STAGES = __STAGES_JSON__;
const PR11   = __PR11_JSON__;

const map = L.map('map');
L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenTopoMap | IFCN Madeira', maxZoom: 17
}).addTo(map);

const polylines = [];
const allBounds = [];
STAGES.forEach(s => {
  const poly = L.polyline(s.coords, {color: s.color, weight: 4, opacity: 0.85}).addTo(map);
  poly.bindTooltip(`<b>${s.label}</b>`, {sticky: true});
  polylines.push({label: s.label, poly});
  allBounds.push(...s.coords);
});
if (allBounds.length) map.fitBounds(allBounds);

STAGES.forEach(s => {
  if (!s.coords.length) return;
  const [lat, lon] = s.coords[0];
  L.marker([lat, lon], {
    icon: L.divIcon({
      className: '',
      html: `<div style="background:${s.color};color:#fff;font-weight:900;font-size:12px;
             padding:3px 9px;border-radius:12px;border:2px solid #fff;
             box-shadow:0 2px 6px rgba(0,0,0,.6);white-space:nowrap">${s.label}</div>`,
      iconAnchor: [0, 14],
    }),
    zIndexOffset: 1000, interactive: false,
  }).addTo(map);
});

const pr11Start = [32.760211, -16.941575];
const pr11End   = [32.805950, -16.944994];
L.polyline([pr11Start, pr11End], {color:'#e74c3c', weight:2, opacity:0.35, dashArray:'6,5'})
 .addTo(map).bindTooltip('PR1.1 Vereda da Ilha (8.2 km)', {sticky:true});

L.marker(pr11Start, {icon: L.divIcon({className:'',
  html:`<div style="background:#e74c3c;color:#fff;font-size:10px;font-weight:800;
        padding:2px 7px;border-radius:8px;border:1.5px solid #fff;
        box-shadow:0 1px 5px rgba(0,0,0,.5);white-space:nowrap">PR1.1 🏔 Pico Ruivo</div>`,
  iconAnchor:[0,10]}), zIndexOffset:800})
  .addTo(map).bindPopup('<b>PR1.1 départ</b><br>Casa de Abrigo do Pico Ruivo');

L.marker(pr11End, {icon: L.divIcon({className:'',
  html:`<div style="background:#e74c3c;color:#fff;font-size:10px;font-weight:800;
        padding:2px 7px;border-radius:8px;border:1.5px solid #fff;
        box-shadow:0 1px 5px rgba(0,0,0,.5);white-space:nowrap">PR1.1 🏘 Ilha</div>`,
  iconAnchor:[0,10]}), zIndexOffset:800})
  .addTo(map).bindPopup('<b>PR1.1 arrivée</b><br>Ilha');

PR11.forEach(seg => {
  L.polyline(seg.coords, {color:'#fff', weight:12, opacity:0.55}).addTo(map);
  L.polyline(seg.coords, {color:'#e74c3c', weight:7, opacity:1}).addTo(map)
   .bindPopup(`<b>Section commune MIUT ${seg.stage} × PR1.1</b><br>
               <span style="color:#e74c3c;font-weight:700">€10.50 – Réservation obligatoire</span><br>
               <a href="https://simplifica.madeira.gov.pt/services/78-82-259" target="_blank">→ Simplifica</a>`);
});

const legEl = document.getElementById('legend');
STAGES.forEach((s, i) => {
  const div = document.createElement('div');
  div.className = 'leg' + (i === 0 ? ' active' : '');
  div.innerHTML = `<div class="dot" style="background:${s.color}"></div>
                   <span class="leg-label">${s.label}</span>`;
  div.addEventListener('click', () => {
    document.querySelectorAll('.leg').forEach((el, j) => el.classList.toggle('active', j === i));
    polylines.forEach((p, j) => p.poly.setStyle({weight: j===i?6:4, opacity: j===i?1:0.45}));
    if (polylines[i].poly.getBounds().isValid())
      map.fitBounds(polylines[i].poly.getBounds(), {padding:[20,20]});
  });
  legEl.appendChild(div);
});
</script>
</body>
</html>
'''


# ── HTML 2 : MIUT + TOUS LES PR (Overpass API / OSM) ────────────────────────

HTML_PR_ALL = r'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Madère – MIUT 2026 × Tous les sentiers PR</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:'Segoe UI',Arial,sans-serif; background:#1a1a2e; color:#eee;
       height:100vh; display:flex; flex-direction:column; }

#header {
  background:linear-gradient(135deg,#16213e,#0f3460);
  padding:8px 16px; display:flex; align-items:center; gap:10px; flex-wrap:wrap;
  box-shadow:0 2px 8px rgba(0,0,0,.5); flex-shrink:0;
}
#header h1 { font-size:1.1rem; letter-spacing:1px; color:#e2b96f; white-space:nowrap; }
#header h1 small { font-size:.65rem; color:#aaa; display:block; letter-spacing:0; }

.sep { width:1px; height:26px; background:rgba(255,255,255,.15); flex-shrink:0; }

#legend { display:flex; gap:6px; flex-wrap:wrap; }
.leg {
  display:flex; align-items:center; gap:5px;
  background:rgba(255,255,255,.08); border-radius:16px; padding:3px 10px;
  cursor:pointer; border:2px solid transparent; transition:.2s; user-select:none;
  font-size:.73rem; font-weight:700; white-space:nowrap;
}
.leg:hover { background:rgba(255,255,255,.15); }
.leg.active { border-color:#fff; }
.dot { width:10px; height:10px; border-radius:50%; flex-shrink:0; }

#pr-controls { display:flex; gap:6px; flex-wrap:wrap; }
.pr-tog {
  display:flex; align-items:center; gap:4px; padding:3px 10px;
  border-radius:16px; cursor:pointer; border:2px solid transparent;
  font-size:.73rem; font-weight:700; transition:.2s; user-select:none; white-space:nowrap;
}
.pr-tog.active { border-color:#fff; }

#pr-status {
  font-size:.7rem; color:#9ab; padding:3px 9px;
  background:rgba(255,255,255,.06); border-radius:12px; white-space:nowrap;
}

#overlap-badge {
  font-size:.73rem; font-weight:700; padding:3px 10px;
  background:rgba(231,76,60,.15); border:2px solid rgba(231,76,60,.4);
  border-radius:16px; color:#e74c3c; white-space:nowrap; display:none;
}

#map { flex:1; }

/* Leaflet popup tweaks */
.leaflet-popup-content { font-size:.85rem; line-height:1.45; }
.leaflet-popup-content a { color:#3498db; }
</style>
</head>
<body>

<div id="header">
  <h1>MIUT 2026 <small>× PR Madère</small></h1>
  <div id="legend"></div>
  <div class="sep"></div>
  <div id="pr-controls">
    <div class="pr-tog active" id="tog-high"
         style="background:rgba(230,126,34,.2);color:#e67e22"
         onclick="togglePR('high')">
      <div class="dot" style="background:#e67e22"></div>PR1 €10.50
    </div>
    <div class="pr-tog active" id="tog-paid"
         style="background:rgba(52,152,219,.18);color:#5dade2"
         onclick="togglePR('paid')">
      <div class="dot" style="background:#5dade2"></div>PR payants €4.50
    </div>
    <div class="pr-tog" id="tog-closed"
         style="background:rgba(127,140,141,.12);color:#7f8c8d"
         onclick="togglePR('closed')">
      <div class="dot" style="background:#7f8c8d"></div>Fermés
    </div>
  </div>
  <div class="sep"></div>
  <div id="pr-status">⏳ Chargement OSM…</div>
  <div id="overlap-badge"></div>
</div>
<div id="map"></div>

<script>
// ── Données MIUT injectées par Python ────────────────────────────────────────
const STAGES = __STAGES_JSON__;

// ── Base tarifaire 2026 (IFCN / SIMplifica) ──────────────────────────────────
// tier: 'high'=€10.50, 'paid'=€4.50, 'closed'=fermé
const PR_DB = {
  'PR1'  :{tier:'high',   fee:10.50},
  'PR1.1':{tier:'high',   fee:10.50},
  'PR1.2':{tier:'high',   fee:10.50},
  'PR1.3':{tier:'closed', fee:0},
  'PR2'  :{tier:'paid',   fee:4.50},
  'PR3'  :{tier:'closed', fee:0},
  'PR3.1':{tier:'paid',   fee:4.50},
  'PR4'  :{tier:'paid',   fee:4.50},
  'PR5'  :{tier:'paid',   fee:4.50},
  'PR6'  :{tier:'paid',   fee:4.50},
  'PR6.1':{tier:'paid',   fee:4.50},
  'PR6.2':{tier:'paid',   fee:4.50},
  'PR6.3':{tier:'paid',   fee:4.50},
  'PR6.4':{tier:'paid',   fee:4.50},
  'PR6.5':{tier:'paid',   fee:4.50},
  'PR6.6':{tier:'paid',   fee:4.50},
  'PR6.7':{tier:'paid',   fee:4.50},
  'PR6.8':{tier:'paid',   fee:4.50},
  'PR7'  :{tier:'closed', fee:0},
  'PR8'  :{tier:'paid',   fee:4.50},
  'PR9'  :{tier:'closed', fee:0},
  'PR10' :{tier:'closed', fee:0},
  'PR11' :{tier:'paid',   fee:4.50},
  'PR13' :{tier:'paid',   fee:4.50},
  'PR13.1':{tier:'paid',  fee:4.50},
  'PR14' :{tier:'paid',   fee:4.50},
  'PR15' :{tier:'paid',   fee:4.50},
  'PR16' :{tier:'paid',   fee:4.50},
  'PR17' :{tier:'paid',   fee:4.50},
  'PR18' :{tier:'paid',   fee:4.50},
  'PR19' :{tier:'paid',   fee:4.50},
  'PR20' :{tier:'closed', fee:0},
  'PR21' :{tier:'paid',   fee:4.50},
  'PR22' :{tier:'paid',   fee:4.50},
  'PR23' :{tier:'paid',   fee:4.50},
  'PR27' :{tier:'closed', fee:0},
  'PR28' :{tier:'closed', fee:0},
};

const TIER_COLOR   = {high:'#e67e22', paid:'#5dade2', closed:'#7f8c8d'};
const TIER_WEIGHT  = {high:3.5,       paid:2.5,       closed:1.8};
const TIER_OPACITY = {high:0.9,       paid:0.8,       closed:0.35};
const TIER_DASH    = {high:'10,5',    paid:'7,5',     closed:'4,4'};

// ── Carte Leaflet ─────────────────────────────────────────────────────────────
const map = L.map('map');
L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
  attribution:'© OpenTopoMap contributors | IFCN Madère 2026', maxZoom:17
}).addTo(map);

// ── Tracés MIUT ───────────────────────────────────────────────────────────────
const miutPolys = [];
const allBounds = [];

STAGES.forEach(s => {
  const poly = L.polyline(s.coords, {
    color:s.color, weight:4.5, opacity:0.92, smoothFactor:1
  }).addTo(map);
  poly.bindTooltip(`<b>MIUT ${s.label}</b>`, {sticky:true});
  miutPolys.push({label:s.label, poly});
  allBounds.push(...s.coords);
});
if (allBounds.length) map.fitBounds(allBounds);

// Labels de départ
STAGES.forEach(s => {
  if (!s.coords.length) return;
  const [lat, lon] = s.coords[0];
  L.marker([lat, lon], {
    icon: L.divIcon({
      className:'',
      html:`<div style="background:${s.color};color:#fff;font-weight:900;font-size:11px;
            padding:2px 8px;border-radius:10px;border:2px solid #fff;
            box-shadow:0 2px 5px rgba(0,0,0,.6);white-space:nowrap">${s.label}</div>`,
      iconAnchor:[0,12],
    }),
    zIndexOffset:1000, interactive:false,
  }).addTo(map);
});

// ── Légende MIUT cliquable ────────────────────────────────────────────────────
const legEl = document.getElementById('legend');
STAGES.forEach((s, i) => {
  const div = document.createElement('div');
  div.className = 'leg' + (i===0?' active':'');
  div.innerHTML = `<div class="dot" style="background:${s.color}"></div>${s.label}`;
  div.addEventListener('click', () => {
    document.querySelectorAll('.leg').forEach((el,j)=>el.classList.toggle('active',j===i));
    miutPolys.forEach((p,j)=>p.poly.setStyle({weight:j===i?6.5:4.5, opacity:j===i?1:0.5}));
    if (miutPolys[i].poly.getBounds().isValid())
      map.fitBounds(miutPolys[i].poly.getBounds(), {padding:[20,20]});
  });
  legEl.appendChild(div);
});

// ── Couches PR par tier ───────────────────────────────────────────────────────
const prLayers  = {high:[], paid:[], closed:[]};
const prVisible = {high:true, paid:true, closed:false};

function togglePR(tier) {
  prVisible[tier] = !prVisible[tier];
  document.getElementById('tog-'+tier).classList.toggle('active', prVisible[tier]);
  prLayers[tier].forEach(poly => {
    prVisible[tier] ? poly.addTo(map) : poly.remove();
  });
}

// ── Haversine (JS) ────────────────────────────────────────────────────────────
function haversine(lat1,lon1,lat2,lon2) {
  const R=6371000, R2=Math.PI/180;
  const p1=lat1*R2, p2=lat2*R2, dp=(lat2-lat1)*R2, dl=(lon2-lon1)*R2;
  const a=Math.sin(dp/2)**2 + Math.cos(p1)*Math.cos(p2)*Math.sin(dl/2)**2;
  return R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a));
}

// ── Détection des sections communes (index spatial) ───────────────────────────
const OVERLAP_BUFFER = 260;  // mètres

function buildSpatialIndex(prTrails) {
  const CELL = 0.004;  // ~440 m par cellule
  const idx  = {};
  prTrails.forEach((pr, pi) => {
    pr.coords.forEach(([lat,lon]) => {
      const k = `${Math.floor(lat/CELL)},${Math.floor(lon/CELL)}`;
      if (!idx[k]) idx[k] = [];
      idx[k].push({lat, lon, pi});
    });
  });
  return {idx, CELL};
}

function nearestPR(lat, lon, {idx, CELL}, prTrails) {
  const bufDeg = OVERLAP_BUFFER / 100000;
  const r0 = Math.floor((lat-bufDeg)/CELL), r1 = Math.floor((lat+bufDeg)/CELL);
  const c0 = Math.floor((lon-bufDeg)/CELL), c1 = Math.floor((lon+bufDeg)/CELL);
  for (let r=r0; r<=r1; r++) {
    for (let c=c0; c<=c1; c++) {
      const pts = idx[`${r},${c}`];
      if (!pts) continue;
      for (const {lat:plat, lon:plon, pi} of pts) {
        if (haversine(lat,lon,plat,plon) <= OVERLAP_BUFFER) return pi;
      }
    }
  }
  return -1;
}

function detectOverlaps(paidTrails) {
  const spatialIdx = buildSpatialIndex(paidTrails);
  const overlaps   = [];

  STAGES.forEach(stage => {
    const pts = stage.coords;
    const near = pts.map(([lat,lon]) => nearestPR(lat,lon,spatialIdx,paidTrails));

    let i = 0;
    while (i < pts.length) {
      const pi = near[i];
      if (pi >= 0) {
        let j = i;
        // Keep going while same PR trail (allow small gaps of 1 pt)
        while (j < pts.length && (near[j]===pi || (j+1<pts.length && near[j+1]===pi))) j++;
        if (j - i >= 2) {
          const seg  = pts.slice(i, j+1);
          const pr   = paidTrails[pi];
          const feeStr = pr.tier==='high' ? '€10.50' : '€4.50';
          // White halo
          L.polyline(seg, {color:'#fff', weight:13, opacity:0.5, smoothFactor:1}).addTo(map);
          // Red overlay
          L.polyline(seg, {color:'#e74c3c', weight:7.5, opacity:1, smoothFactor:1})
           .addTo(map)
           .bindPopup(
             `<b>Section commune</b><br>` +
             `MIUT <b>${stage.label}</b> × <b>${pr.ref}</b><br>` +
             `<i>${pr.name}</i><br>` +
             `<span style="color:#e74c3c;font-weight:700">${feeStr} – Réservation obligatoire</span><br>` +
             `<a href="https://simplifica.madeira.gov.pt" target="_blank">→ SIMplifica</a>`
           );
          overlaps.push({stage:stage.label, ref:pr.ref, tier:pr.tier});
        }
        i = j + 1;
      } else {
        i++;
      }
    }
  });
  return overlaps;
}

// ── Chargement des sentiers PR depuis Overpass/OSM ───────────────────────────
// Requête : toutes les relations hiking avec ref=PR* dans la bbox de Madère
const OVERPASS_QUERY = `[out:json][timeout:90];
relation["route"="hiking"]["ref"~"^PR"](32.60,-17.30,32.90,-16.60);
out geom;`;

async function loadPRTrails() {
  const statusEl = document.getElementById('pr-status');
  const badgeEl  = document.getElementById('overlap-badge');

  try {
    const resp = await fetch('https://overpass-api.de/api/interpreter', {
      method : 'POST',
      headers: {'Content-Type':'application/x-www-form-urlencoded'},
      body   : 'data=' + encodeURIComponent(OVERPASS_QUERY),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    // Construire la liste des trails depuis les relations OSM
    const trails = [];
    for (const el of (data.elements || [])) {
      if (el.type !== 'relation') continue;
      const ref = (el.tags?.ref || '').trim();
      if (!ref.startsWith('PR')) continue;

      // Concaténer la géométrie des ways membres
      const coords = [];
      for (const m of (el.members || [])) {
        if (m.type==='way' && m.geometry) {
          for (const {lat,lon} of m.geometry) coords.push([lat,lon]);
        }
      }
      if (coords.length < 2) continue;

      const db   = PR_DB[ref] || {tier:'paid', fee:4.50};
      const name = el.tags?.name || el.tags?.['name:fr'] || el.tags?.['name:en'] || ref;
      trails.push({ref, name, coords, tier:db.tier, fee:db.fee, osmId:el.id});
    }

    statusEl.textContent = `✅ ${trails.length} sentiers PR chargés depuis OSM`;

    // Affichage des tracés PR
    trails.forEach(pr => {
      const poly = L.polyline(pr.coords, {
        color     : TIER_COLOR[pr.tier],
        weight    : TIER_WEIGHT[pr.tier],
        opacity   : TIER_OPACITY[pr.tier],
        dashArray : TIER_DASH[pr.tier],
        smoothFactor: 1.5,
      });

      const feeHtml = pr.tier==='closed'
        ? `<span style="color:#e74c3c;font-weight:700">⛔ Fermé</span>`
        : `<span style="color:${TIER_COLOR[pr.tier]};font-weight:700">€${pr.fee.toFixed(2)}/pers – SIMplifica</span>`;

      poly.bindPopup(
        `<b>${pr.ref}</b> – ${pr.name}<br>${feeHtml}<br>` +
        `<small><a href="https://www.openstreetmap.org/relation/${pr.osmId}" target="_blank">→ OpenStreetMap</a>` +
        (pr.tier!=='closed' ? ' | <a href="https://simplifica.madeira.gov.pt" target="_blank">→ Réserver</a>' : '') +
        `</small>`
      );
      poly.bindTooltip(`<b>${pr.ref}</b> ${pr.name}`, {sticky:true});

      if (prVisible[pr.tier]) poly.addTo(map);
      prLayers[pr.tier].push(poly);
    });

    // Détection des sections communes MIUT × PR payants
    const paidTrails = trails.filter(t => t.tier !== 'closed');
    if (paidTrails.length === 0) {
      statusEl.textContent = `✅ ${trails.length} sentiers PR | aucun payant trouvé`;
      return;
    }

    statusEl.textContent = `✅ ${trails.length} PR | ⚙ Calcul sections communes…`;
    await new Promise(r => setTimeout(r, 30));  // laisse l'UI se rafraîchir

    const overlaps = detectOverlaps(paidTrails);

    if (overlaps.length > 0) {
      badgeEl.style.display = 'block';
      // Résumé groupé par (stage, PR)
      const summary = overlaps.map(o => `${o.stage}×${o.ref}`).join(', ');
      badgeEl.textContent = `🔴 ${overlaps.length} section(s) commune(s) : ${summary}`;
      statusEl.textContent = `✅ ${trails.length} sentiers PR | ${overlaps.length} section(s) commune(s) MIUT × PR payants`;
    } else {
      statusEl.textContent = `✅ ${trails.length} sentiers PR | aucune section commune détectée`;
    }

  } catch (err) {
    statusEl.textContent = `❌ Erreur Overpass : ${err.message}`;
    console.error('Overpass error:', err);
  }
}

loadPRTrails();
</script>
</body>
</html>
'''


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    base = Path(__file__).parent

    # Carte 1 : MIUT + PR1.1
    print("── Carte MIUT × PR1.1 ──────────────────────────────")
    stages_js, pr11_segs = build_data(base)
    if stages_js:
        html1 = HTML_PR11 \
            .replace('__STAGES_JSON__', json.dumps(stages_js, ensure_ascii=False)) \
            .replace('__PR11_JSON__',   json.dumps(pr11_segs, ensure_ascii=False))
        out1 = base / 'MIUT2026_carte.html'
        out1.write_text(html1, encoding='utf-8')
        total = sum(len(s['coords']) for s in pr11_segs)
        hits  = set(s['stage'] for s in pr11_segs)
        print(f"  → {out1}  ({len(pr11_segs)} seg., {total} pts, étapes: {', '.join(hits) or 'aucune'})")

    # Carte 2 : MIUT + TOUS les PR via Overpass
    print("\n── Carte MIUT × TOUS les PR (OSM/Overpass) ─────────")
    stages_full = build_stages_full(base)
    if stages_full:
        html2 = HTML_PR_ALL.replace('__STAGES_JSON__', json.dumps(stages_full, ensure_ascii=False))
        out2 = base / 'MIUT2026_PR_carte.html'
        out2.write_text(html2, encoding='utf-8')
        print(f"  → {out2}")
        print("  (les tracés PR sont chargés depuis OpenStreetMap à l'ouverture du fichier)")

    print("\n✅ Terminé.")


if __name__ == '__main__':
    main()
