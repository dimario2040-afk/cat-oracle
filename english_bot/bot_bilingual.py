import logging, os, sys, io, random, tempfile, urllib.parse, urllib.request, asyncio
import asyncpg
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

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8827616686:AAFwdGgz5dkKEe_VbXvfHHecZk3Se0oOPek")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))
BOT_USERNAME = "catwood_bot"

# ── cats: Russian ──────────────────────────────────────────────────

CATS_RU = [
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
    (71,"Орешек","Кот-Орешек","Снаружи твёрдая скорлупа, внутри — свет и сила.","земля","🥜",0.4,0.8,60,250),
]

# ── cats: English ──────────────────────────────────────────────────

CATS_EN = [
    (1,"Spirit of Light","The Screaming Beacon","Your voice rips through the void like a dying fluorescent tube in an abandoned ward.","light","✨",0,0.3,0,400),
    (2,"Shadow Keeper","The Creeping Dread","You slither through the dark and whisper things that should've stayed buried.","darkness","🌑",0.3,1.0,50,200),
    (3,"Storm Caller","The Thunder Gobbler","Your roar cracks the sky open! Even the dead flinch.","storm","⚡",0.5,1.0,50,150),
    (4,"Moon Whisperer","The Lunar Leak","Your soft voice is the moon's dirty secret, pulling stars in to listen.","moon","🌙",0,0.15,200,800),
    (5,"Ash Walker","The Dusty Echo","Your crackling voice bounces between dead worlds like a forgotten answering machine.","ash","🌫",0,0.5,150,400),
    (6,"Crystal Ring","The Glass Squeak","Your piercing tone shatters silence into a million twinkling horrors.","crystal","💎",0.05,0.3,400,800),
    (7,"Glowing Coal","The Ember Purr","You purr softly, but inside you there's a volcano with an attitude problem.","fire","🔥",0.05,0.2,80,250),
    (8,"Frozen Wind","The Blizzard Breath","Your voice is an icy draft seeping through forgotten crypts.","ice","❄️",0,0.25,100,300),
    (9,"World Root","The Ancient Trunk","Your voice rumbles like roots digesting secrets deep beneath the earth.","earth","🌳",0.2,0.6,50,150),
    (10,"Spark","The Flicker of Doom","Your voice is a tiny spark that sets the whole forest ablaze.","light","✨",0,0.2,200,600),
    (11,"Twilight","The In-Between Cat","You stand where day goes to die and night hasn't been born yet.","twilight","🌆",0.1,0.4,100,350),
    (12,"Mossy","The Fuzzy Rot","Your voice is like moss soft and ancient and growing over dead things.","earth","🪨",0.2,0.5,50,200),
    (13,"Dewdrop","The Morning Drip","Your voice is disturbingly fresh like a forest dawn after a blood rain.","water","💧",0,0.15,300,700),
    (14,"Volcano","The Magma Cough","Your roar is an eruption from the bowels of the angry earth!","fire","🌋",0.6,1.0,30,120),
    (15,"Zephyr","The Phantom Breeze","You drift like a ghost-cloud that forgot how to disappear.","air","☁️",0,0.2,200,500),
    (16,"Thunderstorm","The Sky Fracture","Your voice booms like the sky is breaking its bones.","storm","🌩",0.5,1.0,40,180),
    (17,"Silence","The Loud Nothing","You say nothing but your meow is deafening in all the wrong ways.","silence","🤫",0,0.1,0,100),
    (18,"Echo","The Repeating Horror","Your voice bounces off the walls of eternity and never really stops.","ether","🔊",0.1,0.5,150,450),
    (19,"Star","The Cosmic Yawn","You purr in rhythm with a dying pulsar light-years away.","cosmos","🌟",0,0.2,400,800),
    (20,"Fern","The Wild Thing","You are chaos wrapped in fur and moss.","nature","🌿",0.1,0.4,100,300),
    (21,"Stream","The Gurgling Ghoul","Your voice babbles like a mountain stream carrying whispers of the drowned.","water","🏔",0,0.2,250,600),
    (22,"Fog","The Vague Cat","Nobody knows what you are including yourself.","fog","🌁",0,0.3,50,250),
    (23,"Clay","The Moldable Meow","Your meow is soft and squishy like wet clay that still remembers being a hand.","earth","🏺",0.1,0.3,80,220),
    (24,"Lightning","The Sky Scratch","Your scream splits the sky in two halves that both bleed.","storm","⚡",0.4,1.0,200,600),
    (25,"Darkness","The Void Leak","From the depths of your throat crawls an ancient sticky darkness.","darkness","🖤",0.3,0.8,30,120),
    (26,"Gold","The Gilded Beast","Your voice shimmers like sunlight through stolen treasure.","light","🌟",0.1,0.4,300,700),
    (27,"Silver","The Moon Drool","Your voice is moonlight drowning in a frozen lake.","moon","🌙",0,0.2,250,650),
    (28,"Iron","The Rusted Clank","Your voice is hard as forged metal that hasn't aged well.","earth","⚙️",0.4,0.7,60,200),
    (29,"Hurricane","The Spinning Rage","There's a whole cyclone trapped in your throat and it wants out.","storm","🌀",0.5,1.0,100,350),
    (30,"Calm","The Dead Stillness","Your voice is an unsettling quiet the kind before something bad happens.","water","🕊",0,0.1,80,200),
    (31,"Flame","The Unholy Purr","You speak and the air around you starts sweating.","fire","🔥",0.3,0.7,100,300),
    (32,"Frost","The Frozen Yowl","Your voice freezes ponds and makes ghosts shiver.","ice","🧊",0,0.2,50,180),
    (33,"Wind","The Invisible Scream","Your voice is a wild thing that's never been tamed.","air","🌬",0.1,0.4,200,500),
    (34,"Boulder","The Unmovable Beast","Your voice has seen things and refuses to elaborate.","earth","⛰",0.3,0.6,40,150),
    (35,"Rainbow","The Vomit of Light","Your voice shifts through every color like a chemical spill.","light","🌈",0.1,0.5,300,750),
    (36,"Night","The Dark Purr","Your voice is the night itself full of secrets and things that bite.","darkness","🌌",0,0.3,60,250),
    (37,"Dawn","The Unwanted Sunrise","Your voice is that first sunbeam you really didn't ask for.","light","🌅",0,0.3,250,600),
    (38,"Thunder","The Sky Fart","Your voice literally shakes the earth. No dignity. Just boom.","storm","💥",0.7,1.0,30,120),
    (39,"Silk","The Smooth Menace","Your voice is unfairly smooth like a predator wearing a fancy suit.","air","🎀",0,0.15,200,500),
    (40,"Flint","The Sparky Jerk","Your voice strikes sparks out of empty silence.","fire","💎",0.3,0.6,100,280),
    (41,"Pollen","The Glowing Sneeze","Your voice swirls like glowing pollen that makes you see things.","nature","🌼",0,0.2,350,750),
    (42,"Abyss","The Bottomless Meow","Your voice comes from somewhere so deep even light gets lost.","water","🌊",0.2,0.5,30,120),
    (43,"Height","The Sky Climber","Your voice floats above the clouds judging everyone below.","air","🦅",0.1,0.4,300,700),
    (44,"Root","The Underground Grumble","Your voice burrows deep into the dirt and finds old bones.","earth","🌱",0.1,0.3,50,180),
    (45,"Sap","The Sticky Voice","Your voice is thick and alive like tree blood that dreams.","nature","🍃",0.1,0.3,200,450),
    (46,"Claw","The Scratchy Truth","Your voice has the unmistakable sound of unsheathed violence.","darkness","🗡️",0.4,0.8,100,300),
    (47,"Purr","The Brain Rattle","Your voice vibrates at a frequency that rearranges thoughts.","ether","🎵",0.1,0.3,50,150),
    (48,"Scream","The Reality Tear","Your voice pierces through reality like a nail through wet cardboard!","storm","📢",0.3,0.7,500,800),
    (49,"Pulse","The Heart Thump","Your voice beats in rhythm with something ancient and hungry.","ether","💓",0.1,0.4,100,350),
    (50,"Mystery","The Question Mark","Your voice hides more than it reveals suspicious.","fog","❓",0,0.3,80,350),
    (51,"Firefly","The Glowing Creep","Your voice flickers in the dark like a swarm of radioactive bugs.","light","🪲",0,0.2,300,700),
    (52,"Tornado","The Sucking Void","Your voice spirals into a vortex that swallows sounds whole!","storm","🌪",0.5,1.0,150,450),
    (53,"Stillness","The Silent Scream","You speak without speaking and somehow it's louder than anything.","silence","🤐",0,0.05,0,50),
    (54,"Bell","The Ringing Curse","Your voice tolls like a funeral bell for the forest's fallen.","ether","🔔",0.2,0.5,400,700),
    (55,"Frostbite","The Icy Touch","Your voice coats everything in a thin layer of frost and regret.","ice","❄️",0,0.2,150,400),
    (56,"Heat","The Melter","Your voice melts rocks and makes demons sweat.","fire","🌋",0.4,0.8,50,200),
    (57,"Breeze","The Gentle Warning","Your voice is a soft wind from the sea right before the tsunami.","air","🌊",0,0.15,200,500),
    (58,"Hail","The Frozen Knuckles","Your voice pelts the world like angry ice from above.","storm","🧊",0.3,0.6,200,500),
    (59,"Vine","The Suffocating Purr","Your voice wraps around things slowly until they can't breathe.","nature","🌿",0.1,0.4,150,350),
    (60,"Jasper","The Ornate Menace","Your voice is a jewel in the forest's crooked crown.","earth","💎",0.1,0.4,100,300),
    (61,"Topaz","The Warm Threat","Your voice is warm and transparent like a predator you can see through.","light","🟡",0.1,0.3,200,500),
    (62,"Lava","The Slow Burn","Your voice flows slowly but leaves nothing behind.","fire","🟠",0.3,0.6,30,120),
    (63,"Spring","The Clean Horror","Your voice is a pure stream in the deep woods probably poisoned.","water","💧",0,0.2,200,500),
    (64,"Reflection","The Mirror Cat","Your voice is a reflection of a reflection and somewhere the original is screaming.","ether","🪞",0.1,0.4,100,350),
    (65,"Zenith","The Blinding Truth","Your voice is the sun at its most aggressive.","light","☀️",0.3,0.6,300,700),
    (66,"Chasm","The Bottomless Drop","Your voice falls into an endless pit and doesn't make a sound when it lands.","darkness","🕳️",0.2,0.5,20,100),
    (67,"Flicker","The Blinking Cat","Your voice appears and disappears in the dark like a faulty bulb.","fog","✨",0,0.3,200,600),
    (68,"Geyser","The Pressurized Scream","Your voice bursts out with an uncontrollable force that scares even birds.","fire","💨",0.5,1.0,100,350),
    (69,"Spectrum","The Full Palette","Your voice is a whole rainbow of wrong sounds!","ether","🌈",0.2,0.6,200,600),
    (70,"Orion","The Starry Guide","Your voice is a constellation that leads lost souls to questionable places.","cosmos","⭐",0.1,0.4,100,400),
    (71,"Nutkin","The Hard Shell","Hard on the outside even weirder on the inside.","earth","🥜",0.4,0.8,60,250),
]

CATALOGUE_RU = [{"id":c[0],"name":c[1],"title":c[2],"description":c[3],"element":c[4],"emoji":c[5],
                 "acoustic":{"min_rms":c[6],"max_rms":c[7],"min_f0":c[8],"max_f0":c[9]}} for c in CATS_RU]
CATALOGUE_EN = [{"id":c[0],"name":c[1],"title":c[2],"description":c[3],"element":c[4],"emoji":c[5],
                 "acoustic":{"min_rms":c[6],"max_rms":c[7],"min_f0":c[8],"max_f0":c[9]}} for c in CATS_EN]

LEGENDARY_IDS = {5, 9, 24, 29, 38, 52, 66, 70, 11, 48}
LEGENDARY_RU = [c for c in CATALOGUE_RU if c['id'] in LEGENDARY_IDS]
LEGENDARY_EN = [c for c in CATALOGUE_EN if c['id'] in LEGENDARY_IDS]

_share_data = {}
_last_analysis = {}
_pending_action = {}

# ── i18n strings ───────────────────────────────────────────────────

_T = {
    # gen_card
    "element_lbl": {"ru": "🌀 СТИХИЯ: {{element}}", "en": "🌀 ELEMENT: {{element}}"},
    "forest_chose": {"ru": "🐾 Дух Леса указал на тебя 🐾", "en": "🐾 The Forest Spirit chose you 🐾"},
    "totem_num": {"ru": "✦ Тотем #{} ✦", "en": "✦ Totem #{} ✦"},
    "legendary_badge": {"ru": "👑 ЛЕГЕНДАРНЫЙ ТОТЕМ 👑", "en": "👑 LEGENDARY TOTEM 👑"},
    "t.me": {"ru": "", "en": ""},  # no translation needed, but placeholder

    # video
    "video_fail": {"ru": "😿 *Дух Леса не смог создать видео...*\nНо тотем уже твой!",
                   "en": "😿 *The Forest Spirit failed to weave the video...*\nBut the totem is yours anyway!"},
    "video_caption_text": {"ru": "🐱 Я записал голос и Дух Леса показал, что я — «{{name}}»!\nА кто ты?\n{{ref}}",
                           "en": "🐱 I recorded my voice and the Forest Spirit said I'm {{name}}!\nWho are YOU?\n{{ref}}"},

    # handle_voice progress
    "listening": {"ru": "🌌 *Дух Леса слышит твой зов...* 🌌",
                  "en": "🌌 *The Forest Spirit hears your call...* 🌌"},
    "echo_progress": {"ru": "🔊 Твой голос плещется в кронах...", "en": "🔊 Your voice echoes through the trees..."},
    "weaving": {"ru": "🔮 Древняя магия ищет твоего кота...", "en": "🔮 Ancient magic is weaving your totem..."},
    "voice_heard": {"ru": "✨ *Готово!*", "en": "✨ *Done!*"},
    "preparing_video": {"ru": "🎥 *Готовлю видео...*", "en": "🎥 *Preparing video...*"},
    "error_retry": {"ru": "🌫 *Туман сгущается...* Попробуй ещё раз! 🐱\n\n_Подсказка: запиши голос подлиннее (3-5 секунд)_",
                    "en": "🌫 *The fog thickens...* Try again! 🐱\n\n_Hint: record a longer voice (3-5 seconds)_"},
    "error_short": {"ru": "🌫 *Туман...* Попробуй ещё раз! 🐱", "en": "🌫 *Fog...* Try again! 🐱"},

    # limits
    "limit_reached": {"ru": "🌫 *Лимит исчерпан* 🌫\n\nТы сегодня уже получил 3 тотема. Дух Леса устал.\n\n✨ Открой безлимитный доступ всего за *1 Star*!",
                      "en": "🌫 *Daily limit reached* 🌫\n\nYou've already received 3 totems today. The Forest Spirit is exhausted.\n\n✨ Unlock unlimited access for just *1 Star*!"},
    "btn_unlimited": {"ru": "⭐ Безлимит (1 Star)", "en": "⭐ Unlimited (1 Star)"},

    # start
    "ref_notify": {"ru": "🎉 *{{name}}* перешёл по твоей ссылке!\nТы получил +1 гадание 🐱",
                   "en": "🎉 *{{name}}* clicked your link!\nYou earned +1 reading 🐱"},
    "welcome_ref": {"ru": "🌿 *{{name}}, {{referrer}} позвал тебя в Зачарованный Лес...* 🌿\n\n70+ кошачьих духов ждут твой голос. Твой первый звук родит тотем.\n\n🎤 *Нажми на микрофон и мяукни.*\nДухи уже слушают...\n\n🐾 *Готов?* Тогда мяу, странник...\n\n💬 /lang — переключить язык",
                     "en": "🌿 *{{name}}, {{referrer}} has summoned you to the Enchanted Woods...* 🌿\n\n70+ cat spirits await your voice. Your first sound will birth a totem.\n\n🎤 *Hit the mic and meow.*\nThe spirits are listening...\n\n🐾 *Ready?* Then meow stranger...\n\n💬 /lang — switch language"},
    "welcome_new": {"ru": "🌿 *{{name}}, ты стоишь на пороге Зачарованного Леса...* 🌿\n\n70+ кошачьих духов ждут твой голос. Твой первый звук родит тотем.\n\n🎤 *Нажми на микрофон и мяукни.*\nДухи уже слушают...\n\n🐾 *Готов?* Тогда мяу, странник...\n\n💬 /lang — переключить язык",
                    "en": "🌿 *{{name}}, you stand at the edge of the Enchanted Woods...* 🌿\n\n70+ cat spirits await your voice. Your first sound will birth a totem.\n\n🎤 *Hit the mic and meow.*\nThe spirits are listening...\n\n🐾 *Ready?* Then meow stranger...\n\n💬 /lang — switch language"},

    # totem reveal caption (photo message after voice analysis)
    "totem_reveal": {"ru": "🌟 *{{title}}* 🌟\n\n{{emoji}} {{name}}\n{{desc}}\n\n🌀 Стихия: {{element}}\n\n👥 *Приведи друга — узнай, кто он:*\n{{ref}}",
                     "en": "🌟 *{{title}}* 🌟\n\n{{emoji}} {{name}}\n{{desc}}\n\n🌀 Element: {{element}}\n\n👥 *Bring a friend — find their totem:*\n{{ref}}"},
    "totem_reveal_prefix": {"ru": "👑 ", "en": "👑 "},

    # share inline
    "inline_share_text": {"ru": "🐱 Я — {{name}}! А кто ты? Кидай войс 👇 {{ref}}",
                          "en": "🐱 I'm {{name}}! Who are YOU? Send a voice 👇 {{ref}}"},
    "inline_share_generic": {"ru": "🐱 Запиши голосовое боту @{{username}} и узнай свой тотем!",
                             "en": "🐱 Send a voice message to @{{username}} and discover your totem!"},
    "inline_btn_cat": {"ru": "🐱 Узнать своего кота!", "en": "🐱 Find YOUR cat!"},
    "inline_voice_title": {"ru": "🎤 {{emoji}} {{name}}", "en": "🎤 {{emoji}} {{name}}"},
    "inline_voice_caption": {"ru": "🎧 Слушай мой тотем! Я — {{emoji}} {{name}}\n\nУзнай своего: t.me/{{username}}",
                             "en": "🎧 Hear my totem! I'm {{emoji}} {{name}}\n\nFind yours: t.me/{{username}}"},
    "inline_share_btn": {"ru": "📢 Поделиться", "en": "📢 Share"},

    # buttons
    "btn_save": {"ru": "📤 Сохранить в Избранное", "en": "📤 Save to Favorites"},
    "btn_share_friends": {"ru": "📢 Поделиться с друзьями", "en": "📢 Share with friends"},

    # save_card
    "card_lost": {"ru": "🌫 Карточка утеряна в тумане... Отправь голосовое заново!",
                  "en": "🌫 Card lost in the fog... Send a new voice message!"},
    "card_saved": {"ru": "✅ Сохранено в Избранном!", "en": "✅ Saved to Favorites!"},
    "card_save_fail": {"ru": "❌ Не удалось сохранить. Попробуй ещё раз.", "en": "❌ Could not save. Try again."},

    # stats
    "stats_deny": {"ru": "❌ Только Хранитель Леса может видеть это.", "en": "❌ Only the Forest Keeper can see this."},
    "stats_header": {"ru": "🌿 *Святилище Кошачьего Духа* 🌿\n\n👣 Заходов: *{{st}}*\n🐱 Тотемов раскрыто: *{{t}}*\n🙏 Странников: *{{us}}*\n📊 За сутки: *{{rd}}* | За неделю: *{{rw}}*\n⭐ Stars заработано: *{{stars}}*\n🔗 Рефералов: *{{refs}}*",
                     "en": "🌿 *Sanctuary of the Cat Spirit* 🌿\n\n👣 Visits: *{{st}}*\n🐱 Totems revealed: *{{t}}*\n🙏 Wanderers: *{{us}}*\n📊 Today: *{{rd}}* | This week: *{{rw}}*\n⭐ Stars earned: *{{stars}}*\n🔗 Referrals: *{{refs}}*"},
    "stats_top": {"ru": "\n\n*Топ-5 тотемов:*\n", "en": "\n\n*Top 5 totems:*\n"},
    "stats_line": {"ru": "  • {{n}}: {{cnt}}", "en": "  • {{n}}: {{cnt}}"},
    "stats_footer": {"ru": "\n\n_Дух Леса доволен._", "en": "\n\n_The Forest Spirit is pleased._"},

    # about
    "about_text": {"ru": "🌲 *О Святилище Котов-Тотемов* 🌲\n\nИдея родилась из разговора двух путников:\n🎭 *Дмитрий* — хотел железную коробку с ИИ для кошек\n🧙 *Тимофей* — заметил тренд с птичьими голосовухами\n\nИ родилась *Кото-печенька* —\nбот, который слушает твой голос и находит\nтвоего древнего кошачьего духа-тотема.\n\n71 кот. 71 судьба. 71 тотем.\n\n🎨 *Стикерпак:* [CatWood](https://t.me/addstickers/CatWood)\n\n🐾 *Запиши свой голос — узнай кто ты* 🐾",
                   "en": "🌲 *About the Totem Cat Sanctuary* 🌲\n\nThe idea was born from a conversation between two wanderers:\n🎭 *Dmitry* — wanted a magical box with AI for cats\n🧙 *Timofey* — noticed the trend of bird voice messages\n\nAnd so the *Cat Fortune Cookie* was born —\na bot that listens to your voice and finds\nyour ancient cat spirit totem.\n\n71 cats. 71 fates. 71 totems.\n\n🎨 *Sticker pack:* [CatWood](https://t.me/addstickers/CatWood)\n\n🐾 *Record your voice — find out who you really are* 🐾"},

    # help
    "help_text": {"ru": "🐱 *Кото-печенька — Как это работает* 🐱\n\n1️⃣ Отправь голосовое сообщение\n2️⃣ Мяукай, мурлычь, шипи, вой, ори\n3️⃣ Получи своего кота-тотема!\n4️⃣ Поделись с друзьями\n\n✨ *Каждый голос уникален — каждый тотем священен* ✨\n\nКоманды: /start /help /stats /about /premium\n💬 /lang — переключить язык на русский/english",
                  "en": "🐱 *Cat Fortune Cookie — How it works* 🐱\n\n1️⃣ Send a voice message\n2️⃣ Meow purr hiss howl scream\n3️⃣ Get your cat totem!\n4️⃣ Share with friends\n\n✨ *Every voice is unique — every totem is sacred* ✨\n\nCommands: /start /help /stats /about /premium\n💬 /lang — switch between русский/english"},

    # premium
    "premium_unlimited": {"ru": "🌟 *У тебя уже есть Безлимитный доступ!* 🌟\n\nСпасибо за поддержку Зачарованного Леса!\n\n👥 *Приведи друга:* ниже твоя ссылка\n{{ref}}\n\n📦 Накоплено бонусных гаданий: *{{bonus}}*\nПриведи друга → получи +1 гадание!\n\n👑 Хочешь Легендарного кота? /premium\n🔄 Или переброс тотема через /premium",
                          "en": "🌟 *You already have Unlimited Access!* 🌟\n\nThanks for supporting the Enchanted Woods!\n\n👥 *Bring a friend:* your referral link below\n{{ref}}\n\n📦 Bonus readings stored: *{{bonus}}*\nBring a friend → get +1 reading!\n\n👑 Want a Legendary cat? /premium\n🔄 Or re-roll your totem via /premium"},
    "premium_regular": {"ru": "🌟 *Зачарованный Лес — Премиум* 🌟\n\n🐱 Бесплатных гаданий сегодня: *{{remaining}}*\n📦 Бонусных (за рефералов): *{{bonus}}*\n\n👥 *Приведи друга — получи +1 гадание:*\n{{ref}}\n\n🎭 Открой все тайны Леса с Telegram Stars!\n\n⭐ *1 Star* — Безлимит на 30 дней ✨\n   Сними дневной лимит!\n\n⭐ *2 Stars* — Переброс тотема 🔄\n   Получи нового кота из своего голоса\n\n⭐ *3 Stars* — Легендарный кот 👑\n   Эксклюзивный тотем из высшей касты!\n\n🌲 *Дух Леса благодарит тебя за поддержку!*",
                        "en": "🌟 *Enchanted Woods — Premium* 🌟\n\n🐱 Free readings today: *{{remaining}}*\n📦 Bonus (referrals): *{{bonus}}*\n\n👥 *Bring a friend — get +1 reading:*\n{{ref}}\n\n🎭 Unlock all the Woods secrets with Telegram Stars!\n\n⭐ *1 Star* — Unlimited for 30 days ✨\n   Remove the daily limit!\n\n⭐ *2 Stars* — Re-roll totem 🔄\n   Get a new cat from your voice\n\n⭐ *3 Stars* — Legendary cat 👑\n   Exclusive totem from the highest caste!\n\n🌲 *The Forest Spirit thanks you for your support!*"},
    "btn_buy_unlimited": {"ru": "⭐ Безлимит (1 Star)", "en": "⭐ Unlimited (1 Star)"},
    "btn_buy_reroll": {"ru": "🔄 Переброс (2 Stars)", "en": "🔄 Re-roll (2 Stars)"},
    "btn_buy_legendary": {"ru": "👑 Легендарный (3 Stars)", "en": "👑 Legendary (3 Stars)"},
    "btn_donate": {"ru": "💝 Поддержать донатом", "en": "💝 Support with a donation"},

    # buy
    "buy_unknown": {"ru": "❌ Неизвестный товар", "en": "❌ Unknown item"},
    "buy_need_totem": {"ru": "❌ Сначала получи тотем! Отправь голосовое сообщение.", "en": "❌ Get a totem first! Send a voice message."},
    "buy_invoice_desc": {"ru": "Поддержка Зачарованного Леса ({{stars}} ⭐)", "en": "Support the Enchanted Woods ({{stars}} ⭐)"},
    "buy_unlimited_title": {"ru": "⭐ Безлимит на 30 дней", "en": "⭐ Unlimited for 30 days"},
    "buy_reroll_title": {"ru": "🔄 Переброс тотема", "en": "🔄 Re-roll totem"},
    "buy_legendary_title": {"ru": "👑 Легендарный кот", "en": "👑 Legendary cat"},

    # payment success
    "pay_unlimited": {"ru": "🌟 *Безлимитный доступ активирован на 30 дней!* 🌟\n\nДух Леса благодарит тебя! Теперь никаких ограничений.\n\nОтправляй голосовые сколько хочешь! 🐾",
                      "en": "🌟 *Unlimited access activated for 30 days!* 🌟\n\nThe Forest Spirit thanks you! No more limits.\n\nSend as many voice messages as you want! 🐾"},
    "pay_reroll_caption": {"ru": "🔄 *Переброс!* 🔄\n\n{{emoji}} {{title}}\n{{desc}}\n\n🌀 Стихия: {{element}}",
                           "en": "🔄 *Re-roll!* 🔄\n\n{{emoji}} {{title}}\n{{desc}}\n\n🌀 Element: {{element}}"},
    "pay_reroll_done": {"ru": "🐾 *Твой новый тотем!* Поделись с друзьями!", "en": "🐾 *Your new totem!* Share with friends!"},
    "pay_reroll_fail": {"ru": "❌ Нет данных о голосе. Отправь голосовое и повтори попытку.", "en": "❌ No voice data found. Send a voice message and try again."},
    "pay_legendary": {"ru": "👑 *Легендарный кот активирован!* 👑\n\n🎤 Отправь голосовое сообщение, и Дух Леса\nвыберет тебе *Легендарного кота* из высшей касты!\n\n🐱 *Мяу-у-у...*",
                      "en": "👑 *Legendary cat activated!* 👑\n\n🎤 Send a voice message and the Forest Spirit\nwill grant you a *Legendary cat* from the highest caste!\n\n🐱 *Mee-ow...*"},
    "pay_donate": {"ru": "💝 *Огромное спасибо за поддержку ({{stars}} ⭐)!* 💝\n\nДух Леса чувствует твою доброту.\nБлагодаря таким путникам, как ты, Лес становится больше!\n\n🐾 *Мяу-у-у...* 🐾",
                   "en": "💝 *Thank you so much for your support ({{stars}} ⭐)!* 💝\n\nThe Forest Spirit feels your kindness.\nThanks to wanderers like you the Woods grow larger!\n\n🐾 *Mee-ow...* 🐾"},

    # donate
    "donate_text": {"ru": "💝 *Поддержать Зачарованный Лес* 💝\n\nЕсли тебе нравится бот и ты хочешь помочь Лесу расти —\nвыбери сумму доната:\n\n⭐ *1 Star* — тёплое спасибо от Духа Леса\n⭐ *3 Stars* — благословение древних котов\n⭐ *5 Stars* — ты становишься Хранителем Леса 🌲",
                    "en": "💝 *Support the Enchanted Woods* 💝\n\nIf you like the bot and want to help the Woods grow —\nchoose a donation amount:\n\n⭐ *1 Star* — a warm thanks from the Forest Spirit\n⭐ *3 Stars* — blessing of the ancient cats\n⭐ *5 Stars* — you become a Forest Keeper 🌲"},
    "donate_short": {"ru": "💝 *Поддержать Зачарованный Лес* 💝\n\nВыбери сумму доната:\n\n⭐ *1 Star* — тёплое спасибо\n⭐ *3 Stars* — благословение древних котов\n⭐ *5 Stars* — ты Хранитель Леса 🌲",
                     "en": "💝 *Support the Enchanted Woods* 💝\n\nChoose a donation amount:\n\n⭐ *1 Star* — a warm thanks\n⭐ *3 Stars* — blessing of ancient cats\n⭐ *5 Stars* — you are a Forest Keeper 🌲"},
    "donate_invoice_title": {"ru": "💝 Донат Зачарованному Лесу", "en": "💝 Donation to the Enchanted Woods"},
    "donate_invoice_desc": {"ru": "Благодарим за поддержку! ({{stars}} ⭐)", "en": "Thank you for supporting! ({{stars}} ⭐)"},
    "btn_donate_amt": {"ru": "💝 {{stars}} Star", "en": "💝 {{stars}} Star"},
    "donate_label": {"ru": "Донат {{stars}} ⭐", "en": "Donation {{stars}} ⭐"},

    # give_oreshek (admin)
    "oreshek_deny": {"ru": "❌ Только Хранитель Леса.", "en": "❌ Only the Forest Keeper."},
    "oreshek_caption": {"ru": "🌟 *{{title}}* 🌟\n\n{{emoji}} {{name}}\n{{desc}}\n\n🌀 Стихия: {{element}}\n\n👥 *Приведи друга — узнай, кто он:*\n{{ref}}",
                         "en": "🌟 *{{title}}* 🌟\n\n{{emoji}} {{name}}\n{{desc}}\n\n🌀 Element: {{element}}\n\n👥 *Bring a friend — find their totem:*\n{{ref}}"},
    "oreshek_fallback": {"ru": "😿 *Лесные духи не смогли проявить образ...*", "en": "😿 *The Forest spirits couldn't manifest the image...*"},


    # language
    "lang_set": {"ru": "🌐 Язык переключён на русский!", "en": "🌐 Language switched to English!"},
    "lang_prompt": {"ru": "🌍 *Выбери язык* / *Choose language*",
                    "en": "🌍 *Choose language* / *Выбери язык*"},
    "btn_lang_ru": {"ru": "🇷🇺 Русский", "en": "🇷🇺 Русский"},
    "btn_lang_en": {"ru": "🇬🇧 English", "en": "🇬🇧 English"},
    "lang_welcome_ru": {"ru": "🌿 *Отлично, {{name}}!* Продолжим на русском 🐱\n\n70+ кошачьих духов ждут твой голос. Твой первый звук родит тотем.\n\n🎤 *Нажми на микрофон и мяукни.*\n\n💬 /lang — переключить язык в любой момент",
                         "en": "🌿 *Great, {{name}}!* Let's continue in Russian 🐱\n\n70+ cat spirits await your voice. Your first sound will birth a totem.\n\n🎤 *Tap the mic and meow.*\n\n💬 /lang — switch language anytime"},
    "lang_welcome_en": {"ru": "🌿 *Great, {{name}}!* Let's continue in English 🐱\n\n70+ cat spirits await your voice. Your first sound will birth a totem.\n\n🎤 *Tap the mic and meow.*\n\n💬 /lang — switch language anytime",
                         "en": "🌿 *Great, {{name}}!* Let's continue in English 🐱\n\n70+ cat spirits await your voice. Your first sound will birth a totem.\n\n🎤 *Tap the mic and meow.*\n\n💬 /lang — switch language anytime"},
}


def _text(key, lang, **fmt):
    """Return localized string, formatting {{placeholders}} with fmt."""
    d = _T.get(key)
    if not d:
        return key
    s = d.get(lang) or d.get("ru", key)
    if fmt:
        for k, v in fmt.items():
            s = s.replace("{{" + k + "}}", str(v))
    return s


def _guess_lang(update):
    """Guess user language from Telegram language_code. Returns 'ru' or 'en'."""
    user = update.effective_user
    if user and user.language_code:
        lc = user.language_code.split("-")[0].strip().lower()
        if lc in ("ru", "be", "uk", "kk"):
            return "ru"
    return "en"

async def _get_user_lang(update):
    """Get stored language from DB, or guess from Telegram language_code."""
    uid = update.effective_user.id
    stored = await _get_lang(uid)
    if stored:
        return stored
    return _guess_lang(update)


# ── classify ───────────────────────────────────────────────────────

def classify_cat(rms, f0, exclude_ids=None, pool=None):
    candidates = pool or CATALOGUE_RU
    if exclude_ids:
        candidates = [c for c in candidates if c['id'] not in exclude_ids]
    if not candidates:
        candidates = CATALOGUE_RU
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

# ── visual ─────────────────────────────────────────────────────────

BG = [(20,15,40),(25,15,30),(40,25,10),(10,30,25),(35,10,20),(15,15,15)]
EC_RU = {"свет":(255,255,200),"тьма":(150,130,200),"огонь":(255,180,80),"вода":(100,200,255),
         "земля":(180,160,100),"воздух":(200,230,255),"буря":(200,180,255),"луна":(200,220,255),
         "лёд":(200,240,255),"туман":(180,180,200),"эфир":(220,200,255),"природа":(180,230,150),
         "космос":(150,150,255),"тишина":(200,200,210),"пепел":(180,170,160),"сумерки":(160,140,180),
         "кристалл":(200,220,255)}
EC_EN = {"light":(255,255,200),"darkness":(150,130,200),"fire":(255,180,80),"water":(100,200,255),
         "earth":(180,160,100),"air":(200,230,255),"storm":(200,180,255),"moon":(200,220,255),
         "ice":(200,240,255),"fog":(180,180,200),"ether":(220,200,255),"nature":(180,230,150),
         "cosmos":(150,150,255),"silence":(200,200,210),"ash":(180,170,160),"twilight":(160,140,180),
         "crystal":(200,220,255)}
SYMS = ["◇","○","△","☯","⟡","✧","∞","⚘","☽","𓋹","⟐","✳"]

def _card_cataas(cat, ec, legendary=False):
    """EN card: CATAAS cat photo + clean layout (no emoji)."""
    W, H = 600, 700
    bg = random.choice(BG)
    img = Image.new("RGBA", (W, H), bg)
    d = ImageDraw.Draw(img)
    try:
        fp = "font.ttf" if os.path.exists("font.ttf") else os.path.join(os.path.dirname(__file__), "font.ttf")
        ft = ImageFont.truetype(fp, 42); fn = ImageFont.truetype(fp, 30); fs = ImageFont.truetype(fp, 18)
    except:
        ft = fn = fs = ImageFont.load_default()
    # Glow around center
    for _ in range(12):
        cx, cy = random.randint(80, 520), random.randint(160, 360)
        r = random.randint(50, 100)
        fill = random.choice([(150, 130, 80, 12), (180, 160, 100, 15), (120, 140, 180, 10)])
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    # Border
    d.rectangle([25, 25, W - 25, H - 25], outline=ec + (80,), width=2)
    # Name (no emoji)
    t = cat['name']; bb = d.textbbox((0, 0), t, font=ft)
    d.text(((W - (bb[2] - bb[0])) // 2, 50), t, font=ft, fill=ec + (230,))
    # Title
    t = cat['title']; bb = d.textbbox((0, 0), t, font=fn); tw = bb[2] - bb[0]
    d.rectangle([(W - tw) // 2 - 15, 118, (W + tw) // 2 + 15, 160],
                fill=bg + (180,), outline=ec + (80,), width=1)
    d.text(((W - tw) // 2, 125), t, font=fn, fill=(255, 255, 255, 230))
    # Separator
    d.line([160, 183, W - 160, 183], fill=ec + (80,), width=1)
    # CATAAS cat photo
    try:
        req = urllib.request.urlopen("https://cataas.com/cat?type=square", timeout=8)
        cat_img = Image.open(req).convert("RGBA").resize((280, 280), Image.LANCZOS)
    except:
        cat_img = Image.new("RGBA", (280, 280), (40, 36, 50, 255))
    img.paste(cat_img, ((W - 280) // 2, 200), cat_img)
    # Bottom separator
    d.line([160, 505, W - 160, 505], fill=ec + (80,), width=1)
    # Element
    t = _text("element_lbl", "en", element=cat['element'].upper())
    bb = d.textbbox((0, 0), t, font=fs)
    d.text(((W - (bb[2] - bb[0])) // 2, 525), t, font=fs, fill=ec + (200,))
    # Diamond (PIL-drawn, safe)
    cx, cy = W // 2, 562; s = 8
    d.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill=ec + (60,), outline=ec + (100,))
    # Legendary badge
    if legendary:
        d.rectangle([20, 20, W - 20, H - 20], outline=(255, 215, 0, 200), width=4)
        t = _text("legendary_badge", "en")
        bb = d.textbbox((0, 0), t, font=fs)
        d.text(((W - (bb[2] - bb[0])) // 2, 480), t, font=fs, fill=(255, 215, 0, 200))
    # Forest Spirit
    t = _text("forest_chose", "en")
    bb = d.textbbox((0, 0), t, font=fs)
    d.text(((W - (bb[2] - bb[0])) // 2, 595), t, font=fs, fill=(255, 255, 255, 150))
    # Username
    t = f"t.me/{BOT_USERNAME}"; bb = d.textbbox((0, 0), t, font=fs)
    d.text(((W - (bb[2] - bb[0])) // 2, 622), t, font=fs, fill=(180, 180, 255, 100))
    # Totem number
    t = f"Totem #{cat['id']}"; bb = d.textbbox((0, 0), t, font=fs)
    d.text(((W - (bb[2] - bb[0])) // 2, 648), t, font=fs, fill=(150, 150, 180, 80))
    buf = io.BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()


def gen_card(cat, lang="ru", legendary=False):
    W, H = 600, 700
    ed = EC_RU if lang == "ru" else EC_EN
    ec = ed.get(cat['element'], (200, 200, 200))

    # ── EN: CATAAS layout (real cat photo) ──
    if lang != "ru":
        return _card_cataas(cat, ec, legendary=legendary)

    # ── RU: original layout (static images with Cyrillic text) ──
    bg = random.choice(BG)
    img = Image.new("RGBA", (W, H), bg)
    d = ImageDraw.Draw(img)
    for _ in range(30):
        x, y, r = random.randint(0, W), random.randint(0, H), random.randint(15, 80)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, random.randint(5, 25)))
    for _ in range(20):
        x, y, r = random.randint(0, W), random.randint(0, H), random.randint(2, 6)
        c = random.choice([(240, 230, 200), (200, 220, 255), (200, 255, 220), (255, 200, 220), (220, 200, 255), (255, 220, 180)])
        d.ellipse([x - r, y - r, x + r, y + r], fill=(c[0], c[1], c[2], random.randint(30, 80)))
    try:
        fp = "font.ttf" if os.path.exists("font.ttf") else os.path.join(os.path.dirname(__file__), "font.ttf")
        ft = ImageFont.truetype(fp, 44); fn = ImageFont.truetype(fp, 32); fd = ImageFont.truetype(fp, 22); fs = ImageFont.truetype(fp, 18)
    except:
        ft = fn = fd = fs = ImageFont.load_default()
    d.rectangle([20, 20, W - 20, H - 20], outline=ec + (80,), width=2)
    t = f"{cat['emoji']}  {cat['name']}  {cat['emoji']}"
    bb = d.textbbox((0, 0), t, font=ft)
    d.text(((W - (bb[2] - bb[0])) // 2, 60), t, font=ft, fill=ec + (230,))
    bb = d.textbbox((0, 0), cat['title'], font=fn); nw = bb[2] - bb[0]
    d.rectangle([(W - nw) // 2 - 15, 122, (W + nw) // 2 + 15, 170], fill=bg + (180,), outline=ec + (120,), width=1)
    d.text(((W - nw) // 2, 130), cat['title'], font=fn, fill=(255, 255, 255, 220))
    d.line([100, 200, 500, 200], fill=ec + (100,), width=1); yd = 240
    for line in cat['description'].split(". "):
        bb = d.textbbox((0, 0), line, font=fd)
        d.text(((W - (bb[2] - bb[0])) // 2, yd), line, font=fd, fill=(200, 220, 220, 200))
        yd += 35
    t = _text("element_lbl", lang, element=cat['element'].upper())
    bb = d.textbbox((0, 0), t, font=fs)
    d.text(((W - (bb[2] - bb[0])) // 2, 350), t, font=fs, fill=ec + (180,))
    s = random.choice(SYMS); bb = d.textbbox((0, 0), s, font=fn)
    d.text(((W - (bb[2] - bb[0])) // 2, 420), s, font=fn, fill=ec + (60,))
    t = _text("forest_chose", lang); bb = d.textbbox((0, 0), t, font=fs)
    d.text(((W - (bb[2] - bb[0])) // 2, 520), t, font=fs, fill=(255, 255, 255, 150))
    t = f"t.me/{BOT_USERNAME}"; bb = d.textbbox((0, 0), t, font=fs)
    d.text(((W - (bb[2] - bb[0])) // 2, 570), t, font=fs, fill=(180, 180, 255, 120))
    if legendary:
        d.rectangle([15, 15, W - 15, H - 15], outline=(255, 215, 0, 200), width=4)
        t = _text("legendary_badge", lang)
        bb = d.textbbox((0, 0), t, font=fs)
        d.text(((W - (bb[2] - bb[0])) // 2, 480), t, font=fs, fill=(255, 215, 0, 200))
    t = _text("totem_num", lang, id=str(cat['id']))
    bb = d.textbbox((0, 0), t, font=fs)
    d.text(((W - (bb[2] - bb[0])) // 2, 630), t, font=fs, fill=(150, 150, 180, 90))
    buf = io.BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()

# ── FFmpeg ─────────────────────────────────────────────────────────

_ffmpeg_semaphore = None

def _get_ffmpeg_path():
    candidates = ["./ffmpeg", "ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]
    for p in candidates:
        if os.path.exists(p):
            return p
    return "ffmpeg"

FFMPEG_PATH = _get_ffmpeg_path()

def _get_ffmpeg_semaphore():
    global _ffmpeg_semaphore
    if _ffmpeg_semaphore is None:
        _ffmpeg_semaphore = asyncio.Semaphore(2)
    return _ffmpeg_semaphore

async def gen_video(image_bytes, voice_ogg_bytes, totem_name, max_duration=15):
    async with _get_ffmpeg_semaphore():
        tmp = tempfile.mkdtemp()
        img_path = os.path.join(tmp, "totem.png")
        voice_path = os.path.join(tmp, "voice.ogg")
        out_path = os.path.join(tmp, "out.mp4")
        try:
            with open(img_path, "wb") as f: f.write(image_bytes)
            with open(voice_path, "wb") as f: f.write(voice_ogg_bytes)
            logger.info(f"gen_video: starting ffmpeg ({FFMPEG_PATH}) for {totem_name}")
            proc = await asyncio.create_subprocess_exec(
                FFMPEG_PATH, "-y",
                "-loop", "1",
                "-i", img_path,
                "-i", voice_path,
                "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2",
                "-c:a", "aac", "-b:a", "96k",
                "-t", str(max_duration),
                "-shortest",
                "-movflags", "+faststart",
                out_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=60)
            if proc.returncode != 0:
                stderr_text = stderr_data.decode("utf-8", errors="replace")[-500:]
                logger.error(f"gen_video: ffmpeg returncode={proc.returncode} stderr={stderr_text}")
                return None
            with open(out_path, "rb") as f:
                data = f.read()
            logger.info(f"gen_video: OK ({len(data)} bytes)")
            return data
        except asyncio.TimeoutError:
            logger.error("gen_video: ffmpeg timed out")
            return None
        except FileNotFoundError:
            logger.error(f"gen_video: ffmpeg NOT FOUND at {FFMPEG_PATH}")
            return None
        except Exception as e:
            logger.error(f"gen_video error: {e}")
            return None
        finally:
            try:
                for f in os.listdir(tmp):
                    os.remove(os.path.join(tmp, f))
                os.rmdir(tmp)
            except:
                pass

async def _send_totem_video(c, chat_id, img_data, voice_data, cat, reply_to, user_id, lang, prog_msg_id=None):
    try:
        mp4 = await gen_video(img_data, voice_data, cat['title'])
        if not mp4:
            logger.warning(f"_send_totem_video: gen_video returned None for user {user_id}")
            if prog_msg_id:
                try:
                    await c.bot.edit_message_text(
                        chat_id=chat_id, message_id=prog_msg_id,
                        text=_text("video_fail", lang),
                        parse_mode="Markdown",
                    )
                except:
                    await c.bot.delete_message(chat_id=chat_id, message_id=prog_msg_id)
            return
        caption = _text("video_caption_text", lang,
                        name=cat['name'],
                        ref=f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}")
        await c.bot.send_video(
            chat_id=chat_id,
            video=io.BytesIO(mp4),
            caption=caption,
            reply_to_message_id=reply_to,
            write_timeout=120, read_timeout=120,
        )
        if prog_msg_id:
            try: await c.bot.delete_message(chat_id=chat_id, message_id=prog_msg_id)
            except: pass
        logger.info(f"_send_totem_video: sent to user {user_id}")
    except Exception as e:
        logger.error(f"_send_totem_video error: {e}")
        if prog_msg_id:
            try:
                await c.bot.edit_message_text(
                    chat_id=chat_id, message_id=prog_msg_id,
                    text=_text("video_fail", lang),
                    parse_mode="Markdown",
                )
            except:
                try: await c.bot.delete_message(chat_id=chat_id, message_id=prog_msg_id)
                except: pass

async def _extract_ogg_from_video_note(mp4_bytes):
    """Extract audio from video note MP4 → returns OGG bytes (mono 16kHz)."""
    tmp = tempfile.gettempdir()
    mp4_path = os.path.join(tmp, "vn.mp4")
    ogg_path = os.path.join(tmp, "vn.ogg")
    with open(mp4_path, "wb") as f:
        f.write(mp4_bytes)
    try:
        proc = await asyncio.create_subprocess_exec(
            FFMPEG_PATH, "-y",
            "-i", mp4_path,
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "libvorbis",
            "-q:a", "3",
            ogg_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            stderr_text = stderr_data.decode("utf-8", errors="replace")[-300:]
            logger.error(f"_extract_ogg_from_video_note: ffmpeg exited {proc.returncode}: {stderr_text}")
            return None
        with open(ogg_path, "rb") as f:
            return f.read()
    except asyncio.TimeoutError:
        logger.error("_extract_ogg_from_video_note: ffmpeg timed out")
        return None
    except FileNotFoundError:
        logger.error(f"_extract_ogg_from_video_note: ffmpeg NOT FOUND at {FFMPEG_PATH}")
        return None
    except Exception as e:
        logger.error(f"_extract_ogg_from_video_note error: {e}")
        return None
    finally:
        for p in [mp4_path, ogg_path]:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except:
                pass

# ── Database ───────────────────────────────────────────────────────

DB_POOL = None

async def get_pool():
    global DB_POOL
    if DB_POOL is None:
        dsn = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/catwood")
        if dsn.startswith("postgres://"):
            dsn = dsn.replace("postgres://", "postgresql://", 1)
        DB_POOL = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=4)
    return DB_POOL

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as c:
        await c.execute("""
            CREATE TABLE IF NOT EXISTS readings(
                id SERIAL PRIMARY KEY, user_id BIGINT,
                cat_id INTEGER, cat_name TEXT,
                file_id TEXT, ts TIMESTAMP DEFAULT NOW()
            )
        """)
        await c.execute("""
            CREATE TABLE IF NOT EXISTS stats(
                id SERIAL PRIMARY KEY, total INTEGER DEFAULT 0,
                users INTEGER DEFAULT 0, starts INTEGER DEFAULT 0
            )
        """)
        await c.execute("""
            CREATE TABLE IF NOT EXISTS user_limits(
                user_id BIGINT PRIMARY KEY, daily_date TEXT,
                daily_count INTEGER DEFAULT 0,
                unlimited_until TEXT, bonus_readings INTEGER DEFAULT 0
            )
        """)
        await c.execute("""
            CREATE TABLE IF NOT EXISTS payments(
                id SERIAL PRIMARY KEY, user_id BIGINT,
                payload TEXT, stars INTEGER, ts TIMESTAMP DEFAULT NOW()
            )
        """)
        await c.execute("""
            CREATE TABLE IF NOT EXISTS referrals(
                id SERIAL PRIMARY KEY, referrer_id BIGINT,
                referee_id BIGINT, ts TIMESTAMP DEFAULT NOW()
            )
        """)
        # lang column — add if not exists (safe migration)
        try:
            await c.execute("ALTER TABLE user_limits ADD COLUMN IF NOT EXISTS lang TEXT DEFAULT 'ru'")
        except:
            pass
        await c.execute("INSERT INTO stats(id,total,users,starts) VALUES(1,0,0,0) ON CONFLICT DO NOTHING")

async def _get_lang(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        v = await conn.fetchval("SELECT lang FROM user_limits WHERE user_id=$1", user_id)
        if v:
            return v
    return None

async def _set_lang(user_id, lang):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_limits(user_id, daily_date, daily_count, lang)
            VALUES($1, '', 0, $2)
            ON CONFLICT(user_id) DO UPDATE SET lang=$2
        """, user_id, lang)

async def record_reading(uid, cid, cname, fid):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO readings(user_id,cat_id,cat_name,file_id,ts) VALUES($1,$2,$3,$4,NOW())", uid, cid, cname, fid)
        await conn.execute("UPDATE stats SET total=COALESCE(total,0)+1 WHERE id=1")
        users = await conn.fetchval("SELECT COUNT(DISTINCT user_id) FROM readings")
        await conn.execute("UPDATE stats SET users=$1 WHERE id=1", users)

async def record_start():
    pool = await get_pool()
    async with pool.acquire() as conn:
        r = await conn.execute("UPDATE stats SET starts=COALESCE(starts,0)+1 WHERE id=1")
        if r == "UPDATE 0":
            await conn.execute("INSERT INTO stats(id,total,users,starts) VALUES(1,0,0,1) ON CONFLICT DO NOTHING")

async def _get_limit_info(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT daily_date, daily_count, unlimited_until, COALESCE(bonus_readings,0) as br FROM user_limits WHERE user_id=$1", user_id)
        if row:
            return {"daily_date": row["daily_date"], "daily_count": row["daily_count"], "unlimited_until": row["unlimited_until"], "bonus_readings": row["br"]}
        return None

async def _can_read(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    info = await _get_limit_info(user_id)
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

async def _use_reading(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    pool = await get_pool()
    async with pool.acquire() as conn:
        info = await _get_limit_info(user_id)
        if info:
            if info["daily_date"] == today:
                bonus = info["bonus_readings"] or 0
                if bonus > 0 and info["daily_count"] >= 3:
                    await conn.execute("UPDATE user_limits SET bonus_readings=bonus_readings-1 WHERE user_id=$1", user_id)
                    return
                await conn.execute("UPDATE user_limits SET daily_count=daily_count+1 WHERE user_id=$1", user_id)
            else:
                bonus = info["bonus_readings"] or 0
                if bonus > 0:
                    await conn.execute("UPDATE user_limits SET daily_date=$1, daily_count=0, bonus_readings=bonus_readings-1 WHERE user_id=$2", today, user_id)
                else:
                    await conn.execute("UPDATE user_limits SET daily_date=$1, daily_count=1 WHERE user_id=$2", today, user_id)
        else:
            await conn.execute("INSERT INTO user_limits(user_id, daily_date, daily_count) VALUES($1,$2,1)", user_id, today)

async def _get_daily_remaining(user_id):
    info = await _get_limit_info(user_id)
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

async def _set_unlimited(user_id, days=30):
    until = (datetime.now() + timedelta(days=days)).isoformat()
    today = datetime.now().strftime("%Y-%m-%d")
    pool = await get_pool()
    async with pool.acquire() as conn:
        cur = await conn.fetchval("SELECT daily_count FROM user_limits WHERE user_id=$1", user_id)
        daily_count = cur if cur is not None else 0
        await conn.execute("""
            INSERT INTO user_limits(user_id, daily_date, daily_count, unlimited_until)
            VALUES($1,$2,$3,$4)
            ON CONFLICT(user_id) DO UPDATE SET daily_date=$2, daily_count=$3, unlimited_until=$4
        """, user_id, today, daily_count, until)

async def _record_payment(user_id, payload, stars):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO payments(user_id, payload, stars, ts) VALUES($1,$2,$3,NOW())", user_id, payload, stars)

async def _add_bonus(user_id, amount=1):
    today = datetime.now().strftime("%Y-%m-%d")
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_limits(user_id,daily_date,daily_count,bonus_readings)
            VALUES($1,$2,0,$3)
            ON CONFLICT(user_id) DO UPDATE SET bonus_readings=COALESCE(user_limits.bonus_readings,0)+$3
        """, user_id, today, amount)

# ── Handlers ───────────────────────────────────────────────────────

async def start(u,c):
    user_id = u.effective_user.id
    await record_start()
    args = c.args

    # check if language is already stored in DB
    stored = await _get_lang(user_id)
    if not stored:
        guess = _guess_lang(u)
        picker_lang = guess
        await u.message.reply_text(
            _text("lang_prompt", picker_lang),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(_text("btn_lang_ru", picker_lang), callback_data="lang_sel_ru")],
                [InlineKeyboardButton(_text("btn_lang_en", picker_lang), callback_data="lang_sel_en")],
            ])
        )
        return

    lang = stored
    referred_by = None
    if args and args[0].startswith("ref_"):
        referrer_id = int(args[0][4:])
        referee_id = u.effective_user.id
        if referrer_id != referee_id:
            pool = await get_pool()
            async with pool.acquire() as conn:
                existing = await conn.fetchval("SELECT 1 FROM referrals WHERE referee_id=$1", referee_id)
                if not existing:
                    await _add_bonus(referrer_id, 1)
                    await conn.execute("INSERT INTO referrals(referrer_id, referee_id, ts) VALUES($1,$2,NOW())", referrer_id, referee_id)
                    try:
                        ref_chat = await c.bot.get_chat(referrer_id)
                        referred_by = ref_chat.first_name
                    except:
                        referred_by = "друг" if lang == "ru" else "someone"
                    try:
                        await c.bot.send_message(
                            chat_id=referrer_id,
                            text=_text("ref_notify", lang, name=u.effective_user.first_name),
                            parse_mode="Markdown",
                        )
                    except:
                        pass
    if referred_by:
        await u.message.reply_text(
            _text("welcome_ref", lang, name=u.effective_user.first_name, referrer=referred_by),
            parse_mode="Markdown"
        )
    else:
        await u.message.reply_text(
            _text("welcome_new", lang, name=u.effective_user.first_name),
            parse_mode="Markdown"
        )

async def handle_voice(u,c):
    user_id = u.effective_user.id
    lang = await _get_user_lang(u)
    s=await u.message.reply_text(_text("listening", lang), parse_mode="Markdown")
    try:
        action = _pending_action.pop(user_id, None)
        if action not in ("legendary", "reroll"):
            status = await _can_read(user_id)
            if status == "limit":
                remaining = await _get_daily_remaining(user_id)
                await c.bot.delete_message(chat_id=u.effective_chat.id,message_id=s.message_id)
                await u.message.reply_text(
                    _text("limit_reached", lang),
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_text("btn_unlimited", lang), callback_data="buy_unlimited")]])
                )
                return
            await _use_reading(user_id)
        is_video_note = bool(u.message.video_note)
        if is_video_note:
            vf=await u.message.video_note.get_file();mp4=await vf.download_as_bytearray();ob=await _extract_ogg_from_video_note(mp4)
            if ob is None:
                await c.bot.edit_message_text(_text("error_retry", lang), chat_id=u.effective_chat.id, message_id=s.message_id, parse_mode="Markdown")
                return
        else:
            vf=await u.message.voice.get_file();ob=await vf.download_as_bytearray()
        await c.bot.edit_message_text(_text("echo_progress", lang), chat_id=u.effective_chat.id, message_id=s.message_id)
        rms,f0=analyze_audio_bytes(ob);logger.info(f"User {user_id}: rms={rms:.3f}, f0={f0:.1f}")
        cat_pool = CATALOGUE_RU if lang == "ru" else CATALOGUE_EN
        leg_pool = LEGENDARY_RU if lang == "ru" else LEGENDARY_EN
        if action == "reroll":
            last = _last_analysis.get(user_id)
            if last:
                cat = classify_cat(rms, f0, exclude_ids={last['cat_id']}, pool=cat_pool)
            else:
                cat = classify_cat(rms, f0, pool=cat_pool)
            logger.info(f"  → Reroll totem: {cat['name']}")
        elif action == "legendary":
            cat = classify_cat(rms, f0, pool=leg_pool)
            logger.info(f"  → Legendary totem: {cat['name']}")
        else:
            cat = classify_cat(rms, f0, pool=cat_pool); logger.info(f"  → Totem: {cat['name']}")
        _last_analysis[user_id] = {"rms": rms, "f0": f0, "cat_id": cat['id']}
        legendary = action == "legendary"
        await c.bot.edit_message_text(_text("weaving", lang), chat_id=u.effective_chat.id, message_id=s.message_id)
        img=gen_card(cat, lang=lang, legendary=legendary)
        await c.bot.delete_message(chat_id=u.effective_chat.id, message_id=s.message_id)
        if is_video_note:
            await u.message.reply_video_note(video_note=u.message.video_note.file_id)
        else:
            await u.message.reply_voice(voice=u.message.voice.file_id, caption=_text("voice_heard", lang), parse_mode="Markdown")
        prefix = _text("totem_reveal_prefix", lang) if legendary else ""
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
        caption = _text("totem_reveal", lang,
                        title=cat['title'],
                        emoji=cat['emoji'],
                        name=cat['name'],
                        desc=cat['description'],
                        element=cat['element'],
                        ref=ref_link)
        if prefix:
            caption = prefix + caption
        share_kb=InlineKeyboardMarkup([
            [InlineKeyboardButton(_text("btn_save", lang), callback_data="save_card")],
            [InlineKeyboardButton(_text("btn_share_friends", lang), switch_inline_query=str(user_id))]
        ])
        image_path = None
        # use static image ONLY for Russian (has Cyrillic text baked in)
        if lang == "ru":
            for ext in ("jpg", "jpeg", "png"):
                candidate = Path("image") / (str(cat['id']) + "." + ext)
                if candidate.is_file():
                    image_path = candidate
                    break
        if image_path is not None:
            with open(image_path, "rb") as img_file:
                img_data = img_file.read()
                sent=await u.message.reply_photo(photo=io.BytesIO(img_data), caption=caption, parse_mode=None, reply_markup=share_kb, write_timeout=120, read_timeout=120)
        else:
            img_data = img
            sent=await u.message.reply_photo(photo=io.BytesIO(img_data), caption=caption, parse_mode=None, reply_markup=share_kb, write_timeout=120, read_timeout=120)
        fid = sent.photo[-1].file_id
        try:await record_reading(user_id,cat['id'],cat['name'],fid)
        except:pass
        _share_data[user_id] = {"file_id": fid, "cat": cat, "chat_id": u.effective_chat.id, "message_id": sent.message_id}
        if ob:
            prog_msg = await c.bot.send_message(chat_id=u.effective_chat.id, text=_text("preparing_video", lang), parse_mode="Markdown")
            asyncio.create_task(_send_totem_video(c, u.effective_chat.id, img_data, ob, cat, sent.message_id, user_id, lang, prog_msg.message_id))
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        try: await c.bot.edit_message_text(_text("error_retry", lang), chat_id=u.effective_chat.id, message_id=s.message_id, parse_mode="Markdown")
        except: await u.message.reply_text(_text("error_short", lang), parse_mode="Markdown")

async def stats(u,c):
    if u.effective_user.id != ADMIN_ID:
        return await u.message.reply_text(_text("stats_deny", _guess_lang(u)))
    lang = await _get_user_lang(u)
    pool = await get_pool()
    async with pool.acquire() as conn:
        t=await conn.fetchval("SELECT COUNT(*) FROM readings") or 0
        us=await conn.fetchval("SELECT COUNT(DISTINCT user_id) FROM readings") or 0
        row=await conn.fetchval("SELECT starts FROM stats WHERE id=1")
        st=row if row else 0
        rd=await conn.fetchval("SELECT COUNT(*) FROM readings WHERE ts>=NOW() - INTERVAL '1 day'") or 0
        rw=await conn.fetchval("SELECT COUNT(*) FROM readings WHERE ts>=NOW() - INTERVAL '7 days'") or 0
        try: stars=await conn.fetchval("SELECT COALESCE(SUM(stars),0) FROM payments") or 0
        except: stars=0
        try: refs=await conn.fetchval("SELECT COUNT(*) FROM referrals") or 0
        except: refs=0
        top_rows=await conn.fetch("SELECT cat_name, COUNT(*) as cnt FROM readings GROUP BY cat_name ORDER BY cnt DESC LIMIT 5")
        top=[(r["cat_name"], r["cnt"]) for r in top_rows]
    msg = _text("stats_header", lang, st=str(st), t=str(t), us=str(us), rd=str(rd), rw=str(rw), stars=str(stars), refs=str(refs))
    if top:
        msg += _text("stats_top", lang)
        for n, cnt in top:
            msg += _text("stats_line", lang, n=n, cnt=str(cnt)) + "\n"
    msg += _text("stats_footer", lang)
    await u.message.reply_text(msg, parse_mode="Markdown")

async def about(u,c):
    lang = await _get_user_lang(u)
    await u.message.reply_text(_text("about_text", lang), parse_mode="Markdown")

async def help_cmd(u,c):
    lang = await _get_user_lang(u)
    await u.message.reply_text(_text("help_text", lang), parse_mode="Markdown")

async def lang_cmd(u,c):
    try:
        user_id = u.effective_user.id
        current = await _get_lang(user_id) or _guess_lang(u)
        new_lang = "en" if current == "ru" else "ru"
        await _set_lang(user_id, new_lang)
        await u.message.reply_text(_text("lang_set", new_lang), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"/lang error: {e}")
        try:
            await u.message.reply_text("⚠️ Language switch failed. Try /start", parse_mode="Markdown")
        except:
            pass

async def language_select_callback(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    await query.answer()
    user_id = u.effective_user.id
    chosen = "ru" if query.data == "lang_sel_ru" else "en"
    await _set_lang(user_id, chosen)
    await query.edit_message_text(
        _text("lang_welcome_" + chosen, chosen, name=u.effective_user.first_name),
        parse_mode="Markdown"
    )

async def premium(u,c):
    user_id = u.effective_user.id
    lang = await _get_user_lang(u)
    remaining = await _get_daily_remaining(user_id)
    if remaining == float('inf'):
        info = await _get_limit_info(user_id)
        bonus = info["bonus_readings"] if info else 0
        await u.message.reply_text(
            _text("premium_unlimited", lang,
                  ref=f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}",
                  bonus=str(bonus)),
            parse_mode="Markdown"
        )
        return

    info = await _get_limit_info(user_id)
    bonus = info["bonus_readings"] if info else 0
    text = _text("premium_regular", lang,
                 remaining=str(remaining),
                 bonus=str(bonus),
                 ref=f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(_text("btn_buy_unlimited", lang), callback_data="buy_unlimited")],
        [InlineKeyboardButton(_text("btn_buy_reroll", lang), callback_data="buy_reroll")],
        [InlineKeyboardButton(_text("btn_buy_legendary", lang), callback_data="buy_legendary")],
        [InlineKeyboardButton(_text("btn_donate", lang), callback_data="donate")],
    ])
    await u.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

async def buy_callback(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    await query.answer()
    user_id = u.effective_user.id
    lang = await _get_user_lang(u)
    payload = query.data
    prices_map = {
        "buy_unlimited": (1, "buy_unlimited_title"),
        "buy_reroll": (2, "buy_reroll_title"),
        "buy_legendary": (3, "buy_legendary_title"),
    }
    if payload not in prices_map:
        await query.edit_message_text(_text("buy_unknown", lang))
        return
    if payload == "buy_reroll" and user_id not in _last_analysis:
        await query.edit_message_text(_text("buy_need_totem", lang))
        return
    stars, title_key = prices_map[payload]
    title = _text(title_key, lang)
    await c.bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=_text("buy_invoice_desc", lang, stars=str(stars)),
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
    lang = await _get_user_lang(u)
    payload = u.message.successful_payment.invoice_payload
    stars = u.message.successful_payment.total_amount
    cat_pool = CATALOGUE_EN if lang == "en" else CATALOGUE_RU
    await _record_payment(user_id, payload, stars)
    if payload == "buy_unlimited":
        await _set_unlimited(user_id)
        await u.message.reply_text(_text("pay_unlimited", lang), parse_mode="Markdown")
    elif payload == "buy_reroll":
        last = _last_analysis.get(user_id)
        if last:
            cat = classify_cat(last['rms'], last['f0'], exclude_ids={last['cat_id']}, pool=cat_pool)
            _last_analysis[user_id] = {"rms": last['rms'], "f0": last['f0'], "cat_id": cat['id']}
            img = gen_card(cat, lang=lang)
            caption = _text("pay_reroll_caption", lang,
                            emoji=cat['emoji'], title=cat['title'],
                            desc=cat['description'], element=cat['element'])
            sent = await u.message.reply_photo(photo=io.BytesIO(img), caption=caption, parse_mode="Markdown", write_timeout=120, read_timeout=120)
            fid = sent.photo[-1].file_id
            try: await record_reading(user_id, cat['id'], cat['name'], fid)
            except: pass
            _share_data[user_id] = {"file_id": fid, "voice_file_id": u.message.voice.file_id, "cat": cat, "chat_id": u.effective_chat.id, "message_id": sent.message_id}
            await u.message.reply_text(_text("pay_reroll_done", lang), parse_mode="Markdown")
        else:
            await u.message.reply_text(_text("pay_reroll_fail", lang))
    elif payload == "buy_legendary":
        _pending_action[user_id] = "legendary"
        await u.message.reply_text(_text("pay_legendary", lang), parse_mode="Markdown")
    elif payload == "donate":
        await u.message.reply_text(_text("pay_donate", lang, stars=str(stars)), parse_mode="Markdown")

async def donate(u,c):
    lang = await _get_user_lang(u)
    await u.message.reply_text(
        _text("donate_text", lang),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(_text("btn_donate_amt", lang, stars="1"), callback_data="donate_1")],
            [InlineKeyboardButton(_text("btn_donate_amt", lang, stars="3"), callback_data="donate_3")],
            [InlineKeyboardButton(_text("btn_donate_amt", lang, stars="5"), callback_data="donate_5")],
        ])
    )

async def donate_show_callback(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    await query.answer()
    user_id = u.effective_user.id
    lang = await _get_user_lang(u)
    await query.edit_message_text(
        _text("donate_short", lang),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(_text("btn_donate_amt", lang, stars="1"), callback_data="donate_1")],
            [InlineKeyboardButton(_text("btn_donate_amt", lang, stars="3"), callback_data="donate_3")],
            [InlineKeyboardButton(_text("btn_donate_amt", lang, stars="5"), callback_data="donate_5")],
        ])
    )

async def donate_amount_callback(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    await query.answer()
    user_id = u.effective_user.id
    lang = await _get_user_lang(u)
    stars = int(query.data.split("_")[1])
    await c.bot.send_invoice(
        chat_id=user_id,
        title=_text("donate_invoice_title", lang),
        description=_text("donate_invoice_desc", lang, stars=str(stars)),
        payload="donate",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=_text("donate_label", lang, stars=str(stars)), amount=stars)],
    )

async def save_card(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    user_id = u.effective_user.id
    lang = await _get_user_lang(u)
    data = _share_data.get(user_id)
    if not data or "chat_id" not in data or "message_id" not in data:
        await query.answer()
        await query.edit_message_text(_text("card_lost", lang))
        return
    try:
        await c.bot.copy_message(chat_id=user_id, from_chat_id=data["chat_id"], message_id=data["message_id"])
        await query.answer(_text("card_saved", lang), show_alert=True)
    except Exception as e:
        logger.error(f"Save card error: {e}", exc_info=True)
        await query.answer(_text("card_save_fail", lang), show_alert=True)

async def _get_user_cat(user_id):
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT cat_id,file_id FROM readings WHERE user_id=$1 ORDER BY ts DESC LIMIT 1", user_id)
            if row:
                for c in CATS_RU:
                    if c[0] == row["cat_id"]:
                        return {"id": c[0], "title": c[1], "name": c[2], "description": c[3], "element": c[4], "emoji": c[5], "file_id": row["file_id"]}
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
    db_cat = await _get_user_cat(user_id) if not data else None
    cat = data["cat"] if data else (db_cat if db_cat else None)
    file_id = data.get("file_id") if data else (db_cat.get("file_id") if db_cat else None)
    voice_file_id = data.get("voice_file_id") if data else None
    # derive language from the cat data (RU has Cyrillic name, EN has Latin)
    lang = "en"
    if cat:
        import re
        lang = "ru" if re.search(r'[а-яё]', cat['name'], re.I) else "en"
    if cat:
        share_text = _text("inline_share_text", lang,
                          name=cat['title'],
                          ref=f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}")
    else:
        share_text = _text("inline_share_generic", "en", username=BOT_USERNAME)
    logger.info(f"Inline: data={'yes' if data else 'no'}, db_cat={'yes' if db_cat else 'no'}, cat={'yes' if cat else 'no'}, file_id={'yes' if file_id else 'no'}")
    results = []
    btn = InlineKeyboardMarkup([[
        InlineKeyboardButton(_text("inline_btn_cat", lang), url=f"https://t.me/{BOT_USERNAME}")
    ]])
    if file_id:
        try:
            results.append(InlineQueryResultCachedPhoto(
                id="photo", photo_file_id=file_id, caption=share_text,
                reply_markup=btn
            ))
        except Exception as e:
            logger.error(f"Inline photo error: {e}", exc_info=True)
    if voice_file_id and cat:
        voice_title = _text("inline_voice_title", lang, emoji=cat['emoji'], name=cat['name'])
        voice_caption = _text("inline_voice_caption", lang, emoji=cat['emoji'], name=cat['name'], username=BOT_USERNAME)
        try:
            results.append(InlineQueryResultCachedVoice(
                id="voice", voice_file_id=voice_file_id, title=voice_title, caption=voice_caption,
                reply_markup=btn
            ))
        except Exception as e:
            logger.error(f"Inline voice error: {e}", exc_info=True)
    if not results:
        results.append(InlineQueryResultArticle(
            id="text", title=_text("inline_share_btn", lang), description=share_text,
            input_message_content=InputTextMessageContent(share_text, disable_web_page_preview=False),
            reply_markup=btn
        ))
    logger.info(f"Inline answering with {len(results)} result(s)")
    try:
        await update.inline_query.answer(results, cache_time=0, is_personal=True)
    except Exception as e:
        logger.error(f"Inline answer error: {e}", exc_info=True)

async def give_oreshek(u,c):
    user_id = u.effective_user.id
    lang = await _get_user_lang(u)
    if user_id != ADMIN_ID:
        return await u.message.reply_text(_text("oreshek_deny", lang))
    cat_ru = {"id":71,"name":"Орешек","title":"Кот-Орешек",
              "description":"Снаружи твёрдая скорлупа, внутри — свет и сила.",
              "element":"земля","emoji":"\U0001f95c"}
    cat_en = {"id":71,"name":"Nutkin","title":"The Hard Shell",
              "description":"Hard on the outside even weirder on the inside.",
              "element":"earth","emoji":"\U0001f95c"}
    cat = cat_ru if lang == "ru" else cat_en
    caption = _text("oreshek_caption", lang,
                    title=cat['title'], emoji=cat['emoji'],
                    name=cat['name'], desc=cat['description'],
                    element=cat['element'],
                    ref=f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}")
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(_text("btn_save", lang), callback_data="save_card")
    ],[
        InlineKeyboardButton(_text("btn_share_friends", lang), switch_inline_query=str(user_id))
    ]])
    try:
        img_path = None
        for ext in ("jpeg", "jpg", "png"):
            p = Path("image") / f"71.{ext}"
            if p.is_file():
                img_path = p
                break
        if img_path:
            await u.message.reply_photo(photo=img_path.read_bytes(), caption=caption, parse_mode="Markdown", reply_markup=kb)
            return
    except Exception as e:
        logger.warning(f"give_oreshek image load failed: {e}")
    try:
        img = gen_card(cat, lang=lang)
        await u.message.reply_photo(photo=io.BytesIO(img), caption=caption, parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"give_oreshek fallback failed: {e}")
        await u.message.reply_text(_text("oreshek_fallback", lang), parse_mode="Markdown")

# ── Main ───────────────────────────────────────────────────────────

async def async_main():
    logger.info("🌿 The Forest Spirit awakens...")
    await init_db()
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
    app.add_handler(CommandHandler("give_oreshek",give_oreshek))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CommandHandler("language", lang_cmd))
    app.add_handler(MessageHandler(filters.VOICE,handle_voice))
    app.add_handler(MessageHandler(filters.VIDEO_NOTE,handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))
    app.add_handler(CallbackQueryHandler(language_select_callback, pattern="^lang_sel_"))
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
    try:
        await app.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        logger.info(f"🌿 Webhook set: {webhook_url}")
    except Exception as e:
        logger.error(f"🌿 Webhook FAILED (bot will still serve health-check): {e}")
    logger.info("🌿 The Forest Spirit watches over the world... Running!")

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
        return web.Response(text="Bot is alive (bilingual v2)")

    web_app = web.Application()
    web_app.router.add_post(f"/{SECRET}", webhook_handle)
    web_app.router.add_get("/", health_handle)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"🌿 HTTP server on port {PORT}")

    try:
        await asyncio.Event().wait()
    finally:
        await app.stop()
        if DB_POOL:
            await DB_POOL.close()

def main():
    asyncio.run(async_main())

if __name__=="__main__":
    main()
