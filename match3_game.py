"""
CatWood Match-3 — Telegram Web App.
Served by the bot at GET /match3. On victory the page calls
window.tg.sendData({event:'win', score, moves_left}) which the bot
receives as a web_app_data update and credits +1 bonus reading (daily-limited).
"""

GAME_HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<title>CatWood Match-3</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --sky:#7EC8FF; --sun:#FFD33D; --coral:#FF7E7E; --grass:#7BD66A; --navy:#1B2A4A;
  --bg1:#EAF6FF; --bg2:#D9EEFF;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;padding:0;font-family:'Fredoka',system-ui,sans-serif;color:var(--navy);
  background:linear-gradient(180deg,var(--bg1),var(--bg2));min-height:100vh;overflow-x:hidden}
#app{max-width:480px;margin:0 auto;padding:12px;display:flex;flex-direction:column;align-items:center}
h1{font-size:24px;margin:6px 0 2px;text-align:center;font-weight:700}
.sub{font-size:13px;opacity:.7;margin-bottom:8px;text-align:center}
.hud{display:flex;gap:10px;width:100%;max-width:340px;margin-bottom:10px}
.hud .box{flex:1;background:#fff;border:3px solid var(--navy);border-radius:14px;padding:8px 6px;
  box-shadow:0 4px 0 var(--navy);text-align:center}
.hud .lbl{font-size:11px;opacity:.7;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.hud .val{font-size:22px;font-weight:700;line-height:1.1}
.hud .val.warn{color:var(--coral)}
.screen{width:100%;max-width:340px;background:#fff;border:3px solid var(--navy);border-radius:18px;
  box-shadow:0 6px 0 var(--navy);padding:14px;margin-bottom:12px}
.board{display:grid;grid-template-columns:repeat(8,1fr);grid-template-rows:repeat(8,1fr);
  gap:3px;background:var(--sky);padding:8px;border-radius:12px;aspect-ratio:1}
.tile{display:flex;align-items:center;justify-content:center;font-size:22px;background:#fff;
  border-radius:8px;border:2px solid rgba(27,42,74,.15);cursor:pointer;user-select:none;
  transition:transform .12s, background .12s, box-shadow .12s;will-change:transform}
.tile.sel{background:var(--sun);box-shadow:0 0 0 3px #fff inset, 0 0 10px var(--sun);transform:scale(.92);
  animation:pulse 1s infinite}
@keyframes pulse{50%{transform:scale(.96)}}
.tile.pop{animation:pop .4s forwards}
@keyframes pop{0%{transform:scale(1)}40%{transform:scale(1.35) rotate(12deg);filter:brightness(1.4)}
  100%{transform:scale(0) rotate(180deg);opacity:0}}
.tile.drop{animation:drop .45s cubic-bezier(.34,1.56,.64,1)}
@keyframes drop{0%{transform:translateY(-120%);opacity:0}60%{transform:translateY(8%);opacity:1}
  100%{transform:translateY(0)}}
.floaty{position:absolute;font-weight:700;font-size:26px;color:var(--coral);
  text-shadow:2px 2px 0 #fff;pointer-events:none;animation:floaty .9s forwards}
@keyframes floaty{0%{transform:translateY(0);opacity:1}100%{transform:translateY(-70px);opacity:0}}
.shake{animation:shake .35s}
@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-5px)}75%{transform:translateX(5px)}}
.btn{display:block;width:100%;background:var(--coral);color:#fff;border:3px solid var(--navy);
  border-radius:14px;padding:14px;font-family:inherit;font-size:18px;font-weight:700;cursor:pointer;
  box-shadow:0 5px 0 var(--navy);transition:transform .08s;margin-top:8px}
.btn:active{transform:translateY(4px);box-shadow:0 1px 0 var(--navy)}
.btn.alt{background:var(--sky)}
.center{text-align:center}
.rules{font-size:13px;line-height:1.5;opacity:.85;margin:8px 0}
.flash{position:fixed;inset:0;background:#fff;opacity:.6;pointer-events:none;animation:flash .25s forwards}
@keyframes flash{from{opacity:.6}to{opacity:0}}
.toast{position:fixed;left:50%;bottom:20px;transform:translateX(-50%);background:var(--navy);color:#fff;
  padding:10px 16px;border-radius:10px;font-size:14px;opacity:0;transition:opacity .3s;pointer-events:none;z-index:99}
.toast.show{opacity:1}
</style>
</head>
<body>
<div id="app">
  <h1>🐱 CatWood Match-3</h1>
  <div class="sub">Собирай ряды — выиграй гадание!</div>

  <div id="hud" class="hud" style="display:none">
    <div class="box"><div class="lbl">Очки</div><div class="val" id="score">0</div></div>
    <div class="box"><div class="lbl">Ходы</div><div class="val" id="moves">15</div></div>
  </div>

  <div id="startScreen" class="screen">
    <div class="center">
      <div style="font-size:46px">🐠🧶🐟🐭🍼</div>
      <div class="rules">
        <b>Как играть:</b><br>
        Нажми на фишку, потом на соседнюю, чтобы поменять местами.<br>
        Собери 3+ в ряд — они лопнут, сверху упадут новые.<br>
        <b>Цель:</b> набери <b>300 очков</b> за <b>15 ходов</b> — получишь <b>+1 гадание</b> в боте!
      </div>
    </div>
    <button class="btn" id="playBtn">▶ Играть</button>
  </div>

  <div id="game" style="display:none;width:100%;max-width:340px;position:relative">
    <div class="board" id="board"></div>
  </div>

  <div id="result" class="screen" style="display:none">
    <div class="center">
      <div id="resEmoji" style="font-size:46px">🎉</div>
      <h2 id="resTitle">Победа!</h2>
      <div class="rules" id="resText">Ты выиграл +1 гадание!</div>
      <button class="btn" id="againBtn">Играть ещё</button>
      <button class="btn alt" id="shareBtn">Поделиться</button>
    </div>
  </div>

  <div class="toast" id="toast"></div>
</div>

<script>
const TYPES=['🐠','🧶','🐟','🐭','🍼'];
const ROWS=8,COLS=8,GOAL=300,MAX_MOVES=15;
let board=[],sel=null,score=0,moves=MAX_MOVES,busy=false,playing=false,sent=false;

function $(id){return document.getElementById(id)}
function toast(t){const x=$('toast');x.textContent=t;x.classList.add('show');setTimeout(()=>x.classList.remove('show'),1600)}

function createBoard(){
  const b=[];
  for(let r=0;r<ROWS;r++){b[r]=[];
    for(let c=0;c<COLS;c++){let t;
      do{t=TYPES[Math.floor(Math.random()*TYPES.length)]}while(
        (c>=2&&b[r][c-1]===t&&b[r][c-2]===t)||
        (r>=2&&b[r-1][c]===t&&b[r-2][c]===t));
      b[r][c]=t;}}
  return b;
}
function findMatches(b){
  const m=new Set();
  for(let r=0;r<ROWS;r++)for(let c=0;c<COLS-2;c++){
    const t=b[r][c];
    if(t&&t===b[r][c+1]&&t===b[r][c+2]){m.add(r+','+c);m.add(r+','+(c+1));m.add(r+','+(c+2));
      let n=c+3;while(n<COLS&&b[r][n]===t){m.add(r+','+n);n++}}}
  for(let c=0;c<COLS;c++)for(let r=0;r<ROWS-2;r++){
    const t=b[r][c];
    if(t&&t===b[r+1][c]&&t===b[r+2][c]){m.add(r+','+c);m.add((r+1)+','+c);m.add((r+2)+','+c);
      let n=r+3;while(n<ROWS&&b[n][c]===t){m.add(n+','+c);n++}}}
  return [...m].map(s=>s.split(',').map(Number));
}
function adj(a,b,c,d){return Math.abs(a-c)+Math.abs(b-d)===1}
function swap(b,r1,c1,r2,c2){const t=b[r1][c1];b[r1][c1]=b[r2][c2];b[r2][c2]=t}

function render(){
  const el=$('board');el.innerHTML='';
  for(let r=0;r<ROWS;r++)for(let c=0;c<COLS;c++){
    const t=document.createElement('div');
    t.className='tile';t.textContent=board[r][c]||'';
    t.dataset.r=r;t.dataset.c=c;
    if(sel&&sel.r===r&&sel.c===c)t.classList.add('sel');
    t.onclick=()=>click(r,c);
    el.appendChild(t);}
}
function floaty(r,c,txt){
  const el=document.createElement('div');el.className='floaty';el.textContent=txt;
  const cell=$('board').children[r*COLS+c];
  if(!cell)return;
  const rect=cell.getBoundingClientRect();const par=$('game').getBoundingClientRect();
  el.style.left=(rect.left-par.left+rect.width/2-15)+'px';
  el.style.top=(rect.top-par.top)+'px';
  $('game').appendChild(el);setTimeout(()=>el.remove(),900);
}
function shake(){const g=$('game').parentElement;g.classList.remove('shake');void g.offsetWidth;g.classList.add('shake')}
function flash(){const f=document.createElement('div');f.className='flash';document.body.appendChild(f);setTimeout(()=>f.remove(),250)}

async function sleep(ms){return new Promise(r=>setTimeout(r,ms))}

async function click(r,c){
  if(busy||!playing)return;
  if(!sel){sel={r,c};render();return;}
  if(sel.r===r&&sel.c===c){sel=null;render();return;}
  if(adj(sel.r,sel.c,r,c)){
    const nb=board.map(x=>x.slice());
    swap(nb,sel.r,sel.c,r,c);
    if(findMatches(nb).length>0){
      board=nb;sel=null;busy=true;render();
      moves--;updateHud();await cascade();
      if(score>=GOAL&&moves>=0){busy=false;return win()}
      if(moves<=0){busy=false;return lose()}
      busy=false;
    }else{sel=null;render();}
  }else{sel={r,c};render();}
}
async function cascade(){
  let total=0;
  while(true){
    const m=findMatches(board);
    if(m.length===0)break;
    total+=m.length*10;
    floaty(m[0][0],m[0][1],'+'+(m.length*10));
    // mark pop
    const cells=$('board').children;
    m.forEach(([r,c])=>{const idx=r*COLS+c;if(cells[idx])cells[idx].classList.add('pop')});
    shake();flash();
    await sleep(380);
    m.forEach(([r,c])=>board[r][c]=null);
    // gravity
    for(let c=0;c<COLS;c++){let gap=0;
      for(let r=ROWS-1;r>=0;r--){if(board[r][c]===null)gap++;else if(gap>0){board[r+gap][c]=board[r][c];board[r][c]=null}}
      for(let r=0;r<gap;r++)board[r][c]=TYPES[Math.floor(Math.random()*TYPES.length)];
    }
    score+=m.length*10;updateHud();render();
    // mark dropped (best-effort: whole board re-render, animate top row)
    await sleep(420);
  }
}
function updateHud(){
  $('score').textContent=score;
  const m=$('moves');m.textContent=moves;
  m.classList.toggle('warn',moves<=3);
}
function start(){
  board=createBoard();sel=null;score=0;moves=MAX_MOVES;busy=false;playing=true;sent=false;
  $('startScreen').style.display='none';
  $('result').style.display='none';
  $('hud').style.display='flex';
  $('game').style.display='block';
  updateHud();render();
}
function win(){
  playing=false;
  $('game').style.display='none';
  $('hud').style.display='none';
  $('result').style.display='block';
  $('resEmoji').textContent='🎉';$('resTitle').textContent='Победа!';
  $('resText').innerHTML='Очки: <b>'+score+'</b>. Ты выиграл <b>+1 гадание</b> в боте!';
  sendData('win');
}
function lose(){
  playing=false;
  $('game').style.display='none';
  $('hud').style.display='none';
  $('result').style.display='block';
  $('resEmoji').textContent='😿';$('resTitle').textContent='Не вышло...';
  $('resText').innerHTML='Очки: <b>'+score+'</b>. Не набрал '+GOAL+'. Попробуй ещё!';
}
function sendData(ev){
  if(sent)return;sent=true;
  const payload=JSON.stringify({event:ev,score,moves_left:moves});
  try{
    if(window.Telegram&&Telegram.WebApp&&Telegram.WebApp.sendData){
      Telegram.WebApp.sendData(payload);
      return;
    }
  }catch(e){}
  // outside telegram (browser debug) — just toast
  toast('Сэмулировано: '+payload);
}
function share(){
  const txt='🐱 Я играю в CatWood Match-3! Собрал '+score+' очков и выиграл гадание. Попробуй: https://t.me/catwood_bot?start=play';
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(txt).then(()=>toast('Скопировано!'),()=>fallbackShare(txt))}
  else fallbackShare(txt);
}
function fallbackShare(txt){
  const ta=document.createElement('textarea');ta.value=txt;document.body.appendChild(ta);ta.select();
  try{document.execCommand('copy');toast('Скопировано!')}catch(e){toast('Нет доступа к буферу')}
  ta.remove();
}
$('playBtn').onclick=start;
$('againBtn').onclick=start;
$('shareBtn').onclick=share;
if(window.Telegram&&Telegram.WebApp){Telegram.WebApp.ready();Telegram.WebApp.expand();}
</script>
</body>
</html>
"""
