"""Construit les tracés de la carte depuis le GeoJSON officiel.

Pourquoi ne pas reprendre `data/svg/departements-2024.svg` : il ne couvre que
la métropole. Les cinq départements d'outre-mer y sont absents alors que la
table canonique contient leurs subventions — ils seraient gris sans qu'on
puisse dire si c'est faute de données ou faute de carte. La Corse y est de
surcroît identifiée en minuscules (`2a`), là où le référentiel dit `2A`.

Projection : conique conforme approchée, centrée sur la France métropolitaine.
L'outre-mer est placé en médaillons, chacun à son échelle — un DOM à l'échelle
réelle serait invisible.

Usage :
    python3 scripts/pipeline/build_carte.py

Sortie : data/aggregates/map-departements.json.gz
"""

import gzip
import io
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import common as C

ROOT = C.ROOT
GEO = os.path.join(ROOT, "data", "geo", "departements-2024.geojson.gz")
OUT = os.path.join(ROOT, "data", "aggregates", "map-departements.json.gz")

WIDTH, HEIGHT = 800.0, 620.0
PRECISION = 1          # décimale conservée : au-delà, l'œil ne voit rien
MIN_RING_AREA = 4.0    # unités² — sous ce seuil, un îlot est invisible
TOLERANCE = 0.30       # unités — écart maximal toléré lors de la simplification

# Médaillons d'outre-mer : (code, x, y, largeur, hauteur) dans le repère final.
INSETS = [
    ("971", 12, 430, 74, 56),   # Guadeloupe
    ("972", 12, 492, 74, 56),   # Martinique
    ("973", 92, 430, 74, 118),  # Guyane
    ("974", 12, 554, 74, 56),   # La Réunion
    ("976", 92, 554, 74, 56),   # Mayotte
]


def conic(lon, lat, lon0=2.5, lat0=46.5):
    """Projection conique conforme approchée — suffisante pour un choroplèthe."""
    x = math.radians(lon - lon0) * math.cos(math.radians(lat0))
    y = math.radians(lat)
    return x, y


def rings_of(geom):
    t, coords = geom["type"], geom["coordinates"]
    if t == "Polygon":
        return [coords[0]]
    if t == "MultiPolygon":
        return [poly[0] for poly in coords]
    return []


def ring_area(ring):
    a = 0.0
    for i in range(len(ring) - 1):
        a += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return abs(a) / 2.0


def _rdp(points, tol):
    """Douglas-Peucker sur une ligne OUVERTE."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        ax, ay = points[i]
        bx, by = points[j]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy) or 1e-9
        best, best_d = -1, tol
        for k in range(i + 1, j):
            px, py = points[k]
            d = abs(dy * px - dx * py + bx * ay - by * ax) / norm
            if d > best_d:
                best, best_d = k, d
        if best != -1:
            keep[best] = True
            stack.append((i, best))
            stack.append((best, j))
    return [p for p, k in zip(points, keep) if k]


def simplify(ring, tol):
    """Simplifie un anneau FERMÉ.

    Appliquer Douglas-Peucker tel quel à un anneau ne donne rien : ses deux
    extrémités étant confondues, la distance à la corde est nulle partout et
    l'algorithme supprime tous les points. On coupe donc l'anneau au point le
    plus éloigné du départ, et on simplifie les deux moitiés séparément.

    Le GeoJSON officiel est bien plus détaillé qu'un choroplèthe n'en a besoin :
    à 800 pixels de large, un écart de 0,3 unité est invisible, et c'est de ces
    points-là que vient l'essentiel du poids du fichier.
    """
    if len(ring) < 4:
        return ring
    closed = ring[0] == ring[-1]
    pts = ring[:-1] if closed else ring[:]
    if len(pts) < 4:
        return ring
    ax, ay = pts[0]
    far = max(range(1, len(pts)), key=lambda i: (pts[i][0] - ax) ** 2 + (pts[i][1] - ay) ** 2)
    out = _rdp(pts[:far + 1], tol)[:-1] + _rdp(pts[far:], tol)
    if closed:
        out = out + [out[0]]
    return out


def to_path(rings):
    """Chemin SVG, coordonnées arrondies et points consécutifs identiques ôtés."""
    parts = []
    for ring in rings:
        simplified = simplify(ring, TOLERANCE)
        pts = []
        last = None
        for x, y in simplified:
            p = (round(x, PRECISION), round(y, PRECISION))
            if p != last:
                pts.append(p)
                last = p
        if len(pts) < 3:
            continue
        parts.append("M" + "L".join(f"{x},{y}" for x, y in pts) + "Z")
    return "".join(parts)


def fit(rings, box):
    """Met une géométrie à l'échelle d'une boîte, en conservant les proportions."""
    bx, by, bw, bh = box
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    if not xs:
        return []
    w, h = (max(xs) - min(xs)) or 1e-9, (max(ys) - min(ys)) or 1e-9
    s = min(bw / w, bh / h)
    ox = bx + (bw - w * s) / 2 - min(xs) * s
    oy = by + (bh - h * s) / 2 + max(ys) * s
    return [[(p[0] * s + ox, oy - p[1] * s) for p in r] for r in rings]


def main():
    print("Construction de la carte depuis le GeoJSON\n")
    with gzip.open(GEO, "rt", encoding="utf-8") as f:
        geo = json.load(f)

    ref = set(C.referentiel()["departements"])
    feats = {}
    for feature in geo["features"]:
        code = str(feature["properties"].get("code") or "").upper()
        if code in ref:
            feats[code] = rings_of(feature["geometry"])

    missing = sorted(ref - set(feats))
    if missing:
        print(f"  ATTENTION — absents du GeoJSON : {missing}")

    inset_codes = {c for c, *_ in INSETS}
    metro = {c: r for c, r in feats.items() if c not in inset_codes}

    # Métropole : une seule projection commune, sinon les départements ne
    # s'emboîtent plus.
    proj = {c: [[conic(x, y) for x, y in ring] for ring in rings]
            for c, rings in metro.items()}
    all_rings = [r for rings in proj.values() for r in rings]
    xs = [p[0] for r in all_rings for p in r]
    ys = [p[1] for r in all_rings for p in r]
    pad = 8.0
    bw, bh = WIDTH - 190 - pad * 2, HEIGHT - pad * 2
    s = min(bw / (max(xs) - min(xs)), bh / (max(ys) - min(ys)))
    ox = 180 + pad - min(xs) * s
    oy = pad + max(ys) * s

    paths = {}
    kept = dropped = 0
    for code, rings in proj.items():
        placed = [[(p[0] * s + ox, oy - p[1] * s) for p in r] for r in rings]
        big = [r for r in placed if ring_area(r) >= MIN_RING_AREA]
        dropped += len(placed) - len(big)
        kept += len(big)
        paths[code] = to_path(big or placed[:1])

    # Outre-mer : chacun à son échelle, sinon invisible.
    for code, x, y, w, h in INSETS:
        if code not in feats:
            continue
        rings = [[conic(a, b) for a, b in ring] for ring in feats[code]]
        placed = fit(rings, (x, y, w, h))
        big = [r for r in placed if ring_area(r) >= MIN_RING_AREA * 0.25]
        paths[code] = to_path(big or placed[:1])

    payload = {
        "viewBox": f"0 0 {WIDTH:.0f} {HEIGHT:.0f}",
        "medaillons": {c: {"x": x, "y": y, "w": w, "h": h} for c, x, y, w, h in INSETS
                       if c in paths},
        "note": ("Outre-mer présenté en médaillons, à une échelle propre à chacun : "
                 "à l'échelle réelle, ces départements seraient invisibles."),
        "traces": paths,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with gzip.GzipFile(OUT, "wb", compresslevel=9, mtime=0) as f:
        f.write(raw)

    print(f"  départements tracés .. {len(paths)} / {len(ref)}")
    print(f"  dont médaillons ...... {len(payload['medaillons'])}")
    pts_before = sum(len(r) for rings in proj.values() for r in rings)
    pts_after = sum(pa.count("L") + pa.count("M") for pa in paths.values())
    print(f"  îlots minuscules ôtés  {dropped} (sur {kept + dropped})")
    print(f"  points ............... {pts_before:,} -> {pts_after:,} "
          f"({100 - pts_after * 100 // max(pts_before, 1)} % en moins)")
    print(f"\n  {len(raw)/1024:.0f} Ko  ->  {os.path.getsize(OUT)/1024:.0f} Ko gzip")


if __name__ == "__main__":
    main()
