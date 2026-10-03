#!/usr/bin/env python3
"""웹 페이지 스모크 테스트 — 헤드리스 Chromium 으로 실제 흐름을 눌러 본다.

  검증판 게임(web/play.html)
    · 카드 한 장은 누를 때만 넘어간다: 제목 → 상황 → 질문 → 결과 → 해설 (움직임 줄이기 켬 · 끔)
    · 처음 온 사람: 맛보기 → 시작하기 → 5장 → 결과 → 홈
    · 복습이 밀린 사람: 복습 2 + 새 카드 5 → 중간에 나가기 → 이어서 하기
    · 1챕터 마지막 카드를 맞히면 전술 부수 5부 · 2챕터까지면 4부
    · 카드를 다 푼 사람: 다음 카드 기다릴게요
    · claude.ai 저장소(가짜): 불러오기 · 쓰기 · 만든 사람의 검증 지표
    · 기록 주소(가짜 fetch): 이벤트 묶음 전송
  블루프린트(web/index.html)
    · 카드 수 × 보기 3 번 재생 — 결과 배지가 채점과 같은가

애니메이션은 requestAnimationFrame 을 타이머로 바꿔 가상 시간으로 돌린다.
브라우저가 없으면 건너뛴다 (CHROME_BIN 으로 경로를 줄 수 있다)."""
import datetime, glob, html, json, os, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


def find_chrome():
    cands = [os.environ.get("CHROME_BIN", "")] + sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    cands += [shutil.which(n) or "" for n in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")]
    return next((c for c in cands if c and os.path.exists(c)), None)


CHROME = find_chrome()
TMP = pathlib.Path(tempfile.mkdtemp(prefix="dmb-smoke-"))
CARDS = sorted((c for f in sorted((ROOT / "data" / "cards").glob("*.json"))
                for c in json.loads(f.read_text(encoding="utf-8"))["cards"]), key=lambda c: c["id"])
IDS = [c["id"] for c in CARDS]

PRE = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
       '<style>[hidden]{display:none!important}body{margin:0}</style><script>{STATE}'
       'window.requestAnimationFrame=function(cb){return setTimeout(function(){cb(performance.now());},16);};'
       'window.cancelAnimationFrame=function(i){clearTimeout(i);};'
       'var _mm=window.matchMedia;window.matchMedia=function(q){return q.indexOf("reduced-motion")>=0?'
       '{matches:{REDUCED},addListener:function(){},addEventListener:function(){}}:_mm.call(window,q);};'
       'window.__ERR=[];window.addEventListener("error",function(e){window.__ERR.push(String(e.message));});'
       '</script>{MOCK}</head><body>')

GAME_PROBE = r"""<script>
(function(){
var LOG=[];function q(s){return document.querySelector(s);}
function vis(){var r=[];['home','play','done','chapter','stats','match'].forEach(function(n){var el=q('#s-'+n);if(el&&!el.hidden)r.push(n);});return r.join(',');}
function snap(tag){var say=q('#p-say'),t=q('#toast');
  var cap=q('#gs-cap');
  LOG.push({tag:tag,screen:vis(),count:q('#bar-play').hidden?'':q('#scount').textContent,dots:document.querySelectorAll('#sdots i').length,
    phase:q('#gs').getAttribute('data-phase'),cap:cap.hidden?null:cap.textContent,rev:!q('#gs-rev').hidden,badge:q('#gs-rev').hidden?null:q('#gs-rev').textContent,
    bridge:q('#gs-bridge').hidden?null:q('#gs-bridge').textContent,chain:q('#c-chain').hidden?null:q('#k-n').textContent,sheet:!q('#p-verdict').hidden,
    score:q('#mscore').hidden?null:q('#mscore').getAttribute('aria-label'),clock:q('#gs-clock').hidden?null:q('#gs-clock').textContent,
    mrec:q('#m-rec').textContent,dhead:q('#s-done').hidden?null:q('#d-head').textContent,dxp:q('#s-done').hidden?null:q('#d-xp').textContent,hc:q('#d-hc').hidden?null:q('#d-hc').textContent,reps:q('.rlist')?q('.rlist').textContent:null,
    lvs:[].map.call(document.querySelectorAll('#ml-lv [aria-pressed=true]'),function(b){return b.getAttribute('data-lv');}).join(','),
    title:q('#gs-name').textContent,scene:q('#gs-scene-t').textContent,dock:q('#gs-dock').textContent.slice(0,90),
    head:q('#t-head').textContent,say:say.hidden?null:say.textContent,prog:q('#p-n').textContent,rank:q('#bar-rank-t').textContent,
    rankup:q('#d-rank').hidden?null:q('#d-rank').textContent,tally:q('#s-done').hidden?null:q('#d-tally').textContent,
    wait:!q('#c-wait').hidden,owner:!q('#h-stats').hidden,stats:q('#s-stats').hidden?null:q('#st-body').textContent.slice(0,200),
    toast:t.hidden?null:t.textContent,writes:window.__writes||0,sent:window.__SENT||null,err:window.__ERR.slice()});
  document.body.setAttribute('data-m',JSON.stringify(LOG));}
function click(sel){var el=q(sel);if(!el){window.__ERR.push('없음 '+sel);return;}el.dispatchEvent(new MouseEvent('click',{bubbles:true}));}
function phase(){return q('#gs').getAttribute('data-phase');}
function tap(){click('#gs-court');}
// 질문이 나올 때까지 코트를 누른다 (제목 → 상황 → 질문). 움직임 줄이기면 도입 공은 바로 끝난다
function ask(){for(var k=0;k<4&&phase()!=='ask';k++)tap();if(phase()!=='ask')window.__ERR.push('질문까지 못 감: '+phase());}
function opt(i){ask();click('#p-opts [data-opt="'+i+'"]');}
function pick(want){var id=q('#p-id').textContent,c=JSON.parse(q('#card-data').textContent).filter(function(x){return x.id===id;})[0];
  var i=0;Court.optsOf(c).forEach(function(x,j){if(x.v===(want||'정답'))i=j;});opt(i);}
var g={q:q,click:click,snap:snap,pick:pick,opt:opt,tap:tap,ask:ask},STEPS=__STEPS__;
setTimeout(function(){snap('start');var i=0;(function next(){if(i>=STEPS.length)return;var s=STEPS[i++];
  setTimeout(function(){try{(new Function('g',s[1]))(g);}catch(err){window.__ERR.push('단계 '+i+': '+err.message);}next();},s[0]);})();},600);
})();
</script>"""

DB_MOCK = r"""<script>
window.__STORE={'players/u_a':{v:1,answered:30,total:30,taste:{v:'정답'},wait:'2026-09-29T10:00:00Z',days:['2026-09-18','2026-09-26'],
  cards:{'C1-01':{f:'정답',l:'정답',n:1,ms:4000}},reports:[{c:'C1-08',r:'그림이 헷갈려요',at:'2026-09-20T01:00:00Z'}]}};
window.__writes=0;
var MOCKDB={doc:function(p){return {path:p,get:function(){var d=window.__STORE[p];return Promise.resolve({exists:!!d,data:function(){return d;}});},
  set:function(d){window.__writes++;window.__STORE[p]=JSON.parse(JSON.stringify(d));return Promise.resolve();}};},
 collection:function(p){return {get:function(){var docs=Object.keys(window.__STORE).filter(function(k){return k.indexOf(p+'/')===0;})
  .map(function(k){return {id:k.split('/').pop(),exists:true,data:function(){return window.__STORE[k];}};});return Promise.resolve({docs:docs,size:docs.length,empty:!docs.length});}};}};
window.claude={use:function(n){return new Promise(function(res){setTimeout(function(){
  if(n==='db')res(MOCKDB);else if(n==='user')res({id:function(){return Promise.resolve('u_me');},isOwner:function(){return Promise.resolve(true);}});else res(null);},40);});}};
</script>"""

FETCH_MOCK = ('<script>window.__SENT=[];window.fetch=function(u,o){var b=JSON.parse(o.body);'
              'window.__SENT.push({mode:o.mode,e:b.events.map(function(x){return x.e;})});return Promise.resolve({});};</script>')


def run(name, page, budget=20000):
    page = page.replace("{REDUCED}", "true")
    f = TMP / (name + ".html")
    f.write_text(page, encoding="utf-8")
    out = subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", f"--virtual-time-budget={budget}",
                          "--window-size=420,1400", "--dump-dom", f.as_uri()], capture_output=True, text=True, timeout=240).stdout
    m = re.search(r'data-m="([^"]*)"', out)
    return json.loads(html.unescape(m.group(1))) if m else None


def game(name, steps, state=None, mock="", config=None, budget=20000, motion=False):
    page = (WEB / "play.html").read_text(encoding="utf-8")
    if config:
        page = page.replace('"endpoint": ""', '"endpoint": "%s"' % config)
    st = ('try{localStorage.setItem("dmb-game-v1",' + json.dumps(json.dumps(state, ensure_ascii=False)) + ')}catch(e){}'
          if state else 'try{localStorage.removeItem("dmb-game-v1")}catch(e){}')
    pre = PRE.replace("{REDUCED}", "false" if motion else "true")
    return run(name, pre.replace("{STATE}", st).replace("{MOCK}", mock) + page
               + GAME_PROBE.replace("__STEPS__", json.dumps(steps, ensure_ascii=False)), budget)


def state(answers):
    today = datetime.date.today()
    day = lambda n: (today + datetime.timedelta(days=n)).isoformat()
    s = {"v": 1, "uid": "p_smoke", "created": day(-5) + "T01:00:00Z", "opens": 2, "onboarded": True,
         "taste": {"v": "정답", "o": 0, "ms": 4000, "at": day(-5) + "T01:00:00Z"}, "cards": {}, "xp": 0,
         "days": [day(-3), day(-2)], "sessions": 1, "rank": "신인부", "rankUp": None, "session": None,
         "reports": [], "wait": None, "ev": []}
    for cid, v, due in answers:
        s["cards"][cid] = {"f": v, "l": v, "n": 1, "ms": 5000, "at": day(-2) + "T10:00:00Z",
                           "due": None if due is None else day(due), "track": None if v == "정답" else v, "box": 0}
    return s


NEXT = [[120, "g.pick()"], [120, "g.click('[data-act=explain]')"], [120, "g.click('[data-act=next]')"]]
fails = []


def check(desc, ok, detail=""):
    print(f"  {'✅' if ok else '❌'} {desc}" + ("" if ok else f"\n      {detail}"))
    if not ok:
        fails.append(desc)


def last(log, tag):
    return next((e for e in reversed(log or []) if e["tag"].startswith(tag)), None)


def main():
    if not CHROME:
        print("⏭  브라우저가 없어 웹 스모크 테스트를 건너뜁니다 (CHROME_BIN 으로 지정)")
        return 0

    # 1) 처음 온 사람
    log = game("new", [[150, "g.ask()"], [150, "g.snap('ask')"], [150, "g.opt(0)"], [150, "g.snap('result')"], [150, "g.tap()"],
                       [150, "g.snap('taste')"], [150, "g.click('[data-act=taste-start]')"], [150, "g.snap('s1')"]] + NEXT * 4 +
               [[120, "g.pick('실수')"], [120, "g.tap()"], [120, "g.click('[data-act=finish]')"], [150, "g.snap('done')"],
                [150, "g.click('[data-act=home]')"], [150, "g.snap('home')"]])
    s0, a, r, t, s1, d, h = (last(log, k) for k in ("start", "ask", "result", "taste", "s1", "done", "home"))
    c24 = next(c for c in CARDS if c["id"] == "C1-24")
    check("처음 온 사람은 맛보기 카드부터 — 어두운 코트에 〈제목〉", s0 and s0["screen"] == "play" and s0["count"] == "맛보기 · 1분"
          and s0["phase"] == "title" and c24["title"] in s0["title"], s0)
    check("코트를 누르면 상황 글을 거쳐 질문 띠", a and a["phase"] == "ask" and c24["question"]["text"] in (a["cap"] or "")
          and a["scene"] == c24["scene"], a)
    check("고르면 결과 배지 — 해설은 누를 때까지 안 나온다", r and r["phase"] == "result" and r["say"] and r["say"][0] in "✓△✕"
          and not r["sheet"] and "해설 보기" in r["dock"], r)
    check("코트를 누르면 해설 시트", t and t["phase"] == "verdict" and t["sheet"], t)
    check("시작하기 → 오늘의 코트 5장", s1 and s1["count"] == "1 / 5" and s1["dots"] == 5, s1)
    check("한 판 결과 — 성공 4 · 실패 1", d and d["screen"] == "done" and "성공 4" in d["tally"] and "실패 1" in d["tally"], d)
    check("홈 진도 5장", h and h["prog"].startswith("5/"), h)
    check("오류 없음 (처음 온 사람)", h and not h["err"], h and h["err"])

    # 1b) 누를 때만 넘어간다 — 움직임을 켠 기기에서 공이 실제로 날 때. 오래 기다려도 혼자 넘어가지 않는다
    log = game("tap", [[9000, "g.snap('t1')"], [100, "g.tap()"], [8000, "g.snap('t2')"], [9000, "g.snap('t3')"],
                       [100, "g.tap()"], [300, "g.snap('t4')"], [100, "g.opt(0)"], [100, "g.snap('t5')"], [8000, "g.snap('t6')"],
                       [9000, "g.snap('t7')"], [100, "g.tap()"], [300, "g.snap('t8')"]], motion=True, budget=70000)
    t = {k: last(log, k) for k in ("t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8")}
    ph = {k: (v or {}).get("phase") for k, v in t.items()}
    check("기다려도 제목에 머문다 → 누르면 공이 나고 상황 글에서 멈춘다", ph["t1"] == "title" and ph["t2"] == "scene"
          and ph["t3"] == "scene" and (t["t2"] or {}).get("scene") == c24["scene"], ph)
    check("누르면 질문 → 고르면 결과 재생 → 결과에서 멈춘다 → 누르면 해설", ph["t4"] == "ask" and ph["t5"] == "out"
          and ph["t6"] == "result" and ph["t7"] == "result" and ph["t8"] == "verdict" and (t["t8"] or {}).get("sheet")
          and not (t["t8"] or {}).get("err"), ph)

    # 2) 복습 2장이 밀린 사람 — 중간에 나갔다 이어서
    st = state([(cid, "정답", None) for cid in IDS[:10]])
    st["cards"][IDS[2]].update(f="실수", l="실수", track="실수", due=(datetime.date.today() - datetime.timedelta(days=1)).isoformat())
    st["cards"][IDS[6]].update(f="실수", l="실수", track="실수", due=datetime.date.today().isoformat())
    log = game("due", [[150, "g.snap('home')"], [150, "g.click('#t-cta')"], [150, "g.snap('s1 '+g.q('#p-id').textContent)"]] + NEXT * 2 +
               [[150, "g.click('#b-x')"], [150, "g.snap('exit')"], [150, "g.click('#t-cta')"], [150, "g.snap('resume')"]], st)
    h, s1, ex, rs = (last(log, k) for k in ("home", "s1", "exit", "resume"))
    check("복습 2장 + 새 카드 5장", h and "새 카드 5장" in h["head"] and "복습 2장" in h["head"], h)
    check("복습 카드가 먼저, '복습' 표시", s1 and s1["count"] == "1 / 7" and s1["rev"], s1)
    check("나가면 '하던 코트가 남았어요'", ex and ex["screen"] == "home" and "하던 코트가" in ex["head"], ex)
    check("이어서 하기 → 3번째 카드", rs and rs["count"] == "3 / 7" and not rs["err"], rs)

    # 3) 1챕터 마지막 카드를 맞히면 5부
    log = game("rank", [[150, "g.click('#t-cta')"]] + NEXT * 4 + [[120, "g.pick()"], [120, "g.tap()"], [120, "g.click('[data-act=finish]')"],
                        [150, "g.snap('done')"], [150, "g.click('[data-act=home]')"], [150, "g.snap('home')"]],
               state([(cid, "정답", None) for cid in IDS[:23]]))
    d, h = last(log, "done"), last(log, "home")
    check("전술 부수 5부 승급 안내", d and d["rankup"] and "5부" in d["rankup"], d)
    check("윗줄 부수 표시 5부", h and h["rank"] == "5부" and not h["err"], h)

    # 3b) 2챕터까지 다 맞힌 사람은 4부 — 부수 사다리는 챕터마다 한 단계
    log = game("rank4", [[150, "g.snap('home')"]], state([(cid, "정답", None) for cid in IDS if cid < "C3"]))
    h = last(log, "home")
    check("2챕터까지 70% 이상이면 전술 부수 4부", h and h["rank"] == "4부" and not h["err"], h)

    # 4) 다 푼 사람
    log = game("all", [[150, "g.snap('home')"], [150, "g.click('[data-act=wait]')"], [150, "g.snap('waited')"]],
               state([(cid, "정답", None) for cid in IDS]))
    h, w = last(log, "home"), last(log, "waited")
    check("다 푼 사람 — 기다림 카드", h and h["wait"] and h["prog"].startswith(f"{len(IDS)}/"), h)
    check("다음 카드 기다릴게요 → 안내", w and w["toast"] and "전했어요" in w["toast"], w)

    # 4b) 두 수 앞 — 첫 수가 정답이면 두 번째 수, 아니면 다음 짝 (PRD 결정 #25)
    log = game("chain", [[150, "g.snap('k0')"], [150, "g.click('[data-act=chain-start]')"], [150, "g.snap('a1')"],
                         [150, "g.pick()"], [150, "g.click('[data-act=explain]')"], [150, "g.snap('a1v')"],
                         [150, "g.click('[data-act=chain-next]')"], [150, "g.snap('b1')"],
                         [150, "g.pick()"], [150, "g.click('[data-act=explain]')"], [150, "g.click('[data-act=chain-next]')"],
                         [150, "g.snap('a2')"], [150, "g.pick('실수')"], [150, "g.click('[data-act=explain]')"], [150, "g.snap('a2v')"],
                         [150, "g.click('[data-act=chain-next]')"], [200, "g.snap('done')"], [150, "g.click('[data-act=home]')"],
                         [150, "g.snap('home2')"]],
               state([(cid, "정답", None) for cid in IDS[:5]]))
    h, a1, a1v, b1, a2v, d, h2 = (last(log, t) for t in ("k0", "a1", "a1v", "b1", "a2v", "done", "home2"))
    check("두 수 앞 — 첫 카드를 푼 짝이 홈에 열린다", h and h["chain"] == "이은 짝 0 / 2", h)
    check("첫 수 → 정답이면 '두 번째 수 →'", a1 and a1["badge"] == "첫 수" and a1["count"] == "두 수 1 / 2" and a1["dots"] == 4
          and a1v and "두 번째 수 →" in a1v["dock"], (a1, a1v))
    check("두 번째 수는 앞 수에서 이어진다", b1 and b1["badge"] == "두 번째 수" and b1["bridge"] == "앞 수에서 이어져요"
          and b1["title"] == "〈서브 후, 남을까요 나갈까요〉", b1)
    check("첫 수가 실수면 끊긴다 → 결과 보기", a2v and "정답이어야 이어져요" in a2v["dock"] and "결과 보기" in a2v["dock"], a2v)
    check("두 수 앞 결과 — 이은 짝 1 · 끊긴 짝 1", d and d["tally"] == "✓ 이은 짝 1✕ 끊긴 짝 1" and not d["err"], d)
    check("이은 짝이 홈에 남는다", h2 and h2["chain"] and h2["chain"].startswith("이은 짝 1 /"), h2)

    # 4c) 실전 모드 — 희철과 한 게임 (10초 룰 + 랠리, PRD 결정 #26)
    WIN = "for(var k=0;k<20;k++){if(!g.q('#s-done').hidden)break;g.pick('정답');g.click('[data-act=match-next]');}"
    LOSE = "for(var k=0;k<20;k++){if(!g.q('#s-done').hidden)break;g.pick('실수');g.click('[data-act=match-next]');}"
    log = game("match", [[150, "g.snap('h0')"], [150, "g.click('[data-act=match-open]')"], [150, "g.snap('lobby')"],
                         [150, "g.click('[data-act=match-lv][data-lv=\"1\"]')"], [150, "g.snap('lv')"],
                         [150, "g.click('[data-act=match-start]')"], [150, "g.snap('ask')"], [150, "g.pick('차선')"], [150, "g.snap('edge')"],
                         [150, "g.click('[data-act=match-next]')"], [150, WIN], [200, "g.snap('won')"],
                         [150, "g.click('[data-act=match-start]')"], [150, LOSE], [200, "g.snap('lost')"],
                         [150, "g.click('[data-act=home]')"], [150, "g.snap('h1')"]],
               state([(cid, "정답", None) for cid in IDS[:5]]))
    h0, lb, lv, ak, ed, wn, ls, h1 = (last(log, t) for t in ("h0", "lobby", "lv", "ask", "edge", "won", "lost", "h1"))
    check("실전 모드 — 처음부터 홈에 있다 · 희철 로비", h0 and h0["mrec"] == "첫 경기" and lb and lb["screen"] == "match" and lb["lvs"] == "5", (h0, lb))
    check("희철 실력 고르기 — 1부(120장)", lv and lv["lvs"] == "1", lv)
    check("경기 — 제목 없이 질문까지 · 10초 시계 · 점수판", ak and ak["phase"] == "ask" and ak["clock"] == "10" and ak["score"] == "나 0, 희철 0"
          and ak["cap"] and len(ak["cap"]) > 10, ak)
    check("차선 — 랠리가 이어지고 희철이 한 발 앞선다", ed and ed["phase"] == "result" and "희철이 한 발 앞서요" in ed["dock"] and "다음 공" in ed["dock"], ed)
    check("다 맞히면 희철을 이긴다", wn and wn["screen"] == "done" and wn["dhead"] == "희철을 이겼어요!"
          and wn["hc"] and "제가 졌어요" in wn["hc"] and not wn["err"], wn)
    check("다 틀리면 희철에게 진다 — 포인트 0 : 4", ls and ls["dhead"] == "희철에게 졌어요" and ls["hc"] and "다시 붙어요" in ls["hc"]
          and "포인트 0 : 4" in (ls["dxp"] or ""), ls)
    check("희철 상대 전적이 홈에 남는다", h1 and h1["mrec"] == "1승 1패", h1)
    log = game("match10", [[150, "g.click('[data-act=match-open]')"], [150, "g.click('[data-act=match-start]')"],
                           [5000, "g.snap('t5')"], [5600, "g.snap('to')"], [150, "g.click('[data-act=explain]')"], [150, "g.snap('tv')"]],
               state([(cid, "정답", None) for cid in IDS[:5]]), budget=30000)
    t5, to, tv = last(log, "t5"), last(log, "to"), last(log, "tv")
    check("10초 — 시계가 줄어든다", t5 and t5["clock"] in ("6", "5", "4"), t5)
    check("10초가 지나면 시간 초과 — 희철 포인트", to and to["say"] and "시간 초과" in to["say"] and to["score"] == "나 0, 희철 15"
          and "포인트 — 희철" in to["dock"], to)
    check("시간 초과 해설 — 정답 장면과 이유", tv and tv["sheet"] and not tv["err"], tv)
    log = game("taste2match", [[150, "g.opt(1)"], [150, "g.tap()"], [150, "g.click('[data-act=taste-match]')"], [150, "g.snap('lb')"]])
    tm = last(log, "lb")
    check("처음 온 사람 — 맛보기 뒤 '희철과 실전 →'", tm and tm["screen"] == "match" and not tm["err"], tm)

    # 5) claude.ai 저장소 (가짜)
    log = game("db", [[300, "g.snap('home')"], [150, "g.click('#t-cta')"], [150, "g.pick('차선')"], [300, "g.snap('answered')"],
                      [150, "g.click('[data-act=explain]')"], [150, "g.click('[data-act=report]')"],
                      [150, "g.q('#rep-note').value='리시버가 늦으면 B 도 맞아요'"], [150, "g.click('#rep-form [type=submit]')"],
                      [150, "g.click('#b-x')"], [150, "g.click('[data-act=stats]')"], [400, "g.snap('stats')"]],
               state([(cid, "정답", None) for cid in IDS[:5]]), mock=DB_MOCK)
    h, a, s = last(log, "home"), last(log, "answered"), last(log, "stats")
    check("저장소 — 불러온 뒤 한 번 동기화, 만든 사람 링크", h and h["writes"] == 1 and h["owner"], h)
    check("저장소 — 답할 때마다 쓴다", a and a["writes"] >= 3, a)
    check("검증 지표 — 참여자 두 명 집계", s and s["stats"] and s["stats"].startswith("2맛보기") and not s["err"], s)
    check("감수 메모 — 신고에 적은 한 줄이 검증 지표에 모인다", s and s["reps"] and "리시버가 늦으면 B 도 맞아요" in s["reps"]
          and "그림이 헷갈려요" in s["reps"], s and s["reps"])

    # 6) 기록 주소 (가짜 fetch)
    log = game("http", [[150, "g.opt(1)"], [150, "g.tap()"], [150, "g.click('[data-act=taste-start]')"],
                        [150, "g.pick()"], [2200, "g.snap('sent')"]], mock=FETCH_MOCK, config="https://example.invalid/log")
    s = last(log, "sent")
    sent = [e for b in (s or {}).get("sent") or [] for e in b["e"]]
    check("기록 주소로 이벤트 묶음 전송 (no-cors)", s and "answer" in sent and "taste" in sent and all(b["mode"] == "no-cors" for b in s["sent"]), s)

    # 7) 블루프린트 — 카드 × 보기 재생 + 공의 길
    page = (WEB / "index.html").read_text(encoding="utf-8")
    sweep = r"""<script>
setTimeout(function(){
  var out=[],n=document.querySelectorAll('#strip button').length;function q(s){return document.querySelector(s);}
  for(var i=0;i<n;i++){q('[data-jump="'+i+'"]').click();var id=q('#p-id').textContent;
    for(var j=0;j<3;j++){if(q('[data-reset]'))q('[data-reset]').click();var e0=window.__ERR.length;
      q('#p-opts [data-opt="'+j+'"]').click();var say=q('#p-say'),b=q('#p-verdict .badge');
      out.push({id:id,say:say.hidden?'':say.textContent,v:b?b.textContent:'',err:window.__ERR.length-e0});}
    if(q('[data-reset]'))q('[data-reset]').click();}
  // 공의 길 — 바운드한 공 · 튄 공을 치러 가는 길 · 아무도 안 친 공은 바닥에서 보아 꺾이지 않는다
  function ang(a,b){return Math.abs(Math.atan2(a[0]*b[1]-a[1]*b[0],a[0]*b[0]+a[1]*b[1]))*180/Math.PI;}
  function dv(p,r){return [r[0]-p[0],r[1]-p[1]];}function len(v){return Math.hypot(v[0],v[1]);}
  var C=JSON.parse(q('#card-data').textContent),kinks=[],nf=0;
  function scan(T,tag){var prev=null;T.flights.forEach(function(f){var P=f.fl.pts,bi=f.fl.bounce,e=P.length-1,a,b;nf++;
    if(bi>=0&&bi<e){a=dv(P[0],P[bi]);b=dv(P[bi],P[e]);if(len(b)>.05&&ang(a,b)>1.5)kinks.push(tag+' 바운드 '+ang(a,b).toFixed(1)+'°');}
    if(prev&&(f.hop||f.team==='none')){var Q=prev.fl.pts,pb=prev.fl.bounce,pe=Q.length-1;a=pb>=0&&pb<pe?dv(Q[pb],Q[pe]):dv(Q[0],Q[pe]);
      b=dv(P[0],bi>=0?P[bi]:P[e]);if(len(a)>.05&&len(b)>.05&&ang(a,b)>1.5)kinks.push(tag+(f.hop?' 튄 공':' 안 친 공')+' '+ang(a,b).toFixed(1)+'°');}
    prev=f;});}
  C.forEach(function(c){scan(Court._tl.intro(c),c.id+' 도입');for(var j=0;j<3;j++)scan(Court._tl.outcome(c,j),c.id+' 보기'+j);});
  out.push({kinks:kinks,flights:nf});
  document.body.setAttribute('data-m',JSON.stringify(out));},400);
</script>"""
    out = run("blueprint", PRE.replace("{STATE}", "try{localStorage.removeItem('dmb-player-v2')}catch(e){}").replace("{MOCK}", "") + page + sweep, 12000)
    path = out.pop() if out and "kinks" in out[-1] else {}
    SAY = {"✓": "정답", "△": "차선", "✕": "실수"}
    bad = [r for r in out or [] if r["err"] or not r["say"] or not r["v"].endswith(SAY.get(r["say"][0], "?"))]
    check(f"블루프린트 {len(out or [])}번 재생 — 결과 배지 = 채점", out and len(out) == len(IDS) * 3 and not bad, bad[:3])
    check(f"공의 길 {path.get('flights', 0)}개 — 바운드에서 꺾이지 않는다",
          path.get("flights", 0) > len(IDS) * 3 and not path.get("kinks"), (path.get("kinks") or [])[:5])

    shutil.rmtree(TMP, ignore_errors=True)
    print(f"웹 스모크 테스트 {'통과' if not fails else f'실패 {len(fails)}건'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
