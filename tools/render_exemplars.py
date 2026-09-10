#!/usr/bin/env python3
"""검증된 카드 데이터 → reference/card-exemplars.md (few-shot 앵커)
손으로 고치지 않는다. 카드가 바뀌면 예시도 따라 바뀐다."""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PICK = ["C1-03", "C2-08"]
BADGE = {"정답": "✅ **정답**", "차선": "🟡 **차선**", "실수": "🔴 **실수**"}
KEYS = "ABC"

cards = {}
for f in sorted((ROOT / "data" / "cards").glob("*.json")):
    for c in json.loads(f.read_text(encoding="utf-8"))["cards"]:
        cards[c["id"]] = c

L = []
w = L.append
w("# 상황 카드 완성 예시 (Few-shot 앵커)")
w("")
w("> 프롬프트에 **이 두 장을 통째로 넣으세요.** 설명 열 줄보다 완성본 한 장이 정확합니다.")
w("> AI는 \"형식\"보다 \"예시의 밀도\"를 따라갑니다.")
w(">")
w("> ⚙️ 이 문서는 `data/cards/*.json` 에서 **생성**됩니다 (`tools/render_exemplars.py`).")
w("> 손으로 고치지 마세요 — 카드 데이터를 고치고 다시 생성합니다.")
w("> 실린 카드는 `tools/validate_cards.py` 를 통과한 것입니다.")
w("")

for n, cid in enumerate(PICK):
    c = cards[cid]
    # 보기 순서: 차선 → 정답 → 실수
    opts = []
    for d in c["distractors"]:
        if d["severity"] == "차선":
            opts.append((d["zone"], "차선", d["short"], d["why"]))
    opts.append((c["answer"]["zone"], "정답", c["answer"]["short"], c["answer"]["why"]))
    for d in c["distractors"]:
        if d["severity"] == "실수":
            opts.append((d["zone"], "실수", d["short"], d["why"]))

    w("---")
    w("")
    w(f"## 예시 {chr(65+n)} — {c['title']} (질문 유형: `{c['question']['type']}`)")
    w("")
    w("### 사람이 보는 화면")
    w("")
    w(f"**상황 ({c['id']} · 난이도 {c['difficulty']} · 내 역할: {c['myRole']})**")
    w("")
    w(c["scene"])
    w("")
    w(f"> 👀 **단서** — {c['cue']}")
    w("")
    w(f"> 🎾 **{c['question']['text']}**")
    w("")
    w("| | 선택지 | 결과 |")
    w("|---|---|---|")
    for i, (z, v, short, why) in enumerate(opts):
        # 보기 라벨이 해설 첫 문장과 겹치면 해설에서 덜어낸다
        if why.startswith(short + "."):
            why = why[len(short) + 1:].lstrip()
        cell = BADGE[v] if v == "정답" else f"{BADGE[v]} — {why}"
        w(f"| {KEYS[i]} | `{z}` {short} | {cell} |")
    w("")
    ai = next(i for i, o in enumerate(opts) if o[1] == "정답")
    w(f"**왜 {KEYS[ai]}인가**")
    w("")
    w(c["answer"]["why"])
    w("")
    w("> 💬 **한 줄로 기억하기**")
    w(f"> {c['coachLine']}")
    w("")
    w(f"**연결** → {c['nextBeat']}")
    w("")
    w("### 데이터")
    w("")
    w("```json")
    w(json.dumps(c, ensure_ascii=False, indent=2))
    w("```")
    w("")

w("---")
w("")
w("## 이 예시가 담고 있는 \"좋은 카드\"의 조건")
w("")
w("프롬프트에서 이 조건을 명시적으로 요구하세요.")
w("")
w("1. **오답이 매력적이다.** 세 보기 모두 실제로 코트에서 사람들이 하는 선택입니다.")
w("2. **차선과 실수를 구분한다.** \"왜 나쁜가\"가 아니라 \"얼마나 나쁜가\"를 가르칩니다.")
w("3. **조건이 붙어 있다.** \"가운데는 좋다\"가 아니라 \"넷맨이 없을 때 좋다\".")
w("   → 초보자가 규칙을 **오적용**하는 걸 막는 게 진짜 교육입니다.")
w("4. **단서(cue)가 관찰 가능하다.** \"라켓 준비가 늦다\"는 눈으로 보입니다. \"상대가 약하다\"는 안 보입니다.")
w("5. **상황(scene)과 단서(cue)가 분리돼 있다.** 상황은 배경, 단서는 *읽어야 할 것*입니다.")
w("6. **다음 수로 이어진다.** 한 장으로 끝나지 않고 랠리로 연결됩니다.")
w("7. **한 줄 요약이 코트에서 떠오른다.** 실전에서 기억나는 건 문장 하나입니다.")
w("")
w("## 기계로 검사되는 것 (`tools/validate_cards.py`)")
w("")
w("사람 눈으로는 매번 놓치는 종류입니다. 실제로 이 검사에서 **서브 방향이 뒤집힌 카드**가 잡혔습니다.")
w("")
w("- 서브는 센터 기준 대각선으로 가는가 / 서브 출발점이 서버 위치와 같은가")
w("- 서버와 넷맨이 센터 기준 반대 반쪽에 서 있는가")
w("- 좌표가 선언한 존 안에 있는가 / 마커끼리 0.12 이상 떨어져 있는가")
w("- 정답과 오답 존이 겹치지 않는가 / 오답이 차선 1 + 실수 1 인가")
w("- `target` 정답이 상대 코트(`E-`)인가, `move` 정답이 우리 코트(`A-`)인가")
w("- 한 배치에서 같은 정답 존이 과하게 반복되지 않는가")
w("")

doc = "\n".join(L)
(ROOT / "reference" / "card-exemplars.md").write_text(doc, encoding="utf-8")
print(f"reference/card-exemplars.md  {len(doc):,} chars")
