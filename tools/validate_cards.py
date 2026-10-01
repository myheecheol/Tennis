#!/usr/bin/env python3
"""상황 카드 검증기 — 사람 눈으로 매번 놓치는 오류를 기계로 잡는다.

지금까지 실제로 잡은 것:
  · 서브 방향이 뒤집힌 카드 (서버는 왼쪽인데 공은 상대 오른쪽 박스로)
  · 서브를 베이스라인 안쪽에서 넣는 카드 11장
  · 베이스라인 뒤(아웃)를 '로브 착지점'으로 쓴 보기
  · 설명 없이 쓴 전문 용어
"""
import json, sys, pathlib, collections, itertools, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import court3d  # noqa: E402

# 선수 위치 검사용 — 바깥 열은 사이드라인 밖으로 끌려나간 선수까지 받는다
COLS = {"L": (-0.15, 1 / 3), "C": (1 / 3, 2 / 3), "R": (2 / 3, 1.15)}
ROWS = court3d.ROWS
PRINCIPLES = {"P-01", "P-02", "P-03", "P-04", "P-05"}
ARCS = {"hold", "serve", "serve2", "flat", "normal", "high", "lob", "volley", "smash"}
SERVE_ARCS = {"serve", "serve2"}
REVEALS = {"move", "shot", "oppShot", "look"}
MIN_GAP = 0.12        # 마커끼리 최소 거리
MIN_TAP = 1100        # 누를 수 있는 존의 최소 화면 넓이(px²) — 약 33×33px
EPS = 1e-9

# 간결함 한도 (글자 수) — 넘치면 오류. 해설은 한 문장.
LIMITS = {"title": 20, "scene": 38, "cue": 26, "question": 14,
          "short": 14, "why": 56, "coachLine": 24, "next": 18}

# 초보자가 모르는 말. 괄호로 풀어 쓰거나, 그 카드가 가르치는 개념(tags)이어야 한다.
# 크로스·발리·슬라이스·로브·스매시는 레슨에서 매번 듣는 기본 어휘라 제외한다.
JARGON = ["듀스 코트", "애드 코트", "서브앤발리", "스플릿 스텝", "노맨스랜드",
          "다운더라인", "원업원백", "투업", "투백", "앵글", "포치", "스위치"]

# 말투 — 해요체. 코치가 코트 옆에서 존댓말로 짧게 말한다.
# 해라체·반말 어미(-다 · -까? · -냐 · -니 · -라 · -자)로 끝나는 문장은 거부한다.
# 명사로 끝나는 짧은 문장("빠른 퍼스트 서브.")과 보기 라벨("-기")은 괜찮다.
BANMAL_END = re.compile(r"(다|까|냐|니|라|자)$")
NOUN_END_OK = re.compile(r"(숫자|혼자|남자|여자|의자|상자)$")


def banmal(text):
    """해라체·반말로 끝나는 문장을 돌려준다."""
    bad = []
    for sent in re.split(r"(?<=[.!?…])\s+", text.strip()):
        core = re.sub(r"[\s.,!?…'\"“”‘’)\]]+$", "", sent)
        if core and BANMAL_END.search(core) and not NOUN_END_OK.search(core):
            bad.append(sent)
    return bad


INDEX = {c["id"] for c in json.loads(
    (ROOT / "data" / "cards-index.json").read_text(encoding="utf-8"))["cards"]}


def zone_box(z):
    try:
        side, col, row = z[0], z[2], z[3]
        return (*COLS[col], *ROWS[side][row])
    except (KeyError, IndexError):
        return None


def in_zone(xy, z):
    b = zone_box(z)
    x, y = xy
    return b and b[0] - EPS <= x <= b[1] + EPS and b[2] - EPS <= y <= b[3] + EPS


def dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** .5


PLAYERS = ("me", "partner", "opp1", "opp2")
CALLS = {"풋폴트", "폴트", "아웃", "네트"}
ZONE_CENTER_ROWS = {"A": {"N": .57, "M": .75, "B": .93, "X": 1.049},
                    "E": {"N": .43, "M": .25, "B": .07, "X": -.049}}
MOVE_TYPES = ("move", "both")


def zone_center(z):
    return [{"L": 1 / 6, "C": .5, "R": 5 / 6}[z[2]], ZONE_CENTER_ROWS[z[0]][z[3]]]


def resolve(v, pos):
    """존 코드 · 선수 이름 · 좌표를 좌표로"""
    if isinstance(v, list):
        return v
    if v in PLAYERS:
        return list(pos[v])
    return zone_center(v)


def check_play(c, o, severity, e):
    """보기 하나의 결과 장면이 채점과 맞는지, 공이 말이 되는지 — 엔진과 같은 순서로 따라간다."""
    tag = f"[{severity} {o['zone']}]"
    if not o.get("caption"):
        e(f"{tag} 결과 한 줄(caption)이 없다"); return
    if len(o["caption"]) > 12:
        e(f"{tag} caption 이 길다 ({len(o['caption'])}자 > 12): {o['caption']}")
    play = o.get("play") or []
    if not 1 <= len(play) <= 4:
        e(f"{tag} 결과 장면의 공은 1~4개여야 한다 (현재 {len(play)})"); return

    s_ = c["setup"]
    pos = {k: list(s_[k]["xy"]) for k in PLAYERS}
    t = c["question"]["type"]
    rv = c["answer"].get("reveal", {}).get("type")
    moving = t in MOVE_TYPES or (t == "readNext" and rv in ("move", "oppShot"))

    # 0단계 — 내가 먼저 움직인다
    if "moves" in o:
        for k, xy in o["moves"].items():
            pos[k] = list(xy)
    elif moving:
        if "stand" in o:
            if not in_zone(o["stand"], o["zone"]):
                e(f"{tag} stand {o['stand']} 가 고른 존 {o['zone']} 밖이다")
            pos["me"] = list(o["stand"])
        elif not in_zone(pos["me"], o["zone"]):
            pos["me"] = zone_center(o["zone"])

    b0 = s_["ball"]
    if b0["arc"] == "hold":
        cur = {"pt": b0["from"], "state": "hold"}
    elif "to" in b0:
        cur = {"pt": b0["to"], "state": "air"}
    else:
        cur = {"pt": b0["bounce"], "state": "ground"}

    if t == "target" and play[0].get("by") != "me":
        e(f"{tag} 공을 보내는 문제는 첫 공을 내가 친다")

    for k, b in enumerate(play):
        by = b.get("by")
        if by not in PLAYERS + ("none",):
            e(f"{tag} 공{k + 1}: 알 수 없는 by {by}"); return
        if b.get("arc") not in ARCS - {"hold"}:
            e(f"{tag} 공{k + 1}: 알 수 없는 arc {b.get('arc')}")
        if "call" in b and b["call"] not in CALLS:
            e(f"{tag} 공{k + 1}: 알 수 없는 call {b['call']}")
        if "reach" in b and b["reach"] not in PLAYERS:
            e(f"{tag} 공{k + 1}: 알 수 없는 reach {b['reach']}")
        for key in ("bounce", "to"):
            v = b.get(key)
            if isinstance(v, str) and v not in PLAYERS and zone_box(v) is None:
                e(f"{tag} 공{k + 1}: {key} 를 알 수 없다 ({v})")

        # 출발점 — 엔진과 같은 규칙
        if "from" in b:
            start = b["from"]
        elif by == "none" or cur["state"] == "air":
            start = cur["pt"]
        else:
            start = pos[by]
        if by != "none":
            run = ((pos[by][0] - start[0]) * 10.97) ** 2 + ((pos[by][1] - start[1]) * 23.77) ** 2
            if run ** .5 > 9.0:
                e(f"{tag} 공{k + 1}: {by} 가 치러 가기엔 너무 멀다 ({run ** .5:.1f}m)")
            pos[by] = list(start)

        call = b.get("call")
        bo = resolve(b["bounce"], pos) if "bounce" in b else None
        if bo and by != "none":
            if (start[1] - .5) * (bo[1] - .5) > 0:
                e(f"{tag} 공{k + 1}: 자기 코트에 바운드한다 (출발 y={start[1]:.2f}, 바운드 y={bo[1]:.2f})")
        if bo:
            inside = -EPS <= bo[0] <= 1 + EPS and -EPS <= bo[1] <= 1 + EPS
            if call == "아웃" and inside:
                e(f"{tag} 공{k + 1}: 아웃인데 바운드가 코트 안이다")
            if call != "아웃" and not inside:
                e(f"{tag} 공{k + 1}: 바운드 {bo} 가 코트 밖이다")
        if b.get("arc") in SERVE_ARCS:
            behind = start[1] > 1.0 if start[1] > .5 else start[1] < 0.0
            if not behind and call != "풋폴트":
                e(f"{tag} 공{k + 1}: 서브를 베이스라인 안에서 넣는다")
            if bo and call != "폴트":
                ok_x = 0.111 <= bo[0] <= 0.889 and (start[0] - .5) * (bo[0] - .5) < 0
                ok_y = (0.223 <= bo[1] <= .5) if bo[1] < .5 else (.5 <= bo[1] <= 0.777)
                if not (ok_x and ok_y):
                    e(f"{tag} 공{k + 1}: 서브가 대각선 서비스 박스에 안 들어간다")
        if t == "target" and k == 0 and bo and not call and not in_zone(bo, o["zone"]):
            e(f"{tag} 내 공이 고른 존 {o['zone']} 에 떨어지지 않는다 ({bo})")

        # 공이 끝나는 곳과 받는 사람
        if "to" in b:
            end = resolve(b["to"], pos)
            if isinstance(b["to"], list):
                catcher = b.get("reach") or (play[k + 1]["by"] if k + 1 < len(play) and play[k + 1]["by"] != "none" else None)
                if catcher:
                    pos[catcher] = list(end)
            cur = {"pt": end, "state": "air"}
        elif bo:
            cur = {"pt": bo, "state": "ground"}

    # 결과 — 마지막 공으로 판정
    last = play[-1]
    by, call, win = last["by"], last.get("call"), last.get("winner")
    ours = by in ("me", "partner")
    if call:
        result = "lost" if ours else "won"
    elif win:
        if by == "none":
            result = "lost" if cur["pt"][1] > .5 else "won"
        else:
            result = "won" if ours else "lost"
    else:
        result = "play"
    want = {"정답": "won 이거나 우리가 마지막에 친다", "차선": "랠리가 이어진다", "실수": "포인트를 잃는다"}[severity]
    ok = ((severity == "실수" and result == "lost")
          or (severity == "차선" and result == "play")
          or (severity == "정답" and (result == "won" or (result == "play" and ours))))
    if not ok:
        e(f"{tag} 결과가 채점과 안 맞는다 — 장면 결과 '{result}', 기대: {want}")


def check(cards):
    errs, warns = [], []
    ans_zones = collections.Counter()
    bc = court3d.broadcast_camera()

    for c in cards:
        cid = c.get("id", "?")
        def e(m): errs.append(f"{cid}: {m}")
        def w(m): warns.append(f"{cid}: {m}")

        need = ("id", "chapter", "title", "difficulty", "myRole", "phase", "setup",
                "scene", "cue", "question", "answer", "distractors", "coachLine", "next")
        miss = [k for k in need if k not in c]
        if miss:
            e(f"필수 필드 누락: {', '.join(miss)}"); continue

        a, ds, q, s = c["answer"], c["distractors"], c["question"], c["setup"]
        ans_zones[a["zone"]] += 1

        # ── 간결함 ──
        texts = {"title": c["title"], "scene": c["scene"], "cue": c["cue"],
                 "question": q["text"], "coachLine": c["coachLine"], "next": c["next"].get("text", "")}
        for k, v in texts.items():
            if len(v) > LIMITS[k]:
                e(f"{k} 가 길다 ({len(v)}자 > {LIMITS[k]}): {v}")
        for label, o in [("정답", a)] + [(d.get("severity", "?"), d) for d in ds]:
            if len(o.get("short", "")) > LIMITS["short"]:
                e(f"{label} 보기 라벨이 길다 ({len(o['short'])}자 > {LIMITS['short']}): {o['short']}")
            if len(o.get("why", "")) > LIMITS["why"]:
                e(f"{label} 해설이 길다 ({len(o['why'])}자 > {LIMITS['why']})")
            if not o.get("short"):
                e(f"{label} 보기 라벨(short)이 없다")

        # ── 말투 (해요체) ──
        spoken = dict(texts)
        for label, o in [("정답", a)] + [(d.get("severity", "?"), d) for d in ds]:
            for k in ("short", "why", "caption"):
                spoken[f"{label}.{k}"] = o.get(k, "")
        for k, v in spoken.items():
            for sent in banmal(v):
                e(f"{k} 반말 어미 — 해요체로: {sent}")

        # ── 다음 수 ──
        if c["next"].get("id") not in INDEX:
            e(f"next.id 가 커리큘럼에 없다: {c['next'].get('id')}")

        # ── 보기 구성 ──
        if len(ds) != 2:
            e(f"오답은 정확히 2개여야 한다 (현재 {len(ds)})")
        if sorted(d.get("severity") for d in ds) != ["실수", "차선"]:
            e("오답 severity 는 차선 1 + 실수 1 이어야 한다")
        zones = [a["zone"]] + [d["zone"] for d in ds]
        if len(set(zones)) != len(zones):
            e(f"정답/오답 존이 겹친다 {zones}")
        for z in zones:
            if zone_box(z) is None:
                e(f"알 수 없는 존 코드 {z}")
        if a.get("principle") not in PRINCIPLES:
            e(f"알 수 없는 원칙 {a.get('principle')}")

        # ── 질문 유형 ──
        t = q.get("type")
        if t not in ("move", "target", "both", "readNext"):
            e(f"알 수 없는 질문 유형 {t}")
        if t == "target":
            if not a["zone"].startswith("E-"):
                e("target 카드의 정답은 상대 코트(E-)여야 한다")
            # 베이스라인 뒤(X)는 선수가 서는 곳이다 — 공이 떨어지면 아웃
            outs = [z for z in zones if z.endswith("X")]
            if outs:
                e(f"공을 보내는 보기에 아웃 지역(베이스라인 뒤)이 있다: {outs}")
        if t in ("move", "both") and not a["zone"].startswith("A-"):
            e(f"{t} 카드의 정답은 우리 코트(A-)여야 한다")
        rv = a.get("reveal", {}).get("type")
        if t == "readNext" and not rv:
            e("readNext 카드는 answer.reveal 로 정답 연출을 정해야 한다")
        if rv and rv not in REVEALS:
            e(f"알 수 없는 reveal {rv}")
        if rv in ("oppShot", "look") and a["reveal"].get("by") not in ("opp1", "opp2"):
            e("oppShot/look reveal 은 by: opp1|opp2 가 필요하다")

        # ── 선수 좌표 ──
        players = {}
        for who in ("me", "partner", "opp1", "opp2"):
            m = s.get(who)
            if not m:
                e(f"setup.{who} 누락"); continue
            players[who] = m["xy"]
            if zone_box(m["zone"]) is None:
                e(f"setup.{who} 존 코드 이상 {m['zone']}")
            elif not in_zone(m["xy"], m["zone"]):
                e(f"setup.{who} 좌표 {m['xy']} 가 존 {m['zone']} 밖")
        for k1, k2 in itertools.combinations(players, 2):
            d = dist(players[k1], players[k2])
            if d < MIN_GAP:
                e(f"{k1}·{k2} 가 너무 가깝다 ({d:.3f} < {MIN_GAP})")
        if players["me"][1] < .5 or players["partner"][1] < .5:
            e("우리 팀 마커가 상대 코트에 있다")
        if players["opp1"][1] > .5 or players["opp2"][1] > .5:
            e("상대 마커가 우리 코트에 있다")

        # ── 공 ──
        b = s.get("ball", {})
        arc = b.get("arc")
        if arc not in ARCS:
            e(f"알 수 없는 arc {arc}")
        fr = b.get("from")
        hitter = min(players, key=lambda k: dist(players[k], fr)) if fr else None
        if not fr:
            e("ball.from 이 없다")
        elif dist(players[hitter], fr) > 0.06:
            e(f"ball.from {fr} 근처에 치는 선수가 없다")
        if arc == "hold":
            if "bounce" in b or "to" in b:
                e("hold(서브 준비) 공은 from 만 가진다")
        elif "bounce" not in b and "to" not in b:
            e("날아가는 공은 bounce 나 to 가 있어야 한다")
        bo = b.get("bounce")
        if bo and fr:
            if not (0 - EPS <= bo[0] <= 1 + EPS and 0 - EPS <= bo[1] <= 1 + EPS):
                e(f"바운드 {bo} 가 코트 밖이다 (아웃)")
            if (fr[1] - .5) * (bo[1] - .5) > 0:
                e(f"공이 자기 코트에 바운드한다 (from y={fr[1]}, bounce y={bo[1]})")

        # ── 서브는 베이스라인 뒤에서, 대각선 서비스 박스로 ──
        is_serve = arc in SERVE_ARCS or b.get("kind", "").startswith("서브")
        if is_serve and fr and hitter:
            hy = players[hitter][1]
            behind = hy > 1.0 if hy > .5 else hy < 0.0
            if not behind:
                e(f"서브를 베이스라인 안에서 넣는다 ({hitter} y={hy}) — 서버는 라인 뒤에 선다")
            if (hitter in ("me", "partner")) != (hy > .5):
                e("서버가 자기 코트 쪽에 있지 않다")
        if arc in SERVE_ARCS and bo and fr:
            if (fr[0] - .5) * (bo[0] - .5) >= 0:
                e(f"서브가 대각선이 아니다: 출발 x={fr[0]} 바운드 x={bo[0]}")
            in_box_x = 0.111 <= bo[0] <= 0.889
            in_box_y = (0.223 <= bo[1] <= .5) if bo[1] < .5 else (.5 <= bo[1] <= 0.777)
            if not (in_box_x and in_box_y):
                e(f"서브 바운드 {bo} 가 서비스 박스 밖이다 (폴트)")
            server = {"넷맨": "partner", "서버": "me"}.get(c["myRole"])
            if server and hitter != server:
                e(f"{c['myRole']} 카드인데 서브를 {hitter} 가 넣는다")

        # ── 보기마다 결과 장면이 채점과 맞는가 ──
        check_play(c, a, "정답", e)
        for d in ds:
            check_play(c, d, d.get("severity", "?"), e)

        # ── 원업원백이면 서버와 넷맨은 반대 반쪽 ──
        if c["myRole"] in ("서버", "넷맨"):
            if (players["me"][0] - .5) * (players["partner"][0] - .5) > 0:
                w("서버와 넷맨이 같은 반쪽에 있다")

        # ── 시점은 중계 하나 (PRD 결정 #20) · 존이 화면에서 누를 만큼 보이는가 ──
        if "view" in c:
            e("시점은 중계 하나다 — view 를 지운다")
        for z in zones:
            ar = court3d.visible_area(bc, z)
            if ar < MIN_TAP:
                e(f"중계 시점에서 존 {z} 가 너무 작다 ({ar:.0f}px²)")

        # ── 초보자가 모르는 말 ──
        body = " ".join([c["scene"], c["cue"], a["short"], a["why"], c["coachLine"]]
                        + [d["short"] + " " + d["why"] for d in ds]).replace(" (", "(")
        for term in JARGON:
            if term in body and (term + "(") not in body and ("(" + term + ")") not in body \
                    and not any(term in tg for tg in c.get("tags", [])):
                w(f"설명 없이 쓴 전문 용어: '{term}'")
        for bad in ("약하", "약해", "긴장", "분위기", "잘하", "잘해", "실력"):
            if bad in c["cue"]:
                w(f"cue 에 관찰 불가능한 표현: '{bad}'")

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
    for m in warns:
        print(f"  ⚠️  {m}")
    for m in errs:
        print(f"  ❌ {m}")
    if errs:
        print(f"\n실패: 오류 {len(errs)}건, 경고 {len(warns)}건")
        return 1
    print(f"✅ 통과 — 오류 0건, 경고 {len(warns)}건")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or sorted(str(p) for p in (ROOT / "data" / "cards").glob("*.json"))))
