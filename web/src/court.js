/* 복식 무브 — 코트 엔진: 3D 코트 · 공 궤적 · 도입 멈춤 · 결과 재생.
   web/build.py 가 각 페이지의 COURT_JS 자리에 그대로 넣는다 (블루프린트 페이지와 검증판 게임이 같은 엔진을 쓴다).
   기하는 tools/court3d.py 와 같고, 결과 장면은 tools/validate_cards.py 의 check_play 와 같은 순서로 따라간다.
   쓰는 법: Court.init(cameras.json) → var st = new Court.Stage(svg, 배지) → st.show(카드, {view, pick, shown, mode}, 끝났을_때) */
var Court=(function(){
"use strict";
var CAM,W,H,BCAM;
var REDUCED=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
function init(cam){CAM=cam;W=cam.stage.w;H=cam.stage.h;BCAM=broadcastCam();}

/* ═════════ 3D 코어 — tools/court3d.py 와 같은 식 ═════════ */
var CW=10.97, CL=23.77, NETY=CL/2, SGL=4.115, SVC=6.40;
var COLS={L:[0,1/3],C:[1/3,2/3],R:[2/3,1]};
var ROWS={A:{N:[.5,.64],M:[.64,.86],B:[.86,1],X:[1,1.098]},E:{N:[.36,.5],M:[.14,.36],B:[0,.14],X:[-.098,0]}};
function world(xy,z){return [(xy[0]-.5)*CW,(1-xy[1])*CL,z||0];}
function sub(a,b){return [a[0]-b[0],a[1]-b[1],a[2]-b[2]];}
function dot(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
function cross(a,b){return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];}
function norm(a){var l=Math.sqrt(dot(a,a))||1;return [a[0]/l,a[1]/l,a[2]/l];}
function Cam(eye,look,focal,cx,cy,near){
  this.eye=eye;this.focal=focal;this.cx=cx;this.cy=cy;this.near=near||0.3;
  this.f=norm(sub(look,eye));this.r=norm(cross(this.f,[0,0,1]));this.u=cross(this.r,this.f);
}
Cam.prototype.c=function(p){var d=sub(p,this.eye);return [dot(d,this.r),dot(d,this.u),dot(d,this.f)];};
Cam.prototype.s=function(c){return [this.cx+this.focal*c[0]/c[2],this.cy-this.focal*c[1]/c[2]];};
Cam.prototype.p=function(p){var c=this.c(p);return c[2]<this.near?null:this.s(c);};
Cam.prototype.ppm=function(p){var c=this.c(p);return c[2]<this.near?0:this.focal/c[2];};
function broadcastCam(){
  var b=CAM.broadcast,el=b.elev*Math.PI/180,look=[0,b.lookY,0];
  var eye=[0,b.lookY-b.dist*Math.cos(el),b.dist*Math.sin(el)];
  var u=new Cam(eye,look,1,0,0),xs=[],ys=[];
  b.fit.x.forEach(function(x){b.fit.y.forEach(function(y){b.fit.z.forEach(function(z){
    var q=u.s(u.c([x,y,z]));xs.push(q[0]);ys.push(q[1]);});});});
  var mnx=Math.min.apply(0,xs),mxx=Math.max.apply(0,xs),mny=Math.min.apply(0,ys),mxy=Math.max.apply(0,ys);
  var pd=b.pad,aw=W-pd.left-pd.right,ah=H-pd.top-pd.bottom,s=Math.min(aw/(mxx-mnx),ah/(mxy-mny));
  var ox=pd.left+(aw-s*(mxx-mnx))/2-s*mnx, oy=pd.top+(ah-s*(mxy-mny))/2-s*mny;
  return new Cam(eye,look,s,ox,oy,0.3);
}
function meCam(meXY){
  var m=CAM.me,w=world(meXY);
  return new Cam([w[0],w[1]-m.back,m.height],[w[0]*(1-m.yawToCenter),w[1]+m.ahead,m.lookZ],m.focal*H,W/2,m.cy*H,m.near);
}

/* 근평면 자르기 + 투영 */
function clipNear(cam,poly3){
  var cs=poly3.map(function(p){return cam.c(p);}),out=[],n=cam.near;
  for(var i=0;i<cs.length;i++){
    var a=cs[i],b=cs[(i+1)%cs.length],ia=a[2]>=n,ib=b[2]>=n;
    if(ia)out.push(a);
    if(ia!==ib){var t=(n-a[2])/(b[2]-a[2]);out.push([a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,n]);}
  }
  return out.map(function(c){return cam.s(c);});
}
function clipRect(pts,x0,y0,x1,y1){
  var E=[[function(p){return p[0]>=x0;},function(a,b){var t=(x0-a[0])/(b[0]-a[0]);return [x0,a[1]+(b[1]-a[1])*t];}],
         [function(p){return p[0]<=x1;},function(a,b){var t=(x1-a[0])/(b[0]-a[0]);return [x1,a[1]+(b[1]-a[1])*t];}],
         [function(p){return p[1]>=y0;},function(a,b){var t=(y0-a[1])/(b[1]-a[1]);return [a[0]+(b[0]-a[0])*t,y0];}],
         [function(p){return p[1]<=y1;},function(a,b){var t=(y1-a[1])/(b[1]-a[1]);return [a[0]+(b[0]-a[0])*t,y1];}]];
  E.forEach(function(e){if(pts.length<3)return;var o=[];for(var i=0;i<pts.length;i++){var a=pts[i],b=pts[(i+1)%pts.length];
    if(e[0](a))o.push(a);if(e[0](a)!==e[0](b))o.push(e[1](a,b));}pts=o;});
  return pts;
}
function ptsStr(pts){return pts.map(function(q){return q[0].toFixed(1)+','+q[1].toFixed(1);}).join(' ');}
function poly(cam,poly3,attrs){var p=clipNear(cam,poly3);return p.length<3?'':'<polygon points="'+ptsStr(p)+'" '+attrs+'/>';}
function seg(cam,a,b,attrs){
  var ca=cam.c(a),cb=cam.c(b),n=cam.near;
  if(ca[2]<n&&cb[2]<n)return '';
  if(ca[2]<n){var t=(n-ca[2])/(cb[2]-ca[2]);ca=[ca[0]+(cb[0]-ca[0])*t,ca[1]+(cb[1]-ca[1])*t,n];}
  if(cb[2]<n){var t2=(n-cb[2])/(ca[2]-cb[2]);cb=[cb[0]+(ca[0]-cb[0])*t2,cb[1]+(ca[1]-cb[1])*t2,n];}
  var p=cam.s(ca),q=cam.s(cb);
  return '<line x1="'+p[0].toFixed(1)+'" y1="'+p[1].toFixed(1)+'" x2="'+q[0].toFixed(1)+'" y2="'+q[1].toFixed(1)+'" '+attrs+'/>';
}
function circle3(c,r,z,n){var o=[];for(var i=0;i<(n||20);i++){var t=i/(n||20)*Math.PI*2;o.push([c[0]+r*Math.cos(t),c[1]+r*Math.sin(t),z||0]);}return o;}
function zoneQuad(code){
  var sd=code.charAt(0),col=COLS[code.charAt(2)],row=ROWS[sd][code.charAt(3)];
  return [world([col[0],row[0]]),world([col[1],row[0]]),world([col[1],row[1]]),world([col[0],row[1]])];
}
function zoneCenter(code){var q=zoneQuad(code);return [(q[0][0]+q[2][0])/2,(q[0][1]+q[2][1])/2,0];}
function clamp(v,a,b){return Math.max(a,Math.min(b,v));}

/* ═════════ 공 궤적 — 실제 포물선 ═════════ */
var Z0={serve:2.6,serve2:2.6,smash:2.8,volley:1.0,flat:.9,normal:.9,high:.9,lob:.9};
var BULGE={serve:.12,serve2:.55,flat:.5,normal:1.05,high:2.4,lob:5.6,volley:.3,smash:0};
function arcPts(a,b,k,n){
  // 네트를 넘는 구간이면 네트 위 1m 를 반드시 통과하도록 휨을 키운다
  if((a[1]-NETY)*(b[1]-NETY)<0){
    var t=(NETY-a[1])/(b[1]-a[1]),lin=(1-t)*a[2]+t*b[2],need=(1.0-lin)/(4*t*(1-t));
    if(need>k)k=need+.05;
  }
  var o=[];for(var i=0;i<=n;i++){var s=i/n;
    o.push([a[0]+(b[0]-a[0])*s,a[1]+(b[1]-a[1])*s,(1-s)*a[2]+s*b[2]+4*k*s*(1-s)]);}
  return o;
}
/* 공 데이터(from/bounce/to/arc) → 3D 점열 + 바운드 인덱스 */
function flight(ball,opt){
  opt=opt||{};
  var arc=ball.arc,k=BULGE[arc]||1,z0=opt.z0!=null?opt.z0:(Z0[arc]||1);
  var A=world(ball.from,z0),pts,bi=-1;
  if(ball.bounce){
    var B=world(ball.bounce,0);pts=arcPts(A,B,k,36);bi=pts.length-1;
    if(ball.to){
      var zt=ball.toZ!=null?ball.toZ:.95,k2=Math.max(.35,k*.35);
      pts=pts.concat(arcPts(B,world(ball.to,zt),k2,14).slice(1));
    }
  }else{
    var zt2=ball.toZ!=null?ball.toZ:((arc==='high'||arc==='lob')?2.3:1.1);
    pts=arcPts(A,world(ball.to,zt2),k,40);
  }
  return {pts:pts,bounce:bi};
}
function depthTag(ball){
  if(ball.arc==='serve'||ball.arc==='serve2')return '서브';
  var h={lob:'로브',high:'높게',flat:'낮게'}[ball.arc]||'';
  if(!ball.bounce)return h;
  var d=Math.abs(world(ball.bounce)[1]-NETY),w=d<SVC?'짧게':(d<9.5?'중간':'깊게');
  return h?w+' · '+h:w;
}

/* 리본 + 그림자 + 정점 높이선 + 바운드 링 + 입체 화살촉 */
function ballArt(cam,fl,col,tag,refPpm,avoid,opt){
  var P=fl.pts,scr=[],sh=[],wd=[],s='',i;
  for(i=0;i<P.length;i++){
    var c=cam.c(P[i]),g=cam.c([P[i][0],P[i][1],0]);
    scr.push(c[2]>=cam.near?cam.s(c):null);sh.push(g[2]>=cam.near?cam.s(g):null);
    var k=clamp(cam.ppm(P[i])/refPpm,.55,1.6);wd.push((2.2+(6.2-2.2)*i/(P.length-1))*k);
  }
  // 그림자 — 바닥에 드리운 실제 코스
  var shp=sh.filter(Boolean);
  if(shp.length>1)s+='<polyline points="'+ptsStr(shp)+'" fill="none" stroke="#12210B" stroke-opacity=".42" stroke-width="3.2" stroke-linecap="round" stroke-dasharray="1 5"/>';
  // 정점 높이선 — 공이 얼마나 뜨는지
  var top=0;for(i=1;i<P.length;i++)if(P[i][2]>P[top][2])top=i;
  if(P[top][2]>1.5&&scr[top]&&sh[top])
    s+='<line x1="'+scr[top][0].toFixed(1)+'" y1="'+scr[top][1].toFixed(1)+'" x2="'+sh[top][0].toFixed(1)+'" y2="'+sh[top][1].toFixed(1)+'" stroke="#fff" stroke-opacity=".55" stroke-width="1.2" stroke-dasharray="2 3"/>';
  // 바운드 링
  if(fl.bounce>=0){
    var bp=P[fl.bounce],ring=clipNear(cam,circle3(bp,.46,0));
    if(ring.length>2)s+='<polygon points="'+ptsStr(ring)+'" fill="'+col.fill+'" fill-opacity=".22" stroke="'+col.fill+'" stroke-width="2.2"/>';
    var dotp=cam.p(bp);if(dotp)s+='<circle cx="'+dotp[0].toFixed(1)+'" cy="'+dotp[1].toFixed(1)+'" r="2.4" fill="'+col.fill+'"/>';
  }
  // 리본 (꼬리는 가늘고 머리로 갈수록 굵다 — 날아오는 방향)
  var L=[],R=[];
  for(i=0;i<P.length;i++){
    if(!scr[i])continue;
    var a=scr[Math.max(0,i-1)]||scr[i],b=scr[Math.min(P.length-1,i+1)]||scr[i];
    var dx=b[0]-a[0],dy=b[1]-a[1],l=Math.sqrt(dx*dx+dy*dy)||1,nx=-dy/l,ny=dx/l,hw=wd[i]/2;
    L.push([scr[i][0]+nx*hw,scr[i][1]+ny*hw]);R.unshift([scr[i][0]-nx*hw,scr[i][1]-ny*hw]);
  }
  if(L.length>1)s+='<polygon points="'+ptsStr(L.concat(R))+'" fill="'+col.fill+'" fill-opacity=".95" stroke="'+col.edge+'" stroke-opacity=".55" stroke-width="1"/>';
  // 입체 화살촉 — 밝은 면과 어두운 면
  var e=scr.length-1;while(e>0&&!scr[e])e--;
  var pe=scr[e],pp=scr[Math.max(0,e-3)];
  if(pe&&pp&&!(opt&&opt.noHead)){
    var ux=pe[0]-pp[0],uy=pe[1]-pp[1],ul=Math.sqrt(ux*ux+uy*uy)||1;ux/=ul;uy/=ul;
    var hw2=wd[e]*1.55,len=wd[e]*2.7,tip=[pe[0]+ux*len*.62,pe[1]+uy*len*.62],base=[pe[0]-ux*len*.38,pe[1]-uy*len*.38];
    var bl=[base[0]-uy*hw2,base[1]+ux*hw2],br=[base[0]+uy*hw2,base[1]-ux*hw2];
    s+='<polygon points="'+ptsStr([tip,bl,base])+'" fill="'+col.fill+'"/>'
     +'<polygon points="'+ptsStr([tip,base,br])+'" fill="'+col.shade+'"/>'
     +'<polygon points="'+ptsStr([tip,bl,br])+'" fill="none" stroke="'+col.edge+'" stroke-opacity=".6" stroke-width="1"/>';
  }
  // 깊이 태그
  if(tag){
    var at=fl.bounce>=0?cam.p(P[fl.bounce]):pe;
    if(at){
      var tw=tag.length*11+14,best=null,bs=-1e9;
      [[12,-26],[12,10],[-tw-12,-26],[-tw-12,10],[-tw/2,16],[-tw/2,-36]].forEach(function(o){
        var x=clamp(at[0]+o[0],4,W-tw-4),y=clamp(at[1]+o[1],48,H-24),cx=x+tw/2,cy=y+9.5,d=1e9;
        (avoid||[]).forEach(function(p){d=Math.min(d,Math.max(Math.abs(p[0]-cx)-tw/2,Math.abs(p[1]-cy)-9.5));});
        if(d>bs+2){bs=d;best=[x,y];}
      });
      var tx=best[0],ty=best[1];
      s+='<g><rect x="'+tx.toFixed(1)+'" y="'+ty.toFixed(1)+'" width="'+tw+'" height="19" rx="9.5" fill="#12210B" fill-opacity=".86" stroke="'+col.fill+'" stroke-opacity=".7"/>'
       +'<text x="'+(tx+tw/2).toFixed(1)+'" y="'+(ty+13.4).toFixed(1)+'" text-anchor="middle" font-size="11.5" font-weight="700" fill="'+col.fill+'">'+tag+'</text></g>';
    }
  }
  return s;
}
var WHITE={fill:'#FFFFFF',shade:'#C9D6DE',edge:'#12210B'},
    YEL={fill:'#E4FF3D',shade:'#A9BD1F',edge:'#2A3A06'},
    OPPC={fill:'#4A5FD0',shade:'#2B3A91',edge:'#FFFFFF'};

/* ═════════ 장면 ═════════ */
var PIN={
  me:{head:'#E4FF3D',body:'#A9BD1F',ink:'#14230D',label:'나',shape:'o'},
  partner:{head:'#FFFFFF',body:'#C7D3BC',ink:'#14230D',label:'짝',shape:'o'},
  opp1:{head:'#26357F',body:'#18235A',ink:'#FFFFFF',label:'1',shape:'s'},
  opp2:{head:'#26357F',body:'#18235A',ink:'#FFFFFF',label:'2',shape:'s'}
};
function pinArt(cam,who,xy,ghost,flat){
  var st=PIN[who],g=world(xy),hd=[g[0],g[1],1.62],ft=cam.p(g),hp=cam.p(hd);
  if(flat&&ft){
    var gl2=clipNear(cam,circle3(g,.85,0,24)),in2=clipNear(cam,circle3(g,.42,0,20)),rr=clamp(cam.ppm(g)*.26,11,16);
    return (gl2.length>2?'<polygon points="'+ptsStr(gl2)+'" fill="#E4FF3D" fill-opacity="'+(ghost?.2:.55)+'" stroke="#fff" stroke-opacity="'+(ghost?.5:1)+'" stroke-width="1.8"/>':'')
      +(in2.length>2?'<polygon points="'+ptsStr(in2)+'" fill="none" stroke="#E4FF3D" stroke-opacity="'+(ghost?.4:1)+'" stroke-width="2.4"/>':'')
      +(ghost?'':'<circle cx="'+ft[0].toFixed(1)+'" cy="'+ft[1].toFixed(1)+'" r="'+rr.toFixed(1)+'" fill="#E4FF3D" stroke="#14230D" stroke-width="1.8"/><text x="'+ft[0].toFixed(1)+'" y="'+(ft[1]+rr*.36).toFixed(1)+'" text-anchor="middle" font-size="'+(rr*1.02).toFixed(1)+'" font-weight="800" fill="#14230D">나</text>');
  }
  if(!ft||!hp)return '';
  var ppm=cam.ppm(hd),r=clamp(ppm*.3,10,21),bw=clamp(ppm*.34,5,r*.62),s='';
  var sh=clipNear(cam,circle3(g,.42,0,16));
  if(who==='me'&&!ghost){var gl=clipNear(cam,circle3(g,.85,0,24));if(gl.length>2)s+='<polygon points="'+ptsStr(gl)+'" fill="#E4FF3D" fill-opacity=".6" stroke="#fff" stroke-width="1.8"/>';}
  if(sh.length>2)s+='<polygon points="'+ptsStr(sh)+'" fill="#12210B" fill-opacity=".38"/>';
  if(ghost)return '<g opacity=".45">'+s+'</g>';
  s+='<line x1="'+ft[0].toFixed(1)+'" y1="'+ft[1].toFixed(1)+'" x2="'+hp[0].toFixed(1)+'" y2="'+hp[1].toFixed(1)+'" stroke="'+st.body+'" stroke-width="'+bw.toFixed(1)+'" stroke-linecap="round"/>';
  if(who==='me')s+='<circle cx="'+hp[0].toFixed(1)+'" cy="'+hp[1].toFixed(1)+'" r="'+(r+2.8).toFixed(1)+'" fill="#fff"/>';
  if(st.shape==='o')s+='<circle cx="'+hp[0].toFixed(1)+'" cy="'+hp[1].toFixed(1)+'" r="'+r.toFixed(1)+'" fill="'+st.head+'" stroke="#14230D" stroke-width="1.8"/>';
  else s+='<rect x="'+(hp[0]-r).toFixed(1)+'" y="'+(hp[1]-r).toFixed(1)+'" width="'+(2*r).toFixed(1)+'" height="'+(2*r).toFixed(1)+'" rx="'+(r*.34).toFixed(1)+'" fill="'+st.head+'" stroke="#14230D" stroke-width="1.8"/>';
  s+='<text x="'+hp[0].toFixed(1)+'" y="'+(hp[1]+r*.36).toFixed(1)+'" text-anchor="middle" font-size="'+(r*1.02).toFixed(1)+'" font-weight="800" fill="'+st.ink+'">'+st.label+'</text>';
  return s;
}
function courtArt(cam,isMe){
  var s='',ppmNet=cam.ppm([0,NETY,0])||20;
  if(isMe){
    s+='<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8FCBEA"/><stop offset="1" stop-color="#E6F5FC"/></linearGradient></defs>'
     +'<rect width="'+W+'" height="'+H+'" fill="url(#sky)"/>';
  }else s+='<rect width="'+W+'" height="'+H+'" fill="#88B04B"/>';
  s+=poly(cam,[[-19,-14,0],[19,-14,0],[19,36,0],[-19,36,0]],'fill="#88B04B"');
  if(isMe)s+=poly(cam,[[-19,30,0],[19,30,0],[19,30,3.2],[-19,30,3.2]],'fill="#2E5A34"')+seg(cam,[-19,30,3.2],[19,30,3.2],'stroke="#1C3A20" stroke-width="3"');
  for(var b=0;b<12;b++){var y0=CL*b/12,y1=CL*(b+1)/12;
    s+=poly(cam,[[-CW/2,y0,0],[CW/2,y0,0],[CW/2,y1,0],[-CW/2,y1,0]],'fill="'+(b%2?'#66A646':'#5A9A3B')+'"');}
  return s;
}
function linesArt(cam,isMe){
  var h=CW/2,L=[[[-h,0],[h,0]],[[-h,CL],[h,CL]],[[-h,0],[-h,CL]],[[h,0],[h,CL]],[[-SGL,0],[-SGL,CL]],[[SGL,0],[SGL,CL]],
    [[-SGL,NETY-SVC],[SGL,NETY-SVC]],[[-SGL,NETY+SVC],[SGL,NETY+SVC]],[[0,NETY-SVC],[0,NETY+SVC]],[[0,0],[0,.18]],[[0,CL-.18],[0,CL]]];
  var s='';
  L.forEach(function(l){
    var a=[l[0][0],l[0][1],0],b=[l[1][0],l[1][1],0],len=Math.hypot(b[0]-a[0],b[1]-a[1]),n=isMe?Math.max(1,Math.ceil(len/1.6)):1;
    for(var i=0;i<n;i++){
      var p=[a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n,0],q=[a[0]+(b[0]-a[0])*(i+1)/n,a[1]+(b[1]-a[1])*(i+1)/n,0];
      var m=[(p[0]+q[0])/2,(p[1]+q[1])/2,0],sw=clamp(cam.ppm(m)*.06,1.1,4);
      s+=seg(cam,p,q,'stroke="#fff" stroke-opacity=".95" stroke-width="'+sw.toFixed(2)+'" stroke-linecap="round"');
    }
  });
  return s;
}
function netArt(cam){
  var P=6.4,top=[],i;
  for(i=0;i<=12;i++){var x=-P+2*P*i/12,t=x/P;top.push([x,NETY,.914+(1.07-.914)*t*t]);}
  var s=poly(cam,[[-P,NETY,0],[P,NETY,0]].concat(top.slice().reverse()),'fill="#14230D" fill-opacity=".5"');
  for(i=0;i<12;i++)s+=seg(cam,top[i],top[i+1],'stroke="#fff" stroke-width="2.4" stroke-linecap="round"');
  s+=seg(cam,[0,NETY,0],[0,NETY,.914],'stroke="#fff" stroke-opacity=".5" stroke-width="1.4"');
  s+=seg(cam,[-P,NETY,0],[-P,NETY,1.07],'stroke="#14230D" stroke-width="4" stroke-linecap="round"');
  s+=seg(cam,[P,NETY,0],[P,NETY,1.07],'stroke="#14230D" stroke-width="4" stroke-linecap="round"');
  return s;
}
/* 바닥에 붙은 입체 이동 화살표 */
function moveArrow(cam,fromXY,to3){
  var a=world(fromXY),b=to3,dx=b[0]-a[0],dy=b[1]-a[1],l=Math.hypot(dx,dy)||1,ux=dx/l,uy=dy/l,nx=-uy,ny=ux;
  var st=.55,ed=Math.max(st+.2,l-.35),hw=.24,hh=.62,hl=Math.min(1.05,l*.45);
  function P(t,o,z){return [a[0]+ux*t+nx*o,a[1]+uy*t+ny*o,z];}
  function shape(z){return [P(st,-hw,z),P(ed-hl,-hw,z),P(ed-hl,-hh,z),P(ed,0,z),P(ed-hl,hh,z),P(ed-hl,hw,z),P(st,hw,z)];}
  return poly(cam,shape(0),'fill="#3E5212" fill-opacity=".85"')+poly(cam,shape(.1),'fill="#E4FF3D" stroke="#2A3A06" stroke-opacity=".5" stroke-width="1"');
}

/* ═════════ 카드 — 보기 순서와 정답 ═════════ */
var KEYS=['A','B','C'],PL=['me','partner','opp1','opp2'];
function optsOf(c){
  var lo=c.distractors.filter(function(d){return d.severity==='차선';})[0],hi=c.distractors.filter(function(d){return d.severity==='실수';})[0];
  var o=[{zone:lo.zone,v:'차선',short:lo.short,why:lo.why,src:lo},{zone:c.answer.zone,v:'정답',short:c.answer.short,why:c.answer.why,src:c.answer},{zone:hi.zone,v:'실수',short:hi.short,why:hi.why,src:hi}];
  // 정답 자리를 카드마다 흩는다 — 글자 합은 이어진 카드에서 B·A·C 로 돌아 외워졌다. FNV-1a 해시로 섞는다
  var h=2166136261;for(var i=0;i<c.id.length;i++){h^=c.id.charCodeAt(i);h=Math.imul(h,16777619)>>>0;}var sh=h%3;
  return o.slice(sh).concat(o.slice(0,sh));
}
function correctIdx(c){var o=optsOf(c);for(var i=0;i<3;i++)if(o[i].v==='정답')return i;return -1;}
function revealOf(c){if(c.answer.reveal)return c.answer.reveal;return {type:c.question.type==='target'?'shot':'move'};}

/* ═════════ 시간표 — 누가 언제 어디로, 공이 언제 어디로 ═════════
   카드 데이터(setup.ball, 보기의 stand/moves/play)만 읽는다. tools/validate_cards.py 의
   check_play 와 같은 순서로 따라가므로, 검증기를 통과한 장면은 여기서도 말이 된다. */
var SPEED={serve:24,serve2:18,flat:19,normal:16,high:11,lob:9,volley:14,smash:22},RUN=5,TS=.9;
var COLSX={L:[-.15,1/3],C:[1/3,2/3],R:[2/3,1.15]};
function inZoneN(xy,z){var c0=COLSX[z.charAt(2)],r0=ROWS[z.charAt(0)][z.charAt(3)];return xy[0]>=c0[0]-1e-9&&xy[0]<=c0[1]+1e-9&&xy[1]>=r0[0]-1e-9&&xy[1]<=r0[1]+1e-9;}
function zoneN(z){var q=zoneCenter(z);return [q[0]/CW+.5,1-q[1]/CL];}
function resolveXY(v,pos){if(Array.isArray(v))return v.slice();if(PL.indexOf(v)>=0)return pos[v].slice();return zoneN(v);}
function nearestPlayer(c,xy){var best='me',bd=1e9;PL.forEach(function(k){var p=c.setup[k].xy,d=Math.hypot((p[0]-xy[0])*CW,(p[1]-xy[1])*CL);if(d<bd){bd=d;best=k;}});return best;}
function flDur(fl,arc){var P=fl.pts,L=0;for(var i=1;i<P.length;i++)L+=Math.hypot(P[i][0]-P[i-1][0],P[i][1]-P[i-1][1]);return clamp(L/(SPEED[arc]||14),.45,1.9)*TS;}
function runDur(a,b){return Math.hypot((a[0]-b[0])*CW,(a[1]-b[1])*CL)/RUN*TS;}
function ease(u){return u<.5?2*u*u:1-Math.pow(-2*u+2,2)/2;}
function lerpPts(P,x){var i=Math.min(P.length-2,Math.max(0,Math.floor(x))),r=clamp(x-i,0,1),a=P[i],b=P[i+1];return [a[0]+(b[0]-a[0])*r,a[1]+(b[1]-a[1])*r,a[2]+(b[2]-a[2])*r];}
function newTL(c){var p={};PL.forEach(function(k){p[k]=c.setup[k].xy.slice();});return {dur:0,start:p,moves:[],flights:[],hold:null,look:null,res:null,moved:null};}

/* 도입 — 상황 속 공이 날아와, 결정하는 순간에 멈춘다 */
function buildIntro(c){
  var T=newTL(c),b=c.setup.ball;
  if(b.arc==='hold'){T.hold={who:nearestPlayer(c,b.from),t1:1e9};return T;}
  var fl=flight(b),d=flDur(fl,b.arc);
  T.flights.push({t0:.15,t1:.15+d,fl:fl,col:WHITE,tag:depthTag(b),intro:true});
  T.dur=.15+d;return T;
}

/* 결과 — 고른 보기대로 내가 움직이고, 공이 이어진다 */
function buildOutcome(c,oi){
  var o=optsOf(c)[oi],src=o.src,T=newTL(c),pos={},t=.2,b0=c.setup.ball,cur,z1=null,i;
  PL.forEach(function(k){pos[k]=c.setup[k].xy.slice();});
  if(b0.arc==='hold'){cur={st:'hold'};T.hold={who:nearestPlayer(c,b0.from),t1:0};}
  else{
    var f0=flight(b0),e0=f0.pts[f0.pts.length-1];
    T.flights.push({t0:-1,t1:0,fl:f0,col:WHITE,tag:depthTag(b0),intro:true,faint:true});
    cur=b0.to?{st:'air',pt:b0.to.slice()}:{st:'ground',pt:b0.bounce.slice()};z1=e0[2];
  }
  var rv=revealOf(c),ty=c.question.type,moving=ty==='move'||ty==='both'||(ty==='readNext'&&(rv.type==='move'||rv.type==='oppShot'));
  var dest={};
  if(src.moves)Object.keys(src.moves).forEach(function(k){dest[k]=src.moves[k].slice();});
  else if(moving){if(src.stand)dest.me=src.stand.slice();else if(!inZoneN(pos.me,o.zone))dest.me=zoneN(o.zone);}
  if(rv.type==='look')T.look={t0:t,who:nearestPlayer(c,zoneN(o.zone))};
  var play=src.play||[],b1=play[0];
  var start1=b1.from?b1.from.slice():(b1.by==='none'||cur.st==='air')?cur.pt.slice():(dest[b1.by]||pos[b1.by]).slice();
  if(b1.by!=='none')dest[b1.by]=start1;
  if(dest.me)T.moved={a:pos.me.slice(),b:dest.me.slice()};
  // 0단계 — 동시에 뛴다
  var d0=0;
  Object.keys(dest).forEach(function(k){var d=runDur(pos[k],dest[k]);
    if(d>.02){var dd=Math.max(.3,d);T.moves.push({who:k,t0:t,t1:t+dd,a:pos[k].slice(),b:dest[k].slice()});d0=Math.max(d0,dd);}
    pos[k]=dest[k].slice();});
  if(T.look)d0=Math.max(d0,.6);
  if(cur.st==='ground'&&b1.by!=='none'){   // 바운드한 공이 치는 사람 쪽으로 튀어 오른다
    var hop=flight({arc:'normal',from:cur.pt,to:start1,toZ:.95},{z0:0}),hd=Math.max(.35,flDur(hop,'normal')*.8),h0=t+Math.max(0,d0-hd);
    T.flights.push({t0:h0,t1:h0+hd,fl:hop,col:WHITE,hop:true});d0=Math.max(d0,hd);z1=.95;cur={st:'air',pt:start1.slice()};
  }
  t+=d0+(d0>0?.1:0);
  if(T.hold)T.hold.t1=t;
  for(i=0;i<play.length;i++){
    var b=play[i],by=b.by,start=i===0?start1:b.from?b.from.slice():(by==='none'||cur.st==='air')?cur.pt.slice():pos[by].slice();
    if(i>0&&by!=='none'&&Math.hypot((pos[by][0]-start[0])*CW,(pos[by][1]-start[1])*CL)>.05){
      var rd=runDur(pos[by],start);T.moves.push({who:by,t0:t,t1:t+rd,a:pos[by].slice(),b:start.slice()});pos[by]=start.slice();t+=rd;
    }
    if(i>0&&cur.st==='ground'&&by!=='none'){
      var hop2=flight({arc:'normal',from:cur.pt,to:start,toZ:.95},{z0:0}),hd2=Math.max(.3,flDur(hop2,'normal')*.8);
      T.flights.push({t0:t,t1:t+hd2,fl:hop2,col:WHITE,hop:true});t+=hd2;z1=.95;
    }
    var ball={arc:b.arc,from:start};
    if(b.bounce)ball.bounce=resolveXY(b.bounce,pos);
    if(b.to)ball.to=resolveXY(b.to,pos);
    if(b.toZ!=null)ball.toZ=b.toZ;
    var z0=(b.arc==='serve'||b.arc==='serve2')?undefined:(z1!=null?z1:undefined);
    var fl=flight(ball,z0!=null?{z0:z0}:{}),dur=flDur(fl,b.arc),team=by==='none'?'none':(by==='me'||by==='partner')?'us':'them';
    T.flights.push({t0:t,t1:t+dur,fl:fl,col:team==='us'?YEL:team==='them'?OPPC:WHITE,call:b.call,winner:b.winner,team:team});
    if(b.to&&Array.isArray(b.to)){   // 받는 사람이 공을 향해 뛴다
      var catcher=b.reach||(play[i+1]&&play[i+1].by!=='none'?play[i+1].by:null);
      if(catcher){T.moves.push({who:catcher,t0:t,t1:t+dur,a:pos[catcher].slice(),b:ball.to.slice()});pos[catcher]=ball.to.slice();}
    }
    var ep=fl.pts[fl.pts.length-1];
    if(b.to){cur={st:'air',pt:ball.to};z1=ep[2];}else{cur={st:'ground',pt:ball.bounce};z1=null;}
    t+=dur+.14;
  }
  T.dur=t+.1;T.res={v:o.v,caption:src.caption,zone:o.zone};
  return T;
}

function posAt(T,who,t){var p=T.start[who];T.moves.forEach(function(m){if(m.who!==who||t<m.t0)return;var u=clamp((t-m.t0)/Math.max(1e-3,m.t1-m.t0),0,1),k=ease(u);p=[m.a[0]+(m.b[0]-m.a[0])*k,m.a[1]+(m.b[1]-m.a[1])*k];});return p;}
function ballState(T,t,pos){
  for(var i=T.flights.length-1;i>=0;i--){var f=T.flights[i];
    if(t>=f.t0){if(t<f.t1){var x=(t-f.t0)/(f.t1-f.t0)*(f.fl.pts.length-1);return {p:lerpPts(f.fl.pts,x),fly:true,f:f,x:x};}
      return {p:f.fl.pts[f.fl.pts.length-1],fly:false,f:f};}}
  if(T.hold){var g=world(pos[T.hold.who]);return {p:[g[0]+.3,g[1],2.2],fly:false,hold:true};}
  return null;
}

/* ═════════ 그리기 ═════════ */
function callTag(p,text){var tw=text.length*12+16,x=clamp(p[0]-tw/2,4,W-tw-4),y=clamp(p[1]-30,48,H-24);
  return '<g><rect x="'+x.toFixed(1)+'" y="'+y.toFixed(1)+'" width="'+tw+'" height="20" rx="10" fill="#C0442B"/><text x="'+(x+tw/2).toFixed(1)+'" y="'+(y+14).toFixed(1)+'" text-anchor="middle" font-size="12" font-weight="800" fill="#fff">'+text+'</text></g>';}
function staticLayer(c,cam,isMe,withZones){
  var s=courtArt(cam,isMe);
  if(withZones)optsOf(c).forEach(function(o,i){
    s+=poly(cam,zoneQuad(o.zone),'class="zone" data-opt="'+i+'" tabindex="0" role="button" aria-label="'+KEYS[i]+': '+o.short+'" fill="#fff" fill-opacity=".14" stroke="#fff" stroke-opacity=".75" stroke-width="2" stroke-dasharray="6 5"');});
  return s+linesArt(cam,isMe)+netArt(cam);
}
/* 존 글자 — 화면에 보이는 존 안에서, 선수에게서 가장 먼 점에 */
function chipsLayer(c,cam,isMe){
  var marks=[],s='';
  PL.forEach(function(k){var xy=c.setup[k].xy,f2=cam.p(world(xy)),h2=cam.p(world(xy,1.62));if(f2)marks.push(f2);if(h2&&!(isMe&&k==='me'))marks.push(h2);});
  optsOf(c).forEach(function(o,i){
    var sp=clipRect(clipNear(cam,zoneQuad(o.zone)),14,48,W-14,H-12);if(sp.length<3)return;
    var cx=0,cy=0;sp.forEach(function(q){cx+=q[0];cy+=q[1];});cx/=sp.length;cy/=sp.length;
    var cands=[[cx,cy]].concat(sp.map(function(q){return [cx+(q[0]-cx)*.55,cy+(q[1]-cy)*.55];})),best=null,bd=-1;
    cands.forEach(function(cd){var md=1e9;marks.forEach(function(m){md=Math.min(md,Math.hypot(m[0]-cd[0],m[1]-cd[1]));});if(md>bd){bd=md;best=cd;}});
    s+='<g pointer-events="none"><circle cx="'+best[0].toFixed(1)+'" cy="'+best[1].toFixed(1)+'" r="11" fill="#12210B" fill-opacity=".8" stroke="#fff" stroke-opacity=".8"/><text x="'+best[0].toFixed(1)+'" y="'+(best[1]+4.5).toFixed(1)+'" text-anchor="middle" font-size="12.5" font-weight="900" fill="#fff">'+KEYS[i]+'</text></g>';
  });
  return s;
}
/* 시각 t 의 움직이는 층 */
function drawFrame(T,t,ended,ctx){
  var cam=ctx.cam,isMe=ctx.isMe,ref=cam.ppm([0,NETY,0])||20,s='',pos={},AV=[],tags='';
  PL.forEach(function(k){pos[k]=posAt(T,k,t);var f=cam.p(world(pos[k])),h=cam.p(world(pos[k],1.62));if(f)AV.push(f);if(h)AV.push(h);});
  if(T.res){   // 고른 존 — 끝나면 결과 색, 틀렸으면 정답 존도
    var col=!ended?'#FFFFFF':{정답:'#2F7A22',차선:'#D9A12E',실수:'#D0573B'}[T.res.v];
    s+=poly(cam,zoneQuad(T.res.zone),'fill="'+col+'" fill-opacity="'+(ended?.24:.1)+'" stroke="'+col+'" stroke-width="3"');
    if(ended&&T.res.v!=='정답'&&ctx.correct)s+=poly(cam,zoneQuad(ctx.correct),'fill="#E4FF3D" fill-opacity=".2" stroke="#E4FF3D" stroke-width="2.6" stroke-dasharray="7 5"');
  }
  if(T.moved&&!ctx.follow&&Math.hypot((T.moved.a[0]-T.moved.b[0])*CW,(T.moved.a[1]-T.moved.b[1])*CL)>.5)
    s+=pinArt(cam,'me',T.moved.a,true,isMe)+moveArrow(cam,T.moved.a,world(T.moved.b));
  T.flights.forEach(function(f){
    if(f.hop||t<f.t0)return;
    var n=f.fl.pts.length,done=t>=f.t1,x=done?n-1:(t-f.t0)/(f.t1-f.t0)*(n-1);
    var pts=f.fl.pts.slice(0,Math.floor(x)+1);if(!done)pts.push(lerpPts(f.fl.pts,x));
    if(pts.length<2)return;
    var bi=f.fl.bounce>=0&&f.fl.bounce<=x?f.fl.bounce:-1;
    var art=ballArt(cam,{pts:pts,bounce:bi},f.col,f.intro&&done&&!f.faint?f.tag:'',ref,AV,{noHead:!done});
    s+=f.faint?'<g opacity=".35">'+art+'</g>':art;
    if(done&&f.winner&&f.fl.bounce>=0){var wp=clipNear(cam,circle3(f.fl.pts[f.fl.bounce],.9,0,24));if(wp.length>2)s+='<polygon points="'+ptsStr(wp)+'" fill="none" stroke="'+f.col.fill+'" stroke-width="3" stroke-dasharray="3 4"/>';}
    if(!done&&bi>=0&&x<bi+4){var bp=cam.p(f.fl.pts[bi]);if(bp)s+='<circle cx="'+bp[0].toFixed(1)+'" cy="'+bp[1].toFixed(1)+'" r="'+(8+(x-bi)*8).toFixed(1)+'" fill="none" stroke="#fff" stroke-opacity="'+(1-(x-bi)/4).toFixed(2)+'" stroke-width="2"/>';}
    if(done&&f.call){var q=f.call==='풋폴트'?[f.fl.pts[0][0],f.fl.pts[0][1],0]:f.fl.pts[n-1],cp=cam.p(q);if(cp)tags+=callTag(cp,f.call);}   // 판정 글자는 맨 위에, 풋폴트는 서버 발밑에
  });
  if(T.look&&t>=T.look.t0){
    var e1=cam.p(world(pos.me,1.62)),e2=cam.p(world(pos[T.look.who],1.62));
    if(e1&&e2)s+='<line x1="'+e1[0].toFixed(1)+'" y1="'+e1[1].toFixed(1)+'" x2="'+e2[0].toFixed(1)+'" y2="'+e2[1].toFixed(1)+'" stroke="#14230D" stroke-opacity=".45" stroke-width="5" stroke-linecap="round"/>'
      +'<line x1="'+e1[0].toFixed(1)+'" y1="'+e1[1].toFixed(1)+'" x2="'+e2[0].toFixed(1)+'" y2="'+e2[1].toFixed(1)+'" stroke="#E4FF3D" stroke-width="2.6" stroke-dasharray="7 6" stroke-linecap="round"/>';
    var lr=clipNear(cam,circle3(world(pos[T.look.who]),.95,0,24));if(lr.length>2)s+='<polygon points="'+ptsStr(lr)+'" fill="none" stroke="#E4FF3D" stroke-width="2.6"/>';
  }
  PL.slice().sort(function(a,b){return cam.c(world(pos[b]))[2]-cam.c(world(pos[a]))[2];})
    .forEach(function(w){s+=pinArt(cam,w,pos[w],false,isMe&&w==='me');});
  var B=ballState(T,t,pos);
  if(B){var sp=cam.p(B.p),gp=cam.p([B.p[0],B.p[1],0]),r=clamp(cam.ppm(B.p)*.18,4.5,12);
    if(gp&&!B.hold&&B.p[2]>.05)s+='<ellipse cx="'+gp[0].toFixed(1)+'" cy="'+gp[1].toFixed(1)+'" rx="'+(r*.95).toFixed(1)+'" ry="'+(r*.45).toFixed(1)+'" fill="#12210B" fill-opacity=".5"/>';
    if(sp){s+='<circle cx="'+sp[0].toFixed(1)+'" cy="'+sp[1].toFixed(1)+'" r="'+r.toFixed(1)+'" fill="#F1FF8A" stroke="#14230D" stroke-width="1.4"/>';
      if(ctx.freeze)s+='<circle class="pulse" cx="'+sp[0].toFixed(1)+'" cy="'+sp[1].toFixed(1)+'" r="'+(r+5).toFixed(1)+'" fill="none" stroke="#fff" stroke-width="2.4"/>';}}
  return s+tags;
}

/* ═════════ 재생 — 무대 하나 ═════════ */
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function camKey(p){return p[0].toFixed(3)+','+p[1].toFixed(3);}
var SAY={정답:['win','✓ 성공'],차선:['meh','△ 아쉬움'],실수:['lose','✕ 실패']};
var FREEZE_SAY='⏸ 지금, 어떻게 할까요?';

function Stage(svg,sayEl){this.svg=svg;this.sayEl=sayEl;this.anim=null;this.finishNow=null;this.bg=null;this.dyn=null;}
Stage.prototype.stop=function(){if(this.anim)cancelAnimationFrame(this.anim);this.anim=null;this.finishNow=null;};
Stage.prototype.busy=function(){return !!this.finishNow;};
Stage.prototype.skip=function(){if(this.finishNow)this.finishNow();};
Stage.prototype.say=function(kind,text,sub){var el=this.sayEl;el.className='p-say '+kind;el.innerHTML=text+(sub?' <small>'+esc(sub)+'</small>':'');el.hidden=false;
  if(!REDUCED){el.classList.remove('pop');void el.offsetWidth;el.classList.add('pop');}};
Stage.prototype.paint=function(T,t,ended,ctx){
  if(!this.dyn)return;
  if(ctx.follow){var p=posAt(T,'me',t),k=camKey(p);   // 내 시점은 카메라가 내 등 뒤를 따라간다
    if(k!==ctx.camKey){ctx.camKey=k;ctx.cam=meCam(p);this.bg.innerHTML=staticLayer(ctx.c,ctx.cam,true,false);}}
  this.dyn.innerHTML=drawFrame(T,t,ended,ctx);
};
Stage.prototype.run=function(T,ctx,onEnd){
  var self=this;this.stop();
  if(REDUCED||T.dur<=0){this.paint(T,T.dur,true,ctx);if(onEnd)onEnd();return;}
  var t0=null;
  this.finishNow=function(){self.stop();self.paint(T,T.dur,true,ctx);if(onEnd)onEnd();};
  function step(ts){if(t0===null)t0=ts;var t=(ts-t0)/1000;
    if(t>=T.dur){self.anim=null;self.finishNow=null;self.paint(T,T.dur,true,ctx);if(onEnd)onEnd();return;}
    self.paint(T,t,false,ctx);self.anim=requestAnimationFrame(step);}
  this.anim=requestAnimationFrame(step);
};
/* 카드 한 장을 무대에 올린다.
   o.view 'top'|'me' · o.pick 고른 보기(-1 = 아직) · o.shown 보여 줄 보기(정답 장면 보기) ·
   o.mode 'intro'(도입 재생 후 멈춤) | 'out'(결과 재생) | 'replay'(도입+결과) | 'still'(끝 장면만) |
          'pose'(도입 직전 — 선수만 서 있고 공은 아직. 제목 화면 뒤에 깔린다)
   o.freezeSay 멈출 때 배지 글 — false 면 배지 없이 멈춘다(페이지가 질문을 직접 띄울 때) · o.onFreeze 멈춘 뒤 부른다
   done(res) — 결과 장면이 끝났을 때. res = {v: 정답|차선|실수, caption, zone} */
Stage.prototype.show=function(c,o,done){
  var self=this,pick=o.pick==null?-1:o.pick,isMe=o.view==='me',cam=isMe?meCam(c.setup.me.xy):BCAM;
  this.stop();this.sayEl.hidden=true;
  this.svg.innerHTML='<g class="bg">'+staticLayer(c,cam,isMe,pick<0)+'</g><g class="dyn" pointer-events="none"></g>'+(pick<0?chipsLayer(c,cam,isMe):'');
  this.bg=this.svg.querySelector('.bg');this.dyn=this.svg.querySelector('.dyn');
  this.svg.setAttribute('aria-label',c.title+' — '+(isMe?'내 시점':'중계 시점')+' 코트 그림');
  var corZone=optsOf(c)[correctIdx(c)].zone,ctx={c:c,cam:cam,isMe:isMe,correct:corZone,follow:isMe&&pick>=0,camKey:camKey(c.setup.me.xy)};
  var TI=buildIntro(c);
  if(pick<0){
    if(o.mode==='pose'){this.paint(TI,0,false,ctx);return;}
    var fz={c:c,cam:cam,isMe:isMe,freeze:true};
    var freeze=function(){self.paint(TI,TI.dur,true,fz);if(o.freezeSay!==false)self.say('',o.freezeSay||FREEZE_SAY);if(o.onFreeze)o.onFreeze();};
    if(o.mode==='still')freeze();else this.run(TI,ctx,freeze);
    return;
  }
  var si=o.shown!=null?o.shown:pick,TO=buildOutcome(c,si);
  var end=function(){var s=SAY[TO.res.v];self.say(s[0],(si!==pick?'정답이면 ':'')+s[1],TO.res.caption);if(done)done(TO.res);};
  if(o.mode==='still'){this.paint(TO,TO.dur,true,ctx);end();return;}
  if(o.mode==='replay'){this.run(TI,ctx,function(){self.run(TO,ctx,end);});return;}
  this.run(TO,ctx,end);
};

return {init:init,Stage:Stage,KEYS:KEYS,optsOf:optsOf,correctIdx:correctIdx,esc:esc,clamp:clamp,
        reduced:function(){return REDUCED;}};
})();
