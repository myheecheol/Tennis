#!/usr/bin/env python3
"""페이지를 만든다. 공용 엔진(web/src/court.js · court.css)과 검증된 카드 · 카메라 규격을 각 템플릿에 넣는다.
   index.html — 블루프린트 페이지 (prompts/*.md 의 ```text 블록도 함께)
   play.html  — Phase 1 검증판 게임 (챕터 정보 · 원 포인트 게임 짝 · 실전 모드의 상대 그림 · play.config.json 설정도 함께)
   site/index.html — 같은 게임을 문서 뼈대(doctype · charset · viewport · 미리보기 글)째로. claude.ai 밖 정적 호스팅용
                     (claude.ai 는 게시할 때 뼈대를 씌우므로 play.html 은 조각으로 둔다 — design/08-phase1.md §4B)"""
import base64, json, re, pathlib

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

def all_cards():
    """검증된 카드 전체를 id 순서로. 페이지가 카드 스키마를 그대로 읽는다."""
    cards = []
    for f in sorted((ROOT / "data" / "cards").glob("*.json")):
        cards += json.loads(f.read_text(encoding="utf-8"))["cards"]
    return sorted(cards, key=lambda c: c["id"])


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

cards = all_cards()
cams = json.loads((ROOT / "data" / "cameras.json").read_text(encoding="utf-8"))


def blob(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", r"<\/")


COURT_JS = (WEB / "src" / "court.js").read_text(encoding="utf-8")
COURT_CSS = (WEB / "src" / "court.css").read_text(encoding="utf-8")
assert "</script" not in COURT_JS.lower(), "엔진 안에 </script 가 있으면 페이지가 깨진다"


def page(template, out, data):
    html = (WEB / template).read_text(encoding="utf-8")
    html = html.replace("/*COURT_CSS*/", COURT_CSS).replace("/*COURT_JS*/", COURT_JS)
    for key, obj in data:
        html = html.replace("/*" + key + "*/", blob(obj))
    assert "_JSON*/" not in html and "/*COURT_" not in html, f"{out}: 주입 자리가 남았다"
    (WEB / out).write_text(html, encoding="utf-8")
    return html


html = page("template.html", "index.html",
            (("PROMPTS_JSON", steps), ("CARDS_JSON", cards), ("CAMERAS_JSON", cams)))
print(f"index.html  {len(html):,} bytes")

index = json.loads((ROOT / "data" / "cards-index.json").read_text(encoding="utf-8"))
chapters = [{"id": ch["id"], "title": ch["title"], "goal": ch["goal"], "free": ch["free"],
             "total": sum(1 for c in index["cards"] if c["chapter"] == ch["id"])} for ch in index["chapters"]]
config = json.loads((WEB / "play.config.json").read_text(encoding="utf-8"))
chains = json.loads((ROOT / "data" / "chains.json").read_text(encoding="utf-8"))
# 실전 모드의 상대(이름은 play.config.json 의 opponent) — 사용자가 준 캐릭터 시트에서 배경 없이 오린 얼굴 다섯 · 전신
opponent = {f.stem: "data:image/webp;base64," + base64.b64encode(f.read_bytes()).decode("ascii")
            for f in sorted((WEB / "assets" / "opponent").glob("*.webp"))}
play = page("play.template.html", "play.html",
            (("CARDS_JSON", cards), ("CAMERAS_JSON", cams), ("CHAPTERS_JSON", chapters), ("CONFIG_JSON", config),
             ("CHAINS_JSON", {"pairs": chains["pairs"]}), ("OPPONENT_JSON", opponent)))
print(f"play.html   {len(play):,} bytes  (검증판 · 카드 {len(cards)}장 · 원 포인트 게임 {len(chains['pairs'])}짝 · 기록 주소 {'있음' if config.get('endpoint') else '없음'})")

# 정적 호스팅용 — 뼈대가 없으면 폰에서 데스크톱 폭(980px)으로 작게 그려지고, 서버가 charset 을 안 주면 한글이 깨진다
DESC = "복식 테니스 초보를 위한 전술 게임 — 공이 멈추면 고르고, 고른 대로 공과 사람이 움직여요. 츄어리와 10초 실전도."
ICON = ("data:image/svg+xml," "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='29' fill='%23D7F23C'/%3E"
        "%3Cpath d='M9 18c13 6 13 22 0 28M55 18c-13 6-13 22 0 28' fill='none' stroke='%23fff' stroke-width='4'/%3E%3C/svg%3E")
cut = play.index("</style>") + len("</style>")
site = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f'<meta name="description" content="{DESC}">\n<meta property="og:type" content="website">\n'
        f'<meta property="og:title" content="복식 무브">\n<meta property="og:description" content="{DESC}">\n'
        '<meta name="theme-color" content="#F3F8EA">\n<meta name="format-detection" content="telephone=no">\n'
        f'<link rel="icon" href="{ICON}">\n'
        + play[:cut] + "\n</head>\n<body>\n" + play[cut:] + "\n</body>\n</html>\n")
(ROOT / "site").mkdir(exist_ok=True)
(ROOT / "site" / "index.html").write_text(site, encoding="utf-8")
print(f"site/index.html {len(site):,} bytes  (정적 호스팅용 — 문서 뼈대 · 미리보기 글 포함)")
print(f"  카드 {len(cards)}장  {cards[0]['id']} … {cards[-1]['id']}")
for s in steps:
    print(f"  {s['no']:<7} {s['title']:<22} blocks={len(s['blocks'])}  "
          f"{sum(len(b['text']) for b in s['blocks']):>5} chars")
