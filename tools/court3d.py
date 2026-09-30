#!/usr/bin/env python3
"""코트 3D 기하 — 정규 좌표 → 월드(미터) → 카메라 → 화면.
web/template.html 의 JS 구현과 같은 식을 쓴다. 검증기가 '이 존이 화면에서 누를 만큼 보이는가'를
계산할 때 쓴다. 카메라 값은 data/cameras.json 한 곳에서만 정한다."""
import json, math, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAM = json.loads((ROOT / "data" / "cameras.json").read_text(encoding="utf-8"))
COURT_W, COURT_L = 10.97, 23.77
NET_Y = COURT_L / 2

# 존 경계 (그리기·판정용 — 코트 선 기준. 바깥 존은 선수 위치 검사에서만 넓게 쓴다)
COLS = {"L": (0.0, 1 / 3), "C": (1 / 3, 2 / 3), "R": (2 / 3, 1.0)}
ROWS = {"A": {"N": (.500, .640), "M": (.640, .860), "B": (.860, 1.000), "X": (1.000, 1.098)},
        "E": {"N": (.360, .500), "M": (.140, .360), "B": (.000, .140), "X": (-.098, .000)}}


def world(nx, ny, z=0.0):
    """정규 좌표(nx 0=왼쪽 복식라인, ny 0=상대 베이스라인) → 월드 미터(X 오른쪽, Y 상대 쪽, Z 위)"""
    return ((nx - 0.5) * COURT_W, (1 - ny) * COURT_L, z)


def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def _norm(a):
    l = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / l, a[1] / l, a[2] / l)


class Camera:
    def __init__(self, eye, look, focal, cx, cy, near=0.3):
        self.eye, self.focal, self.cx, self.cy, self.near = eye, focal, cx, cy, near
        self.f = _norm(_sub(look, eye))
        self.r = _norm(_cross(self.f, (0, 0, 1)))
        self.u = _cross(self.r, self.f)

    def to_cam(self, p):
        d = _sub(p, self.eye)
        return (_dot(d, self.r), _dot(d, self.u), _dot(d, self.f))

    def to_screen(self, c):
        return (self.cx + self.focal * c[0] / c[2], self.cy - self.focal * c[1] / c[2])


def broadcast_camera():
    p, st = CAM["broadcast"], CAM["stage"]
    el = math.radians(p["elev"])
    look = (0.0, p["lookY"], 0.0)
    eye = (0.0, p["lookY"] - p["dist"] * math.cos(el), p["dist"] * math.sin(el))
    cam = Camera(eye, look, 1.0, 0.0, 0.0)
    fx, fy, fz = p["fit"]["x"], p["fit"]["y"], p["fit"]["z"]
    pts = [cam.to_screen(cam.to_cam((x, y, z))) for x in fx for y in fy for z in fz]
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    pad = p["pad"]
    aw, ah = st["w"] - pad["left"] - pad["right"], st["h"] - pad["top"] - pad["bottom"]
    s = min(aw / (max(xs) - min(xs)), ah / (max(ys) - min(ys)))
    # 화면 좌표 = s·(u,v) + 오프셋 — 맞춘 상자를 가운데 정렬
    ox = pad["left"] + (aw - s * (max(xs) - min(xs))) / 2 - s * min(xs)
    oy = pad["top"] + (ah - s * (max(ys) - min(ys))) / 2 - s * min(ys)
    return Camera(eye, look, s, ox, oy)


def me_camera(me_xy):
    p, st = CAM["me"], CAM["stage"]
    mx, my, _ = world(*me_xy)
    eye = (mx, my - p["back"], p["height"])
    look = (mx * (1 - p["yawToCenter"]), my + p["ahead"], p["lookZ"])
    return Camera(eye, look, p["focal"] * st["h"], st["w"] / 2, p["cy"] * st["h"], p["near"])


def _clip_near(poly, near):
    out = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        ina, inb = a[2] >= near, b[2] >= near
        if ina:
            out.append(a)
        if ina != inb:
            t = (near - a[2]) / (b[2] - a[2])
            out.append(tuple(a[k] + (b[k] - a[k]) * t for k in range(3)))
    return out


def _clip_rect(poly, w, h):
    def clip(pts, inside, inter):
        out = []
        for i, a in enumerate(pts):
            b = pts[(i + 1) % len(pts)]
            if inside(a):
                out.append(a)
            if inside(a) != inside(b):
                out.append(inter(a, b))
        return out
    lerp = lambda a, b, t: (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    edges = [(lambda p: p[0] >= 0, lambda a, b: lerp(a, b, (0 - a[0]) / (b[0] - a[0]))),
             (lambda p: p[0] <= w, lambda a, b: lerp(a, b, (w - a[0]) / (b[0] - a[0]))),
             (lambda p: p[1] >= 0, lambda a, b: lerp(a, b, (0 - a[1]) / (b[1] - a[1]))),
             (lambda p: p[1] <= h, lambda a, b: lerp(a, b, (h - a[1]) / (b[1] - a[1])))]
    for inside, inter in edges:
        if not poly:
            break
        poly = clip(poly, inside, inter)
    return poly


def zone_quad(code):
    side, col, row = code[0], code[2], code[3]
    x0, x1 = COLS[col]
    y0, y1 = ROWS[side][row]
    return [world(x0, y0), world(x1, y0), world(x1, y1), world(x0, y1)]


def visible_area(cam, code):
    """존이 화면 안에서 차지하는 넓이(px²). 카메라 뒤·화면 밖은 잘라낸다."""
    st = CAM["stage"]
    poly = _clip_near([cam.to_cam(p) for p in zone_quad(code)], cam.near)
    if len(poly) < 3:
        return 0.0
    poly = _clip_rect([cam.to_screen(c) for c in poly], st["w"], st["h"])
    if len(poly) < 3:
        return 0.0
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly)))) / 2


if __name__ == "__main__":
    bc = broadcast_camera()
    print(f"중계 시점  scale={bc.focal:.1f}  eye={tuple(round(v, 1) for v in bc.eye)}")
    for code in ("A-CN", "A-RX", "E-LB", "E-LX", "E-CN"):
        print(f"  {code}  {visible_area(bc, code):7.0f} px²")
    mc = me_camera((0.30, 0.59))
    print("내 시점 (넷맨 왼쪽 네트 앞)")
    for code in ("A-LN", "A-CN", "A-LM", "E-LB", "E-RM", "E-CM"):
        print(f"  {code}  {visible_area(mc, code):7.0f} px²")
