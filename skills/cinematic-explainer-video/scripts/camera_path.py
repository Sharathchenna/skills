"""Smooth, speed-checked camera paths for the Three.js world.

A few camera keys become one C1-continuous Hermite spline (velocity never jumps and never stops dead at a key),
sampled once per frame. The world plays the samples back exactly, so the path that was measured here is the path
that renders. Import it from your generator:

    from camera_path import build_path
    path, report = build_path(KEYS, total=TOTAL, fps=30)   # raises SystemExit if a move is too fast
    cfg["camPath"], cfg["fps"] = path, 30

KEYS is a list of (t, [x, y, z] position, [x, y, z] look-at). In world.html:

    const PATH = CFG.camPath, FPS = CFG.fps;
    function cameraAt(t) {
      const f = cl(t * FPS, 0, PATH.length - 1), i = Math.floor(f), j = Math.min(i + 1, PATH.length - 1), u = f - i;
      const a = PATH[i], b = PATH[j];
      camera.position.set(lerp(a[0], b[0], u), lerp(a[1], b[1], u), lerp(a[2], b[2], u));
      camera.lookAt(lerp(a[3], b[3], u), lerp(a[4], b[4], u), lerp(a[5], b[5], u));
      if (a.length > 6) { camera.fov = lerp(a[6], b[6], u); camera.updateProjectionMatrix(); }   // optional zoom
    }

Limits (defaults): 2.6 world units per second and 30 degrees per second of turn, for a set about 3 units wide
seen from about 6 units away with a 52-degree lens. Speed limits scale with camera distance: with the studio
template's 30-degree lens (camera ~13 units away) use max_speed=4.8. A move that needs more is a whip: give it more time, start it earlier (under the end
of the previous sentence), or make it shorter. Never use a hard cut inside the world.

Run directly for a self-test: python3 -I camera_path.py
"""
import math


def _tangents(keys, idx):
    ts = [k[0] for k in keys]
    out = []
    for i in range(len(keys)):
        j0, j1 = max(0, i - 1), min(len(keys) - 1, i + 1)
        scale = 0.5 if i in (0, len(keys) - 1) else 1.0   # ease into the first key and out of the last
        out.append([(keys[j1][idx][d] - keys[j0][idx][d]) / (ts[j1] - ts[j0]) * scale for d in range(3)])
    return out


def sample(keys, total, fps=30):
    """One [px, py, pz, lx, ly, lz] row per frame from t=0 to t=total."""
    keys = sorted(keys, key=lambda k: k[0])
    ts = [k[0] for k in keys]
    if len(set(ts)) != len(ts):
        raise SystemExit("camera keys must have distinct times (no cuts inside the world)")
    tp, tl = _tangents(keys, 1), _tangents(keys, 2)
    rows = []
    for f in range(int(round(total * fps)) + 1):
        t = min(total, f / fps)
        k = 0
        while k < len(keys) - 2 and ts[k + 1] <= t:
            k += 1
        h = ts[k + 1] - ts[k]
        u = 0.0 if h <= 0 else min(1.0, max(0.0, (t - ts[k]) / h))
        h00, h10, h01, h11 = 2*u**3 - 3*u**2 + 1, u**3 - 2*u**2 + u, -2*u**3 + 3*u**2, u**3 - u**2
        row = []
        for idx, tg in ((1, tp), (2, tl)):
            a, b = keys[k][idx], keys[k + 1][idx]
            row += [round(h00*a[d] + h10*h*tg[k][d] + h01*b[d] + h11*h*tg[k + 1][d], 4) for d in range(3)]
        rows.append(row)
    return rows


def report(rows, fps=30):
    """Worst positional speed (units/s) and turn rate (deg/s), with the times they happen."""
    worst = {"speed": 0.0, "speedAt": 0.0, "turn": 0.0, "turnAt": 0.0}
    for f in range(1, len(rows)):
        p0, p1 = rows[f - 1], rows[f]
        v = math.dist(p0[:3], p1[:3]) * fps
        d0 = [p0[3 + i] - p0[i] for i in range(3)]
        d1 = [p1[3 + i] - p1[i] for i in range(3)]
        c = sum(a * b for a, b in zip(d0, d1)) / (math.hypot(*d0) * math.hypot(*d1))
        w = math.degrees(math.acos(max(-1.0, min(1.0, c)))) * fps
        if v > worst["speed"]:
            worst["speed"], worst["speedAt"] = round(v, 2), round(f / fps, 2)
        if w > worst["turn"]:
            worst["turn"], worst["turnAt"] = round(w, 1), round(f / fps, 2)
    return worst


def build_path(keys, total, fps=30, max_speed=2.6, max_turn=30.0, strict=True, fov_keys=None):
    """fov_keys: optional [(t, vertical_fov_degrees)] for zooms; appended as a 7th value per row.
    Prefer a zoom from the wide position over a dolly in when objects stand between the camera and the subject."""
    rows = sample(keys, total, fps)
    if fov_keys:
        fov = sample([(t, [f, 0, 0], [0, 0, 1]) for t, f in fov_keys], total, fps)
        rows = [r + [round(f[0], 3)] for r, f in zip(rows, fov)]
    r = report(rows, fps)
    print(f"camera: max speed {r['speed']} u/s at {r['speedAt']}s, max turn {r['turn']} deg/s at {r['turnAt']}s")
    if strict and (r["speed"] > max_speed or r["turn"] > max_turn):
        raise SystemExit(f"camera too fast (limits {max_speed} u/s, {max_turn} deg/s): give that move more time")
    return rows, r


if __name__ == "__main__":
    slow = [(0, [0, 3, 6.6], [0, 0, -0.3]), (5, [0.3, 2.9, 6.2], [0, 0, -0.3]), (10, [0, 2.6, 2.6], [0, 0.3, -1.2])]
    rows, r = build_path(slow, 10, fov_keys=[(0, 30), (5, 30), (10, 12)])
    assert len(rows) == 301 and r["speed"] < 2.6 and len(rows[0]) == 7 and abs(rows[-1][6] - 12) < 0.01, r
    whip = [(0, [0, 3, 6.6], [0, 0, -0.3]), (5, [0, 3, 6.6], [0, 0, -0.3]), (5.5, [0, 2.6, 1.0], [0, 0.3, -1.2])]
    try:
        build_path(whip, 6)
        raise AssertionError("whip not caught")
    except SystemExit as e:
        assert "too fast" in str(e)
    print("self-test OK")
