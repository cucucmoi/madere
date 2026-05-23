#!/usr/bin/env python3
"""MIUT 2026 – carte avec sections PR1.1 surlignées en rouge"""

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

# PR1.1 – Vereda da Ilha (coordonnées exactes tirées du panneau IFCN officiel)
# Départ : Casa de Abrigo do Pico Ruivo  32°45'36.76"N / 16°56'29.67"W
# Arrivée : Ilha                          32°48'21.42"N / 16°56'41.98"W
# Distance : 8.2 km  |  Durée : 3h  |  Déniv. : 1764→490 m
PR11_START = (32.760211, -16.941575)   # 32°45'36.76"N 16°56'29.67"W
PR11_END   = (32.805950, -16.944994)   # 32°48'21.42"N 16°56'41.98"W
PR11_BUFFER_M = 280                    # tolérance latérale en mètres


# ── Fonctions utilitaires ──────────────────────────────────────────────────

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def dist_to_segment(lat, lon, lat1, lon1, lat2, lon2):
    """Distance minimale d'un point à un segment géographique (haversine)."""
    # On discrétise le segment en 200 points intermédiaires
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
    """Extrait les segments du tracé MIUT qui longent le PR1.1."""
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
    pr11_all  = []   # liste de {stage, color, coords}

    for s in STAGES:
        path = base_dir / s['file']
        if not path.exists():
            print(f"⚠ {path} manquant"); continue
        pts = parse_gpx(path)
        coords_map = sample(pts, 1500)

        # Extraction overlap PR1.1 sur points full-res
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


HTML = r'''<!DOCTYPE html>
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

/* ── Header ── */
#header {
  background: linear-gradient(135deg, #16213e, #0f3460);
  padding: 10px 20px; display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
  box-shadow: 0 2px 8px rgba(0,0,0,.5); flex-shrink: 0;
}
#header h1 { font-size: 1.2rem; letter-spacing: 2px; color: #e2b96f; white-space: nowrap; }
#header h1 small { font-size: .7rem; color: #aaa; display: block; letter-spacing: 0; }

/* ── Légende ── */
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

/* ── Badge PR1.1 ── */
#pr-badge {
  background: rgba(231,76,60,.18); border: 2px solid rgba(231,76,60,.5);
  border-radius: 20px; padding: 4px 13px; font-size: .78rem; font-weight: 700;
  color: #e74c3c; white-space: nowrap;
}

/* ── Map ── */
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
const STAGES  = __STAGES_JSON__;
const PR11    = __PR11_JSON__;   // [{stage, color, coords}, …]

// ── Carte ────────────────────────────────────────────────────────────────
const map = L.map('map');
L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenTopoMap | IFCN Madeira', maxZoom: 17
}).addTo(map);

// ── Tracés MIUT ───────────────────────────────────────────────────────────
const polylines = [];
const allBounds = [];

STAGES.forEach(s => {
  const poly = L.polyline(s.coords, {
    color: s.color, weight: 4, opacity: 0.85, smoothFactor: 1
  }).addTo(map);
  poly.bindTooltip(`<b>${s.label}</b>`, {sticky: true});
  polylines.push({label: s.label, poly});
  allBounds.push(...s.coords);
});

if (allBounds.length) map.fitBounds(allBounds);

// ── Labels de début d'étape ────────────────────────────────────────────
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

// ── Tracé PR1.1 (du panneau IFCN officiel) ────────────────────────────
const pr11Start = [32.760211, -16.941575];
const pr11End   = [32.805950, -16.944994];
L.polyline([pr11Start, pr11End], {
  color: '#e74c3c', weight: 2, opacity: 0.35, dashArray: '6,5'
}).addTo(map)
 .bindTooltip('PR1.1 Vereda da Ilha (tracé complet 8.2 km)', {sticky: true});

// Marqueurs départ/arrivée PR1.1
L.marker(pr11Start, {
  icon: L.divIcon({
    className: '',
    html: `<div style="background:#e74c3c;color:#fff;font-size:10px;font-weight:800;
           padding:2px 7px;border-radius:8px;border:1.5px solid #fff;
           box-shadow:0 1px 5px rgba(0,0,0,.5);white-space:nowrap">PR1.1 🏔 Pico Ruivo</div>`,
    iconAnchor: [0, 10],
  }), zIndexOffset: 800,
}).addTo(map).bindPopup('<b>PR1.1 départ</b><br>Casa de Abrigo do Pico Ruivo<br>32°45\'36.76"N / 16°56\'29.67"W');

L.marker(pr11End, {
  icon: L.divIcon({
    className: '',
    html: `<div style="background:#e74c3c;color:#fff;font-size:10px;font-weight:800;
           padding:2px 7px;border-radius:8px;border:1.5px solid #fff;
           box-shadow:0 1px 5px rgba(0,0,0,.5);white-space:nowrap">PR1.1 🏘 Ilha</div>`,
    iconAnchor: [0, 10],
  }), zIndexOffset: 800,
}).addTo(map).bindPopup('<b>PR1.1 arrivée</b><br>Ilha<br>32°48\'21.42"N / 16°56\'41.98"W');

// ── Sections communes MIUT ∩ PR1.1 (en rouge épais) ──────────────────
if (PR11.length === 0) {
  console.log('Aucune section commune trouvée.');
} else {
  PR11.forEach(seg => {
    // Halo blanc
    L.polyline(seg.coords, {
      color: '#fff', weight: 12, opacity: 0.55, smoothFactor: 1
    }).addTo(map);
    // Ligne rouge vive
    L.polyline(seg.coords, {
      color: '#e74c3c', weight: 7, opacity: 1, smoothFactor: 1
    }).addTo(map)
     .bindPopup(`<b>Section commune MIUT ${seg.stage} × PR1.1</b><br>
                 <span style="color:#e74c3c;font-weight:700">Réservation obligatoire – €10.50</span><br>
                 <a href="https://simplifica.madeira.gov.pt/services/78-82-259" target="_blank">→ Simplifica</a>`);
  });
}

// ── Légende cliquable ─────────────────────────────────────────────────
const legEl = document.getElementById('legend');
STAGES.forEach((s, i) => {
  const div = document.createElement('div');
  div.className = 'leg' + (i === 0 ? ' active' : '');
  div.innerHTML = `<div class="dot" style="background:${s.color}"></div>
                   <span class="leg-label">${s.label}</span>`;
  div.addEventListener('click', () => {
    document.querySelectorAll('.leg').forEach((el, j) => el.classList.toggle('active', j === i));
    polylines.forEach((p, j) => p.poly.setStyle({
      weight: j === i ? 6 : 4,
      opacity: j === i ? 1 : 0.45,
    }));
    if (polylines[i].poly.getBounds().isValid())
      map.fitBounds(polylines[i].poly.getBounds(), {padding: [20, 20]});
  });
  legEl.appendChild(div);
});
</script>
</body>
</html>
'''


def main():
    base = Path(__file__).parent
    print("Calcul des sections communes MIUT × PR1.1…")
    stages_js, pr11_segs = build_data(base)
    if not stages_js:
        print("Aucun fichier GPX trouvé."); return

    html = HTML \
        .replace('__STAGES_JSON__', json.dumps(stages_js, ensure_ascii=False)) \
        .replace('__PR11_JSON__',   json.dumps(pr11_segs, ensure_ascii=False))

    out = base / 'MIUT2026_carte.html'
    out.write_text(html, encoding='utf-8')
    print(f"\n✅ {out}")

    total = sum(len(s['coords']) for s in pr11_segs)
    stages_hit = set(s['stage'] for s in pr11_segs)
    print(f"   {len(pr11_segs)} segment(s) commun(s), {total} points GPS, étapes : {', '.join(stages_hit) or 'aucune'}")


if __name__ == '__main__':
    main()
