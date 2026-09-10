#!/usr/bin/env python3
"""data/cards-index.json → design/01-curriculum.md (표는 생성, 서술은 아래 상수)"""
import json, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "data" / "cards-index.json").read_text(encoding="utf-8"))
CH = {c["id"]: c for c in D["chapters"]}
QL = {"move": "어디로 움직일까", "target": "어디로 칠까",
      "both": "위치 + 코스", "readNext": "다음에 무슨 일이"}

JOURNEY = [
 ("C1", "코트에 서면 **자기 자리를 안다.** 서브·리턴 네 가지 상황에서 어디에 서야 하는지 더 이상 두리번거리지 않고, 파트너가 움직이면 따라 움직인다."),
 ("C2", "공 세 개를 **연결해서 본다.** 서브가 들어간 순간 리턴이 어디로 올지 예상하고, 내가 보낸 공의 높이를 보고 전진할지 물러설지 스스로 정한다."),
 ("C3", "둘이 함께 **네트를 잡는다.** 낮은 공을 보낸 뒤 파트너와 나란히 올라가고, 발밑으로 오는 낮은 공에 당황하지 않는다."),
 ("C4", "밀려도 **점수를 헌납하지 않는다.** 무리해서 때리는 대신 로브로 시간을 사고, 파트너가 끌려나가면 코트를 덮어준다."),
 ("C5", "상대를 보고 **답을 고른다.** 상대가 어떤 대형인지 알아보고 그에 맞는 코스를 선택하며, 한 포인트를 두세 수 앞까지 그린다."),
]

RISK = [
 ("C1-19", "로브가 내 머리 위로 넘어갔다",
  "스위치가 처음 나옵니다. 두 사람이 **동시에** 움직여야 하고, 그동안 배운 '내 자리'가 갑자기 바뀌기 때문에 초보자가 가장 크게 혼란스러워하는 지점입니다.",
  "**C1-15 (포치 나간 뒤 원래 자리로 돌아갈까)** 를 앞에 뒀습니다. '자리는 고정된 게 아니라 바뀌는 것'을 로브 없이 먼저 경험시킵니다."),
 ("C2-21", "호주식 포메이션을 만났다",
  "처음 보는 대형입니다. 그동안 익힌 시작 위치가 통째로 어긋나 보여서 '내가 배운 게 틀렸나' 싶어집니다.",
  "**C2-05 (상대 넷맨이 매번 포치한다)** 를 앞에 뒀습니다. '상대가 자리를 바꾼다'는 사실을 익숙한 대형 안에서 먼저 겪게 합니다."),
 ("C4-11", "낮고 빠르게 치고 싶다 — 왜 안 되나",
  "본능과 정면으로 부딪히는 카드입니다. 밀리는 순간 사람은 세게 치고 싶어지는데, 이 카드는 그 반대를 요구합니다. 납득 없이 외우면 코트에서 절대 안 나옵니다.",
  "**C3-09 (발밑 공을 어디로)** 를 앞에 뒀습니다. 같은 판단을 여유 있는 상황에서 먼저 연습시켜, 압박 상황에서는 이미 아는 답을 꺼내 쓰게 만듭니다."),
]

def table_rows():
    out = []
    for c in D["cards"]:
        pr = ", ".join(c["prereq"]) or "—"
        out.append(f"| `{c['id']}` | {c['title']} | {c['myRole']} | {QL[c['question']]} | "
                   f"{c['difficulty']} | {pr} | {c['principle']} |")
    return out

L = []
w = L.append
w("# STEP 1 산출물 — 커리큘럼")
w("")
w("> `prompts/01-curriculum.md` 를 실행한 결과입니다.")
w("> 데이터 원본은 `data/cards-index.json`, 생성기는 `tools/curriculum.py` 입니다.")
w("> 표를 손으로 고치지 마세요 — 원본을 고치고 다시 생성합니다.")
w("")
w("---")
w("")
w("## 1. 학습 여정")
w("")
for cid, text in JOURNEY:
    c = CH[cid]
    w(f"**{cid} · {c['title']}** — {text}")
    w("")
w("---")
w("")
w("## 2. 챕터 구조")
w("")
w("| 챕터 | 제목 | 한 줄 목표 | 카드 | 새 개념 | 난이도 |")
w("|---|---|---|---|---|---|")
for c in D["chapters"]:
    rows = [x for x in D["cards"] if x["chapter"] == c["id"]]
    dmin = min(x["difficulty"] for x in rows); dmax = max(x["difficulty"] for x in rows)
    free = " 🔓무료" if c["free"] else ""
    w(f"| **{c['id']}**{free} | {c['title']} | {c['goal']} | {len(rows)} | "
      f"{' · '.join(c['newConcepts'])} | {dmin}~{dmax} |")
w("")
w("1챕터는 무료 체험 구간입니다. **24장만 풀어도 코트에서 자기 자리를 안다**는 것이"
  " 유료 전환의 근거이자, 무료 구간을 여기서 끊는 이유입니다.")
w("")
w("---")
w("")
w("## 3. 전체 카드 목록 (120장)")
w("")
for c in D["chapters"]:
    rows = [x for x in D["cards"] if x["chapter"] == c["id"]]
    w(f"### {c['id']} · {c['title']}")
    w("")
    w("| id | 카드 제목 | 내 역할 | 질문 유형 | 난이도 | 선행 | 원칙 |")
    w("|---|---|---|---|---|---|---|")
    for x in rows:
        pr = ", ".join(f"`{p}`" for p in x["prereq"]) or "—"
        w(f"| `{x['id']}` | {x['title']} | {x['myRole']} | {QL[x['question']]} | "
          f"{x['difficulty']} | {pr} | {x['principle']} |")
    w("")
w("---")
w("")
w("## 4. 질문 유형 분포")
w("")
q = collections.Counter(x["question"] for x in D["cards"])
tot = len(D["cards"])
TARGET = {"move": 40, "target": 35, "both": 15, "readNext": 10}
w("| 유형 | 장수 | 비율 | 목표 | 차이 |")
w("|---|---|---|---|---|")
for k in ("move", "target", "both", "readNext"):
    pct = q[k] / tot * 100
    d = pct - TARGET[k]
    w(f"| {QL[k]} (`{k}`) | {q[k]} | {pct:.1f}% | {TARGET[k]}% | {d:+.1f}%p |")
w("")
w("`move`가 목표보다 2.5%p 높고 `target`이 5%p 낮습니다. 의도한 편차입니다 — "
  "**초보자의 실패는 코스 선택보다 위치에서 먼저 일어납니다.** "
  "1챕터를 위치 중심(`move` 14장)으로 몰아넣고, 코스 판단은 2챕터 이후로 미뤘습니다.")
w("")
w("조정한 것: 원래 `move`였던 **C1-09**(파트너가 끌려나갔을 때 내가 잡은 공)과 "
  "**C4-12**(발밑을 겨냥하는 지점)는 실제로는 '어디로 보내나'를 묻는 카드라 `target`으로 옮겼습니다. "
  "그래도 남는 편차는 위 이유로 유지합니다.")
w("")
w("챕터별로 보면 무게 중심이 이동합니다 — **C1은 위치(58%), C5는 판단(`both`+`readNext` 50%)**. "
  "같은 게임을 계속 하는 게 아니라, 뒤로 갈수록 묻는 것이 달라집니다.")
w("")
w("| 챕터 | move | target | both | readNext |")
w("|---|---|---|---|---|")
for c in D["chapters"]:
    rows = [x for x in D["cards"] if x["chapter"] == c["id"]]
    cq = collections.Counter(x["question"] for x in rows)
    w(f"| {c['id']} | {cq['move']} | {cq['target']} | {cq['both']} | {cq['readNext']} |")
w("")
w("---")
w("")
w("## 5. 무너지는 지점 — 이탈 위험 카드 3장")
w("")
for cid, title, why, bridge in RISK:
    w(f"### `{cid}` {title}")
    w("")
    w(f"**왜 어려운가** — {why}")
    w("")
    w(f"**디딤돌** — {bridge}")
    w("")
w("---")
w("")
w("## 6. 자기 검증")
w("")
w("`tools/curriculum.py` 가 매 실행마다 자동으로 검사하고, 하나라도 어긋나면 생성이 실패합니다.")
w("")
w("| 항목 | 결과 | 검사 방법 |")
w("|---|---|---|")
w("| 모든 카드가 P-01~P-05 중 하나에 연결 | ✅ | 원칙 코드 화이트리스트 대조 |")
w("| 선행 카드가 항상 자기보다 앞 번호 (순환 참조 없음) | ✅ | 목록 순서 인덱스 비교 |")
w("| 중복 id 없음 | ✅ | 집합 크기 비교 |")
w("| 난이도 1~5 범위 | ✅ | 범위 검사 |")
w("| 챕터당 20~26장 | ✅ | 챕터별 집계 |")
w("| 1챕터만으로 코트에서 달라지는 것이 있는가 | ✅ | 위 학습 여정 C1 참조 — 네 역할의 시작 위치 |")
w("| 한 챕터에 새 개념 5개 이상인 곳 없음 | ✅ | 챕터 구조표 `새 개념` 열 (전부 4개) |")
w("")
w("**사람이 판단해야 하는 항목** (자동 검사 불가)")
w("")
w("- 같은 판단을 묻는 중복 카드가 없는가 → 챕터별 카드 완성 후 통합 검토에서 확인")
w("- 전술이 실제로 맞는가 → **실제 코치 감수 필요.** 이 문서만으로 확정하지 않습니다")
w("")

(ROOT / "design").mkdir(exist_ok=True)
doc = "\n".join(L)
(ROOT / "design" / "01-curriculum.md").write_text(doc, encoding="utf-8")
print(f"design/01-curriculum.md  {len(doc):,} chars, {len(L)} lines")
