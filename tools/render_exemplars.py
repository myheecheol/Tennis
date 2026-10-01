#!/usr/bin/env python3
"""검증된 카드 데이터 → reference/card-exemplars.md (few-shot 앵커)
손으로 고치지 않는다. 카드가 바뀌면 예시도 따라 바뀐다."""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PICK = ["C1-03", "C2-08"]
BADGE = {"정답": "✅ 정답", "차선": "🟡 차선", "실수": "🔴 실수"}

cards = {}
for f in sorted((ROOT / "data" / "cards").glob("*.json")):
    for c in json.loads(f.read_text(encoding="utf-8"))["cards"]:
        cards[c["id"]] = c

L = []
w = L.append
w("# 상황 카드 완성 예시 (Few-shot 앵커)")
w("")
w("> 프롬프트에 **이 두 장을 통째로 넣으세요.** 설명 열 줄보다 완성본 한 장이 정확합니다.")
w(">")
w("> ⚙️ `data/cards/*.json` 에서 **생성**됩니다 (`tools/render_exemplars.py`). 손으로 고치지 마세요.")
w("> 실린 카드는 `tools/validate_cards.py` 를 통과한 것입니다.")
w("")

for n, cid in enumerate(PICK):
    c = cards[cid]
    opts = [(d["zone"], d["severity"], d["short"], d["why"]) for d in c["distractors"] if d["severity"] == "차선"]
    opts.append((c["answer"]["zone"], "정답", c["answer"]["short"], c["answer"]["why"]))
    opts += [(d["zone"], d["severity"], d["short"], d["why"]) for d in c["distractors"] if d["severity"] == "실수"]

    w("---")
    w("")
    w(f"## 예시 {chr(65 + n)} — {c['title']}")
    w("")
    w(f"`{c['id']}` · {c['myRole']} · 난이도 {c['difficulty']} · 질문 `{c['question']['type']}`")
    w("")
    w(f"> {c['scene']}  ")
    w(f"> 👀 {c['cue']}")
    w("")
    w(f"**{c['question']['text']}**")
    w("")
    w("| 보기 | 판정 | 한 줄 해설 |")
    w("|---|---|---|")
    for z, v, short, why in opts:
        w(f"| {short} `{z}` | {BADGE[v]} | {why} |")
    w("")
    w(f"> 💬 **{c['coachLine']}**  ")
    w(f"> 다음 → {c['next']['text']} (`{c['next']['id']}`)")
    w("")
    w("```json")
    w(json.dumps(c, ensure_ascii=False, indent=2))
    w("```")
    w("")

w("---")
w("")
w("## 좋은 카드의 조건")
w("")
w("1. **보기가 모두 실제로 코트에서 하는 선택이다.** 허수아비 보기는 학습 가치가 0이다")
w("2. **차선과 실수를 구분한다.** '왜 나쁜가'가 아니라 '얼마나 나쁜가'를 가르친다")
w("3. **조건이 붙어 있다.** '가운데는 좋다'가 아니라 '넷맨이 없을 때 좋다'")
w("4. **짧다.** 해설은 한 문장(56자), 보기는 14자, 한 줄 요약은 24자. 코트에서 기억나는 건 한 문장이다")
w("5. **단서는 눈에 보이는 것이다.** '백스윙이 늦다'는 보이고 '상대가 약하다'는 안 보인다")
w("6. **공의 길을 좌표로 적는다.** 친 곳(`from`)·바운드(`bounce`)·받는 곳(`to`)·궤적(`arc`) — 화면이 길고 짧음, 높고 낮음을 그린다")
w("7. **다음 수로 이어진다.** `next.id` 가 다음 카드를 가리킨다")
w("")
w("## 기계가 검사하는 것 (`tools/validate_cards.py`)")
w("")
w("- 서브는 **베이스라인 뒤**에서, **대각선 서비스 박스** 안으로 들어가는가")
w("- 공을 보내는 보기에 **아웃 지역(베이스라인 뒤)** 이 없는가")
w("- 공이 자기 코트에 바운드하지 않는가 / 친 곳 근처에 치는 선수가 있는가")
w("- 좌표가 존 안에 있는가 / 마커끼리 겹치지 않는가 / 정답·오답 존이 겹치지 않는가")
w("- 모든 존이 중계 화면에서 **손가락으로 누를 만큼** 보이는가")
w("- 글자 수 한도 / 설명 없이 쓴 전문 용어")
w("")

doc = "\n".join(L)
(ROOT / "reference" / "card-exemplars.md").write_text(doc, encoding="utf-8")
print(f"reference/card-exemplars.md  {len(doc):,} chars")
