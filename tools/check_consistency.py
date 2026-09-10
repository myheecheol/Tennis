#!/usr/bin/env python3
"""카드 데이터와 커리큘럼 인덱스가 어긋나지 않았는지 대조한다."""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
idx = {c["id"]: c for c in json.loads(
    (ROOT / "data" / "cards-index.json").read_text(encoding="utf-8"))["cards"]}

bad, n = [], 0
for f in sorted((ROOT / "data" / "cards").glob("*.json")):
    for c in json.loads(f.read_text(encoding="utf-8"))["cards"]:
        n += 1
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

print(f"인덱스 대조 — 카드 {n}장 / 인덱스 {len(idx)}장")
for b in bad:
    print("  ❌", b)
if bad:
    print(f"\n불일치 {len(bad)}건")
    sys.exit(1)
print("  ✅ 일치")
