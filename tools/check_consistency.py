#!/usr/bin/env python3
"""카드 데이터와 커리큘럼 인덱스가 어긋나지 않았는지 대조한다.
두 수 앞 짝(data/chains.json)이 정말 이어지는지도 본다."""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
idx = {c["id"]: c for c in json.loads(
    (ROOT / "data" / "cards-index.json").read_text(encoding="utf-8"))["cards"]}

bad, n, cards = [], 0, {}
for f in sorted((ROOT / "data" / "cards").glob("*.json")):
    for c in json.loads(f.read_text(encoding="utf-8"))["cards"]:
        n += 1
        cards[c["id"]] = c
        i = idx.get(c["id"])
        if not i:
            bad.append(f"{c['id']}: 커리큘럼 인덱스에 없는 카드"); continue
        for key, label in (("title", "제목"), ("myRole", "역할"),
                           ("difficulty", "난이도"), ("prereq", "선행")):
            if c[key] != i[key]:
                bad.append(f"{c['id']} {label}: 카드={c[key]!r} / 인덱스={i[key]!r}")
        if c["question"]["type"] != i["question"]:
            bad.append(f"{c['id']} 질문유형: 카드={c['question']['type']!r} / 인덱스={i['question']!r}")
        if c["answer"]["principle"] != i["principle"]:
            bad.append(f"{c['id']} 원칙: 카드={c['answer']['principle']!r} / 인덱스={i['principle']!r}")

# 두 수 앞 — 둘째 카드는 첫 카드의 다음 수(next)이고, 첫 카드 정답 장면은 포인트를 끝내지 않는다
pairs = json.loads((ROOT / "data" / "chains.json").read_text(encoding="utf-8"))["pairs"]
seen = set()
for a, b in pairs:
    tag = f"두 수 {a}→{b}"
    if a not in cards or b not in cards:
        bad.append(f"{tag}: 없는 카드"); continue
    if (a, b) in seen:
        bad.append(f"{tag}: 같은 짝이 두 번 있다")
    seen.add((a, b))
    if cards[a]["next"]["id"] != b:
        bad.append(f"{tag}: 첫 카드의 다음 수(next.id)가 {cards[a]['next']['id']} 다")
    last = cards[a]["answer"]["play"][-1]
    if last.get("winner") or last.get("call"):
        bad.append(f"{tag}: 첫 카드 정답 장면이 포인트를 끝낸다 — 둘째 카드로 이어질 수 없다")

print(f"인덱스 대조 — 카드 {n}장 / 인덱스 {len(idx)}장 · 두 수 앞 짝 {len(pairs)}개")
for b in bad:
    print("  ❌", b)
if bad:
    print(f"\n불일치 {len(bad)}건")
    sys.exit(1)
print("  ✅ 일치")
