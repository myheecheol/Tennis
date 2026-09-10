#!/usr/bin/env python3
"""prompts/*.md 의 ```text 블록을 뽑아 web/template.html 에 주입해 index.html 을 만든다."""
import json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROMPTS, WEB = ROOT / "prompts", ROOT / "web"

META = [
    ("00-context.md", "STEP 0", "공통 컨텍스트 블록",
     "매 단계 프롬프트 맨 앞에 붙인다. 사용자 정의 · 절대 규칙 7가지 · 톤 · Non-goals.", []),
    ("01-curriculum.md", "STEP 1", "커리큘럼 설계",
     "5챕터 구조와 카드 100~130장 목록. 난이도 곡선과 선행관계까지.",
     ["reference/doubles-domain-pack.md"]),
    ("02-situation-cards.md", "STEP 2", "상황 카드 생성 · 핵심",
     "카드를 본문 + JSON 두 벌로. 8장씩 끊어서 반복 실행한다.",
     ["doubles-domain-pack.md", "court-coordinates.md", "card-exemplars.md"]),
    ("03-court-visuals.md", "STEP 3", "코트 시각화 명세",
     "좌표 변환 · 마커 · 화면 상태 5가지 · 애니메이션 타임라인 · 접근성.",
     ["court-coordinates.md"]),
    ("04-game-design.md", "STEP 4", "게임 설계",
     "코어 루프 · 채점(정답/차선/실수) · 모드 4가지 · 리텐션 · 온보딩 60초.",
     ["STEP 1·2 결과물"]),
    ("05-platform-monetization.md", "STEP 5", "플랫폼 · 수익화",
     "초안을 반박하게 만들어 검증한다. 대안 4가지 비교 후 하나를 고르게.",
     ["platform-recommendation.md", "STEP 4 결과물"]),
    ("06-prd-assembly.md", "STEP 6", "기획서 통합",
     "1~5단계를 하나의 PRD로 조립. 문서 간 모순을 지적하게 만든다.",
     ["STEP 1~5 결과물 전부"]),
    ("07-review-gate.md", "STEP 7", "검수 · 품질 게이트",
     "4인 페르소나 리뷰 + 사실 검증 + 최종 압축. 가장 값싼 단계다.",
     ["STEP 6 기획서"]),
    ("99-master-oneshot.md", "원샷", "마스터 프롬프트",
     "시간이 없을 때 한 번에. 품질은 체인이 낫다는 걸 알고 쓰세요.",
     ["reference/ 전체"]),
]

FENCE = re.compile(r"^```text\s*$")

# 데모에 싣는 카드 — 난이도 1→3, 역할과 질문 유형이 겹치지 않게 고른다
DEMO = ["C1-04", "C1-03", "C2-08"]
QLABEL = {"move": "어디로 움직일까", "target": "어디로 칠까",
          "both": "위치 + 코스", "readNext": "다음에 무슨 일이"}
PRINCIPLE = {"P-01": "P-01 로프 원칙", "P-02": "P-02 각도 원칙",
             "P-03": "P-03 높낮이 원칙", "P-04": "P-04 가운데 원칙",
             "P-05": "P-05 다운더라인 금지"}


def demo_cards():
    """검증된 카드 데이터를 페이지가 쓰는 모양으로 옮긴다."""
    src, chapters = {}, {}
    for f in sorted((ROOT / "data" / "cards").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        chapters[d["chapter"]] = d["title"]
        for c in d["cards"]:
            src[c["id"]] = c

    out = []
    for cid in DEMO:
        c = src[cid]
        lo = [d for d in c["distractors"] if d["severity"] == "차선"]
        hi = [d for d in c["distractors"] if d["severity"] == "실수"]
        opts = [{"zone": d["zone"], "v": d["severity"], "label": d["short"], "why": d["why"]}
                for d in lo]
        opts.append({"zone": c["answer"]["zone"], "v": "정답",
                     "label": c["answer"]["short"], "why": c["answer"]["why"]})
        opts += [{"zone": d["zone"], "v": d["severity"], "label": d["short"], "why": d["why"]}
                 for d in hi]
        # 정답이 늘 가운데 보기가 되지 않도록 카드 id 로 자리를 흔든다
        shift = sum(ord(ch) for ch in cid) % 3
        opts = opts[shift:] + opts[:shift]

        s = c["setup"]
        out.append({
            "id": c["id"], "ch": chapters[c["chapter"]], "diff": c["difficulty"],
            "role": c["myRole"], "qtype": c["question"]["type"],
            "qlabel": QLABEL[c["question"]["type"]], "title": c["title"],
            "scene": c["scene"], "cue": c["cue"], "ask": c["question"]["text"],
            "setup": {"me": s["me"]["xy"], "partner": s["partner"]["xy"],
                      "opp1": s["opp1"]["xy"], "opp2": s["opp2"]["xy"],
                      "ball": s["ball"]["path"]},
            "opts": opts, "coach": c["coachLine"],
            "principle": PRINCIPLE[c["answer"]["principle"]], "next": c["nextBeat"]})
    return out


def blocks(md: str):
    """```text 펜스 안의 원문과, 그 앞의 가장 가까운 ## 제목을 뽑는다."""
    out, heading, buf, inside = [], None, [], False
    for line in md.splitlines():
        if inside:
            if line.strip() == "```":
                out.append({"name": heading or "메인 프롬프트", "text": "\n".join(buf).strip()})
                buf, inside = [], False
            else:
                buf.append(line)
            continue
        if FENCE.match(line):
            inside = True
        elif line.startswith("## "):
            heading = line[3:].strip()
    if len(out) == 1:
        out[0]["name"] = "메인 프롬프트"
    return out


steps = []
for fname, no, title, desc, attach in META:
    bs = blocks((PROMPTS / fname).read_text(encoding="utf-8"))
    if not bs:
        raise SystemExit(f"no ```text block found in {fname}")
    steps.append({"no": no, "title": title, "desc": desc, "attach": attach, "blocks": bs})

cards = demo_cards()
payload = json.dumps(steps, ensure_ascii=False).replace("</", r"<\/")
cards_payload = json.dumps(cards, ensure_ascii=False).replace("</", r"<\/")
html = (WEB / "template.html").read_text(encoding="utf-8")
html = html.replace("/*PROMPTS_JSON*/", payload).replace("/*CARDS_JSON*/", cards_payload)
(WEB / "index.html").write_text(html, encoding="utf-8")

assert "/*CARDS_JSON*/" not in html and "/*PROMPTS_JSON*/" not in html, "주입 자리가 남았다"
print(f"index.html  {len(html):,} bytes")
print(f"  데모 카드  {', '.join(c['id'] for c in cards)}")
for s in steps:
    print(f"  {s['no']:<7} {s['title']:<22} blocks={len(s['blocks'])}  "
          f"{sum(len(b['text']) for b in s['blocks']):>5} chars")
