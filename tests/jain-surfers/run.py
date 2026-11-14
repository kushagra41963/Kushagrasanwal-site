"""Headless checks for Jain Surfers. Needs: pip install playwright, and Chrome (set CHROME=/path/to/chrome).
Serves static/ so the game is tested at /jain-surfers/. Run: python3 tests/jain-surfers/run.py"""
import json, sys, time, subprocess, os
from playwright.sync_api import sync_playwright
REPO=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); ROOT=os.path.join(REPO,'static'); SHOTS=os.path.join(REPO,'tests','jain-surfers','shots'); os.makedirs(SHOTS,exist_ok=True)
CHROME=os.environ.get('CHROME','/usr/bin/google-chrome'); URL='http://127.0.0.1:8765/jain-surfers/'
srv=subprocess.Popen([sys.executable,'-m','http.server','8765','--bind','127.0.0.1'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(1); res={}; errs=[]
def ok(n,c,extra=''): res[n]=bool(c); print(('PASS ' if c else 'FAIL ')+n, extra)
BOT='''(runs)=>{const J=window.__jainSurfers,{G,P,obs}=J;const out=[];
for(let r=0;r<runs;r++){J.start();let t=0;
 while(G.mode==='play'&&G.dist<7000&&t<60*900){
  const v=G.speed; let rowZ=1e9;
  for(const o of obs){if(!o.on||o.fly)continue;const z=o.d-G.dist;if(z>0.35&&z<rowZ)rowZ=z;}
  if(rowZ<v*REACT){const st=[null,null,null];let wide=false;
   for(const o of obs){if(!o.on||o.fly)continue;const z=o.d-G.dist;if(Math.abs(z-rowZ)<0.01){if(o.cls==='wide')wide=true;else st[o.x+1]=o.cls;}}
   if(wide){if(rowZ<v*0.25&&P.slide<=0&&P.y<=0)J.act('down');}
   else{const cost=l=>(st[l]===null?0:st[l]==='tall'?99:1)+Math.abs(l-P.lane)*0.3;
    let best=P.lane;for(let l=0;l<3;l++)if(cost(l)<cost(best))best=l;
    if(best<P.lane)J.act('left');else if(best>P.lane)J.act('right');
    else{const c=st[P.lane];
     if(c==='low'&&rowZ<v*0.2&&P.y<=0)J.act('up');
     if(c==='ban'&&rowZ<v*0.25&&P.slide<=0&&P.y<=0)J.act('down');}}}
  J.advance(1/60);t++;}
 out.push({dist:Math.round(G.dist),mode:G.mode,killer:G.killer,coins:G.coins,speed:+G.speed.toFixed(1)});
 if(G.mode==='dying'){for(let i=0;i<80;i++)J.advance(1/60);}}
return out;}'''
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=CHROME,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
    ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True)
    pg=ctx.new_page(); pg.on('console',lambda m: errs.append(m.text) if m.type in('error','warning') else None); pg.on('pageerror',lambda e: errs.append(str(e)))
    reqs=[]; pg.on('request',lambda r: reqs.append(r.url))
    pg.goto(URL); pg.wait_for_timeout(600)
    ok('loads, start screen visible', pg.is_visible('#ovStart') and pg.is_visible('#bPlay'))
    ok('no external requests', all(u.startswith(URL) or u.startswith('data:') for u in reqs), str([u for u in reqs if '127.0.0.1' not in u and not u.startswith('data:')]))
    ok('audio not started before interaction', pg.evaluate("()=>!document.querySelector('audio') && true"))
    pg.screenshot(path=SHOTS+'/01-menu-mobile.png')
    pg.tap('#bPlay'); pg.wait_for_timeout(300)
    ok('play starts, HUD shown', pg.evaluate("()=>__jainSurfers.G.mode")=='play' and pg.is_visible('#hud'))
    # touch swipes via CDP
    cdp=ctx.new_cdp_session(pg)
    def swipe(dx,dy):
        x,y=195,500
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
        for i in range(1,5): cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x+dx*i/4,'y':y+dy*i/4}]})
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    st=lambda: pg.evaluate("()=>{const {P,G}=__jainSurfers;return {lane:P.lane,y:P.y,slide:P.slide,mode:G.mode,dist:G.dist}}")
    swipe(-80,0); pg.wait_for_timeout(60); ok('swipe left -> lane 0', st()['lane']==0)
    swipe(80,0); pg.wait_for_timeout(60); ok('swipe right -> lane 1', st()['lane']==1)
    swipe(0,-80); pg.wait_for_timeout(120); ok('swipe up -> jump', st()['y']>0.1)
    pg.wait_for_timeout(700); swipe(0,80); pg.wait_for_timeout(60); ok('swipe down -> slide', st()['slide']>0)
    # one lane change per gesture: short and long swipes, both directions, from every lane
    def swipe_n(dx,steps):
        x,y=195,500
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
        for i in range(1,steps+1): cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x+dx*i/steps,'y':y+(3 if i%2 else -3)}]})
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    bad=[]
    for lane in (0,1,2):
        for dx,steps,label in ((-45,3,'short left'),(45,3,'short right'),(-170,12,'long left'),(170,12,'long right'),(-185,40,'slow long left'),(185,40,'slow long right')):
            pg.evaluate("(l)=>{const J=__jainSurfers;if(J.G.mode!=='play')J.start();J.G.lastRowD=1e9;for(const o of J.obs)o.on=false;J.P.lane=l;J.P.x=l-1;}",lane)
            swipe_n(dx,steps); pg.wait_for_timeout(40)
            got=st()['lane']; want=max(0,min(2,lane+(1 if dx>0 else -1)))
            if got!=want: bad.append((lane,label,got,want))
    ok('swipe matrix: exactly one lane change per gesture (18 cases)', not bad, str(bad))
    # lock resets on lift: two separate swipes move two lanes; pointercancel also resets
    pg.evaluate("()=>{const J=__jainSurfers;J.P.lane=0;J.P.x=-1}"); swipe_n(170,12); swipe_n(60,4); pg.wait_for_timeout(40)
    ok('lock resets on pointerup: two swipes = two lanes', st()['lane']==2)
    pg.evaluate("()=>{const J=__jainSurfers;J.P.lane=0;J.P.x=-1}")
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':195,'y':500}]}); cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':260,'y':500}]}); cdp.send('Input.dispatchTouchEvent',{'type':'touchCancel','touchPoints':[]})
    swipe_n(60,4); pg.wait_for_timeout(40)
    ok('lock resets on pointercancel', st()['lane']==2, str(st()['lane']))
    # one gesture: sideways then up still jumps, and a long vertical swipe is one jump
    pg.evaluate("()=>{const J=__jainSurfers;J.P.lane=1;J.P.x=0;J.P.y=0;J.P.vy=0;J.P.slide=0}")
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':195,'y':500}]})
    for pt in ((240,500),(300,500),(300,450),(300,400)): cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':pt[0],'y':pt[1]}]})
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]}); pg.wait_for_timeout(80)
    ok('sideways-then-up in one gesture: one lane change plus a jump', st()['lane']==2 and st()['y']>0.05, str(st()))
    pg.wait_for_timeout(700)
    ok('page did not scroll', pg.evaluate("()=>window.scrollY===0 && document.documentElement.scrollTop===0"))
    # pause button, blur, visibility
    pg.tap('#bPause'); pg.wait_for_timeout(100); d0=st()['dist']; pg.wait_for_timeout(400)
    ok('pause button freezes game', st()['mode']=='pause' and st()['dist']==d0 and pg.is_visible('#ovPause'))
    pg.tap('#bResume'); pg.wait_for_timeout(200); ok('resume continues', st()['mode']=='play' and st()['dist']>d0)
    pg.evaluate("()=>window.dispatchEvent(new Event('blur'))"); pg.wait_for_timeout(300)
    ok('blur pauses and stays paused', st()['mode']=='pause'); pg.tap('#bResume')
    pg.evaluate("()=>{Object.defineProperty(document,'hidden',{value:true,configurable:true});document.dispatchEvent(new Event('visibilitychange'));Object.defineProperty(document,'hidden',{value:false,configurable:true});document.dispatchEvent(new Event('visibilitychange'));}")
    pg.wait_for_timeout(300); ok('tab hide pauses, needs explicit resume', st()['mode']=='pause'); pg.tap('#bResume')
    # rotation / resize mid-run
    pg.set_viewport_size({'width':844,'height':390}); pg.wait_for_timeout(300)
    sz=pg.evaluate("()=>{const c=document.getElementById('game');return [c.width,c.height,innerWidth,innerHeight]}")
    ok('rotate to landscape resizes canvas', sz[0]==sz[2]*2 and sz[1]==sz[3]*2, str(sz))
    pg.evaluate("()=>{const J=__jainSurfers;J.G.mode==='pause'&&J.resume();}")
    pg.screenshot(path=SHOTS+'/02-landscape.png')
    pg.set_viewport_size({'width':390,'height':844}); pg.wait_for_timeout(200)
    # fairness bot
    for react,label,runs in ((0.45,'0.45s reaction',25),(0.32,'0.32s reaction',15)):
        out=pg.evaluate(BOT.replace('REACT',str(react)),runs)
        deaths=[o for o in out if o['mode']!='play']
        ok(f'fairness bot ({label}) survives {runs} runs to 7000 m at speed cap', not deaths, json.dumps(deaths[:4]) if deaths else f"min coins {min(o['coins'] for o in out)}, speed {out[0]['speed']}")
    # collisions
    col=pg.evaluate('''()=>{const J=__jainSurfers,{G,P,obs}=J;const r={};
      const run=(setup,kind)=>{J.start();for(let i=0;i<10;i++)J.advance(1/60);for(const o of obs)o.on=false;G.lastRowD=1e9;
        const o=obs[0];Object.assign(o,{on:true,fly:false,y:0,t:0,x:0,d:G.dist+6,hw:.4,cls:kind,kind:kind==='low'?'onion':kind==='tall'?'cart':'banner',txt:'X',v:0});if(kind==='wide'){o.hw=1.55}
        let t=0;while(G.mode==='play'&&o.d-G.dist>-1&&t<600){setup(o.d-G.dist);J.advance(1/60);t++}return G.mode};
      r.lowHit=run(()=>{},'low'); r.lowJump=run(z=>{if(z<1.8&&P.y<=0&&!P.j){P.j=1;J.act('up')}},'low'); P.j=0;
      r.tallHit=run(()=>{},'tall'); r.tallDodge=run(z=>{if(z<4)P.lane===1&&J.act('left')},'tall');
      r.tallJump=run(z=>{if(z<1.8&&P.y<=0&&!P.j){P.j=1;J.act('up')}},'tall'); P.j=0;
      r.banHit=run(()=>{},'wide'); r.banSlide=run(z=>{if(z<2&&P.slide<=0)J.act('down')},'wide');
      r.banJump=run(z=>{if(z<1.8&&P.y<=0&&!P.j){P.j=1;J.act('up')}},'wide'); P.j=0;
      // shield absorbs one hit, chai is invincible
      r.shield=run(z=>{if(z>5)P.shield=true},'tall'); r.shieldGone=!P.shield;
      r.chai=run(z=>{P.chai=3},'tall');
      r.chaiEnd=run(z=>{if(z>0.6)P.chai=0.001},'tall');
      return r}''')
    ok('low obstacle: hit if ignored, cleared by jump', col['lowHit']=='dying' and col['lowJump']=='play', str(col))
    ok('cart: hit if ignored or jumped, cleared by lane change', col['tallHit']=='dying' and col['tallJump']=='dying' and col['tallDodge']=='play')
    ok('banner: hit if ignored or jumped, cleared by slide', col['banHit']=='dying' and col['banJump']=='dying' and col['banSlide']=='play')
    ok('shield absorbs exactly one hit', col['shield']=='play' and col['shieldGone'])
    ok('chai boost is invincible', col['chai']=='play')
    ok('chai boost running out next to an obstacle is not an instant loss', col['chaiEnd']=='play')
    # coins, magnet, scoring
    sc=pg.evaluate('''()=>{const J=__jainSurfers,{G,P,obs,coins,pows}=J;J.start();for(const o of obs)o.on=false;for(const c of coins)c.on=false;G.lastRowD=1e9;
      for(let i=0;i<5;i++){const c=coins[i];Object.assign(c,{on:true,x:1,y:.45,d:G.dist+6+i,ph:0})}
      Object.assign(pows[0],{on:true,x:0,d:G.dist+3,kind:'magnet'});
      for(let i=0;i<120;i++)J.advance(1/60);
      return {coins:G.coins,score:G.score,dist:Math.floor(G.dist),magnet:P.magnet>0,pill:document.getElementById('pwMagnet').classList.contains('on')||true}}''')
    ok('magnet pulls coins from another lane; score = distance + 10/coin', sc['coins']==5 and sc['score']==sc['dist']+50 and sc['magnet'], str(sc))
    # repeated restart
    rs=pg.evaluate('''()=>{const J=__jainSurfers,{G,obs,coins}=J;let bad=0;for(let r=0;r<40;r++){J.start();for(let i=0;i<200&&G.mode==='play';i++)J.advance(1/30);
      J.start();if(G.dist!==0||G.coins!==0||obs.some(o=>o.on)||coins.some(c=>c.on)||G.mode!=='play')bad++;}return bad}''')
    ok('40 restarts leave clean state', rs==0)
    # game over screen + best saved across reload
    pg.evaluate("()=>{const J=__jainSurfers;J.start();J.G.dist=1234;J.G.lastRowD=1e9;J.G.coins=7;J.advance(1/60);const o=J.obs[0];Object.assign(o,{on:true,fly:false,y:0,x:0,d:J.G.dist+1,hw:.4,cls:'tall',kind:'cart',v:0});}")
    pg.wait_for_timeout(2300)
    ok('game over screen shows results', pg.is_visible('#ovOver') and pg.inner_text('#oCoins')=='7' and len(pg.inner_text('#oQuip'))>5, pg.inner_text('#oQuip')+' | '+pg.inner_text('#oScore'))
    pg.screenshot(path=SHOTS+'/05-gameover.png')
    best=int(pg.inner_text('#oBest')); pg.reload(); pg.wait_for_timeout(400)
    ok('best score persists after reload', int(pg.inner_text('#sBest'))==best and best>1200, str(best))
    # keyboard on desktop
    d=b.new_context(viewport={'width':1280,'height':720}); p2=d.new_page(); p2.on('pageerror',lambda e: errs.append(str(e))); p2.on('console',lambda m: errs.append(m.text) if m.type=='error' else None)
    p2.goto(URL); p2.wait_for_timeout(400); p2.screenshot(path=SHOTS+'/03-menu-desktop.png')
    p2.keyboard.press('Enter'); p2.wait_for_timeout(200)
    g=lambda: p2.evaluate("()=>{const {P,G}=__jainSurfers;return {lane:P.lane,y:P.y,slide:P.slide,mode:G.mode}}")
    k=[]
    p2.keyboard.press('ArrowLeft'); k.append(g()['lane']==0); p2.keyboard.press('KeyD'); k.append(g()['lane']==1); p2.keyboard.press('ArrowRight'); k.append(g()['lane']==2); p2.keyboard.press('KeyA'); k.append(g()['lane']==1)
    p2.keyboard.press('KeyW'); p2.wait_for_timeout(100); k.append(g()['y']>0.1); p2.wait_for_timeout(700)
    p2.keyboard.press('ArrowUp'); p2.wait_for_timeout(100); k.append(g()['y']>0.1); p2.keyboard.press('ArrowDown'); p2.wait_for_timeout(250); k.append(g()['slide']>0 and g()['y']==0)
    p2.wait_for_timeout(700); p2.keyboard.press('KeyS'); p2.wait_for_timeout(50); k.append(g()['slide']>0)
    p2.keyboard.press('Escape'); p2.wait_for_timeout(100); k.append(g()['mode']=='pause'); p2.keyboard.press('KeyP'); p2.wait_for_timeout(100); k.append(g()['mode']=='play')
    ok('keyboard: arrows, WASD, fast-fall slide, Esc/P pause', all(k), str(k))
    # gameplay screenshots with a staged scene
    stage='''(o)=>{const J=__jainSurfers,{G,P,obs,coins,pows}=J;J.start();G.dist=o.dist;G.lastRowD=1e9;J.advance(1/60);for(const x of obs)x.on=false;for(const c of coins)c.on=false;
      const add=(i,cls,kind,x,z,hw)=>Object.assign(obs[i],{on:true,fly:false,y:0,t:0,x,d:G.dist+z,hw,cls,kind,txt:cls==='wide'?'MEGA PYAAZ MELA':'ALOO',v:i%4,spin:1});
      add(0,'low','onion',-1,3,.36);add(1,'tall','cart',1,5,.42);add(2,'low','sack',0,9,.36);add(3,'tall','crate',-1,13,.42);add(4,'low','garlic',1,12,.36);add(5,'ban','banner',0,17,.48);add(6,'wide','banner',0,26,1.55);
      for(let i=0;i<6;i++)Object.assign(coins[i],{on:true,x:0,y:.45,d:G.dist+2+i*1.1,ph:i});
      Object.assign(pows[0],{on:true,x:1,d:G.dist+9,kind:'chai'});Object.assign(pows[1],{on:true,x:-1,d:G.dist+8,kind:'magnet'});Object.assign(pows[2],{on:true,x:0,d:G.dist+13,kind:'shield'});
      if(o.jump){P.y=0.9;P.vy=1} if(o.slide){P.slide=.5} if(o.pw){P.shield=true;P.magnet=5;P.chai=3}
      G.mode='pause';J.render();}'''
    p2.evaluate(stage,{'dist':300,'jump':False}); p2.wait_for_timeout(100); p2.screenshot(path=SHOTS+'/04-play-desktop.png')
    pg.evaluate("()=>__jainSurfers.start()"); pg.evaluate(stage,{'dist':300,'jump':True,'pw':True})
    pg.evaluate("()=>{document.getElementById('ovPause').classList.remove('on')}"); pg.wait_for_timeout(100); pg.screenshot(path=SHOTS+'/06-play-mobile-jump.png')
    pg.evaluate(stage,{'dist':300,'slide':True}); pg.evaluate("()=>{document.getElementById('ovPause').classList.remove('on')}"); pg.wait_for_timeout(100); pg.screenshot(path=SHOTS+'/07-play-mobile-slide.png')
    far='''()=>{const J=__jainSurfers,{G,obs,coins,pows}=J;J.start();G.dist=300;G.lastRowD=1e9;J.advance(1/60);for(const x of obs)x.on=false;for(const c of coins)c.on=false;for(const p of pows)p.on=false;
      const add=(i,cls,kind,x,z,hw)=>Object.assign(obs[i],{on:true,fly:false,y:0,t:0,x,d:G.dist+z,hw,cls,kind,txt:cls==='wide'?'ALOO BONANZA TODAY':'PYAAZ',v:i%4,spin:1});
      add(0,'low','onion',-1,14,.36);add(1,'tall','cart',1,16,.42);add(2,'low','sack',0,20,.36);add(3,'tall','crate',-1,26,.42);add(4,'low','garlic',1,24,.36);add(5,'ban','banner',0,30,.48);add(6,'low','onion',0,36,.36);add(7,'tall','cart',-1,40,.42);add(8,'low','garlic',1,34,.36);add(9,'wide','banner',0,48,1.55);
      G.mode='pause';J.render();document.getElementById('ovPause').classList.remove('on')}'''
    p2.evaluate(far); p2.wait_for_timeout(100); p2.screenshot(path=SHOTS+'/08-far-desktop.png')
    pg.evaluate(far); pg.wait_for_timeout(100); pg.screenshot(path=SHOTS+'/09-far-mobile.png')
    pg.evaluate("()=>__jainSurfers.start()")
    # ---- mum chaser: visual only, never overlaps the runner, HUD or the hazard area ----
    MUM = """async (shotMode)=>{const J=__jainSurfers,{G,P,M,obs,coins}=J;const r={};
      const hud=()=>{let b=0;for(const id of ['hScore','hDist','bPause','bMute','pwMagnet','pwShield','pwChai']){const e=document.getElementById(id).getBoundingClientRect();if(e.height)b=Math.max(b,e.bottom)}return b};
      const hit=(a,b)=>a.x0<b.x1&&a.x1>b.x0&&a.y0<b.y1&&a.y1>b.y0;
      const clear=()=>{for(const o of obs)o.on=false;for(const c of coins)c.on=false;G.lastRowD=1e9};
      const watch=(secs,label,needBelowGround)=>{let seen=0,bad=[];for(let i=0;i<secs*60&&G.mode==='play';i++){J.advance(1/60);J.render();if(!M.vis)continue;seen++;const v=J.view();
          if(hit(M,v.girl))bad.push(label+' overlaps runner t='+M.t.toFixed(2));if(M.y0<hud()&&M.x0<v.W&&M.x1>0)bad.push(label+' overlaps HUD');
          if(needBelowGround&&M.y0<v.gndY)bad.push(label+' rises into hazard area');
          // also while the runner jumps, slides and changes lane
          if(i%37===5)J.act('up');if(i%53===9)J.act('down');if(i%41===3)J.act(i%2?'left':'right');}
        return {seen,bad:bad.slice(0,3)}};
      // 1 start intro
      J.start();clear();J.advance(1/60);J.render();r.introMode=M.mode;r.introVisible=M.vis;
      if(shotMode==='intro'){J.advance(0.25);J.render();G.mode='pause';return r}
      r.intro=watch(2.4,'intro',false);r.introGone=!M.vis&&M.mode==='idle';
      // 2 glimpse
      M.next=0;J.advance(1/60);r.glimpseMode=M.mode;
      if(shotMode==='glimpse'){J.advance(0.9);J.render();G.mode='pause';return r}
      r.glimpse=watch(3.2,'glimpse',true);r.glimpseGone=!M.vis;
      // 3 shield absorbs a hit -> catch-up, no other rule changes
      clear();P.lane=1;P.x=0;P.y=0;P.slide=0;P.shield=true;const c0=G.coins;
      Object.assign(obs[0],{on:true,fly:false,y:0,t:0,x:0,d:G.dist+1.2,hw:.42,cls:'tall',kind:'cart',v:0});
      for(let i=0;i<30&&M.mode!=='catchup';i++)J.advance(1/60);
      r.catchupMode=M.mode;r.stillPlaying=G.mode==='play';r.shieldUsed=!P.shield;r.coinsSame=G.coins===c0;
      if(shotMode==='catchup'){J.advance(0.6);J.render();G.mode='pause';return r}
      r.catchup=watch(2.6,'catchup',true);r.catchupGone=!M.vis&&M.mode==='idle';
      // 4 pause freezes her
      M.next=0;J.advance(0.5);J.pause();const a=[M.t,M.ph,M.r];await new Promise(q=>setTimeout(q,350));r.pauseFrozen=a[0]===M.t&&a[1]===M.ph&&a[2]===M.r;J.resume();
      window.dispatchEvent(new Event('blur'));const b=[M.t,M.ph,M.r];await new Promise(q=>setTimeout(q,350));r.blurFrozen=G.mode==='pause'&&b[0]===M.t&&b[1]===M.ph;J.resume();
      // 5 unprotected crash -> catch animation -> game over
      clear();P.lane=1;P.x=0;P.y=0;P.slide=0;P.shield=false;P.grace=0;P.chai=0;
      Object.assign(obs[0],{on:true,fly:false,y:0,t:0,x:0,d:G.dist+1.2,hw:.42,cls:'tall',kind:'cart',v:0});
      for(let i=0;i<30&&G.mode==='play';i++)J.advance(1/60);
      r.crashMode=G.mode;r.catchMode=M.mode;const d0=G.dist;
      if(shotMode==='catch'){J.advance(1.0);J.render();document.getElementById('hud').classList.remove('on');G.mode='pause';return r}
      let n=0;while(G.mode==='dying'&&n<400){J.advance(1/60);n++}
      r.catchSecs=+(n/60).toFixed(2);r.overMode=G.mode;r.movedAfterCrash=+(G.dist-d0).toFixed(1);
      r.line=document.querySelector('#ovOver .mum').textContent;r.overVisible=document.getElementById('ovOver').classList.contains('on');
      // Play Again works the instant the result screen is up
      document.getElementById('bAgain').click();r.againMode=G.mode;r.againMum=M.mode==='intro'&&M.t<0.05&&M.r===0&&!M.said;
      // 6 repeated restarts, including mid-glimpse, mid-catch-up and mid-catch
      let bad=0;for(let k=0;k<30;k++){J.start();clear();J.advance(0.3+k*0.11);if(k%3===0){M.next=0;J.advance(0.8)}if(k%3===1){P.shield=true;Object.assign(obs[0],{on:true,fly:false,y:0,t:0,x:P.x,d:G.dist+0.5,hw:.42,cls:'tall',kind:'cart',v:0});J.advance(0.4)}
        if(k%3===2){Object.assign(obs[0],{on:true,fly:false,y:0,t:0,x:P.x,d:G.dist+0.5,hw:.42,cls:'tall',kind:'cart',v:0});J.advance(0.6)}
        J.start();if(!(M.mode==='intro'&&M.t===0&&M.r===0&&M.off===-1.4&&M.side===-1&&G.mode==='play'&&G.dist===0))bad++}
      r.restartBad=bad;J.start();clear();return r}"""
    for name,vp,touch in (('phone portrait',{'width':390,'height':844},True),('phone landscape',{'width':844,'height':390},True),('desktop',{'width':1280,'height':720},False)):
        cm=b.new_context(viewport=vp,device_scale_factor=2,has_touch=touch,is_mobile=touch); pm=cm.new_page(); em=[]; pm.on('pageerror',lambda e:em.append(str(e)))
        pm.goto(URL); pm.wait_for_timeout(300); r=pm.evaluate(MUM,'')
        tag=name.replace(' ','-')
        ok(f'mum [{name}]: chase intro starts close, then falls out of view', r['introMode']=='intro' and r['introVisible'] and r['intro']['seen']>30 and not r['intro']['bad'] and r['introGone'], str(r['intro']))
        ok(f'mum [{name}]: glimpse stays below the ground line, clear of runner and HUD', r['glimpseMode']=='glimpse' and r['glimpse']['seen']>30 and not r['glimpse']['bad'] and r['glimpseGone'], str(r['glimpse']))
        ok(f'mum [{name}]: shield hit -> catch-up then falls back; run continues, nothing else changes', r['catchupMode']=='catchup' and r['stillPlaying'] and r['shieldUsed'] and r['coinsSame'] and r['catchup']['seen']>30 and not r['catchup']['bad'] and r['catchupGone'], str(r['catchup']))
        ok(f'mum [{name}]: frozen while paused and on tab blur', r['pauseFrozen'] and r['blurFrozen'])
        ok(f'mum [{name}]: crash -> short catch animation -> game-over line', r['crashMode']=='dying' and r['catchMode']=='catch' and r['overMode']=='over' and r['overVisible'] and 1.0<r['catchSecs']<1.6 and r['line']=='Mummy caught you. Sabzi shopping continues.' and r['movedAfterCrash']==0, f"{r['catchSecs']}s, drift {r['movedAfterCrash']} m, {r['line']}")
        ok(f'mum [{name}]: Play Again works immediately and resets her', r['againMode']=='play' and r['againMum'])
        ok(f'mum [{name}]: 30 restarts from every mum state reset cleanly', r['restartBad']==0 and not em, str(em))
        for mode in ('intro','glimpse','catchup','catch'):
            pm.evaluate("()=>__jainSurfers.start()"); pm.evaluate(MUM,mode); pm.evaluate("()=>{document.getElementById('ovPause').classList.remove('on');__jainSurfers.render()}"); pm.wait_for_timeout(60)
            pm.screenshot(path=SHOTS+f'/mum-{tag}-{mode}.png')
        if touch and vp['width']<vp['height']:
            # one long swipe still moves exactly one lane with mum in the game
            cd2=cm.new_cdp_session(pm); pm.evaluate("()=>{const J=__jainSurfers;J.start();J.G.lastRowD=1e9;J.P.lane=0;J.P.x=-1}")
            cd2.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':80,'y':520}]})
            for i in range(1,25): cd2.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':80+i*11,'y':520}]})
            cd2.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]}); pm.wait_for_timeout(50)
            ok('one long swipe (264 px) from the left lane still moves exactly one lane', pm.evaluate("()=>__jainSurfers.P.lane")==1)
        cm.close()
    # storage blocked -> in-memory fallback
    c3=b.new_context(viewport={'width':390,'height':700}); c3.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new Error('blocked')}})")
    p3=c3.new_page(); e3=[]; p3.on('pageerror',lambda e:e3.append(str(e))); p3.goto(URL); p3.wait_for_timeout(300)
    v=p3.evaluate("()=>{const s=__jainSurfers.store;s.set('jainSurfers.best',42);return s.get('jainSurfers.best')}")
    ok('storage blocked: no crash, in-memory fallback works', v=='42' and not e3, str(e3))
    # frame pacing (headless software rendering, indicative only)
    p2.evaluate("()=>{document.getElementById('ovPause').classList.remove('on');__jainSurfers.start()}")
    fps=p2.evaluate("()=>new Promise(r=>{let n=0,t0=performance.now();const f=()=>{n++;if(performance.now()-t0<2000)requestAnimationFrame(f);else r(n/2)};requestAnimationFrame(f)})")
    print('INFO headless fps (software GL, 1280x720):',fps)
    ok('no console errors or page errors', not errs, str(errs[:5]))
    b.close()
srv.terminate()
print(sum(res.values()),'/',len(res),'passed'); sys.exit(0 if all(res.values()) else 1)
