import logging, os, sys, io, random, tempfile, sqlite3, urllib.parse, asyncio
from aiohttp import web
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultCachedPhoto, InlineQueryResultCachedVoice, InlineQueryResultArticle, InputTextMessageContent, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, InlineQueryHandler, CallbackQueryHandler, PreCheckoutQueryHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

import os
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8827616686:AAFwdGgz5dkKEe_VbXvfHHecZk3Se0oOPek")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))

BOT_USERNAME = "catwood_bot"

CATS = [
    (1,"Дух Света","Светозарный Кот","Твой голос прорезает тьму, как первый луч рассвета.","свет","✨",0,0.3,0,400),
    (2,"Хранитель Теней","Кот-Тень","Ты крадёшься в темноте и шепчешь древние тайны.","тьма","🌑",0.3,1.0,50,200),
    (3,"Буревестник","Кот-Штормогром","Твой рёв сотрясает небеса! Даже духи трепещут.","буря","⚡",0.5,1.0,50,150),
    (4,"Шёпот Луны","Лунный Кот","Твой тихий голос — шёпот самой луны, манящий звёзды.","луна","🌙",0,0.15,200,800),
    (5,"Пепельный Странник","Кот-Странник","Твой прерывистый голос эхом разносится меж миров.","пепел","🌫",0,0.5,150,400),
    (6,"Кристальный Звон","Кот-Хрусталь","Высокий чистый звон твоего голоса разбивает тишину на осколки.","кристалл","💎",0.05,0.3,400,800),
    (7,"Тлеющий Уголь","Кот-Огонёк","Ты тихо мурлычешь, но внутри — жар древнего вулкана.","огонь","🔥",0.05,0.2,80,250),
    (8,"Ледяной Ветер","Кот-Вьюга","Твой голос — ледяной сквозняк из забытых пещер.","лёд","❄️",0,0.25,100,300),
    (9,"Корень Мира","Кот-Древо","Твой голос — глубокий гул корней, уходящих в самое сердце земли.","земля","🌳",0.2,0.6,50,150),
    (10,"Искра","Кот-Искра","Твой голос — искра, зажжённая в сердце леса.","свет","✨",0,0.2,200,600),
    (11,"Сумерки","Кот-Сумерки","Ты стоишь на грани дня и ночи.","сумерки","🌆",0.1,0.4,100,350),
    (12,"Мшистый","Мшистый Кот","Твой мурлыкающий голос — как мох на древних камнях.","земля","🪨",0.2,0.5,50,200),
    (13,"Роса","Кот-Роса","Твой голос свеж, как утро в лесу после дождя.","вода","💧",0,0.15,300,700),
    (14,"Вулкан","Кот-Вулкан","Твой рёв — извержение из недр земли!","огонь","🌋",0.6,1.0,30,120),
    (15,"Зефир","Кот-Зефир","Ты лёгкий, как облачко в летнем небе.","воздух","☁️",0,0.2,200,500),
    (16,"Гроза","Кот-Гроза","Твой голос гремит как раскаты грома.","буря","🌩",0.5,1.0,40,180),
    (17,"Тишина","Кот-Тишина","Ты молчалив, но твоё мяу — оглушительно в тишине.","тишина","🤫",0,0.1,0,100),
    (18,"Эхо","Кот-Эхо","Твой голос отражается в вечности.","эфир","🔊",0.1,0.5,150,450),
    (19,"Звезда","Звёздный Кот","Ты мяукаешь в такт пульсару вселенной.","космос","🌟",0,0.2,400,800),
    (20,"Папоротник","Кот-Папоротник","Ты — дикий и прекрасный, как лесная чаща.","природа","🌿",0.1,0.4,100,300),
    (21,"Ручей","Кот-Ручей","Твой голос журчит, как горный ручей весной.","вода","🏔",0,0.2,250,600),
    (22,"Туман","Туманный Кот","Ты — таинственен, как лес в предрассветном тумане.","туман","🌁",0,0.3,50,250),
    (23,"Глина","Кот-Глина","Твой мяу — мягкий и податливый, как сырая глина.","земля","🏺",0.1,0.3,80,220),
    (24,"Молния","Кот-Молния","Твой крик разрезает небо пополам!","буря","⚡",0.4,1.0,200,600),
    (25,"Мрак","Кот-Мрак","Из глубины твоего голоса выползает древний мрак.","тьма","🖤",0.3,0.8,30,120),
    (26,"Золото","Золотой Кот","Твой голос переливается, как солнечный свет в листве.","свет","🌟",0.1,0.4,300,700),
    (27,"Серебро","Серебряный Кот","Твой голос — лунный свет на поверхности озера.","луна","🌙",0,0.2,250,650),
    (28,"Железо","Железный Кот","Твой голос твёрд, как кованый металл.","земля","⚙️",0.4,0.7,60,200),
    (29,"Буря","Кот-Буря","В твоём голосе — сила урагана!","буря","🌀",0.5,1.0,100,350),
    (30,"Покой","Кот-Покой","Твой голос — тихая гавань в бушующем мире.","вода","🕊",0,0.1,80,200),
    (31,"Пламя","Кот-Пламя","Ты говоришь — и воздух вокруг нагревается.","огонь","🔥",0.3,0.7,100,300),
    (32,"Лёд","Кот-Лёд","От твоего голоса стынут озёра.","лёд","🧊",0,0.2,50,180),
    (33,"Ветер","Кот-Ветер","Твой голос — вольный ветер в степи.","воздух","🌬",0.1,0.4,200,500),
    (34,"Скала","Кот-Скала","Твой голос непоколебим, как утёс.","земля","⛰",0.3,0.6,40,150),
    (35,"Радуга","Радужный Кот","Твой голос переливается всеми цветами!","свет","🌈",0.1,0.5,300,750),
    (36,"Ночь","Ночной Кот","Твой голос — сама ночь, полная тайн и звёзд.","тьма","🌌",0,0.3,60,250),
    (37,"Заря","Кот-Заря","Твой голос — первый луч солнца над горизонтом.","свет","🌅",0,0.3,250,600),
    (38,"Гром","Кот-Гром","Твой голос сотрясает землю!","буря","💥",0.7,1.0,30,120),
    (39,"Шёлк","Шёлковый Кот","Твой голос гладкий и нежный, как шёлк.","воздух","🎀",0,0.15,200,500),
    (40,"Кремень","Кот-Кремень","Твой голос высекает искры из тишины.","огонь","💎",0.3,0.6,100,280),
    (41,"Пыльца","Кот-Пыльца","Твой голос кружится, как светящаяся пыльца в лесу.","природа","🌼",0,0.2,350,750),
    (42,"Глубина","Глубинный Кот","Твой голос идёт из самой бездны.","вода","🌊",0.2,0.5,30,120),
    (43,"Высота","Кот-Высота","Твой голос парит под облаками.","воздух","🦅",0.1,0.4,300,700),
    (44,"Корень","Кот-Корень","Твой голос уходит глубоко в землю.","земля","🌱",0.1,0.3,50,180),
    (45,"Сок","Кот-Сок","Твой голос сочный и живительный.","природа","🍃",0.1,0.3,200,450),
    (46,"Коготь","Кот-Коготь","В твоём голосе слышен звон выпущенных когтей.","тьма","🗡️",0.4,0.8,100,300),
    (47,"Мур","Кот-Мурлыка","Твой голос — вибрация, исцеляющая душу.","эфир","🎵",0.1,0.3,50,150),
    (48,"Визг","Кот-Визг","Твой голос пронзает реальность насквозь!","буря","📢",0.3,0.7,500,800),
    (49,"Пульс","Кот-Пульс","Твой голос бьётся в ритме сердца леса.","эфир","💓",0.1,0.4,100,350),
    (50,"Тайна","Таинственный Кот","Твой голос скрывает больше, чем раскрывает.","туман","❓",0,0.3,80,350),
    (51,"Светляк","Кот-Светляк","Твой голос мерцает во тьме, как рой светлячков.","свет","🪲",0,0.2,300,700),
    (52,"Смерч","Кот-Смерч","Твой голос закручивается в воронку!","буря","🌪",0.5,1.0,150,450),
    (53,"Безмолвие","Кот-Безмолвие","Ты говоришь молчанием, и это громче любых слов.","тишина","🤐",0,0.05,0,50),
    (54,"Звон","Кот-Звон","Твой голос звучит как колокол в храме леса.","эфир","🔔",0.2,0.5,400,700),
    (55,"Иней","Кот-Иней","Твой голос покрывает всё вокруг серебристым инеем.","лёд","❄️",0,0.2,150,400),
    (56,"Жар","Кот-Жар","От твоего голоса плавится камень.","огонь","🌋",0.4,0.8,50,200),
    (57,"Бриз","Кот-Бриз","Твой голос — лёгкий ветерок с моря.","воздух","🌊",0,0.15,200,500),
    (58,"Град","Кот-Град","Твой голос стучит, как град по крыше мира.","буря","🧊",0.3,0.6,200,500),
    (59,"Лоза","Кот-Лоза","Твой голос вьётся, как дикий виноград.","природа","🌿",0.1,0.4,150,350),
    (60,"Яшма","Яшмовый Кот","Твой голос — драгоценный камень в короне леса.","земля","💎",0.1,0.4,100,300),
    (61,"Топаз","Топазовый Кот","Твой голос прозрачный и тёплый, как топаз.","свет","🟡",0.1,0.3,200,500),
    (62,"Лава","Кот-Лава","Твой голос течёт медленно, но обжигает!","огонь","🟠",0.3,0.6,30,120),
    (63,"Родник","Кот-Родник","Твой голос — чистый источник в глубине чащи.","вода","💧",0,0.2,200,500),
    (64,"Отражение","Кот-Отражение","Твой голос — отражение отражения в бесконечности.","эфир","🪞",0.1,0.4,100,350),
    (65,"Зенит","Кот-Зенит","Твой голос — солнце в зените!","свет","☀️",0.3,0.6,300,700),
    (66,"Пропасть","Кот-Пропасть","Твой голос падает в бесконечную пропасть.","тьма","🕳️",0.2,0.5,20,100),
    (67,"Мерцание","Мерцающий Кот","Твой голос то появляется, то исчезает во тьме.","туман","✨",0,0.3,200,600),
    (68,"Гейзер","Кот-Гейзер","Твой голос вырывается наружу с неудержимой силой!","огонь","💨",0.5,1.0,100,350),
    (69,"Спектр","Кот-Спектр","Твой голос — это целая палитра звуков!","эфир","🌈",0.2,0.6,200,600),
    (70,"Орион","Кот-Орион","Твой голос — созвездие, которое ведёт заблудших.","космос","⭐",0.1,0.4,100,400),
]

CATALOGUE = [{"id":c[0],"name":c[1],"title":c[2],"description":c[3],"element":c[4],"emoji":c[5],
              "acoustic":{"min_rms":c[6],"max_rms":c[7],"min_f0":c[8],"max_f0":c[9]}} for c in CATS]

LEGENDARY_IDS = {5, 9, 24, 29, 38, 52, 66, 70, 11, 48}
LEGENDARY_CATS = [c for c in CATALOGUE if c['id'] in LEGENDARY_IDS]

_share_data = {}
_last_analysis = {}
_pending_action = {}

def classify_cat(rms, f0, exclude_ids=None, pool=None):
    candidates = pool or CATALOGUE
    if exclude_ids:
        candidates = [c for c in candidates if c['id'] not in exclude_ids]
    if not candidates:
        candidates = CATALOGUE
    similarities = []
    for cat in candidates:
        a = cat['acoustic']
        rms_range = a["max_rms"] - a["min_rms"]
        f0_range = a["max_f0"] - a["min_f0"]
        if rms_range < 1e-6: rms_range = 1e-6
        if f0_range < 1e-6: f0_range = 1e-6
        rms_outside = 0.0
        if rms < a["min_rms"]:
            rms_outside = (a["min_rms"] - rms) / rms_range
        elif rms > a["max_rms"]:
            rms_outside = (rms - a["max_rms"]) / rms_range
        f0_outside = 0.0
        if f0 < a["min_f0"]:
            f0_outside = (a["min_f0"] - f0) / f0_range
        elif f0 > a["max_f0"]:
            f0_outside = (f0 - a["max_f0"]) / f0_range
        dist = (rms_outside**2 + f0_outside**2) ** 0.5
        similarity = __import__('math').exp(-dist * 1.0)
        similarities.append(similarity)
    total = sum(similarities)
    if total == 0:
        probabilities = [1.0 / len(candidates)] * len(candidates)
    else:
        probabilities = [s / total for s in similarities]
    import random
    chosen_index = random.choices(range(len(candidates)), weights=probabilities)[0]
    return candidates[chosen_index]


def analyze_audio_bytes(ogg_bytes):
    tmp = tempfile.gettempdir()
    ogg_path = os.path.join(tmp, "cv.ogg")
    with open(ogg_path, "wb") as f: f.write(ogg_bytes)
    try:
        y, sr = sf.read(ogg_path, dtype="float32")
        if len(y) > sr * 5: y = y[:sr * 5]
    finally:
        if os.path.exists(ogg_path): os.remove(ogg_path)
    if len(y) < 1024: return float(np.abs(y).mean()), 200.0
    y = y - np.mean(y)
    n = len(y)
    fft = np.fft.fft(y, n=2*n)
    acf = np.fft.ifft(fft * np.conj(fft)).real[:n]
    acf = acf / (acf[0] + 1e-10)
    min_lag = max(1, int(sr / 800))
    max_lag = min(len(acf) - 1, int(sr / 50))
    if min_lag >= max_lag: return float(np.abs(y).mean()), 200.0
    peak = np.argmax(acf[min_lag:max_lag]) + min_lag
    f0 = sr / peak if acf[peak] > 0.1 else 200.0
    return float(np.abs(y).mean()), float(f0)

BG = [(20,15,40),(25,15,30),(40,25,10),(10,30,25),(35,10,20),(15,15,15)]
EC = {"свет":(255,255,200),"тьма":(150,130,200),"огонь":(255,180,80),"вода":(100,200,255),
      "земля":(180,160,100),"воздух":(200,230,255),"буря":(200,180,255),"луна":(200,220,255),
      "лёд":(200,240,255),"туман":(180,180,200),"эфир":(220,200,255),"природа":(180,230,150),
      "космос":(150,150,255),"тишина":(200,200,210),"пепел":(180,170,160),"сумерки":(160,140,180),
      "кристалл":(200,220,255)}
SYMS = ["◇","○","△","☯","⟡","✧","∞","⚘","☽","𓋹","⟐","✳"]

def gen_card(cat, legendary=False):
    W,H=600,700;bg=random.choice(BG)
    img=Image.new("RGBA",(W,H),bg);d=ImageDraw.Draw(img)
    for _ in range(30):
        x,y,r=random.randint(0,W),random.randint(0,H),random.randint(15,80)
        d.ellipse([x-r,y-r,x+r,y+r],fill=(255,255,255,random.randint(5,25)))
    for _ in range(20):
        x,y,r=random.randint(0,W),random.randint(0,H),random.randint(2,6)
        c=random.choice([(240,230,200),(200,220,255),(200,255,220),(255,200,220),(220,200,255),(255,220,180)])
        d.ellipse([x-r,y-r,x+r,y+r],fill=(c[0],c[1],c[2],random.randint(30,80)))
    ec=EC.get(cat['element'],(200,200,200))
    try:
        fp=os.path.join(os.path.dirname(__file__),"font.ttf")
        ft=ImageFont.truetype(fp,44);fn=ImageFont.truetype(fp,32);fd=ImageFont.truetype(fp,22);fs=ImageFont.truetype(fp,18)
    except:
        ft=fn=fd=fs=ImageFont.load_default()
    d.rectangle([20,20,W-20,H-20],outline=ec+(80,),width=2)
    t=f"{cat['emoji']}  {cat['name']}  {cat['emoji']}";bb=d.textbbox((0,0),t,font=ft);d.text(((W-(bb[2]-bb[0]))//2,60),t,font=ft,fill=ec+(230,))
    bb=d.textbbox((0,0),cat['title'],font=fn);nw=bb[2]-bb[0];d.rectangle([(W-nw)//2-15,122,(W+nw)//2+15,170],fill=bg+(180,),outline=ec+(120,),width=1);d.text(((W-nw)//2,130),cat['title'],font=fn,fill=(255,255,255,220))
    d.line([100,200,500,200],fill=ec+(100,),width=1);yd=240
    for line in cat['description'].split(". "):
        bb=d.textbbox((0,0),line,font=fd);d.text(((W-(bb[2]-bb[0]))//2,yd),line,font=fd,fill=(200,220,220,200));yd+=35
    t=f"🌀 СТИХИЯ: {cat['element'].upper()}";bb=d.textbbox((0,0),t,font=fs);d.text(((W-(bb[2]-bb[0]))//2,350),t,font=fs,fill=ec+(180,))
    s=random.choice(SYMS);bb=d.textbbox((0,0),s,font=fn);d.text(((W-(bb[2]-bb[0]))//2,420),s,font=fn,fill=ec+(60,))
    t="🐾 Дух Леса указал на тебя 🐾";bb=d.textbbox((0,0),t,font=fs);d.text(((W-(bb[2]-bb[0]))//2,520),t,font=fs,fill=(255,255,255,150))
    t=f"t.me/{BOT_USERNAME}";bb=d.textbbox((0,0),t,font=fs);d.text(((W-(bb[2]-bb[0]))//2,570),t,font=fs,fill=(180,180,255,120))
    if legendary:
        d.rectangle([15,15,W-15,H-15],outline=(255,215,0,200),width=4)
        t="👑 ЛЕГЕНДАРНЫЙ ТОТЕМ 👑";bb=d.textbbox((0,0),t,font=fs);d.text(((W-(bb[2]-bb[0]))//2,480),t,font=fs,fill=(255,215,0,200))
    t=f"✦ Тотем #{cat['id']} ✦";bb=d.textbbox((0,0),t,font=fs);d.text(((W-(bb[2]-bb[0]))//2,630),t,font=fs,fill=(150,150,180,90))
    buf=io.BytesIO();img.save(buf,format="PNG");return buf.getvalue()

DB=os.path.join(os.path.dirname(__file__),"sanctuary.db")
def init_db():
    with sqlite3.connect(DB) as c:
        c.execute("CREATE TABLE IF NOT EXISTS readings(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,cat_id INTEGER,cat_name TEXT,file_id TEXT,ts TEXT)")
        try:c.execute("ALTER TABLE readings ADD COLUMN file_id TEXT")
        except:pass
        c.execute("CREATE TABLE IF NOT EXISTS stats(id INTEGER PRIMARY KEY AUTOINCREMENT,total INTEGER DEFAULT 0,users INTEGER DEFAULT 0,starts INTEGER DEFAULT 0)")
        try: c.execute("ALTER TABLE stats ADD COLUMN starts INTEGER DEFAULT 0")
        except: pass
        c.execute("CREATE TABLE IF NOT EXISTS user_limits(user_id INTEGER PRIMARY KEY,daily_date TEXT,daily_count INTEGER DEFAULT 0,unlimited_until TEXT,bonus_readings INTEGER DEFAULT 0)")
        try: c.execute("ALTER TABLE user_limits ADD COLUMN bonus_readings INTEGER DEFAULT 0")
        except: pass
        c.execute("CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,payload TEXT,stars INTEGER,ts TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS referrals(id INTEGER PRIMARY KEY AUTOINCREMENT,referrer_id INTEGER,referee_id INTEGER,ts TEXT)")
def record_reading(uid,cid,cname,fid):
    with sqlite3.connect(DB) as c:
        c.execute("INSERT INTO readings(user_id,cat_id,cat_name,file_id,ts) VALUES(?,?,?,?,?)",(uid,cid,cname,fid,datetime.now().isoformat()))
        c.execute("UPDATE stats SET total=COALESCE(total,0)+1 WHERE id=1")
        if c.rowcount==0:c.execute("INSERT INTO stats(id,total,users) VALUES(1,1,0)")
        c.execute("SELECT COUNT(DISTINCT user_id) FROM readings");c.execute("UPDATE stats SET users=? WHERE id=1",(c.fetchone()[0],))
def record_start():
    with sqlite3.connect(DB) as c:
        c.execute("UPDATE stats SET starts=COALESCE(starts,0)+1 WHERE id=1")
        if c.rowcount==0:c.execute("INSERT INTO stats(id,total,users,starts) VALUES(1,0,0,1)")

def _get_limit_info(user_id):
    with sqlite3.connect(DB) as conn:
        try:
            row = conn.execute("SELECT daily_date, daily_count, unlimited_until, bonus_readings FROM user_limits WHERE user_id=?", (user_id,)).fetchone()
            if row: return {"daily_date": row[0], "daily_count": row[1], "unlimited_until": row[2], "bonus_readings": row[3] or 0}
        except:
            row = conn.execute("SELECT daily_date, daily_count, unlimited_until FROM user_limits WHERE user_id=?", (user_id,)).fetchone()
            if row: return {"daily_date": row[0], "daily_count": row[1], "unlimited_until": row[2], "bonus_readings": 0}
        return None

def _can_read(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    info = _get_limit_info(user_id)
    if info and info["unlimited_until"]:
        try:
            if datetime.fromisoformat(info["unlimited_until"]) > datetime.now():
                return "premium"
        except: pass
    daily_used = info["daily_count"] if info and info["daily_date"] == today else 0
    extra = info["bonus_readings"] if info else 0
    if daily_used >= 3 + extra:
        return "limit"
    return "ok"

def _use_reading(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB) as conn:
        info = _get_limit_info(user_id)
        if info:
            if info["daily_date"] == today:
                bonus = info["bonus_readings"] or 0
                if bonus > 0 and info["daily_count"] >= 3:
                    conn.execute("UPDATE user_limits SET bonus_readings=bonus_readings-1 WHERE user_id=?", (user_id,))
                    return
                conn.execute("UPDATE user_limits SET daily_count=daily_count+1 WHERE user_id=?", (user_id,))
            else:
                bonus = info["bonus_readings"] or 0
                if bonus > 0:
                    conn.execute("UPDATE user_limits SET daily_date=?, daily_count=0, bonus_readings=bonus_readings-1 WHERE user_id=?", (today, user_id))
                else:
                    conn.execute("UPDATE user_limits SET daily_date=?, daily_count=1 WHERE user_id=?", (today, user_id))
        else:
            conn.execute("INSERT INTO user_limits(user_id, daily_date, daily_count) VALUES(?,?,1)", (user_id, today))

def _get_daily_remaining(user_id):
    info = _get_limit_info(user_id)
    if not info: return 3
    if info["unlimited_until"]:
        try:
            if datetime.fromisoformat(info["unlimited_until"]) > datetime.now():
                return float('inf')
        except: pass
    today = datetime.now().strftime("%Y-%m-%d")
    extra = info["bonus_readings"] or 0
    if info["daily_date"] == today: return max(0, 3 + extra - info["daily_count"])
    return 3 + extra

def _set_unlimited(user_id, days=30):
    until = (datetime.now() + timedelta(days=days)).isoformat()
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB) as conn:
        conn.execute("INSERT OR REPLACE INTO user_limits(user_id, daily_date, daily_count, unlimited_until) VALUES(?,?,COALESCE((SELECT daily_count FROM user_limits WHERE user_id=?),0),?)", (user_id, today, user_id, until))

def _record_payment(user_id, payload, stars):
    with sqlite3.connect(DB) as conn:
        conn.execute("INSERT INTO payments(user_id, payload, stars, ts) VALUES(?,?,?,?)", (user_id, payload, stars, datetime.now().isoformat()))

def _add_bonus(user_id, amount=1):
    try:
        with sqlite3.connect(DB) as conn:
            conn.execute("INSERT INTO user_limits(user_id,daily_date,daily_count,bonus_readings) VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET bonus_readings=bonus_readings+?", (user_id, datetime.now().strftime("%Y-%m-%d"), 0, amount, amount))
    except:
        try:
            with sqlite3.connect(DB) as conn:
                conn.execute("INSERT OR IGNORE INTO user_limits(user_id,daily_date,daily_count) VALUES(?,?,0)", (user_id, datetime.now().strftime("%Y-%m-%d")))
        except: pass

async def start(u,c):
    record_start()
    args = c.args
    if args and args[0].startswith("ref_"):
        referrer_id = int(args[0][4:])
        referee_id = u.effective_user.id
        if referrer_id != referee_id:
            _add_bonus(referrer_id, 1)
            try:
                with sqlite3.connect(DB) as conn:
                    conn.execute("INSERT INTO referrals(referrer_id, referee_id, ts) VALUES(?,?,?)", (referrer_id, referee_id, datetime.now().isoformat()))
            except: pass
    await u.message.reply_text(
        f"🌿 *Дух Леса приветствует тебя, {u.effective_user.first_name}...* 🌿\n\n"
        "Ты стоишь на пороге *Зачарованного Леса*.\n"
        "Духи слышат твои шаги. Они хотят услышать твой голос.\n\n"
        "🎤 *Нажми на микрофон* и издай звук как кот:\n"
        "— Мяу, мурлыкай, шипи, вой, рычи...\n\n"
        "🐾 *Готов?* Тогда мяу, странник... 🐾",
        parse_mode="Markdown"
    )

async def handle_voice(u,c):
    user_id = u.effective_user.id
    s=await u.message.reply_text("🌌 *Дух Леса внимает твоему зову...* 🌌",parse_mode="Markdown")
    try:
        action = _pending_action.pop(user_id, None)
        if action not in ("legendary", "reroll"):
            status = _can_read(user_id)
            if status == "limit":
                remaining = _get_daily_remaining(user_id)
                await c.bot.delete_message(chat_id=u.effective_chat.id,message_id=s.message_id)
                await u.message.reply_text(
                    f"🌫 *Лимит исчерпан* 🌫\n\nТы сегодня уже получил 3 тотема. Дух Леса устал.\n\n"
                    f"✨ Открой безлимитный доступ всего за *1 Star*!",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⭐ Безлимит (1 Star)", callback_data="buy_unlimited")]])
                )
                return
            _use_reading(user_id)
        vf=await u.message.voice.get_file();ob=await vf.download_as_bytearray()
        await c.bot.edit_message_text("🎵 Эхо разносится по лесу...",chat_id=u.effective_chat.id,message_id=s.message_id)
        rms,f0=analyze_audio_bytes(ob);logger.info(f"User {user_id}: rms={rms:.3f}, f0={f0:.1f}")
        if action == "reroll":
            last = _last_analysis.get(user_id)
            if last:
                cat = classify_cat(rms, f0, exclude_ids={last['cat_id']})
            else:
                cat = classify_cat(rms, f0)
            logger.info(f"  → Reroll тотем: {cat['name']}")
        elif action == "legendary":
            cat = classify_cat(rms, f0, pool=LEGENDARY_CATS)
            logger.info(f"  → Легендарный тотем: {cat['name']}")
        else:
            cat=classify_cat(rms,f0);logger.info(f"  → Тотем: {cat['name']}")
        _last_analysis[user_id] = {"rms": rms, "f0": f0, "cat_id": cat['id']}
        legendary = action == "legendary"
        await c.bot.edit_message_text("🔮 Древние силы сплетают твою суть...",chat_id=u.effective_chat.id,message_id=s.message_id)
        img=gen_card(cat, legendary=legendary)
        await c.bot.delete_message(chat_id=u.effective_chat.id,message_id=s.message_id)
        await u.message.reply_voice(voice=u.message.voice.file_id, caption="🎧 *Твой голос услышан...*", parse_mode="Markdown")
        prefix = "👑 " if legendary else ""
        caption=f"{prefix}🌟 {cat['title']} 🌟\n\n{cat['emoji']} {cat['name']}\n{cat['description']}\n\n🌀 Стихия: {cat['element']}\n\nХочешь узнать свой тотем? Отправь боту голосовое сообщение с кошачьим голосом! 🐾\n\n👥 Приведи друга — получи +1 гадание: https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
        share_kb=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Сохранить в Избранное", callback_data="save_card")],[InlineKeyboardButton("📢 Поделиться с друзьями", switch_inline_query=str(user_id))]])
        image_path = None
        for ext in ("jpg", "jpeg", "png"):
            candidate = Path("image") / (str(cat['id']) + "." + ext)
            if candidate.is_file():
                image_path = candidate
                break
        if image_path is not None:
            with open(image_path, "rb") as img_file:
                sent=await u.message.reply_photo(photo=img_file, caption=caption, parse_mode=None, reply_markup=share_kb, write_timeout=120, read_timeout=120)
        else:
            sent=await u.message.reply_photo(photo=io.BytesIO(img), caption=caption, parse_mode=None, reply_markup=share_kb, write_timeout=120, read_timeout=120)
        fid = sent.photo[-1].file_id
        try:record_reading(user_id,cat['id'],cat['name'],fid)
        except:pass
        _share_data[user_id] = {"file_id": fid, "cat": cat, "chat_id": u.effective_chat.id, "message_id": sent.message_id}
    except Exception as e:
        logger.error(f"Ошибка: {e}",exc_info=True)
        try:await c.bot.edit_message_text("🌫 *Туман сгущается...* Попробуй ещё раз! 🐱\n\n_Подсказка: запиши голос подлиннее (3-5 секунд)_",chat_id=u.effective_chat.id,message_id=s.message_id,parse_mode="Markdown")
        except:await u.message.reply_text("🌫 *Туман...* Попробуй ещё раз! 🐱",parse_mode="Markdown")

async def stats(u,c):
    if u.effective_user.id!=ADMIN_ID:return await u.message.reply_text("❌ Только Хранитель Леса может видеть это.")
    with sqlite3.connect(DB) as conn:
        t=conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        us=conn.execute("SELECT COUNT(DISTINCT user_id) FROM readings").fetchone()[0]
        st=conn.execute("SELECT COALESCE(starts,0) FROM stats WHERE id=1").fetchone()[0]
        rd=conn.execute("SELECT COUNT(*) FROM readings WHERE ts>=datetime('now','-1 day')").fetchone()[0]
        rw=conn.execute("SELECT COUNT(*) FROM readings WHERE ts>=datetime('now','-7 days')").fetchone()[0]
        stars=conn.execute("SELECT COALESCE(SUM(stars),0) FROM payments").fetchone()[0]
        refs=conn.execute("SELECT COUNT(*) FROM referrals").fetchone()[0]
        top=conn.execute("SELECT cat_name, COUNT(*) as cnt FROM readings GROUP BY cat_name ORDER BY cnt DESC LIMIT 5").fetchall()
    msg=(
        f"🌿 *Святилище Кошачьего Духа* 🌿\n\n"
        f"👣 Заходов: *{st}*\n"
        f"🐱 Тотемов раскрыто: *{t}*\n"
        f"🙏 Странников: *{us}*\n"
        f"📊 За сутки: *{rd}* | За неделю: *{rw}*\n"
        f"⭐ Stars заработано: *{stars}*\n"
        f"🔗 Рефералов: *{refs}*"
    )
    if top:msg+="\n\n*Топ-5 тотемов:*\n"+("\n".join(f"  • {n}: {cnt}" for n,cnt in top))
    msg+="\n\n_Дух Леса доволен._"
    await u.message.reply_text(msg,parse_mode="Markdown")

async def about(u,c):
    await u.message.reply_text(
        "🌲 *О Святилище Котов-Тотемов* 🌲\n\n"
        "Идея родилась из разговора двух путников:\n"
        "🎭 *Дмитрий* — хотел железную коробку с ИИ для кошек\n"
        "🧙 *Тимофей* — заметил тренд с птичьими голосовухами\n\n"
        "И родилась *Кото-печенька* —\n"
        "бот, который слушает твой голос и находит\n"
        "твоего древнего кошачьего духа-тотема.\n\n"
        "70 кошек. 70 судеб. 70 тотемов.\n\n"
        "🎨 *Стикерпак:* [CatWood](https://t.me/addstickers/CatWood)\n\n"
        "🐾 *Запиши свой голос — узнай кто ты* 🐾",
        parse_mode="Markdown"
    )

async def help_cmd(u,c):
    await u.message.reply_text(
        "🐱 *Кото-печенька — Как это работает* 🐱\n\n"
        "1️⃣ Отправь голосовое сообщение\n"
        "2️⃣ Мяукай, мурлычь, шипи, вой, ори\n"
        "3️⃣ Получи своего кота-тотема!\n"
        "4️⃣ Поделись с друзьями\n\n"
        "✨ *Каждый голос уникален — каждый тотем священен* ✨\n\n"
        "Команды: /start /help /stats /about /premium",
        parse_mode="Markdown"
    )

async def premium(u,c):
    remaining = _get_daily_remaining(u.effective_user.id)
    if remaining == float('inf'):
        await u.message.reply_text(
            "🌟 *У тебя уже есть Безлимитный доступ!* 🌟\n\n"
            "Спасибо за поддержку Зачарованного Леса!\n\n"
            "👑 Хочешь Легендарного кота? Открой /premium\n"
            "🔄 Или перебрось тотем через /premium",
            parse_mode="Markdown"
        )
        return
    text = (
        f"🌟 *Зачарованный Лес — Премиум* 🌟\n\n"
        f"🐱 Бесплатных гаданий сегодня: *{remaining}*\n"
        f"🎭 Открой все тайны Леса с Telegram Stars!\n\n"
        f"⭐ *1 Star* — Безлимит на 30 дней ✨\n"
        f"   Сними дневной лимит!\n\n"
        f"⭐ *2 Stars* — Переброс тотема 🔄\n"
        f"   Получи нового кота из своего голоса\n\n"
        f"⭐ *3 Stars* — Легендарный кот 👑\n"
        f"   Эксклюзивный тотем из высшей касты!\n\n"
        f"🌲 *Дух Леса благодарит тебя за поддержку!*"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Безлимит (1 Star)", callback_data="buy_unlimited")],
        [InlineKeyboardButton("🔄 Переброс (2 Stars)", callback_data="buy_reroll")],
        [InlineKeyboardButton("👑 Легендарный (3 Stars)", callback_data="buy_legendary")],
        [InlineKeyboardButton("💝 Поддержать донатом", callback_data="donate")],
    ])
    await u.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

async def buy_callback(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    await query.answer()
    user_id = u.effective_user.id
    payload = query.data
    prices_map = {
        "buy_unlimited": (1, "⭐ Безлимит на 30 дней"),
        "buy_reroll": (2, "🔄 Переброс тотема"),
        "buy_legendary": (3, "👑 Легендарный кот"),
    }
    if payload not in prices_map:
        await query.edit_message_text("❌ Неизвестный товар")
        return
    if payload == "buy_reroll" and user_id not in _last_analysis:
        await query.edit_message_text("❌ Сначала получи тотем! Отправь голосовое сообщение.")
        return
    stars, title = prices_map[payload]
    await c.bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=f"Поддержка Зачарованного Леса ({stars} ⭐)",
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=title, amount=stars)],
    )

async def pre_checkout_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    user_id = u.effective_user.id
    payload = u.message.successful_payment.invoice_payload
    stars = u.message.successful_payment.total_amount
    _record_payment(user_id, payload, stars)
    if payload == "buy_unlimited":
        _set_unlimited(user_id)
        await u.message.reply_text(
            "🌟 *Безлимитный доступ активирован на 30 дней!* 🌟\n\n"
            "Дух Леса благодарит тебя! Теперь никаких ограничений.\n\n"
            "Отправляй голосовые сколько хочешь! 🐾",
            parse_mode="Markdown"
        )
    elif payload == "buy_reroll":
        last = _last_analysis.get(user_id)
        if last:
            cat = classify_cat(last['rms'], last['f0'], exclude_ids={last['cat_id']})
            _last_analysis[user_id] = {"rms": last['rms'], "f0": last['f0'], "cat_id": cat['id']}
            img = gen_card(cat)
            caption = f"🔄 *Переброс!* 🔄\n\n{cat['emoji']} {cat['title']}\n{cat['description']}\n\n🌀 Стихия: {cat['element']}"
            sent = await u.message.reply_photo(photo=io.BytesIO(img), caption=caption, parse_mode="Markdown", write_timeout=120, read_timeout=120)
            fid = sent.photo[-1].file_id
            try: record_reading(user_id, cat['id'], cat['name'], fid)
            except: pass
            _share_data[user_id] = {"file_id": fid, "voice_file_id": u.message.voice.file_id, "cat": cat, "chat_id": u.effective_chat.id, "message_id": sent.message_id}
            await u.message.reply_text("🐾 *Твой новый тотем!* Поделись с друзьями!", parse_mode="Markdown")
        else:
            await u.message.reply_text("❌ Нет данных о голосе. Отправь голосовое и повтори попытку.")
    elif payload == "buy_legendary":
        _pending_action[user_id] = "legendary"
        await u.message.reply_text(
            "👑 *Легендарный кот активирован!* 👑\n\n"
            "🎤 Отправь голосовое сообщение, и Дух Леса\n"
            "выберет тебе *Легендарного кота* из высшей касты!\n\n"
            "🐱 *Мяу-у-у...*",
            parse_mode="Markdown"
        )
    elif payload == "donate":
        stars = u.message.successful_payment.total_amount
        await u.message.reply_text(
            f"💝 *Огромное спасибо за поддержку ({stars} ⭐)!* 💝\n\n"
            "Дух Леса чувствует твою доброту.\n"
            "Благодаря таким путникам, как ты, Лес становится больше!\n\n"
            "🐾 *Мяу-у-у...* 🐾",
            parse_mode="Markdown"
        )

async def donate(u,c):
    await u.message.reply_text(
        "💝 *Поддержать Зачарованный Лес* 💝\n\n"
        "Если тебе нравится бот и ты хочешь помочь Лесу расти —\n"
        "выбери сумму доната:\n\n"
        "⭐ *1 Star* — тёплое спасибо от Духа Леса\n"
        "⭐ *3 Stars* — благословение древних котов\n"
        "⭐ *5 Stars* — ты становишься Хранителем Леса 🌲",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💝 1 Star", callback_data="donate_1")],
            [InlineKeyboardButton("💝 3 Stars", callback_data="donate_3")],
            [InlineKeyboardButton("💝 5 Stars", callback_data="donate_5")],
        ])
    )

async def donate_show_callback(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    await query.answer()
    await query.edit_message_text(
        "💝 *Поддержать Зачарованный Лес* 💝\n\n"
        "Выбери сумму доната:\n\n"
        "⭐ *1 Star* — тёплое спасибо\n"
        "⭐ *3 Stars* — благословение древних котов\n"
        "⭐ *5 Stars* — ты Хранитель Леса 🌲",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💝 1 Star", callback_data="donate_1")],
            [InlineKeyboardButton("💝 3 Stars", callback_data="donate_3")],
            [InlineKeyboardButton("💝 5 Stars", callback_data="donate_5")],
        ])
    )

async def donate_amount_callback(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    await query.answer()
    user_id = u.effective_user.id
    stars = int(query.data.split("_")[1])
    await c.bot.send_invoice(
        chat_id=user_id,
        title="💝 Донат Зачарованному Лесу",
        description=f"Благодарим за поддержку! ({stars} ⭐)",
        payload="donate",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"Донат {stars} ⭐", amount=stars)],
    )

async def save_card(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    user_id = u.effective_user.id
    data = _share_data.get(user_id)
    if not data or "chat_id" not in data or "message_id" not in data:
        await query.answer()
        await query.edit_message_text("🌫 Карточка утеряна в тумане... Отправь голосовое заново!")
        return
    try:
        await c.bot.copy_message(chat_id=user_id, from_chat_id=data["chat_id"], message_id=data["message_id"])
        await query.answer("✅ Сохранено в Избранном!", show_alert=True)
    except Exception as e:
        logger.error(f"Save card error: {e}", exc_info=True)
        await query.answer("❌ Не удалось сохранить. Попробуй ещё раз.", show_alert=True)

def _get_user_cat(user_id):
    try:
        with sqlite3.connect(DB) as conn:
            cur = conn.execute("SELECT cat_id,file_id FROM readings WHERE user_id=? ORDER BY ts DESC LIMIT 1", (user_id,))
            row = cur.fetchone()
            if row:
                for c in CATS:
                    if c[0] == row[0]:
                        return {"id": c[0], "title": c[1], "name": c[2], "description": c[3], "element": c[4], "emoji": c[5], "file_id": row[1]}
    except: pass
    return None

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.inline_query.query
    logger.info(f"Inline query from user {update.effective_user.id}: q={q!r}")
    try:
        user_id = int(q)
    except (ValueError, TypeError):
        logger.info(f"Invalid inline query (not a user_id): {q!r}")
        await update.inline_query.answer([], cache_time=0, is_personal=True)
        return
    data = _share_data.get(user_id)
    db_cat = _get_user_cat(user_id) if not data else None
    cat = data["cat"] if data else (db_cat if db_cat else None)
    file_id = data.get("file_id") if data else (db_cat.get("file_id") if db_cat else None)
    voice_file_id = data.get("voice_file_id") if data else None
    if cat:
        share_text = f"🐱 Я записал голос и Дух Леса показал, что я — «{cat['title']}»! А кто ты? https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    else:
        share_text = f"🐱 Запиши голосовое боту @{BOT_USERNAME} и узнай свой тотем!"
    logger.info(f"Inline: data={'yes' if data else 'no'}, db_cat={'yes' if db_cat else 'no'}, cat={'yes' if cat else 'no'}, file_id={'yes' if file_id else 'no'}")
    results = []
    if file_id:
        try:
            results.append(InlineQueryResultCachedPhoto(
                id="photo", photo_file_id=file_id, caption=share_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🐱 Узнать своего кота!", url=f"https://t.me/{BOT_USERNAME}")
                ]])
            ))
        except Exception as e:
            logger.error(f"Inline photo error: {e}", exc_info=True)
    if voice_file_id and cat:
        voice_title = f"🎤 {cat['emoji']} {cat['title']}"
        voice_caption = f"🎧 Слушай мой тотем! Я — {cat['emoji']} {cat['title']}\n\nУзнай своего: t.me/{BOT_USERNAME}"
        try:
            results.append(InlineQueryResultCachedVoice(
                id="voice", voice_file_id=voice_file_id, title=voice_title, caption=voice_caption,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🐱 Узнать своего кота!", url=f"https://t.me/{BOT_USERNAME}")
                ]])
            ))
        except Exception as e:
            logger.error(f"Inline voice error: {e}", exc_info=True)
    if not results:
        results.append(InlineQueryResultArticle(
            id="text", title="📢 Поделиться", description=share_text,
            input_message_content=InputTextMessageContent(share_text, disable_web_page_preview=False),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🐱 Узнать своего кота!", url=f"https://t.me/{BOT_USERNAME}")
            ]])
        ))
    logger.info(f"Inline answering with {len(results)} result(s)")
    try:
        await update.inline_query.answer(results, cache_time=0, is_personal=True)
    except Exception as e:
        logger.error(f"Inline answer error: {e}", exc_info=True)

async def async_main():
    logger.info("🌿 Дух Леса пробуждается...")
    init_db()
    PORT = int(os.environ.get("PORT", 10000))
    BASE = os.environ.get("RENDER_EXTERNAL_URL", "https://cat-oracle-3jeq.onrender.com")
    SECRET = os.environ.get("WEBHOOK_SECRET", "forest-whisper")
    app = Application.builder().token(BOT_TOKEN).updater(None).request(HTTPXRequest(read_timeout=120, write_timeout=120, connect_timeout=30, pool_timeout=10)).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("help",help_cmd))
    app.add_handler(CommandHandler("stats",stats))
    app.add_handler(CommandHandler("about",about))
    app.add_handler(CommandHandler("premium",premium))
    app.add_handler(CommandHandler("donate",donate))
    app.add_handler(MessageHandler(filters.VOICE,handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))
    app.add_handler(CallbackQueryHandler(save_card, pattern="^save_card$"))
    app.add_handler(CallbackQueryHandler(buy_callback, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(donate_show_callback, pattern="^donate$"))
    app.add_handler(CallbackQueryHandler(donate_amount_callback, pattern="^donate_\\d+$"))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(InlineQueryHandler(inline_query))
    await app.initialize()
    await app.start()
    webhook_url = f"{BASE}/{SECRET}"
    await app.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
    logger.info(f"🌿 Webhook установлен: {webhook_url}")
    logger.info("🌿 Дух Леса взирает на мир... Запущен!")

    async def webhook_handle(request):
        try:
            data = await request.json()
            keys = list(data.keys())
            uid = data.get("update_id")
            has_inline = "inline_query" in keys
            logger.info(f"Webhook update_id={uid} keys={keys} inline={has_inline}")
            update = Update.de_json(data, app.bot)
            if has_inline:
                asyncio.ensure_future(inline_query(update, None))
            else:
                asyncio.ensure_future(app.process_update(update))
            return web.Response(status=200)
        except Exception as e:
            logger.error(f"Webhook error: {e}", exc_info=True)
            return web.Response(status=200)

    async def health_handle(_request):
        return web.Response(text="Bot is alive")

    web_app = web.Application()
    web_app.router.add_post(f"/{SECRET}", webhook_handle)
    web_app.router.add_get("/", health_handle)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"🌿 HTTP сервер на порту {PORT}")

    try:
        await asyncio.Event().wait()
    finally:
        await app.stop()

def main():
    asyncio.run(async_main())

if __name__=="__main__":
    main()









