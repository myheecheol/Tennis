#!/usr/bin/env python3
"""웹 페이지 스모크 테스트 — 헤드리스 Chromium 으로 실제 흐름을 눌러 본다.

  검증판 게임(web/play.html)
    · 처음 온 사람: 닉네임 → 튜토리얼 → 시작하기 → 5장 → 결과 → 홈
    · 기록은 있는데 닉네임이 없는 사람: 닉네임만 묻고 홈 · 홈에서 닉네임 바꾸기
    · 카드 한 장은 누를 때만 넘어간다: 제목 → 상황 → 질문 → 결과 → 해설 (움직임 줄이기 켬 · 끔)
    · 복습이 밀린 사람: 복습 2 + 새 카드 5 → 중간에 나가기 → 이어서 하기
    · 1챕터 마지막 카드를 맞히면 전술 부수 5부 · 2챕터까지면 4부
    · 카드를 다 푼 사람: 다음 카드 기다릴게요
    · 원 포인트 게임!: 첫 수가 정답이면 두 번째 수가 첫 수의 끝 모습에서 이어진다
    · 실전 모드: 츄어리와 한 게임 — 10초 · 랠리가 이어지면 저절로 다음 공 · 앞 장면에서 이어 온다(순간이동 없음) · 경기 뒤 카드 해설
    · claude.ai 저장소(가짜): 불러오기 · 쓰기 · 만든 사람의 검증 지표
    · 기록 주소(가짜 fetch): 이벤트 묶음 전송
    · Firebase(가짜 — 규칙 · 빈 칸 · 겹친 배열을 실제처럼 거부): 익명 참여자 문서 · #owner Google 로그인 → 검증 지표 · 설정이 없으면 SDK 를 받지 않는다
  블루프린트(web/index.html)
    · 카드 수 × 보기 3 번 재생 — 결과 배지가 채점과 같은가

애니메이션은 requestAnimationFrame 을 타이머로 바꿔 가상 시간으로 돌린다. Math.random 은 씨앗을 고정해 매번 같은 판이 나온다.
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
       'Math.random=(function(){var s=20261003;return function(){s=s*16807%2147483647;return (s-1)/2147483646;};})();'
       '</script>{MOCK}</head><body>')

GAME_PROBE = r"""<script>
(function(){
var LOG=[];function q(s){return document.querySelector(s);}
// 무대가 어떻게 열렸는지(pose · intro · link …, '+' = 앞 장면에서) · 이어 붙인 거리(m)를 기록한다
var _sh=Court.Stage.prototype.show,SHOWS=[],LINKS=[];
function dm(a,b){return Math.hypot((a[0]-b[0])*10.97,(a[1]-b[1])*23.77);}
Court.Stage.prototype.show=function(c,o){
  if(this.svg===q('#stage')&&o){SHOWS.push((o.mode||'')+(o.from?'+':''));
    if(o.mode==='link'&&o.from){var st=c.setup,F=o.from.pos;
      LINKS.push({ball:!!o.from.ball,me:dm(F.me,st.me.xy),pa:dm(F.partner,st.partner.xy),kind:Court.linkKind(c,o.from),
        op:(dm(F.opp1,st.opp1.xy)+dm(F.opp2,st.opp2.xy))/2,
        // 다시 치기 — 방금 친 우리 공이 우리 쪽으로 돌아와 우리가 또 친다(same 이 아닌데 우리 쪽 도입 공)
        replay:!!o.from.ball&&o.from.ball.by==='us'&&Court.linkKind(c,o.from)==='next'&&st.ball.arc!=='hold'&&st.ball.from[1]>.5});}}
  return _sh.apply(this,arguments);};
function linkStat(){var mid=LINKS.filter(function(x){return x.ball;}),s={n:LINKS.length,mid:mid.length,me:0,pa:0,op:0,max:0,replay:0,same:0};
  mid.forEach(function(x){s.me+=x.me/mid.length;s.pa+=x.pa/mid.length;s.op+=x.op/mid.length;if(x.replay)s.replay++;if(x.kind==='same')s.same++;});
  LINKS.forEach(function(x){s.max=Math.max(s.max,x.me,x.pa);});return s;}
function vis(){var r=[];['home','play','done','chapter','stats','match','hello'].forEach(function(n){var el=q('#s-'+n);if(el&&!el.hidden)r.push(n);});return r.join(',');}
function snap(tag){var say=q('#p-say'),t=q('#toast');
  var cap=q('#gs-cap');
  LOG.push({tag:tag,screen:vis(),count:q('#bar-play').hidden?'':q('#scount').textContent,dots:document.querySelectorAll('#sdots i').length,
    phase:q('#gs').getAttribute('data-phase'),cap:cap.hidden?null:cap.textContent,rev:!q('#gs-rev').hidden,badge:q('#gs-rev').hidden?null:q('#gs-rev').textContent,
    bridge:q('#gs-bridge').hidden?null:q('#gs-bridge').textContent,chain:q('#c-chain').hidden?null:q('#k-n').textContent,sheet:!q('#p-verdict').hidden,
    score:q('#mscore').hidden?null:q('#mscore').getAttribute('aria-label'),clock:q('#gs-clock').hidden?null:q('#gs-clock').textContent,
    mrec:q('#m-rec').textContent,hl:q('#s-hello').hidden?null:q('#hl-head').textContent+' | '+q('#nick-go').textContent,nerr:!q('#nick-err').hidden,
    nick:q('#h-nick').textContent,id:q('#p-id').textContent,tapt:q('#gs-tap').textContent,tut:q('.sh-taste')?q('.sh-taste').textContent:null,
    shows:SHOWS.slice(-3).join(','),links:linkStat(),ownerln:!q('#h-owner').hidden,where:!q('#h-where').hidden,
    fsw:window.__FSW||0,fskeys:window.__FS?Object.keys(window.__FS).sort().join(','):null,fbcfg:window.__FBCFG?window.__FBCFG.projectId:null,
    fsdoc:window.__FS&&window.__FS['players/anon1']?{nick:window.__FS['players/anon1'].nick,taste:!!window.__FS['players/anon1'].taste,answered:window.__FS['players/anon1'].answered}:null,
    gst:document.querySelectorAll('script[src*="gstatic"]').length,errs:q('#s-stats').hidden?null:(q('#st-body').textContent.match(/기기 오류 \d+/)||[null])[0],dcards:q('#d-cards').hidden?null:q('#d-cards').textContent.slice(0,120),dhead:q('#s-done').hidden?null:q('#d-head').textContent,dxp:q('#s-done').hidden?null:q('#d-xp').textContent,hc:q('#d-hc').hidden?null:q('#d-hc').textContent,reps:q('.rlist')?q('.rlist').textContent:null,
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
function nick(v){q('#nick-in').value=v;click('#nick-go');}
// 실전 — 포인트가 났으면 '다음 포인트 →', 랠리가 이어지는 중이면 버튼 없이 저절로 넘어간다(코트를 누르면 바로)
function next(){if(q('[data-act=match-next]'))click('[data-act=match-next]');else tap();}
var g={q:q,click:click,snap:snap,pick:pick,opt:opt,tap:tap,ask:ask,nick:nick,next:next},STEPS=__STEPS__;
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

# Firebase compat SDK 의 가짜 — 규칙(firebase/firestore.rules)과 같은 권한, 실제 Firestore 처럼 undefined · 겹친 배열을 거부한다
FB_MOCK = r"""<script>
window.__FS={'players/u_a':{v:1,answered:30,total:30,taste:{v:'정답'},days:['2026-09-18','2026-09-26'],cards:{'C1-01':{f:'정답',l:'정답',n:1,ms:4000}},reports:[]}};
window.__FSW=0;window.__FBCFG=null;
(function(){
  var user=null,cbs=[],nAnon=0,ignoreUndef=false;
  function fire(){cbs.slice().forEach(function(cb){setTimeout(function(){cb(user);},0);});}
  function denied(){var e=new Error('Missing or insufficient permissions.');e.code='permission-denied';return Promise.reject(e);}
  function bad(v,inArr){if(v===undefined)return ignoreUndef?null:'undefined';
    if(Array.isArray(v)){if(inArr)return 'nested array';for(var i=0;i<v.length;i++){var r=bad(v[i],true);if(r)return r;}return null;}
    if(v&&typeof v==='object'){for(var k in v){var r2=bad(v[k],false);if(r2)return r2+' @'+k;}}return null;}
  function own(p){return !!user&&p.split('/')[1]===user.uid;}
  function owner(){return !!user&&!user.isAnonymous&&user.email==='owner@example.com';}
  var auth={onAuthStateChanged:function(cb){cbs.push(cb);setTimeout(function(){cb(user);},0);return function(){var i=cbs.indexOf(cb);if(i>=0)cbs.splice(i,1);};},
    signInAnonymously:function(){nAnon++;user={uid:'anon'+nAnon,isAnonymous:true,email:null};fire();return Promise.resolve({user:user});},
    signInWithPopup:function(){user={uid:'g_owner',isAnonymous:false,email:'owner@example.com'};fire();return Promise.resolve({user:user});}};
  Object.defineProperty(auth,'currentUser',{get:function(){return user;}});
  var fs={settings:function(o){if(o&&o.ignoreUndefinedProperties)ignoreUndef=true;},
    doc:function(p){return {get:function(){if(!(own(p)||owner()))return denied();var d=window.__FS[p];
        return Promise.resolve({exists:!!d,id:p.split('/')[1],data:function(){return d?JSON.parse(JSON.stringify(d)):undefined;}});},
      set:function(d){if(!own(p))return denied();var b=bad(d,false);
        if(b){var e=new Error('Unsupported field value: '+b);e.code='invalid-argument';window.__FSBAD=b;return Promise.reject(e);}
        window.__FSW++;window.__FS[p]=JSON.parse(JSON.stringify(d));return Promise.resolve();}};},
    collection:function(c){var q={get:function(){if(!owner())return denied();
        var docs=Object.keys(window.__FS).filter(function(k){return k.indexOf(c+'/')===0;}).map(function(k){var d=window.__FS[k];
          return {exists:true,id:k.split('/')[1],data:function(){return JSON.parse(JSON.stringify(d));}};});
        return Promise.resolve({docs:docs,size:docs.length,empty:!docs.length});},limit:function(){return q;}};return q;}};
  var app={auth:function(){return auth;},firestore:function(){return fs;}};
  window.firebase={apps:[],initializeApp:function(cfg){window.__FBCFG=cfg;this.apps.push(app);return app;},app:function(){return app;},
    auth:{GoogleAuthProvider:function(){}},firestore:function(){return fs;}};
})();
</script>"""
FB_CFG = {"firebase": {"apiKey": "test-key", "authDomain": "dmb-test.firebaseapp.com", "projectId": "dmb-test", "appId": "1:1:web:1"}}

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


def game(name, steps, state=None, mock="", config=None, budget=20000, motion=False, cfg=None, hash=""):
    page = (WEB / "play.html").read_text(encoding="utf-8")
    if config:
        page = page.replace('"endpoint": ""', '"endpoint": "%s"' % config)
    if cfg:   # play.config.json 칸을 바꿔 넣는다 (예: firebase)
        m = re.search(r'<script id="config-data" type="application/json">(.*?)</script>', page, re.S)
        c = json.loads(m.group(1))
        c.update(cfg)
        page = page[:m.start(1)] + json.dumps(c, ensure_ascii=False) + page[m.end(1):]
    st = ('try{localStorage.setItem("dmb-game-v1",' + json.dumps(json.dumps(state, ensure_ascii=False)) + ')}catch(e){}'
          if state else 'try{localStorage.removeItem("dmb-game-v1")}catch(e){}')
    if hash:
        st += "history.replaceState(null,'','%s');" % hash
    pre = PRE.replace("{REDUCED}", "false" if motion else "true")
    return run(name, pre.replace("{STATE}", st).replace("{MOCK}", mock) + page
               + GAME_PROBE.replace("__STEPS__", json.dumps(steps, ensure_ascii=False)), budget)


def state(answers):
    today = datetime.date.today()
    day = lambda n: (today + datetime.timedelta(days=n)).isoformat()
    s = {"v": 1, "uid": "p_smoke", "nick": "테스터", "created": day(-5) + "T01:00:00Z", "opens": 2, "onboarded": True,
         "taste": {"v": "정답", "o": 0, "ms": 4000, "at": day(-5) + "T01:00:00Z"}, "cards": {}, "xp": 0,
         "days": [day(-3), day(-2)], "sessions": 1, "rank": "신인부", "rankUp": None, "session": None,
         "reports": [], "wait": None, "ev": []}
    for cid, v, due in answers:
        s["cards"][cid] = {"f": v, "l": v, "n": 1, "ms": 5000, "at": day(-2) + "T10:00:00Z",
                           "due": None if due is None else day(due), "track": None if v == "정답" else v, "box": 0}
    return s


NEXT = [[120, "g.pick()"], [120, "g.click('[data-act=explain]')"], [120, "g.click('[data-act=next]')"]]
NEWBIE = {"v": 1, "uid": "p_new", "nick": "희철", "cards": {}}   # 닉네임만 정하고 아직 아무것도 안 푼 사람
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

    # 1) 처음 온 사람 — 닉네임을 묻고, 첫 카드는 튜토리얼
    log = game("new", [[150, "g.snap('hello')"], [150, "g.click('#nick-go')"], [150, "g.snap('empty')"], [150, "g.nick('희철')"],
                       [150, "g.snap('t0')"], [150, "g.ask()"], [150, "g.snap('ask')"], [150, "g.opt(0)"], [150, "g.snap('result')"],
                       [150, "g.tap()"], [150, "g.snap('taste')"], [150, "g.click('[data-act=taste-start]')"], [150, "g.snap('s1')"]] + NEXT * 4 +
               [[120, "g.pick('실수')"], [120, "g.tap()"], [120, "g.click('[data-act=finish]')"], [150, "g.snap('done')"],
                [150, "g.click('[data-act=home]')"], [150, "g.snap('home')"]])
    hl, em, s0, a, r, t, s1, d, h = (last(log, k) for k in ("hello", "empty", "t0", "ask", "result", "taste", "s1", "done", "home"))
    c24 = next(c for c in CARDS if c["id"] == "C1-24")
    check("처음 온 사람은 닉네임부터 — '반가워요!' · 튜토리얼 시작 →", hl and hl["screen"] == "hello" and "반가워요" in (hl["hl"] or "")
          and "튜토리얼 시작 →" in (hl["hl"] or ""), hl)
    check("닉네임이 비면 안내하고 그대로", em and em["screen"] == "hello" and em["nerr"], em)
    check("닉네임을 적으면 튜토리얼 — 어두운 코트에 〈제목〉 · '튜토리얼 1/4'", s0 and s0["screen"] == "play" and s0["count"] == "튜토리얼 · 1분"
          and s0["badge"] == "튜토리얼" and s0["phase"] == "title" and c24["title"] in s0["title"] and s0["tapt"].startswith("튜토리얼 1/4"), s0)
    check("코트를 누르면 상황 글을 거쳐 질문 띠", a and a["phase"] == "ask" and c24["question"]["text"] in (a["cap"] or "")
          and a["scene"] == c24["scene"], a)
    check("고르면 결과 배지 — 해설은 누를 때까지 안 나온다 · '튜토리얼 4/4'", r and r["phase"] == "result" and r["say"] and r["say"][0] in "✓△✕"
          and not r["sheet"] and "해설 보기" in r["dock"] and "튜토리얼 4/4" in r["dock"], r)
    check("코트를 누르면 해설 시트 — '튜토리얼 끝이에요, 희철님'", t and t["phase"] == "verdict" and t["sheet"]
          and "튜토리얼 끝이에요, 희철님" in (t["tut"] or ""), t)
    check("시작하기 → 오늘의 코트 5장", s1 and s1["count"] == "1 / 5" and s1["dots"] == 5, s1)
    check("한 판 결과 — 성공 4 · 실패 1", d and d["screen"] == "done" and "성공 4" in d["tally"] and "실패 1" in d["tally"], d)
    check("홈 진도 5장 · 닉네임", h and h["prog"].startswith("5/") and h["nick"] == "희철", h)
    check("오류 없음 (처음 온 사람)", h and not h["err"], h and h["err"])

    # 1a) 기록은 있는데 닉네임이 없는 사람(앞 판에서 온 사람) — 닉네임만 묻고 홈. 홈에서 바꿀 수 있다
    st = state([(cid, "정답", None) for cid in IDS[:5]])
    st["nick"] = ""
    log = game("nick", [[150, "g.snap('n0')"], [150, "g.nick('  철수  ')"], [150, "g.snap('n1')"], [150, "g.click('[data-act=nick]')"],
                        [150, "g.snap('n2')"], [150, "g.nick('영희')"], [150, "g.snap('n3')"]], st)
    n0, n1, n2, n3 = (last(log, k) for k in ("n0", "n1", "n2", "n3"))
    check("닉네임이 없는 옛 기록 — 닉네임만 묻는다(튜토리얼 없이)", n0 and n0["screen"] == "hello" and "반가워요" not in (n0["hl"] or "")
          and "확인" in (n0["hl"] or ""), n0)
    check("적으면 홈으로 — 앞뒤 빈칸은 지운다", n1 and n1["screen"] == "home" and n1["nick"] == "철수", n1)
    check("홈에서 닉네임 바꾸기", n2 and n2["screen"] == "hello" and "바꿀까요" in (n2["hl"] or "") and n3 and n3["nick"] == "영희"
          and not n3["err"], (n2, n3))

    # 1b) 누를 때만 넘어간다 — 움직임을 켠 기기에서 공이 실제로 날 때. 오래 기다려도 혼자 넘어가지 않는다
    log = game("tap", [[9000, "g.snap('t1')"], [100, "g.tap()"], [8000, "g.snap('t2')"], [9000, "g.snap('t3')"],
                       [100, "g.tap()"], [300, "g.snap('t4')"], [100, "g.opt(0)"], [100, "g.snap('t5')"], [8000, "g.snap('t6')"],
                       [9000, "g.snap('t7')"], [100, "g.tap()"], [300, "g.snap('t8')"]], NEWBIE, motion=True, budget=70000)
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

    # 4b) 원 포인트 게임!(옛 두 수 앞) — 첫 수가 정답이면 두 번째 수가 그 장면에서 이어진다, 아니면 다음 랠리 (PRD 결정 #25 #27)
    log = game("chain", [[150, "g.snap('k0')"], [150, "g.click('[data-act=chain-start]')"], [150, "g.snap('k1')"],
                         [150, "g.pick()"], [150, "g.click('[data-act=explain]')"], [150, "g.snap('v1')"],
                         [150, "g.click('[data-act=chain-next]')"], [150, "g.snap('k2')"], [150, "g.ask()"], [150, "g.snap('q2')"],
                         [150, "g.pick()"], [150, "g.click('[data-act=explain]')"], [150, "g.click('[data-act=chain-next]')"],
                         [150, "g.snap('k3')"], [150, "g.pick('실수')"], [150, "g.click('[data-act=explain]')"], [150, "g.snap('v3')"],
                         [150, "g.click('[data-act=chain-next]')"], [200, "g.snap('done')"], [150, "g.click('[data-act=home]')"],
                         [150, "g.snap('home2')"]],
               state([(cid, "정답", None) for cid in ("C2-08", "C3-09")]))
    h, a1, a1v, b1, bq, a2, a2v, d, h2 = (last(log, t) for t in ("k0", "k1", "v1", "k2", "q2", "k3", "v3", "done", "home2"))
    check("원 포인트 게임! — 첫 카드를 푼 랠리가 홈에 열린다", h and h["chain"] == "이은 랠리 0 / 2", h)
    check("첫 수 → 정답이면 '두 번째 수 →'", a1 and a1["badge"] == "첫 수" and a1["count"] == "랠리 1 / 2" and a1["dots"] == 4
          and a1["shows"].endswith("pose") and a1v and "두 번째 수 →" in a1v["dock"], (a1, a1v))
    check("두 번째 수는 첫 수가 끝난 모습 그대로 서 있다가 이어진다", b1 and b1["badge"] == "두 번째 수" and b1["bridge"] == "앞 수에서 이어져요"
          and b1["title"] == "〈세컨 리턴 후 전진, 어디까지 갈까요〉" and b1["shows"].endswith("pose+") and bq and bq["phase"] == "ask"
          and "link+" in bq["shows"], (b1, bq))
    check("새 랠리의 첫 수는 이어 오지 않는다", a2 and a2["shows"].endswith("pose") and a2["badge"] == "첫 수", a2)
    check("첫 수가 실수면 끊긴다 → 결과 보기", a2v and "정답이어야 이어져요" in a2v["dock"] and "결과 보기" in a2v["dock"], a2v)
    check("원 포인트 게임 결과 — 이은 랠리 1 · 끊긴 랠리 1", d and d["tally"] == "✓ 이은 랠리 1✕ 끊긴 랠리 1" and not d["err"], d)
    check("이은 랠리가 홈에 남는다", h2 and h2["chain"] and h2["chain"].startswith("이은 랠리 1 /"), h2)
    # 두 번째 수가 같은 포인트의 서브 순간이면 이어 오지 않고 돌아간다고 알린다 (C1-01 → C1-07)
    log = game("chainrw", [[150, "g.click('[data-act=chain-start]')"], [150, "g.pick()"], [150, "g.click('[data-act=explain]')"],
                           [150, "g.click('[data-act=chain-next]')"], [150, "g.snap('w')"]], state([("C1-01", "정답", None)]))
    w = last(log, "w")
    check("서브로 돌아가는 두 번째 수 — '서브 순간으로 돌아가요' · 이어 오지 않는다", w and w["badge"] == "두 번째 수"
          and w["bridge"] == "같은 포인트 · 서브 순간으로 돌아가요" and w["shows"].endswith("pose") and not w["err"], w)

    # 4c) 실전 모드 — 츄어리와 한 게임 (10초 룰 + 랠리, PRD 결정 #26 #27)
    WIN = "for(var k=0;k<40;k++){if(!g.q('#s-done').hidden)break;g.pick('정답');g.next();}"
    LOSE = "for(var k=0;k<40;k++){if(!g.q('#s-done').hidden)break;g.pick('실수');g.next();}"
    log = game("match", [[150, "g.snap('h0')"], [150, "g.click('[data-act=match-open]')"], [150, "g.snap('lobby')"],
                         [150, "g.click('[data-act=match-lv][data-lv=\"1\"]')"], [150, "g.snap('lv')"],
                         [150, "g.click('[data-act=match-start]')"], [150, "g.snap('ask')"], [150, "g.pick('차선')"], [150, "g.snap('edge')"],
                         [2200, "g.snap('auto')"], [150, WIN], [200, "g.snap('won')"],
                         [150, "g.click('[data-act=mreview][data-i=\"0\"]')"], [150, "g.snap('rv')"], [150, "g.click('[data-act=mback]')"],
                         [150, "g.snap('back')"], [150, "g.click('[data-act=match-start]')"], [150, LOSE], [200, "g.snap('lost')"],
                         [150, "g.click('[data-act=home]')"], [150, "g.snap('h1')"]],
               state([(cid, "정답", None) for cid in IDS[:5]]))
    h0, lb, lv, ak, ed, au, wn, rv, bk, ls, h1 = (last(log, t) for t in ("h0", "lobby", "lv", "ask", "edge", "auto", "won", "rv", "back", "lost", "h1"))
    check("실전 모드 — 처음부터 홈에 있다 · 츄어리 로비", h0 and h0["mrec"] == "첫 경기" and lb and lb["screen"] == "match" and lb["lvs"] == "5", (h0, lb))
    check("츄어리 실력 고르기 — 1부(120장)", lv and lv["lvs"] == "1", lv)
    check("경기 — 제목 없이 질문까지 · 10초 시계 · 점수판에 닉네임", ak and ak["phase"] == "ask" and ak["clock"] == "10"
          and ak["score"] == "테스터 0, 츄어리 0" and ak["cap"] and len(ak["cap"]) > 10 and ak["shows"].endswith("intro"), ak)
    check("차선 — 랠리가 이어지고 츄어리가 한 발 앞선다 · 누르지 않아도 다음 공", ed and ed["phase"] == "result"
          and "츄어리가 한 발 앞서요" in ed["dock"] and "잠깐, 해설 볼게요" in ed["dock"] and "다음 공" not in ed["dock"], ed)
    check("랠리가 저절로 이어진다 — 앞 장면에서 다음 카드로(순간이동 없음)", au and ed and au["phase"] == "ask" and au["id"] != ed["id"]
          and au["shows"].endswith("link+") and au["score"] == "테스터 0, 츄어리 0" and au["clock"] in ("10", "9"), au)
    check("다 맞히면 츄어리를 이긴다 — 이번 게임의 카드 목록", wn and wn["screen"] == "done" and wn["dhead"] == "테스터님이 츄어리를 이겼어요!"
          and wn["hc"] and "제가 졌어요" in wn["hc"] and "눌러서 해설" in (wn["dcards"] or "") and not wn["err"], wn)
    check("경기 뒤 카드를 누르면 해설 → 경기 결과로", rv and rv["screen"] == "play" and rv["count"].endswith("다시 보기") and rv["sheet"]
          and bk and bk["screen"] == "done" and bk["dhead"] == wn["dhead"], (rv, bk))
    check("다 틀리면 츄어리에게 진다 — 포인트 0 : 4", ls and ls["dhead"] == "테스터님, 츄어리에게 졌어요" and ls["hc"] and "다시 붙어요" in ls["hc"]
          and "포인트 0 : 4" in (ls["dxp"] or ""), ls)
    check("츄어리 상대 전적이 홈에 남는다", h1 and h1["mrec"] == "1승 1패" and not h1["err"], h1)

    # 4d) 랠리 잇기 — 여러 게임을 이어 치며 앞 장면에서 다음 카드까지의 거리를 잰다 (무작위로 고르면 내 자리 평균 6 m)
    RALLY = ("for(var k=0;k<70;k++){if(!g.q('#s-done').hidden)g.click('[data-act=match-start]');"
             "g.pick(['정답','차선','정답','정답'][k%4]);g.next();}")
    log = game("rally", [[150, "g.click('[data-act=match-open]')"], [150, "g.click('[data-act=match-lv][data-lv=\"1\"]')"],
                         [150, "g.click('[data-act=match-start]')"], [150, RALLY], [200, "g.snap('r')"]],
               state([(cid, "정답", None) for cid in IDS[:5]]))
    r = last(log, "r")
    lk = (r or {}).get("links") or {}
    check(f"랠리 중 이어 붙이기 {lk.get('mid', 0)}번 — 내 자리 평균 {lk.get('me', 0):.1f} m · 친 공을 다시 치지 않는다",
          lk.get("mid", 0) >= 8 and lk.get("me", 99) < 3.5 and lk.get("pa", 99) < 4 and lk.get("op", 99) < 4 and lk.get("replay", 1) == 0
          and not r["err"], lk)

    log = game("match10", [[150, "g.click('[data-act=match-open]')"], [150, "g.click('[data-act=match-start]')"],
                           [5000, "g.snap('t5')"], [5600, "g.snap('to')"], [150, "g.click('[data-act=explain]')"], [150, "g.snap('tv')"]],
               state([(cid, "정답", None) for cid in IDS[:5]]), budget=30000)
    t5, to, tv = last(log, "t5"), last(log, "to"), last(log, "tv")
    check("10초 — 시계가 줄어든다", t5 and t5["clock"] in ("6", "5", "4"), t5)
    check("10초가 지나면 시간 초과 — 츄어리 포인트", to and to["say"] and "시간 초과" in to["say"] and to["score"] == "테스터 0, 츄어리 15"
          and "포인트 — 츄어리" in to["dock"], to)
    check("시간 초과 해설 — 정답 장면과 이유", tv and tv["sheet"] and not tv["err"], tv)
    # 다른 앱에 가 있는 동안 저절로 다음 공이 와도, 시계는 돌아온 뒤부터 센다
    HIDE = ("window.__H=false;Object.defineProperty(document,'hidden',{configurable:true,get:function(){return window.__H;}});"
            "window.__vis=function(h){window.__H=h;document.dispatchEvent(new Event('visibilitychange'));};")
    log = game("matchhid", [[150, HIDE], [150, "g.click('[data-act=match-open]')"], [150, "g.click('[data-act=match-start]')"],
                            [150, "g.pick('차선')"], [100, "window.__vis(true)"], [14000, "window.__vis(false)"], [300, "g.snap('back')"],
                            [3000, "g.snap('later')"]],
               state([(cid, "정답", None) for cid in IDS[:5]]), budget=40000)
    bk, lt = last(log, "back"), last(log, "later")
    check("숨은 동안 저절로 넘어온 질문 — 돌아온 뒤부터 10초", bk and bk["phase"] == "ask" and bk["clock"] == "10" and lt
          and lt["clock"] in ("8", "7", "6") and not (lt["say"] or "").startswith("⏱"), (bk, lt))
    log = game("taste2match", [[150, "g.opt(1)"], [150, "g.tap()"], [150, "g.click('[data-act=taste-match]')"], [150, "g.snap('lb')"]], NEWBIE)
    tm = last(log, "lb")
    check("처음 온 사람 — 튜토리얼 뒤 '츄어리와 실전 →'", tm and tm["screen"] == "match" and not tm["err"], tm)

    # 5) claude.ai 저장소 (가짜)
    log = game("db", [[300, "g.snap('home')"], [150, "g.click('#t-cta')"], [150, "g.pick('차선')"], [300, "g.snap('answered')"],
                      [150, "g.click('[data-act=explain]')"], [150, "g.click('[data-act=report]')"],
                      [150, "g.q('#rep-note').value='리시버가 늦으면 B 도 맞아요'"], [150, "g.click('#rep-form [type=submit]')"],
                      [150, "g.click('#b-x')"], [150, "g.click('[data-act=stats]')"], [400, "g.snap('stats')"]],
               state([(cid, "정답", None) for cid in IDS[:5]]), mock=DB_MOCK)
    h, a, s = last(log, "home"), last(log, "answered"), last(log, "stats")
    check("저장소 — 불러온 뒤 한 번 동기화, 만든 사람 링크", h and h["writes"] == 1 and h["owner"], h)
    check("저장소 — 답할 때마다 쓴다", a and a["writes"] >= 3, a)
    check("검증 지표 — 참여자 두 명 집계", s and s["stats"] and s["stats"].startswith("2튜토리얼") and not s["err"], s)
    check("감수 메모 — 신고에 적은 한 줄이 검증 지표에 모인다", s and s["reps"] and "리시버가 늦으면 B 도 맞아요" in s["reps"]
          and "그림이 헷갈려요" in s["reps"] and "테스터" in s["reps"], s and s["reps"])

    # 5b) 참여자 기기에서 난 오류가 기록되고, 만든 사람의 검증 지표에 보인다
    log = game("errlog", [[300, "setTimeout(function(){null.boom();},0)"], [300, "g.click('[data-act=stats]')"], [400, "g.snap('st')"]],
               state([(cid, "정답", None) for cid in IDS[:5]]), mock=DB_MOCK)
    s = last(log, "st")
    check("기기 오류 — 이벤트로 남고 검증 지표에 '기기 오류 1'", s and s["errs"] == "기기 오류 1", s and (s["errs"], s["err"]))

    # 6) 기록 주소 (가짜 fetch)
    log = game("http", [[150, "g.nick('희철')"], [150, "g.opt(1)"], [150, "g.tap()"], [150, "g.click('[data-act=taste-start]')"],
                        [150, "g.pick()"], [2200, "g.snap('sent')"]], mock=FETCH_MOCK, config="https://example.invalid/log")
    s = last(log, "sent")
    sent = [e for b in (s or {}).get("sent") or [] for e in b["e"]]
    check("기록 주소로 이벤트 묶음 전송 (no-cors)", s and "answer" in sent and "taste" in sent and "nick" in sent
          and all(b["mode"] == "no-cors" for b in s["sent"]), s)

    # 6b) 정적 호스팅용 site/index.html — 문서 뼈대째. 표준 모드 · 제목 · 처음 온 사람은 닉네임부터
    site = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    head = site[:site.index("<body>")]
    probe = ('<script>setTimeout(function(){var v=document.querySelector("meta[name=viewport]");document.body.setAttribute("data-m",JSON.stringify([{tag:"site",'
             'mode:document.compatMode,title:document.title,vp:v?v.content:"",cs:document.characterSet,hello:!document.querySelector("#s-hello").hidden}]));},900);</script>')
    page = site.replace("<head>\n", "<head>\n<script>try{localStorage.removeItem('dmb-game-v1')}catch(e){}</script>\n", 1)
    out = run("site", page.replace("</body>", probe + "</body>"), 8000)
    o = (out or [{}])[0]
    check("정적 호스팅용 페이지 — 표준 모드 · UTF-8 · viewport · 미리보기 글", site.startswith("<!doctype html>") and site.count("<body>") == 1
          and "<title>" in head and 'property="og:title"' in head and o.get("mode") == "CSS1Compat" and o.get("cs") == "UTF-8"
          and "width=device-width" in o.get("vp", "") and o.get("title") == "복식 무브" and o.get("hello"), o)

    # 6c) Firebase (GitHub Pages 판, PRD #29) — 가짜 SDK 로. 익명 참여자는 자기 문서만, #owner 에서 Google 로그인하면 검증 지표
    log = game("fb", [[400, "g.snap('f0')"], [150, "g.opt(0)"], [400, "g.snap('f1')"]], NEWBIE, mock=FB_MOCK, cfg=FB_CFG)
    f0, f1 = last(log, "f0"), last(log, "f1")
    check("Firebase — 익명 로그인 · 튜토리얼 답이 참여자 문서에 (빈 칸 · 겹친 배열 없이)", f0 and f0["fbcfg"] == "dmb-test" and f1
          and f1["fsdoc"] and f1["fsdoc"]["nick"] == "희철" and f1["fsdoc"]["taste"] and f1["fsw"] >= 1 and not f1["err"], (f0, f1))
    log = game("fbowner", [[400, "g.snap('o0')"], [150, "g.click('[data-act=owner-login]')"], [400, "g.snap('o1')"],
                           [150, "g.click('[data-act=stats]')"], [400, "g.snap('o2')"]],
               state([(cid, "정답", None) for cid in IDS[:5]]), mock=FB_MOCK, cfg=FB_CFG, hash="#owner")
    o0, o1, o2 = last(log, "o0"), last(log, "o1"), last(log, "o2")
    check("Firebase — 참여자는 남의 기록을 못 본다 · 주소 #owner 에만 '만든 사람 로그인' · 저장 위치 안내", o0 and o0["ownerln"]
          and not o0["owner"] and o0["where"] and "players/anon1" in (o0["fskeys"] or ""), o0)
    check("Firebase — Google 로그인한 만든 사람 → 검증 지표에 모든 참여자", o1 and o1["owner"] and not o1["ownerln"]
          and "만든 사람으로 로그인" in (o1["toast"] or "") and o2 and o2["stats"] and o2["stats"].startswith("3")
          and "players/g_owner" in (o2["fskeys"] or "") and not o2["err"], (o1, o2))
    log = game("fboff", [[300, "g.snap('x')"]], state([(cid, "정답", None) for cid in IDS[:5]]), hash="#owner")
    x = last(log, "x")
    check("Firebase 설정이 없으면 SDK 를 받지 않는다 · 로그인 링크도 없다", x and x["gst"] == 0 and not x["ownerln"] and not x["where"]
          and not x["err"], x)

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
