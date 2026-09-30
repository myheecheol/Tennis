#!/usr/bin/env python3
"""검증기 회귀 테스트 — 실제로 났던 오류를 일부러 재현해, 검증기가 여전히 잡는지 확인한다.
검증기 규칙을 고치다 실수로 구멍을 내면 여기서 실패한다."""
import copy, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import validate_cards as V  # noqa: E402

base = {c["id"]: c for f in sorted((ROOT / "data" / "cards").glob("*.json"))
        for c in json.loads(f.read_text(encoding="utf-8"))["cards"]}


def set_(path, value):
    def f(c):
        o = c
        for k in path[:-1]:
            o = o[k]
        o[path[-1]] = value
    return f


def both(*fs):
    def f(c):
        for g in fs:
            g(c)
    return f


CASES = [
    # (설명, 카드, 변형, 오류 메시지에 있어야 할 말)
    ("서브를 베이스라인 안에서 넣는다 — 사용자가 찾은 버그", "C1-04",
     both(set_(["setup", "opp1", "xy"], [0.84, 0.04]), set_(["setup", "opp1", "zone"], "E-RB"),
          set_(["setup", "ball", "from"], [0.84, 0.04])), "베이스라인 안"),
    ("서브 방향이 뒤집혔다 — 첫 예시 카드의 버그", "C1-03",
     set_(["setup", "ball", "bounce"], [0.80, 0.27]), "대각선이 아니다"),
    ("서브가 서비스 박스 밖", "C1-03", set_(["setup", "ball", "bounce"], [0.30, 0.10]), "서비스 박스 밖"),
    ("아웃 지역(베이스라인 뒤)을 노리는 보기", "C1-08", set_(["distractors", 0, "zone"], "E-LX"), "아웃 지역"),
    ("공이 자기 코트에 바운드", "C1-13", set_(["setup", "ball", "bounce"], [0.48, 0.80]), "자기 코트"),
    ("장황한 해설", "C1-03", set_(["answer", "why"], "가" * 57), "해설이 길다"),
    ("설명 없는 전문 용어", "C1-13", set_(["scene"], "파트너가 투백으로 내려갔다."), "전문 용어"),
    ("베이스라인에서 보는 내 시점 — 먼 존이 너무 작다", "C1-12", set_(["view"], "me"), "내 시점에서 누르기 어려운"),
    ("정답과 오답이 같은 존", "C1-03", set_(["distractors", 0, "zone"], "A-CN"), "겹친다"),
    # 결과 장면 — 채점과 장면이 어긋나는 것을 막는다 (C1-07 의 요약·채점 모순과 같은 종류)
    ("실수를 골랐는데 포인트를 딴다", "C1-03",
     set_(["distractors", 1, "play"], [{"by": "me", "arc": "volley", "bounce": "E-CM", "winner": True}]),
     "결과가 채점과 안 맞는다"),
    ("정답을 골랐는데 포인트를 잃는다", "C1-03",
     set_(["answer", "play"], [{"by": "opp1", "arc": "normal", "bounce": "A-CM", "winner": True}]),
     "결과가 채점과 안 맞는다"),
    ("결과 장면의 공이 자기 코트에 바운드", "C1-03",
     set_(["answer", "play"], [{"by": "opp1", "arc": "normal", "bounce": "E-CM", "to": "me"}]),
     "자기 코트에 바운드"),
    ("공을 보내는 문제인데 내 공이 고른 존에 안 떨어진다", "C1-08",
     set_(["answer", "play"], [{"by": "me", "arc": "normal", "bounce": [0.84, 0.08]}]),
     "고른 존"),
    ("결과 한 줄이 길다", "C1-03", set_(["answer", "caption"], "가" * 13), "caption 이 길다"),
]

fail = 0
for desc, cid, mutate, expect in CASES:
    c = copy.deepcopy(base[cid])
    mutate(c)
    errs, warns, _ = V.check([c])
    hit = any(expect in m for m in errs + warns)
    fail += not hit
    print(f"  {'✅' if hit else '❌'} {desc}")
    if not hit:
        print(f"      기대: '{expect}' / 실제: {errs + warns}")
print(f"회귀 테스트 {len(CASES) - fail}/{len(CASES)} 통과")
sys.exit(1 if fail else 0)
