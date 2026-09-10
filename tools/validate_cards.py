#!/usr/bin/env python3
"""상황 카드 검증기 — court-coordinates.md 규격과 복식 기하를 기계적으로 검사한다.
사람 눈으로는 매번 놓치는 오류(서브 방향 뒤집힘, 마커 겹침, 존 밖 좌표)를 잡는 게 목적."""
import json, sys, pathlib, collections, itertools

ROOT = pathlib.Path(__file__).resolve().parent.parent
COLS = {"L": (-0.15, 1/3), "C": (1/3, 2/3), "R": (2/3, 1.15)}
ROWS = {"A": {"N": (.500, .640), "M": (.640, .860), "B": (.860, 1.000), "X": (1.000, 1.098)},
        "E": {"N": (.360, .500), "M": (.140, .360), "B": (.000, .140), "X": (-.098, .000)}}
PRINCIPLES = {"P-01", "P-02", "P-03", "P-04", "P-05"}
SEVERITY = {"차선", "실수"}
MIN_GAP = 0.12          # 마커끼리 최소 거리
EPS = 1e-9


def zone_box(z):
    side, col, row = z[0], z[2], z[3]
    if side not in ROWS or col not in COLS or row not in ROWS[side]:
        return None
    x0, x1 = COLS[col]
    y0, y1 = ROWS[side][row]
    return x0, x1, y0, y1


def check(cards):
    errs, warns = [], []
    ans_zones = collections.Counter()

    for c in cards:
        cid = c.get("id", "?")

        def e(msg): errs.append(f"{cid}: {msg}")
        def w(msg): warns.append(f"{cid}: {msg}")

        # ── 스키마 ──
        for k in ("id", "chapter", "title", "difficulty", "myRole", "phase",
                  "setup", "scene", "cue", "question", "answer", "distractors", "coachLine"):
            if k not in c:
                e(f"필수 필드 누락: {k}")
        if errs and errs[-1].startswith(f"{cid}: 필수"):
            continue

        a, ds, q = c["answer"], c["distractors"], c["question"]
        ans_zones[a["zone"]] += 1

        # ── 보기 구성 ──
        for d in ds:
            if not d.get("short"):
                e(f"오답 {d.get('zone')} 에 보기 라벨(short)이 없다")
            elif len(d["short"]) > 26:
                w(f"오답 보기 라벨이 길다 ({len(d['short'])}자): {d['short']}")
        if len(ds) != 2:
            e(f"오답은 정확히 2개여야 한다 (현재 {len(ds)})")
        sev = sorted(d.get("severity") for d in ds)
        if sev != ["실수", "차선"]:
            e(f"오답 severity 는 차선 1 + 실수 1 이어야 한다 (현재 {sev})")
        zones = [a["zone"]] + [d["zone"] for d in ds]
        if len(set(zones)) != len(zones):
            e(f"정답/오답 존이 겹친다 {zones}")
        for z in zones:
            if zone_box(z) is None:
                e(f"알 수 없는 존 코드 {z}")

        # ── 원칙 ──
        if a.get("principle") not in PRINCIPLES:
            e(f"알 수 없는 원칙 {a.get('principle')}")

        # ── 질문 유형과 정답 코트 ──
        t = q.get("type")
        if t == "target" and not a["zone"].startswith("E-"):
            e("target 카드의 정답은 상대 코트(E-)여야 한다")
        if t == "move" and not a["zone"].startswith("A-"):
            e("move 카드의 정답은 우리 코트(A-)여야 한다")
        if t not in ("move", "target", "both", "readNext"):
            e(f"알 수 없는 질문 유형 {t}")

        # ── 좌표가 선언한 존 안에 있는가 ──
        s = c["setup"]
        for who in ("me", "partner", "opp1", "opp2"):
            m = s.get(who)
            if not m:
                e(f"setup.{who} 누락"); continue
            b = zone_box(m["zone"])
            if b is None:
                e(f"setup.{who} 존 코드 이상 {m['zone']}"); continue
            x, y = m["xy"]
            x0, x1, y0, y1 = b
            if not (x0 - EPS <= x <= x1 + EPS and y0 - EPS <= y <= y1 + EPS):
                e(f"setup.{who} 좌표 {m['xy']} 가 존 {m['zone']} 밖")

        # ── 마커끼리 겹치지 않는가 ──
        pts = {k: s[k]["xy"] for k in ("me", "partner", "opp1", "opp2") if k in s}
        for k1, k2 in itertools.combinations(pts, 2):
            (x1, y1), (x2, y2) = pts[k1], pts[k2]
            d = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** .5
            if d < MIN_GAP:
                e(f"{k1}·{k2} 가 너무 가깝다 ({d:.3f} < {MIN_GAP})")

        # ── 같은 팀은 네트를 사이에 두고 갈라지지 않는다 ──
        if s["me"]["xy"][1] < .5 or s["partner"]["xy"][1] < .5:
            e("우리 팀 마커가 상대 코트(y<0.5)에 있다")
        if s["opp1"]["xy"][1] > .5 or s["opp2"]["xy"][1] > .5:
            e("상대 마커가 우리 코트(y>0.5)에 있다")

        # ── 서브는 대각선으로 간다 ──
        ball = s.get("ball", {})
        if "서브" in ball.get("kind", "") and len(ball.get("path", [])) >= 2:
            (sx, sy), (lx, ly) = ball["path"][0], ball["path"][-1]
            if (sx - .5) * (lx - .5) > 0:
                e(f"서브가 대각선이 아니다: 출발 x={sx} 착지 x={lx} (센터 0.5 기준 같은 쪽)")
            server = "partner" if c["myRole"] == "넷맨" else ("me" if c["myRole"] == "서버" else None)
            if server and abs(s[server]["xy"][0] - sx) > .06:
                e(f"서브 출발점이 {server} 위치와 다르다 ({sx} vs {s[server]['xy'][0]})")

        # ── 원업원백이면 두 사람은 센터 기준 반대 반쪽 ──
        if c["myRole"] in ("서버", "넷맨"):
            mx, pxx = s["me"]["xy"][0], s["partner"]["xy"][0]
            if (mx - .5) * (pxx - .5) > 0:
                w(f"서버와 넷맨이 같은 반쪽에 있다 (me x={mx}, partner x={pxx})")

        # ── 단서는 관찰 가능해야 한다 ──
        for bad in ("약하다", "긴장", "분위기", "잘한다", "실력"):
            if bad in c["cue"]:
                w(f"cue 에 관찰 불가능한 표현: '{bad}'")
        if len(c["cue"]) > 70:
            w(f"cue 가 길다 ({len(c['cue'])}자) — 단서는 1~2개만")
        if len(c["coachLine"]) > 40:
            w(f"coachLine 이 길다 ({len(c['coachLine'])}자)")

    # ── 배치 전체 다양성 ── (배치가 커지면 한도도 함께 커진다)
    limit = 3 if len(cards) <= 10 else max(3, round(len(cards) * 0.2))
    for z, n in ans_zones.items():
        if n >= limit:
            warns.append(f"정답 존 {z} 이 {n}장에서 반복된다 (한도 {limit})")
    return errs, warns


def main(paths):
    cards = []
    for p in paths:
        d = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
        cards += d["cards"] if isinstance(d, dict) else d
    errs, warns = check(cards)
    print(f"검사 대상 {len(cards)}장")
    for wmsg in warns:
        print(f"  ⚠️  {wmsg}")
    if errs:
        for emsg in errs:
            print(f"  ❌ {emsg}")
        print(f"\n실패: 오류 {len(errs)}건, 경고 {len(warns)}건")
        return 1
    print(f"✅ 통과 — 오류 0건, 경고 {len(warns)}건")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or [ROOT / "data" / "cards" / "c1.json"]))
