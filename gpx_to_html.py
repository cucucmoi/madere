#!/usr/bin/env python3
"""Convertisseur GPX → HTML pour MIUT 2026"""

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

# Sentiers PR classifiés – source IFCN / Simplifica Madeira 2026
# Le radius sert uniquement à délimiter quelle portion du tracé MIUT
# appartient à ce PR (pas affiché comme cercle sur la carte).
PR_ZONES = [
    # ── PR1 réseau – Pico Ruivo (€10.50 – 1 billet = PR1 + PR1.1 + PR1.2) ──
    {'code':'PR1',   'name':'Vereda do Areeiro',             'fee':'€10.50','status':'open',
     'lat':32.7255,'lon':-16.9322,'radius':1800,
     'desc':'Pico do Areeiro → Pico Ruivo (1862 m). Billet inclut PR1.1 et PR1.2.'},
    {'code':'PR1.1', 'name':'Vereda da Ilha',                'fee':'€10.50','status':'open',
     'lat':32.7294,'lon':-16.9396,'radius':1500,
     'desc':'Pico Ruivo → Ilha (inclus dans billet PR1).'},
    {'code':'PR1.2', 'name':'Vereda do Pico Ruivo',          'fee':'€10.50','status':'open',
     'lat':32.7356,'lon':-16.9481,'radius':1500,
     'desc':'Achada do Teixeira → Pico Ruivo (inclus dans billet PR1).'},
    {'code':'PR1.3', 'name':'Vereda da Encumeada',           'fee':'€10.50','status':'closed',
     'lat':32.7390,'lon':-16.9750,'radius':2500,
     'desc':'Pico Ruivo → Encumeada. FERMÉ en 2026.'},
    # ── PR2 Urzal ──
    {'code':'PR2',   'name':'Vereda do Urzal',               'fee':'€4.50','status':'open',
     'lat':32.7422,'lon':-16.9374,'radius':4000,
     'desc':'Curral das Freiras → Boaventura.'},
    # ── PR4 Levada do Barreiro ──
    {'code':'PR4',   'name':'Levada do Barreiro',            'fee':'€4.50','status':'partial',
     'lat':32.7650,'lon':-17.0450,'radius':2200,
     'desc':'Poço da Neve → Casa do Barreiro (Paul da Serra). Partiellement ouvert.'},
    # ── PR6 réseau – Rabacal ──
    {'code':'PR6',   'name':'Levada das 25 Fontes',          'fee':'€4.50','status':'open',
     'lat':32.7625,'lon':-17.0892,'radius':2000,
     'desc':'Rabacal → 25 Fontes. Laurisilva UNESCO.'},
    {'code':'PR6.1', 'name':'Levada do Risco',               'fee':'€4.50','status':'open',
     'lat':32.7730,'lon':-17.0870,'radius':1500,
     'desc':'Rabacal → Cascata do Risco.'},
    {'code':'PR6.2', 'name':'Levada do Alecrim',             'fee':'€4.50','status':'open',
     'lat':32.7680,'lon':-17.0820,'radius':1500,
     'desc':'Rabacal → Nascente Levada do Alecrim.'},
    # ── PR8 Ponta de São Lourenço ──
    {'code':'PR8',   'name':'Vereda da Ponta de São Lourenço','fee':'€4.50','status':'open',
     'lat':32.7364,'lon':-16.7197,'radius':2500,
     'desc':'Caniçal → Ponta de São Lourenço. Péninsule volcanique est.'},
    # ── PR9 Caldeirão Verde (FERMÉ) ──
    {'code':'PR9',   'name':'Levada do Caldeirão Verde',     'fee':'€4.50','status':'closed',
     'lat':32.7583,'lon':-16.9208,'radius':2500,
     'desc':'Queimadas → Caldeirão Verde. FERMÉ en 2026.'},
    # ── PR12 Encumeada ──
    {'code':'PR12',  'name':'Caminho Real da Encumeada',     'fee':'€4.50','status':'partial',
     'lat':32.7472,'lon':-17.0094,'radius':2500,
     'desc':'Serra de Água → Encumeada. Partiellement ouvert.'},
    # ── PR13 Fanal (GRATUIT) ──
    {'code':'PR13',  'name':'Vereda do Fanal',               'fee':'Gratuit','status':'open',
     'lat':32.7900,'lon':-17.0950,'radius':1800,
     'desc':'Fanal – forêt de laurisilva. GRATUIT.'},
    # ── PR14 Levada dos Cedros ──
    {'code':'PR14',  'name':'Levada dos Cedros',             'fee':'€4.50','status':'open',
     'lat':32.7820,'lon':-17.1050,'radius':2000,
     'desc':'Fanal → Levada dos Cedros. Forêt laurisilva UNESCO.'},
    # ── PR15 Ribeira da Janela ──
    {'code':'PR15',  'name':'Vereda da Ribeira da Janela',   'fee':'€4.50','status':'open',
     'lat':32.8210,'lon':-17.1320,'radius':1500,
     'desc':'Ribeira da Janela. Descente avec vues mer.'},
    # ── PR16 Fajã do Rodrigues ──
    {'code':'PR16',  'name':'Levada Fajã do Rodrigues',      'fee':'€4.50','status':'open',
     'lat':32.8040,'lon':-17.0820,'radius':2000,
     'desc':'São Vicente. Tunnels levada.'},
    # ── PR17 Pináculo e Folhadal ──
    {'code':'PR17',  'name':'Caminho do Pináculo e Folhadal','fee':'€4.50','status':'open',
     'lat':32.7690,'lon':-17.0240,'radius':2500,
     'desc':'Encumeada → Pináculo. Crêtes spectaculaires.'},
    # ── PR21 Caminho do Norte ──
    {'code':'PR21',  'name':'Caminho do Norte',              'fee':'€4.50','status':'open',
     'lat':32.7750,'lon':-17.0650,'radius':3000,
     'desc':'Traversée nord de l\'île.'},
    # ── PR22 Vereda do Chão dos Louros ──
    {'code':'PR22',  'name':'Vereda do Chão dos Louros',     'fee':'€4.50','status':'open',
     'lat':32.7600,'lon':-16.9500,'radius':2000,
     'desc':'Forêt de laurisilva, zone centrale.'},
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


def build_pr_segments(stage_full_coords):
    """
    For each PR zone, extract the actual MIUT track segments (polylines)
    that fall within the zone radius. Returns a list of PR entries each
    containing the real GPS coords of the crossing sections.
    """
    result = []
    for pr in PR_ZONES:
        pr_segs = []
        for label, color, pts in stage_full_coords:
            in_zone = [haversine(lat, lon, pr['lat'], pr['lon']) <= pr['radius']
                       for lat, lon in pts]
            i = 0
            while i < len(pts):
                if in_zone[i]:
                    j = i
                    while j < len(pts) and in_zone[j]:
                        j += 1
                    seg_coords = [[pts[k][0], pts[k][1]] for k in range(i, j)]
                    if len(seg_coords) >= 2:
                        pr_segs.append({'stage': label, 'color': color, 'coords': seg_coords})
                    i = j
                else:
                    i += 1

        if not pr_segs:
            continue

        # Centroid = midpoint of the longest segment (for zoom/label)
        largest = max(pr_segs, key=lambda s: len(s['coords']))
        mid = largest['coords'][len(largest['coords']) // 2]

        result.append({
            'code':     pr['code'],
            'name':     pr['name'],
            'fee':      pr['fee'],
            'status':   pr['status'],
            'desc':     pr['desc'],
            'lat':      mid[0],
            'lon':      mid[1],
            'segments': pr_segs,
        })
    return result


def build_stage_data(base_dir):
    data = []
    full_coords = []   # (label, color, [(lat,lon), ...]) – full resolution for PR extraction
    for s in STAGES:
        path = base_dir / s['file']
        if not path.exists():
            print(f"⚠ Fichier manquant : {path}")
            continue
        name, points, waypoints = parse_gpx(path)
        dist, gain, loss, min_e, max_e, cum = compute_stats(points)
        coords = sample([(p[0], p[1]) for p in points], 1500)
        elev_pts = sample(points, 600)
        elev_cum = sample(cum, 600)
        full_latlon = [(p[0], p[1]) for p in points]
        full_coords.append((s['label'], s['color'], full_latlon))
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
            'label':     s['label'],
            'name':      name,
            'color':     s['color'],
            'coords':    [[c[0], c[1]] for c in coords],
            'elevPts':   [round(p[2], 1) for p in elev_pts],
            'elevKm':    [round(d/1000, 2) for d in elev_cum],
            'waypoints': important_wpts,
            'stats': {
                'dist_km': round(dist / 1000, 1),
                'gain_m':  round(gain),
                'loss_m':  round(loss),
                'min_ele': round(min_e),
                'max_ele': round(max_e),
            }
        })
    return data, full_coords


HTML_TEMPLATE = r'''<!DOCTYPE html>
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
  padding: 12px 20px;
  display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
  box-shadow: 0 2px 8px rgba(0,0,0,.5); flex-shrink: 0;
}
#header h1 { font-size: 1.3rem; letter-spacing: 2px; color: #e2b96f; white-space: nowrap; }
#header h1 small { font-size: .72rem; color: #aaa; display: block; letter-spacing: 0; }

/* ── Legend stages ── */
#legend { display: flex; gap: 8px; flex-wrap: wrap; }
.legend-item {
  display: flex; align-items: center; gap: 7px;
  background: rgba(255,255,255,.07); border-radius: 20px; padding: 4px 11px;
  cursor: pointer; transition: background .2s; border: 2px solid transparent; user-select: none;
}
.legend-item:hover { background: rgba(255,255,255,.14); }
.legend-item.active { border-color: #fff; }
.legend-dot { width: 13px; height: 13px; border-radius: 50%; flex-shrink: 0; }
.legend-label { font-size: .8rem; font-weight: 600; }
.legend-dist { font-size: .72rem; color: #bbb; }

/* ── PR toggle button ── */
#pr-toggle {
  display: flex; align-items: center; gap: 7px;
  background: rgba(255,180,0,.12); border: 2px solid rgba(255,180,0,.4);
  border-radius: 20px; padding: 4px 13px; cursor: pointer;
  font-size: .8rem; font-weight: 700; color: #f1c40f;
  transition: all .2s; white-space: nowrap; user-select: none;
}
#pr-toggle:hover { background: rgba(255,180,0,.22); }
#pr-toggle.active { background: rgba(255,180,0,.25); border-color: #f1c40f; }

/* ── Main layout ── */
#main { display: flex; flex: 1; overflow: hidden; }
#map { flex: 1; }

/* ── Side panel ── */
#panel {
  width: 320px; flex-shrink: 0; background: #16213e;
  display: flex; flex-direction: column; overflow: hidden;
  border-left: 1px solid #2a3a5e;
}
#panel-tabs { display: flex; border-bottom: 1px solid #2a3a5e; }
.tab-btn {
  flex: 1; padding: 9px 3px; font-size: .76rem; font-weight: 700;
  background: transparent; color: #888; border: none; cursor: pointer;
  border-bottom: 3px solid transparent; transition: all .2s;
}
.tab-btn:hover { color: #ccc; }
.tab-btn.active { color: #fff; border-bottom-color: var(--stage-color, #e2b96f); }
.tab-content { display: none; flex: 1; flex-direction: column; overflow-y: auto; padding: 14px; }
.tab-content.active { display: flex; }

/* ── Stats ── */
.stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }
.stat-card {
  background: rgba(255,255,255,.06); border-radius: 8px; padding: 10px; text-align: center;
}
.stat-card .val { font-size: 1.25rem; font-weight: 700; color: var(--stage-color, #e2b96f); }
.stat-card .lbl { font-size: .67rem; color: #999; text-transform: uppercase; letter-spacing: .5px; margin-top: 2px; }
.stat-card.full { grid-column: 1 / -1; }
.chart-wrap { flex: 1; min-height: 160px; position: relative; }

/* ── Waypoints list ── */
.wpt-list { list-style: none; }
.wpt-item {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 7px 0; border-bottom: 1px solid rgba(255,255,255,.06); cursor: pointer;
}
.wpt-item:hover { background: rgba(255,255,255,.04); }
.wpt-icon {
  width: 24px; height: 24px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: .9rem; flex-shrink: 0; margin-top: 1px;
}
.wpt-text .wpt-name { font-size: .83rem; font-weight: 600; }
.wpt-text .wpt-type { font-size: .71rem; color: #888; }
.section-title {
  font-size: .71rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1px; color: #aaa; margin: 10px 0 6px;
}

/* ── PR panel tab ── */
.pr-list { list-style: none; }
.pr-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,.06); cursor: pointer;
}
.pr-item:hover { background: rgba(255,255,255,.04); }
.pr-badge {
  min-width: 54px; text-align: center; padding: 3px 6px;
  border-radius: 10px; font-size: .7rem; font-weight: 800;
  flex-shrink: 0;
}
.pr-badge.expensive { background: #c0392b; color: #fff; }
.pr-badge.standard  { background: #e67e22; color: #fff; }
.pr-badge.free      { background: #27ae60; color: #fff; }
.pr-badge.closed    { background: #555; color: #aaa; text-decoration: line-through; }
.pr-info .pr-code   { font-size: .8rem; font-weight: 700; color: #ddd; }
.pr-info .pr-name   { font-size: .72rem; color: #aaa; }
.pr-info .pr-status-closed { font-size: .68rem; color: #e74c3c; font-weight: 700; }

/* ── Scrollbar ── */
#panel ::-webkit-scrollbar { width: 5px; }
#panel ::-webkit-scrollbar-track { background: transparent; }
#panel ::-webkit-scrollbar-thumb { background: #2a3a5e; border-radius: 4px; }

/* ── PR popup ── */
.pr-popup { font-family: 'Segoe UI', Arial, sans-serif; min-width: 200px; }
.pr-popup .pr-popup-code { font-weight: 800; font-size: 1rem; margin-bottom: 4px; }
.pr-popup .pr-popup-name { color: #555; font-size: .85rem; margin-bottom: 6px; }
.pr-popup .pr-popup-fee  { display: inline-block; padding: 2px 8px; border-radius: 8px; font-weight: 700; font-size: .82rem; margin-bottom: 5px; }
.pr-popup .pr-popup-fee.exp   { background: #c0392b; color: #fff; }
.pr-popup .pr-popup-fee.std   { background: #e67e22; color: #fff; }
.pr-popup .pr-popup-fee.free  { background: #27ae60; color: #fff; }
.pr-popup .pr-popup-fee.closed{ background: #999; color: #fff; }
.pr-popup .pr-popup-desc { font-size: .8rem; color: #444; margin-top: 4px; }
.pr-popup .pr-popup-link { font-size: .75rem; color: #3498db; margin-top: 6px; display: block; }
</style>
</head>
<body>

<div id="header">
  <h1>MIUT 2026 <small>Madère Ultra-Trail</small></h1>
  <div id="legend"></div>
  <div id="pr-toggle" onclick="togglePR()">🔒 Sections PR payantes</div>
</div>

<div id="main">
  <div id="map"></div>
  <div id="panel">
    <div id="panel-tabs"></div>
    <div id="panel-body"></div>
  </div>
</div>

<script>
const STAGES   = __STAGES_JSON__;
const PR_SEGS  = __PR_SEGS_JSON__;

// ── Map ────────────────────────────────────────────────────────────────────
const map = L.map('map', { zoomControl: true });
L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenTopoMap | IFCN Madeira',
  maxZoom: 17
}).addTo(map);

const allBounds = [];

// ── Waypoint icons ─────────────────────────────────────────────────────────
function wptIcon(type, color) {
  const isBegin = type === 'Begin', isEnd = type === 'End';
  const isFork  = type.toLowerCase().includes('fork');
  const emoji   = isBegin ? '🏁' : isEnd ? '🏆' : isFork ? '⚠' : '📍';
  const bg      = isBegin ? '#27ae60' : isEnd ? '#e74c3c' : color;
  return L.divIcon({
    className: '',
    html: `<div style="background:${bg};width:28px;height:28px;border-radius:50%;border:2px solid #fff;
           display:flex;align-items:center;justify-content:center;font-size:14px;
           box-shadow:0 2px 6px rgba(0,0,0,.5)">${emoji}</div>`,
    iconSize: [28, 28], iconAnchor: [14, 14],
  });
}

// ── Draw MIUT tracks ───────────────────────────────────────────────────────
const polylines = [];
STAGES.forEach((s, i) => {
  const poly = L.polyline(s.coords, { color: s.color, weight: 4, opacity: 0.85, smoothFactor: 1 }).addTo(map);
  poly.bindTooltip(`<b>${s.label}</b> – ${s.name}<br>${s.stats.dist_km} km · +${s.stats.gain_m}m`, {sticky:true});
  polylines.push(poly);
  allBounds.push(...s.coords);
  s.waypoints.forEach(w => {
    L.marker([w.lat, w.lon], { icon: wptIcon(w.type, s.color) })
      .bindPopup(`<b>${w.name || w.type}</b><br><small style="color:#888">${s.label} – ${s.name}</small>`)
      .addTo(map);
  });
});
if (allBounds.length) map.fitBounds(allBounds);

// ── Stage number labels ────────────────────────────────────────────────────
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

// ── PR sections layer (real GPX polylines, not circles) ────────────────────
const prLayerGroup = L.layerGroup();
let prVisible = false;

function feeClass(pr) {
  if (pr.fee === 'Gratuit')    return 'free';
  if (pr.fee === '€10.50')     return 'exp';
  if (pr.status === 'closed')  return 'closed';
  return 'std';
}

function prLineColor(pr) {
  if (pr.status === 'closed')  return '#888';
  if (pr.fee === 'Gratuit')    return '#27ae60';
  if (pr.fee === '€10.50')     return '#c0392b';
  return '#f39c12';
}

PR_SEGS.forEach(pr => {
  const col  = prLineColor(pr);
  const cls  = feeClass(pr);
  const badge = pr.status === 'closed' ? '🚫' : pr.fee === 'Gratuit' ? '✅' : pr.fee === '€10.50' ? '💰💰' : '💰';
  const statusLabel = pr.status === 'closed'
    ? '<br><b style="color:#e74c3c">⛔ FERMÉ EN 2026</b>'
    : pr.status === 'partial' ? '<br><b style="color:#f39c12">⚠ Partiellement ouvert</b>' : '';

  const popupHtml = `
    <div class="pr-popup">
      <div class="pr-popup-code">${pr.code} ${badge}</div>
      <div class="pr-popup-name">${pr.name}</div>
      <span class="pr-popup-fee ${cls}">${pr.fee}</span>${statusLabel}
      <div class="pr-popup-desc">${pr.desc}</div>
      <a class="pr-popup-link" href="https://simplifica.madeira.gov.pt/services/78-82-259" target="_blank">→ Réserver sur Simplifica</a>
    </div>`;

  // Draw each segment as a highlighted polyline over the MIUT track
  pr.segments.forEach(seg => {
    // White halo for readability
    const halo = L.polyline(seg.coords, {
      color: '#fff', weight: 11, opacity: 0.55, smoothFactor: 1,
    });
    // Colored dashed line on top
    const line = L.polyline(seg.coords, {
      color: col, weight: 7, opacity: 0.9,
      dashArray: pr.status === 'closed' ? '4,6' : '10,5',
      smoothFactor: 1,
    });
    line.bindPopup(popupHtml);
    halo.bindPopup(popupHtml);
    prLayerGroup.addLayer(halo);
    prLayerGroup.addLayer(line);
  });

  // Label at segment midpoint
  const marker = L.marker([pr.lat, pr.lon], {
    icon: L.divIcon({
      className: '',
      html: `<div style="background:${col};color:#fff;font-weight:800;font-size:10px;
             padding:2px 7px;border-radius:8px;border:1.5px solid #fff;
             box-shadow:0 1px 5px rgba(0,0,0,.5);white-space:nowrap;opacity:.95">${pr.code}</div>`,
      iconAnchor: [0, 10],
    }),
    zIndexOffset: 600,
  });
  marker.bindPopup(popupHtml);
  prLayerGroup.addLayer(marker);
});

function togglePR() {
  prVisible = !prVisible;
  const btn = document.getElementById('pr-toggle');
  if (prVisible) {
    prLayerGroup.addTo(map);
    btn.classList.add('active');
    btn.textContent = '🔓 Sections PR payantes (actif)';
  } else {
    map.removeLayer(prLayerGroup);
    btn.classList.remove('active');
    btn.textContent = '🔒 Sections PR payantes';
  }
}

// ── Legend (stages) ────────────────────────────────────────────────────────
const legendEl = document.getElementById('legend');
let activeStage = 0;

function setActive(idx) {
  activeStage = idx;
  document.querySelectorAll('.legend-item').forEach((el,i) => el.classList.toggle('active', i===idx));
  document.querySelectorAll('.tab-btn').forEach((el,i)    => el.classList.toggle('active', i===idx));
  document.querySelectorAll('.tab-content').forEach((el,i) => el.classList.toggle('active', i===idx));
  polylines.forEach((p,i) => p.setStyle({ weight: i===idx ? 6 : 4, opacity: i===idx ? 1 : 0.55 }));
  if (polylines[idx]?.getBounds().isValid()) map.fitBounds(polylines[idx].getBounds(), {padding:[20,20]});
}

STAGES.forEach((s, i) => {
  const item = document.createElement('div');
  item.className = 'legend-item' + (i===0 ? ' active' : '');
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

// Stage tabs
STAGES.forEach((s, i) => {
  const btn = document.createElement('button');
  btn.className = 'tab-btn' + (i===0 ? ' active' : '');
  btn.textContent = s.label;
  btn.style.setProperty('--stage-color', s.color);
  btn.addEventListener('click', () => setActive(i));
  tabsEl.appendChild(btn);

  const content = document.createElement('div');
  content.className = 'tab-content' + (i===0 ? ' active' : '');
  content.style.flexDirection = 'column';
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

  const wptList = content.querySelector(`#wpts-${i}`);
  const wptFiltered = s.waypoints.filter(w => w.name);
  if (!wptFiltered.length) {
    wptList.innerHTML = '<li style="color:#666;font-size:.8rem;padding:6px 0">Aucun point nommé</li>';
  }
  wptFiltered.forEach(w => {
    const isBegin = w.type==='Begin', isEnd = w.type==='End';
    const emoji   = isBegin ? '🏁' : isEnd ? '🏆' : w.type.toLowerCase().includes('fork') ? '⚠' : '📍';
    const bg      = isBegin ? '#27ae60' : isEnd ? '#c0392b' : s.color;
    const li = document.createElement('li');
    li.className = 'wpt-item';
    li.innerHTML = `<div class="wpt-icon" style="background:${bg}">${emoji}</div>
      <div class="wpt-text">
        <div class="wpt-name">${w.name}</div>
        <div class="wpt-type">${w.type.replace(/_/g,' ')}</div>
      </div>`;
    li.addEventListener('click', () => map.setView([w.lat, w.lon], 15));
    wptList.appendChild(li);
  });
});

// PR tab
const prBtn = document.createElement('button');
prBtn.className = 'tab-btn';
prBtn.textContent = '💰 PR';
prBtn.style.setProperty('--stage-color', '#f1c40f');
tabsEl.appendChild(prBtn);

const prContent = document.createElement('div');
prContent.className = 'tab-content';
prContent.style.flexDirection = 'column';
prContent.innerHTML = `
  <p class="section-title">Sections PR payantes 2026</p>
  <div style="font-size:.75rem;color:#aaa;margin-bottom:10px;line-height:1.5">
    Portions du tracé MIUT classées PR. Réservation sur
    <a href="https://simplifica.madeira.gov.pt/services/78-82-259" target="_blank" style="color:#3498db">Simplifica</a>.
    Cliquez pour zoomer sur la section.
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;font-size:.72rem">
    <span style="background:#c0392b;color:#fff;padding:2px 7px;border-radius:8px;font-weight:700">€10.50 PR1</span>
    <span style="background:#e67e22;color:#fff;padding:2px 7px;border-radius:8px;font-weight:700">€4.50 standard</span>
    <span style="background:#27ae60;color:#fff;padding:2px 7px;border-radius:8px;font-weight:700">Gratuit</span>
    <span style="background:#555;color:#aaa;padding:2px 7px;border-radius:8px;font-weight:700">Fermé</span>
  </div>
  <ul class="pr-list" id="pr-list"></ul>
`;
bodyEl.appendChild(prContent);

prBtn.addEventListener('click', () => {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  prBtn.classList.add('active');
  prContent.classList.add('active');
  document.querySelectorAll('.legend-item').forEach(el => el.classList.remove('active'));
  polylines.forEach(p => p.setStyle({ weight: 4, opacity: 0.65 }));
  if (!prVisible) togglePR();
});

const prList = document.getElementById('pr-list');
PR_SEGS.forEach(pr => {
  const cls = feeClass(pr);
  const badgeClass = cls === 'exp' ? 'expensive' : cls === 'free' ? 'free' : cls === 'closed' ? 'closed' : 'standard';
  const feeLabel = pr.status === 'closed' ? '⛔ Fermé' : pr.fee;
  const li = document.createElement('li');
  li.className = 'pr-item';
  li.innerHTML = `
    <span class="pr-badge ${badgeClass}">${feeLabel}</span>
    <div class="pr-info">
      <div class="pr-code">${pr.code} – ${pr.name.length > 28 ? pr.name.slice(0,26)+'…' : pr.name}</div>
      <div class="pr-name">${pr.desc.slice(0, 55)}${pr.desc.length>55?'…':''}</div>
      ${pr.status === 'closed' ? '<div class="pr-status-closed">⛔ FERMÉ EN 2026</div>' : ''}
    </div>`;
  li.addEventListener('click', () => {
    map.setView([pr.lat, pr.lon], 14);
    if (!prVisible) togglePR();
  });
  prList.appendChild(li);
});

// ── Elevation charts ───────────────────────────────────────────────────────
setTimeout(() => {
  STAGES.forEach((s, i) => {
    const canvas = document.getElementById(`chart-${i}`);
    if (!canvas) return;
    new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: s.elevKm,
        datasets: [{
          data: s.elevPts, borderColor: s.color, backgroundColor: s.color + '33',
          borderWidth: 1.5, fill: true, pointRadius: 0, tension: 0.3,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { display: false }, tooltip: {
          callbacks: { title: c => c[0].label + ' km', label: c => c.parsed.y + ' m' }
        }},
        scales: {
          x: { ticks: { color:'#888', maxTicksLimit:6, callback: v => s.elevKm[v]+' km' }, grid: { color:'rgba(255,255,255,.05)' } },
          y: { ticks: { color:'#888', callback: v => v+' m' }, grid: { color:'rgba(255,255,255,.08)' } }
        }
      }
    });
  });
}, 100);
</script>
</body>
</html>
'''


def main():
    base = Path(__file__).parent
    data, full_coords = build_stage_data(base)
    if not data:
        print("Aucun fichier GPX trouvé.")
        return

    pr_segments = build_pr_segments(full_coords)

    html = HTML_TEMPLATE \
        .replace('__STAGES_JSON__', json.dumps(data,         ensure_ascii=False)) \
        .replace('__PR_SEGS_JSON__', json.dumps(pr_segments, ensure_ascii=False))

    out = base / 'MIUT2026_carte.html'
    out.write_text(html, encoding='utf-8')
    print(f"✅ Carte générée : {out}")
    for s in data:
        st = s['stats']
        print(f"  {s['label']:12s} {st['dist_km']} km  +{st['gain_m']}m  -{st['loss_m']}m")

    n_pay = sum(1 for p in pr_segments if p['fee'] != 'Gratuit' and p['status'] != 'closed')
    n_cls = sum(1 for p in pr_segments if p['status'] == 'closed')
    n_fre = sum(1 for p in pr_segments if p['fee'] == 'Gratuit')
    print(f"\n  {len(pr_segments)} sections PR sur tracé "
          f"({n_pay} payantes, {n_cls} fermées, {n_fre} gratuites)")
    for pr in pr_segments:
        total_pts = sum(len(s['coords']) for s in pr['segments'])
        stages_hit = ', '.join(set(s['stage'] for s in pr['segments']))
        print(f"    {pr['code']:6s} {pr['fee']:8s} [{stages_hit}] {total_pts} pts")


if __name__ == '__main__':
    main()
