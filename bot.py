"""
RPG Telegram Bot — Single File Version
تمام کد در یک فایل برای Railway
"""
import os, logging, sqlite3, json, random
from datetime import datetime, timezone, time as dtime
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
GROUP_IDS = [int(x) for x in os.getenv("GROUP_IDS", "").split(",") if x.strip().lstrip("-").isdigit()]
DB_PATH = os.getenv("DB_PATH", "/app/game.db")

# ════════════════════════════════════════════
#  ITEMS
# ════════════════════════════════════════════
WEAPONS = {
    "iron_dagger":        {"name":"🗡️ خنجر آهنی","tier":"common","damage":(15,25),"type":"physical","price":50},
    "wooden_axe":         {"name":"🪓 تبر چوبی","tier":"common","damage":(20,35),"type":"physical","price":75},
    "simple_bow":         {"name":"🏹 کمان ساده","tier":"common","damage":(18,30),"type":"ranged","price":80},
    "steel_sword":        {"name":"⚔️ شمشیر فولادی","tier":"rare","damage":(40,60),"type":"physical","price":200},
    "fire_spear":         {"name":"🔱 نیزه آتشین","tier":"rare","damage":(50,70),"type":"fire","burn_dmg":5,"price":350},
    "silver_bow":         {"name":"🏹 کمان نقره‌ای","tier":"rare","damage":(45,65),"type":"ranged","price":300},
    "dragon_sword":       {"name":"🗡️ شمشیر اژدها","tier":"epic","damage":(80,120),"type":"fire_physical","burn_chance":0.30,"burn_dmg":10,"price":800},
    "thunder_hammer":     {"name":"⚡ چکش صاعقه","tier":"epic","damage":(90,130),"type":"electric","stun_chance":0.20,"price":1000},
    "dark_scythe":        {"name":"🌑 داس تاریکی","tier":"epic","damage":(70,110),"type":"dark","lifesteal":0.15,"price":1200},
    "eternal_light_sword":{"name":"✨ شمشیر نور ابدی","tier":"legendary","damage":(150,200),"type":"holy_physical","curse_break":True,"self_heal":50,"price":5000},
    "phoenix_spear":      {"name":"🔥 نیزه فینیکس","tier":"legendary","damage":(160,220),"type":"holy_fire","revive_once":True,"price":8000},
    "death_star_bow":     {"name":"🌌 کمان ستاره مرگ","tier":"legendary","damage":(200,280),"type":"cosmic","armor_pierce":True,"price":12000,"stock":3},
}
SPELLS = {
    "fireball":       {"name":"🔥 گوی آتش","tier":"common","damage":(20,35),"type":"fire","mana_cost":10,"price":60},
    "ice_arrow":      {"name":"❄️ تیر یخ","tier":"common","damage":(15,25),"type":"ice","mana_cost":8,"slow_turns":1,"price":70},
    "magic_shield":   {"name":"🛡️ سپر جادویی","tier":"rare","type":"defensive","shield_hp":60,"mana_cost":20,"duration":2,"price":250},
    "confusion_mist": {"name":"🌫️ مه فراموشی","tier":"rare","type":"debuff","mana_cost":25,"confuse_turns":1,"price":320},
    "lightning":      {"name":"⚡ رعد و برق","tier":"rare","damage":(60,90),"type":"electric","mana_cost":30,"stun_chance":0.15,"price":400},
    "gods_wrath":     {"name":"💪 خشم خدایان","tier":"epic","type":"buff","damage_boost":0.50,"boost_turns":3,"mana_cost":40,"price":700},
    "magic_tsunami":  {"name":"🌊 سونامی جادویی","tier":"epic","damage":(100,150),"type":"water","mana_cost":50,"armor_pierce_ratio":0.30,"price":900},
    "great_heal":     {"name":"💚 بازیابی عظیم","tier":"epic","type":"heal","heal_amount":120,"mana_cost":45,"price":850},
    "death_star_spell":{"name":"☄️ ستاره مرگبار","tier":"legendary","damage":(200,300),"type":"cosmic","mana_cost":80,"dot_dmg":20,"dot_turns":3,"price":4000},
    "hell_gate":      {"name":"🕳️ دروازه جهنم","tier":"legendary","type":"percent_damage","percent":0.50,"mana_cost":100,"price":7000},
}
POTIONS = {
    "small_health":    {"name":"🧪 معجون سلامت کوچک","tier":"common","type":"heal","heal_amount":30,"price":40},
    "mana_potion":     {"name":"💧 معجون مانا","tier":"common","type":"mana","mana_amount":20,"price":45},
    "large_health":    {"name":"❤️ معجون سلامت بزرگ","tier":"rare","type":"heal","heal_amount":80,"price":180},
    "power_potion":    {"name":"🟡 معجون قدرت","tier":"rare","type":"buff","damage_boost":0.25,"boost_turns":2,"price":280},
    "legendary_potion":{"name":"💜 معجون افسانه‌ای","tier":"epic","type":"full_restore","heal_amount":200,"restore_mana":True,"price":600},
    "dragon_blood":    {"name":"🔴 معجون خون اژدها","tier":"epic","type":"mega_buff","damage_boost":0.40,"heal_amount":50,"boost_turns":3,"price":750},
}
RINGS = {
    "health_ring":  {"name":"💍 انگشتری سلامت","tier":"rare","type":"passive","hp_bonus":50,"price":500},
    "fire_ring":    {"name":"💍 انگشتری آتش","tier":"epic","type":"passive","fire_damage_boost":0.20,"price":1500},
    "shield_ring":  {"name":"💍 انگشتری سپر","tier":"epic","type":"passive","damage_reduction":0.15,"price":2000},
    "mage_ring":    {"name":"💍 انگشتری جادوگر","tier":"epic","type":"passive","spell_boost":0.25,"mana_bonus":30,"price":2500},
    "war_god_ring": {"name":"💍 انگشتری خدای جنگ","tier":"legendary","type":"passive","damage_boost":0.40,"hp_bonus":100,"price":8000,"stock":5},
    "phoenix_ring": {"name":"💍 انگشتری ققنوس","tier":"legendary","type":"passive","daily_revive":True,"revive_hp":50,"price":10000,"stock":5},
    "eternity_ring":{"name":"💍 انگشتری ابدیت","tier":"legendary","type":"passive","hp_boost_pct":0.50,"damage_boost":0.30,"damage_reduction":0.20,"price":15000,"stock":5},
}
ALL_ITEMS = {**WEAPONS, **SPELLS, **POTIONS, **RINGS}
TIER_EMOJI = {"common":"⚪","rare":"🔵","epic":"🟣","legendary":"🟡"}

def get_item(iid): return ALL_ITEMS.get(iid)
def get_cat(iid):
    if iid in WEAPONS: return "weapons"
    if iid in SPELLS:  return "spells"
    if iid in POTIONS: return "potions"
    if iid in RINGS:   return "rings"
    return "unknown"

# ════════════════════════════════════════════
#  DATABASE
# ════════════════════════════════════════════
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn(); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
        hp INTEGER DEFAULT 300, max_hp INTEGER DEFAULT 300,
        mana INTEGER DEFAULT 100, max_mana INTEGER DEFAULT 100,
        points INTEGER DEFAULT 0, wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0, stealth_kills INTEGER DEFAULT 0,
        daily_phoenix_used INTEGER DEFAULT 0,
        last_daily TEXT, last_claim TEXT,
        created_at TEXT DEFAULT(datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS inventory(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, item_id TEXT, quantity INTEGER DEFAULT 1,
        UNIQUE(user_id,item_id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS rings_equipped(
        user_id INTEGER PRIMARY KEY, ring1 TEXT, ring2 TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS duels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER, challenger_id INTEGER, target_id INTEGER,
        status TEXT DEFAULT 'pending', current_turn INTEGER,
        challenger_hp INTEGER, target_hp INTEGER,
        challenger_mana INTEGER, target_mana INTEGER,
        challenger_shield INTEGER DEFAULT 0, target_shield INTEGER DEFAULT 0,
        challenger_buffs TEXT DEFAULT '{}', target_buffs TEXT DEFAULT '{}',
        challenger_debuffs TEXT DEFAULT '{}', target_debuffs TEXT DEFAULT '{}',
        challenger_revive_used INTEGER DEFAULT 0, target_revive_used INTEGER DEFAULT 0,
        message_id INTEGER, created_at TEXT DEFAULT(datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS item_stock(
        item_id TEXT PRIMARY KEY, remaining INTEGER)""")
    conn.commit()
    for iid, item in ALL_ITEMS.items():
        if "stock" in item:
            c.execute("INSERT OR IGNORE INTO item_stock(item_id,remaining) VALUES(?,?)",(iid,item["stock"]))
    conn.commit(); conn.close()

def get_user(uid):
    c=get_conn(); r=c.execute("SELECT * FROM users WHERE user_id=?",(uid,)).fetchone(); c.close()
    return dict(r) if r else None

def create_user(uid, uname, fname):
    c=get_conn(); c.execute("INSERT OR IGNORE INTO users(user_id,username,first_name) VALUES(?,?,?)",(uid,uname,fname)); c.commit(); c.close()

def update_user(uid, **kw):
    if not kw: return
    c=get_conn(); sets=", ".join(f"{k}=?" for k in kw)
    c.execute(f"UPDATE users SET {sets} WHERE user_id=?", list(kw.values())+[uid]); c.commit(); c.close()

def add_points(uid, amt):
    c=get_conn(); c.execute("UPDATE users SET points=MAX(0,points+?) WHERE user_id=?",(amt,uid)); c.commit(); c.close()

def get_leaderboard(limit=10):
    c=get_conn(); rows=c.execute("SELECT user_id,first_name,username,points,wins,losses,stealth_kills FROM users ORDER BY points DESC LIMIT ?",(limit,)).fetchall(); c.close()
    return [dict(r) for r in rows]

def get_inventory(uid):
    c=get_conn(); rows=c.execute("SELECT item_id,quantity FROM inventory WHERE user_id=?",(uid,)).fetchall(); c.close()
    return {r["item_id"]:r["quantity"] for r in rows}

def has_item(uid, iid, qty=1):
    c=get_conn(); r=c.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_id=?",(uid,iid)).fetchone(); c.close()
    return r and r["quantity"]>=qty

def add_item(uid, iid, qty=1):
    c=get_conn(); c.execute("INSERT INTO inventory(user_id,item_id,quantity) VALUES(?,?,?) ON CONFLICT(user_id,item_id) DO UPDATE SET quantity=quantity+?",(uid,iid,qty,qty)); c.commit(); c.close()

def remove_item(uid, iid, qty=1):
    c=get_conn()
    c.execute("UPDATE inventory SET quantity=quantity-? WHERE user_id=? AND item_id=?",(qty,uid,iid))
    c.execute("DELETE FROM inventory WHERE user_id=? AND item_id=? AND quantity<=0",(uid,iid))
    c.commit(); c.close()

def buy_item(uid, iid, price):
    c=get_conn(); u=c.execute("SELECT points FROM users WHERE user_id=?",(uid,)).fetchone()
    if not u or u["points"]<price: c.close(); return False,"امتیاز کافی نداری! 💸"
    sr=c.execute("SELECT remaining FROM item_stock WHERE item_id=?",(iid,)).fetchone()
    if sr is not None:
        if sr["remaining"]<=0: c.close(); return False,"موجودی تموم شده! 😔"
        c.execute("UPDATE item_stock SET remaining=remaining-1 WHERE item_id=?",(iid,))
    c.execute("UPDATE users SET points=points-? WHERE user_id=?",(price,uid))
    c.execute("INSERT INTO inventory(user_id,item_id,quantity) VALUES(?,?,1) ON CONFLICT(user_id,item_id) DO UPDATE SET quantity=quantity+1",(uid,iid))
    c.commit(); c.close(); return True,"خرید موفق! ✅"

def get_rings(uid):
    c=get_conn(); r=c.execute("SELECT ring1,ring2 FROM rings_equipped WHERE user_id=?",(uid,)).fetchone(); c.close()
    return dict(r) if r else {"ring1":None,"ring2":None}

def equip_ring(uid, rid, slot):
    col="ring1" if slot==1 else "ring2"; c=get_conn()
    c.execute(f"INSERT INTO rings_equipped(user_id,{col}) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET {col}=?",(uid,rid,rid)); c.commit(); c.close()

def create_duel(chat_id, cid, tid, c_hp, t_hp, c_mana, t_mana):
    c=get_conn(); cur=c.execute("INSERT INTO duels(chat_id,challenger_id,target_id,status,current_turn,challenger_hp,target_hp,challenger_mana,target_mana) VALUES(?,?,?,'active',?,?,?,?,?)",(chat_id,cid,tid,cid,c_hp,t_hp,c_mana,t_mana)); did=cur.lastrowid; c.commit(); c.close(); return did

def get_duel(did):
    c=get_conn(); r=c.execute("SELECT * FROM duels WHERE id=?",(did,)).fetchone(); c.close(); return dict(r) if r else None

def get_active_duel(chat_id):
    c=get_conn(); r=c.execute("SELECT * FROM duels WHERE chat_id=? AND status='active' ORDER BY created_at DESC LIMIT 1",(chat_id,)).fetchone(); c.close(); return dict(r) if r else None

def get_pending_duel(chat_id):
    c=get_conn(); r=c.execute("SELECT * FROM duels WHERE chat_id=? AND status='pending' ORDER BY created_at DESC LIMIT 1",(chat_id,)).fetchone(); c.close(); return dict(r) if r else None

def update_duel(did, **kw):
    for k,v in kw.items():
        if isinstance(v,dict): kw[k]=json.dumps(v,ensure_ascii=False)
    c=get_conn(); sets=", ".join(f"{k}=?" for k in kw)
    c.execute(f"UPDATE duels SET {sets} WHERE id=?", list(kw.values())+[did]); c.commit(); c.close()

def end_duel(did, winner, loser):
    c=get_conn()
    c.execute("UPDATE duels SET status='ended' WHERE id=?",(did,))
    c.execute("UPDATE users SET wins=wins+1,points=points+100 WHERE user_id=?",(winner,))
    c.execute("UPDATE users SET losses=losses+1,points=MAX(0,points-30) WHERE user_id=?",(loser,))
    c.commit(); c.close()

def get_stock(iid):
    c=get_conn(); r=c.execute("SELECT remaining FROM item_stock WHERE item_id=?",(iid,)).fetchone(); c.close()
    return r["remaining"] if r else None

# ════════════════════════════════════════════
#  COMBAT ENGINE
# ════════════════════════════════════════════
BASE_HP=300; BASE_MANA=100

def calc_stats(uid):
    rings=get_rings(uid); hp_b=0; mana_b=0; hp_p=0
    for s in ["ring1","ring2"]:
        r=get_item(rings.get(s)); 
        if not r: continue
        hp_b+=r.get("hp_bonus",0); mana_b+=r.get("mana_bonus",0); hp_p+=r.get("hp_boost_pct",0)
    return int((BASE_HP+hp_b)*(1+hp_p)), BASE_MANA+mana_b

def ring_bonuses(uid):
    rings=get_rings(uid); b={"damage_boost":0.0,"damage_reduction":0.0,"fire_damage_boost":0.0,"spell_boost":0.0,"daily_revive":False}
    for s in ["ring1","ring2"]:
        r=get_item(rings.get(s))
        if not r: continue
        b["damage_boost"]+=r.get("damage_boost",0); b["damage_reduction"]+=r.get("damage_reduction",0)
        b["fire_damage_boost"]+=r.get("fire_damage_boost",0); b["spell_boost"]+=r.get("spell_boost",0)
        if r.get("daily_revive"): b["daily_revive"]=True
    return b

def fname(uid):
    u=get_user(uid); return u["first_name"] if u else str(uid)

def use_item_in_duel(did, uid, iid):
    duel=get_duel(did)
    if not duel: return False,"دوئل پیدا نشد!",False,None
    if duel["current_turn"]!=uid: return False,"⏳ نوبت تو نیست!",False,None
    item=get_item(iid)
    if not item: return False,"آیتم نامعتبر!",False,None
    if not has_item(uid,iid): return False,"این آیتم رو نداری! 🎒",False,None

    is_c=(uid==duel["challenger_id"]); ap="challenger" if is_c else "target"; dp="target" if is_c else "challenger"
    atk_hp=duel[f"{ap}_hp"]; atk_mana=duel[f"{ap}_mana"]; atk_shield=duel[f"{ap}_shield"]
    def_hp=duel[f"{dp}_hp"]; def_shield=duel[f"{dp}_shield"]
    atk_buffs=json.loads(duel.get(f"{ap}_buffs") or "{}"); atk_debuffs=json.loads(duel.get(f"{ap}_debuffs") or "{}")
    def_buffs=json.loads(duel.get(f"{dp}_buffs") or "{}"); def_debuffs=json.loads(duel.get(f"{dp}_debuffs") or "{}")
    def_mana=duel[f"{dp}_mana"]
    ark=ring_bonuses(uid); def_id=duel["target_id"] if is_c else duel["challenger_id"]; drk=ring_bonuses(def_id)
    cat=get_cat(iid); itype=item.get("type",""); msgs=[]

    if cat=="weapons" or (cat=="spells" and "damage" in item):
        if cat=="spells":
            mc=item.get("mana_cost",0)
            if atk_mana<mc: return False,f"مانا کافی نداری! (نیاز:{mc} 💧)",False,None
            atk_mana-=mc
        dmg=random.randint(*item["damage"]); mul=1.0+ark.get("damage_boost",0)
        if "damage_boost" in atk_buffs: mul+=atk_buffs["damage_boost"]
        if itype in ("fire","fire_physical","holy_fire"): mul+=ark.get("fire_damage_boost",0)
        if cat=="spells": mul+=ark.get("spell_boost",0)
        dmg=int(dmg*mul)
        if item.get("armor_pierce"):
            def_hp-=dmg; msgs.append(f"🌌 {item['name']} — {dmg} دمیج (بدون دفاع)!")
        elif "confusion" in def_debuffs:
            msgs.append(f"😵 گیج بود! حمله به خودش برگشت!"); atk_hp-=dmg; del def_debuffs["confusion"]
        else:
            red=drk.get("damage_reduction",0)
            if "armor_pierce_ratio" in item: red*=(1-item["armor_pierce_ratio"])
            dmg=int(dmg*(1-red))
            if def_shield>0:
                ab=min(def_shield,dmg); def_shield-=ab; dmg-=ab; msgs.append(f"🛡️ سپر {ab} جذب کرد!")
            def_hp-=dmg; msgs.append(f"💥 {item['name']} — {dmg} دمیج!")
            if item.get("lifesteal"):
                h=int(dmg*item["lifesteal"]); atk_hp=min(atk_hp+h,calc_stats(uid)[0]); msgs.append(f"🩸 +{h} HP دزدیده شد!")
            if item.get("burn_chance") and random.random()<item["burn_chance"]:
                def_debuffs["burn"]={"dmg":item.get("burn_dmg",5),"turns":2}; msgs.append("🔥 سوختگی!")
            elif item.get("burn_dmg") and "burn" not in def_debuffs:
                def_debuffs["burn"]={"dmg":item["burn_dmg"],"turns":2}; msgs.append("🔥 سوختگی!")
            if item.get("stun_chance") and random.random()<item["stun_chance"]:
                def_debuffs["stun"]={"turns":1}; msgs.append("⚡ حریف گیج شد!")
            if item.get("self_heal"):
                atk_hp=min(atk_hp+item["self_heal"],calc_stats(uid)[0]); msgs.append(f"✨ +{item['self_heal']} HP!")
            if item.get("dot_dmg"):
                def_debuffs["dot"]={"dmg":item["dot_dmg"],"turns":item.get("dot_turns",3)}; msgs.append("☄️ آسیب کیهانی!")
    elif cat=="spells" and itype=="percent_damage":
        mc=item.get("mana_cost",0)
        if atk_mana<mc: return False,f"مانا کافی نداری!",False,None
        atk_mana-=mc; dmg=int(def_hp*item["percent"]); def_hp-=dmg; msgs.append(f"🕳️ {item['name']} — {dmg} دمیج!")
    elif iid=="magic_shield":
        mc=item.get("mana_cost",0)
        if atk_mana<mc: return False,f"مانا کافی نداری!",False,None
        atk_mana-=mc; atk_shield+=item["shield_hp"]; msgs.append(f"🛡️ سپر {item['shield_hp']} HP فعال!")
    elif iid=="confusion_mist":
        mc=item.get("mana_cost",0)
        if atk_mana<mc: return False,f"مانا کافی نداری!",False,None
        atk_mana-=mc; def_debuffs["confusion"]={"turns":1}; msgs.append("🌫️ مه فراموشی! حریف گیج شد!")
    elif itype in ("buff","mega_buff") and "damage_boost" in item:
        if cat=="spells":
            mc=item.get("mana_cost",0)
            if atk_mana<mc: return False,f"مانا کافی نداری!",False,None
            atk_mana-=mc
        atk_buffs["damage_boost"]=item["damage_boost"]; atk_buffs["damage_boost_turns"]=item.get("boost_turns",2)
        msgs.append(f"💪 +{int(item['damage_boost']*100)}% دمیج برای {item.get('boost_turns',2)} نوبت!")
        if "heal_amount" in item:
            atk_hp=min(atk_hp+item["heal_amount"],calc_stats(uid)[0]); msgs.append(f"❤️ +{item['heal_amount']} HP!")
    elif itype in ("heal","full_restore"):
        h=item.get("heal_amount",0); atk_hp=min(atk_hp+h,calc_stats(uid)[0]); msgs.append(f"💚 +{h} HP!")
        if item.get("restore_mana"): atk_mana=calc_stats(uid)[1]; msgs.append("💧 مانا پر شد!")
    elif itype=="mana":
        atk_mana=min(atk_mana+item["mana_amount"],calc_stats(uid)[1]); msgs.append(f"💧 +{item['mana_amount']} مانا!")
    else:
        return False,"این آیتم اینجا قابل استفاده نیست!",False,None

    if "burn" in def_debuffs:
        b=def_debuffs["burn"]; def_hp-=b["dmg"]; msgs.append(f"🔥 سوختگی: -{b['dmg']} HP!"); b["turns"]-=1
        if b["turns"]<=0: del def_debuffs["burn"]
    if "dot" in def_debuffs:
        d=def_debuffs["dot"]; def_hp-=d["dmg"]; msgs.append(f"☄️ آسیب دوره‌ای: -{d['dmg']} HP!"); d["turns"]-=1
        if d["turns"]<=0: del def_debuffs["dot"]
    if "damage_boost_turns" in atk_buffs:
        atk_buffs["damage_boost_turns"]-=1
        if atk_buffs["damage_boost_turns"]<=0: atk_buffs.pop("damage_boost",None); atk_buffs.pop("damage_boost_turns",None)

    next_turn=def_id
    if "stun" in def_debuffs:
        def_debuffs["stun"]["turns"]-=1
        if def_debuffs["stun"]["turns"]<=0: del def_debuffs["stun"]
        next_turn=uid; msgs.append("⚡ حریف گیج بود! دوباره نوبت توئه!")

    ended=False; winner=None
    if def_hp<=0:
        rk=f"{dp}_revive_used"; ru=duel.get(rk,0)
        has_rv=not ru and (has_item(def_id,"phoenix_ring") or has_item(def_id,"phoenix_spear"))
        ud=get_user(def_id)
        if has_rv and not ud.get("daily_phoenix_used"):
            def_hp=50; msgs.append(f"🔥 رستاخیز! {fname(def_id)} با 50 HP برگشت!"); update_user(def_id,daily_phoenix_used=1); update_duel(did,**{rk:1})
        else:
            ended=True; winner=uid
    if atk_hp<=0: ended=True; winner=def_id

    remove_item(uid,iid)
    ud={f"{ap}_hp":max(0,atk_hp),f"{ap}_mana":max(0,atk_mana),f"{ap}_shield":max(0,atk_shield),
        f"{dp}_hp":max(0,def_hp),f"{dp}_mana":max(0,def_mana),f"{dp}_shield":max(0,def_shield),
        f"{ap}_buffs":atk_buffs,f"{ap}_debuffs":atk_debuffs,f"{dp}_buffs":def_buffs,f"{dp}_debuffs":def_debuffs,
        "current_turn":next_turn if not ended else uid}
    update_duel(did,**ud)
    if ended: loser=def_id if winner==uid else uid; end_duel(did,winner,loser)
    return True,"\n".join(msgs),ended,winner

def do_stealth(atk_id, tgt_id):
    tgt=get_user(tgt_id)
    if not tgt: return False,"کاربر پیدا نشد!"
    atk=get_user(atk_id)
    if atk["points"]<30: return False,"برای حمله مخفیانه به ۳۰ امتیاز نیاز داری!"
    lost=tgt["points"]//4; add_points(tgt_id,-lost); update_user(tgt_id,hp=0)
    add_points(atk_id,-30); add_points(atk_id,50)
    update_user(atk_id,stealth_kills=atk.get("stealth_kills",0)+1)
    return True,f"✅ حمله موفق!\n💀 {fname(tgt_id)} از پا درآمد!\n💸 {lost} امتیاز ازش گرفتی!"

# ════════════════════════════════════════════
#  CLAIM SYSTEM
# ════════════════════════════════════════════
CLAIM_HOURS=8; CLAIM_AMT=50

def can_claim(uid):
    u=get_user(uid); lc=u.get("last_claim") if u else None
    if not lc: return True,0
    try: last=datetime.fromisoformat(lc).replace(tzinfo=timezone.utc)
    except: return True,0
    elapsed=(datetime.now(timezone.utc)-last).total_seconds(); interval=CLAIM_HOURS*3600
    return (elapsed>=interval, 0 if elapsed>=interval else int(interval-elapsed))

def fmt_countdown(sec):
    h=sec//3600; m=(sec%3600)//60; s=sec%60
    parts=[]
    if h: parts.append(f"{h} ساعت")
    if m: parts.append(f"{m} دقیقه")
    if s and not h: parts.append(f"{s} ثانیه")
    return " و ".join(parts) or "چند ثانیه"

# ════════════════════════════════════════════
#  SHOP HANDLERS
# ════════════════════════════════════════════
CATS={"weapons":("⚔️ سلاح‌ها",WEAPONS),"spells":("🔮 اسپل‌ها",SPELLS),"potions":("🧪 معجون‌ها",POTIONS),"rings":("💍 انگشتری‌ها",RINGS)}

async def shop_start(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    u=update.effective_user; create_user(u.id,u.username,u.first_name); ud=get_user(u.id)
    kb=[[InlineKeyboardButton("⚔️ سلاح‌ها",callback_data="sc_weapons"),InlineKeyboardButton("🔮 اسپل‌ها",callback_data="sc_spells")],
        [InlineKeyboardButton("🧪 معجون‌ها",callback_data="sc_potions"),InlineKeyboardButton("💍 انگشتری‌ها",callback_data="sc_rings")],
        [InlineKeyboardButton("🎒 موجودی من",callback_data="inv"),InlineKeyboardButton("📊 پروفایل من",callback_data="myprof")],
        [InlineKeyboardButton("🎁 دریافت امتیاز (هر ۸ ساعت)",callback_data="claimst")]]
    await update.message.reply_text(f"🏪 *فروشگاه RPG*\n\n👤 {u.first_name}\n💎 امتیاز: *{ud['points']}*\n\nیه دسته انتخاب کن:",parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))

async def cb_shop_cat(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); cat=q.data[3:]
    cname,items=CATS[cat]; kb=[]
    for iid,item in items.items():
        st=get_stock(iid); si=f" [{st}✦]" if st is not None else ""
        kb.append([InlineKeyboardButton(f"{TIER_EMOJI[item['tier']]} {item['name']} — 💎{item['price']}{si}",callback_data=f"si_{iid}")])
    kb.append([InlineKeyboardButton("🔙 برگشت",callback_data="sb")])
    await q.edit_message_text(f"*{cname}*\nیه آیتم انتخاب کن:",parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))

async def cb_shop_item(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); iid=q.data[3:]; item=get_item(iid)
    if not item: await q.answer("آیتم پیدا نشد!",show_alert=True); return
    uid=q.from_user.id; u=get_user(uid); inv=get_inventory(uid); has=inv.get(iid,0)
    tn={"common":"معمولی","rare":"نادر","epic":"حماسی","legendary":"افسانه‌ای"}
    sl=[]; 
    if "damage" in item: sl.append(f"⚔️ دمیج: {item['damage'][0]}–{item['damage'][1]}")
    if "heal_amount" in item: sl.append(f"❤️ درمان: +{item['heal_amount']}")
    if "shield_hp" in item: sl.append(f"🛡️ سپر: {item['shield_hp']} HP")
    if "mana_cost" in item: sl.append(f"💧 مانا: {item['mana_cost']}")
    if "hp_bonus" in item: sl.append(f"❤️ HP پایه: +{item['hp_bonus']}")
    if "damage_boost" in item: sl.append(f"💪 دمیج: +{int(item['damage_boost']*100)}%")
    if "damage_reduction" in item: sl.append(f"🛡️ دفاع: +{int(item['damage_reduction']*100)}%")
    if item.get("armor_pierce"): sl.append("🌌 نادیده گرفتن زره")
    st=get_stock(iid); stxt=f"\n⚠️ *موجودی محدود: {st}*" if st is not None else ""
    txt=(f"{TIER_EMOJI[item['tier']]} *{item['name']}*\n🏷️ {tn.get(item['tier'])}\n\n"
         f"{chr(10).join(sl)}\n\n💎 قیمت: *{item['price']}*{stxt}\n💰 امتیاز شما: *{u['points']}*\n🎒 موجودی: {has}")
    kb=[]
    if u["points"]>=item["price"]: kb.append([InlineKeyboardButton("✅ خرید!",callback_data=f"buy_{iid}")])
    else: kb.append([InlineKeyboardButton("❌ امتیاز کافی نداری",callback_data="nop")])
    if iid in RINGS and has>0:
        kb.append([InlineKeyboardButton("💍 جای ۱",callback_data=f"er_{iid}_1"),InlineKeyboardButton("💍 جای ۲",callback_data=f"er_{iid}_2")])
    kb.append([InlineKeyboardButton("🔙",callback_data=f"sc_{get_cat(iid)}")])
    await q.edit_message_text(txt,parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))

async def cb_buy(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; iid=q.data[4:]; item=get_item(iid); uid=q.from_user.id
    ok,msg=buy_item(uid,iid,item["price"]); await q.answer(msg,show_alert=True)
    if ok:
        u=get_user(uid)
        await q.edit_message_text(f"✅ *{item['name']}* خریده شد!\n💎 باقیمانده: {u['points']}",parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛍️ ادامه",callback_data="sb")]]))

async def cb_equip_ring(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); p=q.data.split("_"); slot=int(p[-1]); iid="_".join(p[1:-1])
    uid=q.from_user.id
    if not has_item(uid,iid): await q.answer("این انگشتری رو نداری!",show_alert=True); return
    equip_ring(uid,iid,slot); item=get_item(iid)
    mhp,mma=calc_stats(uid); update_user(uid,max_hp=mhp,max_mana=mma)
    await q.answer(f"✅ {item['name']} تجهیز شد!",show_alert=True)

async def cb_inv(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); uid=q.from_user.id; inv=get_inventory(uid); re=get_rings(uid)
    if not inv:
        await q.edit_message_text("🎒 موجودیت خالیه!",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛍️ فروشگاه",callback_data="sb")]])); return
    lines=["🎒 *موجودی شما:*\n"]
    for iid,qty in inv.items():
        it=get_item(iid)
        if it: lines.append(f"{TIER_EMOJI[it['tier']]} {it['name']} ×{qty}")
    r1=get_item(re["ring1"]); r2=get_item(re["ring2"])
    lines.append(f"\n💍 انگشتری ۱: {r1['name'] if r1 else '—'}\n💍 انگشتری ۲: {r2['name'] if r2 else '—'}")
    await q.edit_message_text("\n".join(lines),parse_mode="Markdown",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="sb")]]))

async def cb_myprof(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); uid=q.from_user.id; u=get_user(uid)
    mhp,mma=calc_stats(uid); re=get_rings(uid); r1=get_item(re["ring1"]); r2=get_item(re["ring2"])
    await q.edit_message_text(
        f"👤 *{u['first_name']}*\n\n💎 {u['points']}\n❤️ {u['hp']}/{mhp}\n💧 {u['mana']}/{mma}\n"
        f"⚔️ {u['wins']}W/{u['losses']}L\n🗡️ مخفیانه: {u['stealth_kills']}\n"
        f"💍 {r1['name'] if r1 else '—'} / {r2['name'] if r2 else '—'}",
        parse_mode="Markdown",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="sb")]]))

async def cb_sb(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); u=get_user(q.from_user.id)
    kb=[[InlineKeyboardButton("⚔️ سلاح‌ها",callback_data="sc_weapons"),InlineKeyboardButton("🔮 اسپل‌ها",callback_data="sc_spells")],
        [InlineKeyboardButton("🧪 معجون‌ها",callback_data="sc_potions"),InlineKeyboardButton("💍 انگشتری‌ها",callback_data="sc_rings")],
        [InlineKeyboardButton("🎒 موجودی من",callback_data="inv"),InlineKeyboardButton("📊 پروفایل من",callback_data="myprof")],
        [InlineKeyboardButton("🎁 دریافت امتیاز (هر ۸ ساعت)",callback_data="claimst")]]
    await q.edit_message_text(f"🏪 *فروشگاه RPG*\n\n💎 امتیاز: *{u['points']}*",parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))

async def cb_claimst(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); uid=q.from_user.id; u=get_user(uid)
    ok,rem=can_claim(uid)
    if ok:
        txt=f"🎁 *می‌تونی امتیاز بگیری!*\n\nبرای دریافت *{CLAIM_AMT} امتیاز* بزن /claim"
    else:
        txt=f"⏳ تا دریافت بعدی: *{fmt_countdown(rem)}*\n💎 امتیاز: {u['points']}"
    await q.edit_message_text(txt,parse_mode="Markdown",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="sb")]]))

# ════════════════════════════════════════════
#  DUEL HANDLERS
# ════════════════════════════════════════════
async def duel_cmd(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    chat=update.effective_chat; user=update.effective_user
    if chat.type=="private": await update.message.reply_text("⚔️ دوئل فقط توی گروه!"); return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚔️ روی پیام کسی reply کن و /duel بزن!"); return
    tgt=update.message.reply_to_message.from_user
    if tgt.id==user.id: await update.message.reply_text("😂 با خودت نمیشه!"); return
    if tgt.is_bot: await update.message.reply_text("🤖 با بات نمیشه!"); return
    if get_active_duel(chat.id): await update.message.reply_text("⚔️ یه دوئل فعال هست!"); return
    if get_pending_duel(chat.id): await update.message.reply_text("⏳ یه درخواست در انتظاره!"); return
    create_user(user.id,user.username,user.first_name); create_user(tgt.id,tgt.username,tgt.first_name)
    if not get_inventory(user.id): await update.message.reply_text(f"🎒 {user.first_name} آیتم نداری! /shop"); return
    if not get_inventory(tgt.id): await update.message.reply_text(f"🎒 {tgt.first_name} آیتم نداره!"); return
    kb=[[InlineKeyboardButton("✅ قبول!",callback_data=f"ad_{user.id}"),InlineKeyboardButton("❌ رد",callback_data=f"rd_{user.id}")]]
    msg=await update.message.reply_text(f"⚔️ *درخواست دوئل!*\n\n🗡️ {user.first_name} به {tgt.mention_markdown()} درخواست داد!\n\n_{tgt.first_name} قبول می‌کنی؟_",
        parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))
    ctx.chat_data["pd"]={"cid":user.id,"tid":tgt.id,"cn":user.first_name,"tn":tgt.first_name,"mid":msg.message_id}

async def cb_accept_duel(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; cid=int(q.data[3:]); aid=q.from_user.id; chat=q.message.chat
    pd=ctx.chat_data.get("pd")
    if not pd or pd["cid"]!=cid: await q.answer("معتبر نیست!",show_alert=True); return
    if aid!=pd["tid"]: await q.answer("این دوئل برای تو نیست!",show_alert=True); return
    await q.answer("✅ شروع شد!")
    tid=pd["tid"]; chp,cma=calc_stats(cid); thp,tma=calc_stats(tid)
    did=create_duel(chat.id,cid,tid,chp,thp,cma,tma)
    ctx.chat_data["adid"]=did; ctx.chat_data.pop("pd",None)
    await q.edit_message_text(f"⚔️ *دوئل شروع شد!*\n\n🗡️ {pd['cn']} ❤️{chp} vs {pd['tn']} ❤️{thp}\n\nنوبت: *{pd['cn']}* 🎯",parse_mode="Markdown")
    await _send_panel(chat.id,cid,ctx)

async def cb_reject_duel(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; cid=int(q.data[3:])
    pd=ctx.chat_data.get("pd")
    if not pd: await q.answer("پیدا نشد!",show_alert=True); return
    if q.from_user.id!=pd["tid"]: await q.answer("این دوئل برات نیست!",show_alert=True); return
    ctx.chat_data.pop("pd",None); await q.answer("❌ رد شد!")
    await q.edit_message_text(f"❌ {q.from_user.first_name} رد کرد!")

async def use_cmd(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    chat=update.effective_chat; user=update.effective_user
    if not ctx.args: await update.message.reply_text("مثال: /use iron_dagger"); return
    did=ctx.chat_data.get("adid")
    if not did: await update.message.reply_text("دوئل فعالی نیست!"); return
    iid=ctx.args[0].lower(); ok,msg,ended,winner=use_item_in_duel(did,user.id,iid)
    if not ok: await update.message.reply_text(f"❌ {msg}"); return
    duel=get_duel(did)
    if not duel: return
    cn=get_user(duel["challenger_id"])["first_name"]; tn=get_user(duel["target_id"])["first_name"]
    stxt=f"⚔️ *وضعیت*\n❤️ {cn}: {duel['challenger_hp']} | ❤️ {tn}: {duel['target_hp']}\n\n{msg}"
    if ended:
        w=get_user(winner); ctx.chat_data.pop("adid",None)
        await update.message.reply_text(f"{stxt}\n\n🏆 *{w['first_name']} برنده شد!*\n💎 +100 برنده | -30 بازنده",parse_mode="Markdown")
    else:
        duel=get_duel(did); nt=get_user(duel["current_turn"])
        await update.message.reply_text(f"{stxt}\n\n🎯 نوبت: *{nt['first_name']}*",parse_mode="Markdown")
        await _send_panel(chat.id,duel["current_turn"],ctx)

async def status_cmd(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    did=ctx.chat_data.get("adid")
    if not did: await update.message.reply_text("دوئل فعالی نیست!"); return
    d=get_duel(did)
    if not d: return
    c=get_user(d["challenger_id"]); t=get_user(d["target_id"]); nt=get_user(d["current_turn"])
    await update.message.reply_text(
        f"⚔️ *وضعیت دوئل*\n\n{c['first_name']}: ❤️{d['challenger_hp']} 💧{d['challenger_mana']}\n"
        f"{t['first_name']}: ❤️{d['target_hp']} 💧{d['target_mana']}\n\n🎯 نوبت: *{nt['first_name']}*",parse_mode="Markdown")

async def _send_panel(chat_id,uid,ctx):
    inv=get_inventory(uid)
    if not inv: return
    u=get_user(uid); lines=[f"🎒 *آیتم‌های {u['first_name']} (نوبت توئه!):*\n"]
    for iid,qty in inv.items():
        it=get_item(iid)
        if it: lines.append(f"`/use {iid}` — {TIER_EMOJI[it['tier']]} {it['name']} ×{qty}")
    await ctx.bot.send_message(chat_id=chat_id,text="\n".join(lines),parse_mode="Markdown")

# ════════════════════════════════════════════
#  STEALTH
# ════════════════════════════════════════════
async def stealth_cmd(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    user=update.effective_user
    if update.effective_chat.type!="private": await update.message.reply_text("🗡️ حمله مخفیانه رو تو پیوی بات انجام بده!"); return
    create_user(user.id,user.username,user.first_name); u=get_user(user.id)
    if u["points"]<30: await update.message.reply_text(f"❌ به ۳۰ امتیاز نیاز داری! (داری: {u['points']})"); return
    ctx.user_data["ss"]="await_target"
    await update.message.reply_text("🗡️ *حمله مخفیانه*\n\nهزینه: 30 امتیاز | موفقیت: +50\n\n⚠️ HP هدف→0 و ۲۵٪ امتیازش از بین میره\n\nایدی عددی هدف رو بفرست:",
        parse_mode="Markdown",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو",callback_data="cst")]]))

async def cb_confirm_stealth(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); tid=int(q.data[4:]); aid=q.from_user.id
    ctx.user_data.pop("ss",None); ctx.user_data.pop("st",None)
    ok,msg=do_stealth(aid,tid)
    if ok:
        tgt=get_user(tid); atk=get_user(aid)
        await q.edit_message_text(f"🗡️ *حمله موفق!*\n\n{msg}\n\n💎 امتیاز شما: {atk['points']}",parse_mode="Markdown")
        try: await q.bot.send_message(chat_id=tid,text="⚠️ *حمله مخفیانه!*\n💀 HP به صفر رسید!\nبرای بازیابی HP معجون بخر /shop",parse_mode="Markdown")
        except: pass
    else: await q.edit_message_text(f"❌ {msg}")

async def cb_cancel_stealth(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); ctx.user_data.pop("ss",None); ctx.user_data.pop("st",None)
    await q.edit_message_text("❌ لغو شد.")

async def cancel_cmd(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    ctx.user_data.pop("ss",None); ctx.user_data.pop("st",None); ctx.user_data.pop("aa",None)
    await update.message.reply_text("❌ لغو شد.")

# ════════════════════════════════════════════
#  CLAIM
# ════════════════════════════════════════════
async def claim_cmd(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    user=update.effective_user
    if update.effective_chat.type!="private": await update.message.reply_text("🎁 برای claim به پیوی بات بیا!"); return
    create_user(user.id,user.username,user.first_name); u=get_user(user.id)
    ok,rem=can_claim(user.id)
    if not ok:
        await update.message.reply_text(f"⏳ *هنوز وقتش نشده!*\n\nتا دریافت بعدی: *{fmt_countdown(rem)}*\n\n💎 امتیاز فعلی: {u['points']}",
            parse_mode="Markdown",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏪 فروشگاه",callback_data="sb")]])); return
    now=datetime.now(timezone.utc).isoformat()
    add_points(user.id,CLAIM_AMT); update_user(user.id,last_claim=now); u=get_user(user.id)
    await update.message.reply_text(f"🎁 *امتیاز دریافت شد!*\n\n✨ +{CLAIM_AMT} امتیاز\n💎 امتیاز جدید: *{u['points']}*\n\n⏰ {CLAIM_HOURS} ساعت دیگه بیا!",
        parse_mode="Markdown",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏪 خرید آیتم",callback_data="sb")]]))

# ════════════════════════════════════════════
#  ADMIN
# ════════════════════════════════════════════
def is_admin(uid): return uid in ADMIN_IDS

async def admin_cmd(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): await update.message.reply_text("❌ دسترسی ندارید."); return
    kb=[[InlineKeyboardButton("🎁 دادن آیتم",callback_data="aa_gi"),InlineKeyboardButton("💎 دادن امتیاز",callback_data="aa_gp")],
        [InlineKeyboardButton("🗡️ حمله مخفیانه",callback_data="aa_st"),InlineKeyboardButton("🏆 لیدربورد",callback_data="aa_lb")],
        [InlineKeyboardButton("👤 اطلاعات کاربر",callback_data="aa_ui"),InlineKeyboardButton("❤️ ریست HP",callback_data="aa_rh")],
        [InlineKeyboardButton("📢 پیام به گروه",callback_data="aa_bc")]]
    await update.message.reply_text("🔧 *پنل ادمین*",parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))

async def cb_admin(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; uid=q.from_user.id
    if not is_admin(uid): await q.answer("❌",show_alert=True); return
    await q.answer(); act=q.data
    bk=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="aa_back")]])
    if act=="aa_gi": ctx.user_data["aa"]="gi_uid"; await q.edit_message_text("🎁 ایدی کاربر:",reply_markup=bk)
    elif act=="aa_gp": ctx.user_data["aa"]="gp_uid"; await q.edit_message_text("💎 ایدی کاربر:",reply_markup=bk)
    elif act=="aa_st": ctx.user_data["aa"]="st_uid"; await q.edit_message_text("🗡️ ایدی هدف حمله:",reply_markup=bk)
    elif act=="aa_ui": ctx.user_data["aa"]="ui_uid"; await q.edit_message_text("👤 ایدی کاربر:",reply_markup=bk)
    elif act=="aa_rh": ctx.user_data["aa"]="rh_uid"; await q.edit_message_text("❤️ ایدی کاربر:",reply_markup=bk)
    elif act=="aa_bc": ctx.user_data["aa"]="bc_cid"; await q.edit_message_text("📢 ایدی گروه:",reply_markup=bk)
    elif act=="aa_lb":
        lb=get_leaderboard(10); md=["🥇","🥈","🥉"]
        lines=["🏆 *لیدربورد:*\n"]+[f"{md[i] if i<3 else str(i+1)+'.'} {u['first_name']} — 💎{u['points']} ⚔️{u['wins']}W" for i,u in enumerate(lb)]
        await q.edit_message_text("\n".join(lines),parse_mode="Markdown",reply_markup=bk)
    elif act=="aa_back":
        ctx.user_data.pop("aa",None)
        kb=[[InlineKeyboardButton("🎁 دادن آیتم",callback_data="aa_gi"),InlineKeyboardButton("💎 دادن امتیاز",callback_data="aa_gp")],
            [InlineKeyboardButton("🗡️ حمله مخفیانه",callback_data="aa_st"),InlineKeyboardButton("🏆 لیدربورد",callback_data="aa_lb")],
            [InlineKeyboardButton("👤 اطلاعات کاربر",callback_data="aa_ui"),InlineKeyboardButton("❤️ ریست HP",callback_data="aa_rh")],
            [InlineKeyboardButton("📢 پیام به گروه",callback_data="aa_bc")]]
        await q.edit_message_text("🔧 *پنل ادمین*",parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))

# ════════════════════════════════════════════
#  MAIN MESSAGE HANDLER (private)
# ════════════════════════════════════════════
async def priv_msg(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type!="private": return
    uid=update.effective_user.id; txt=update.message.text.strip(); aa=ctx.user_data.get("aa"); ss=ctx.user_data.get("ss")

    # ─── stealth ───
    if ss=="await_target":
        if not txt.isdigit(): await update.message.reply_text("❌ ایدی باید عددی باشه!"); return
        tid=int(txt)
        if tid==uid: await update.message.reply_text("😂 به خودت؟"); return
        tgt=get_user(tid)
        if not tgt: await update.message.reply_text("❌ کاربر ثبت‌نام نکرده!"); return
        ctx.user_data["st"]=tid; ctx.user_data["ss"]="confirming"
        await update.message.reply_text(
            f"🎯 *هدف: {tgt['first_name']}*\n❤️ HP: {tgt['hp']}\n💎 امتیاز: {tgt['points']}\n\n"
            f"حمله می‌کنی؟ (۲۵٪ = *{tgt['points']//4}* امتیاز از بین میره)",parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚔️ بزن!",callback_data=f"cst_{tid}"),InlineKeyboardButton("❌ لغو",callback_data="cst")]]))
        return

    if not is_admin(uid) or not aa: return

    # ─── admin flows ───
    if aa=="gi_uid":
        if not txt.isdigit(): await update.message.reply_text("❌ ایدی عددی!"); return
        tgt=get_user(int(txt))
        if not tgt: await update.message.reply_text("❌ پیدا نشد!"); return
        ctx.user_data["at"]=int(txt); ctx.user_data["aa"]="gi_iid"
        lines=["آیدی آیتم را بفرست:\n"]+[f"`{k}` — {TIER_EMOJI[v['tier']]} {v['name']}" for k,v in ALL_ITEMS.items()]
        await update.message.reply_text("\n".join(lines),parse_mode="Markdown")
    elif aa=="gi_iid":
        it=get_item(txt)
        if not it: await update.message.reply_text("❌ آیتم پیدا نشد!"); return
        tid=ctx.user_data["at"]; add_item(tid,txt); tgt=get_user(tid); ctx.user_data.pop("aa",None); ctx.user_data.pop("at",None)
        await update.message.reply_text(f"✅ *{it['name']}* به *{tgt['first_name']}* داده شد!",parse_mode="Markdown")
        try: await ctx.bot.send_message(chat_id=tid,text=f"🎁 ادمین *{it['name']}* رو بهت هدیه داد!",parse_mode="Markdown")
        except: pass
    elif aa=="gp_uid":
        if not txt.isdigit(): await update.message.reply_text("❌ ایدی عددی!"); return
        tgt=get_user(int(txt))
        if not tgt: await update.message.reply_text("❌ پیدا نشد!"); return
        ctx.user_data["at"]=int(txt); ctx.user_data["aa"]="gp_amt"
        await update.message.reply_text(f"👤 {tgt['first_name']} ({tgt['points']} امتیاز)\nچقدر امتیاز؟ (منفی هم قبوله)")
    elif aa=="gp_amt":
        try: amt=int(txt)
        except: await update.message.reply_text("❌ عدد بفرست!"); return
        tid=ctx.user_data["at"]; add_points(tid,amt); tgt=get_user(tid); ctx.user_data.pop("aa",None); ctx.user_data.pop("at",None)
        await update.message.reply_text(f"✅ {'+' if amt>=0 else ''}{amt} به {tgt['first_name']} داده شد! (جدید: {tgt['points']})")
    elif aa=="st_uid":
        if not txt.isdigit(): await update.message.reply_text("❌ ایدی عددی!"); return
        tid=int(txt); tgt=get_user(tid)
        if not tgt: await update.message.reply_text("❌ پیدا نشد!"); return
        lost=tgt["points"]//4; add_points(tid,-lost); update_user(tid,hp=0); ctx.user_data.pop("aa",None)
        await update.message.reply_text(f"🗡️ *حمله ادمین موفق!*\n👤 {tgt['first_name']}\n💀 HP→0\n💸 -{lost} امتیاز",parse_mode="Markdown")
        try: await ctx.bot.send_message(chat_id=tid,text="⚠️ *حمله مخفیانه ادمین!*\n💀 HP به صفر رسید!",parse_mode="Markdown")
        except: pass
    elif aa=="ui_uid":
        if not txt.isdigit(): await update.message.reply_text("❌ ایدی عددی!"); return
        u=get_user(int(txt))
        if not u: await update.message.reply_text("❌ پیدا نشد!"); return
        inv=get_inventory(int(txt)); ctx.user_data.pop("aa",None)
        istr=", ".join(f"{k}×{v}" for k,v in inv.items()) or "خالی"
        await update.message.reply_text(
            f"👤 *{u['first_name']}* (@{u['username']})\n`{u['user_id']}`\n💎 {u['points']}\n❤️ {u['hp']}/{u['max_hp']}\n"
            f"💧 {u['mana']}/{u['max_mana']}\n⚔️ {u['wins']}W/{u['losses']}L\n🗡️ {u['stealth_kills']}\n🎒 {istr}",parse_mode="Markdown")
    elif aa=="rh_uid":
        if not txt.isdigit(): await update.message.reply_text("❌ ایدی عددی!"); return
        tid=int(txt); u=get_user(tid)
        if not u: await update.message.reply_text("❌ پیدا نشد!"); return
        update_user(tid,hp=u["max_hp"],mana=u["max_mana"]); ctx.user_data.pop("aa",None)
        await update.message.reply_text(f"✅ HP/مانای {u['first_name']} ریست شد!")
    elif aa=="bc_cid":
        ctx.user_data["bc_id"]=txt; ctx.user_data["aa"]="bc_txt"; await update.message.reply_text("📢 متن پیام:")
    elif aa=="bc_txt":
        cid=ctx.user_data.get("bc_id"); ctx.user_data.pop("aa",None); ctx.user_data.pop("bc_id",None)
        try: await ctx.bot.send_message(chat_id=int(cid),text=f"📢 *اطلاعیه:*\n\n{txt}",parse_mode="Markdown"); await update.message.reply_text("✅ ارسال شد!")
        except Exception as e: await update.message.reply_text(f"❌ {e}")

# ════════════════════════════════════════════
#  SCHEDULER
# ════════════════════════════════════════════
async def daily_lb(ctx:ContextTypes.DEFAULT_TYPE):
    lb=get_leaderboard(10)
    if not lb: return
    md=["🥇","🥈","🥉"]
    lines=["🌅 *لیدربورد امروز!*\n","━━━━━━━━━━━━"]+\
        [f"{md[i] if i<3 else str(i+1)+'.'} {u['first_name']}\n   💎{u['points']} | ⚔️{u['wins']}W/{u['losses']}L | 🗡️{u['stealth_kills']}" for i,u in enumerate(lb)]+\
        ["━━━━━━━━━━━━","💪 پیوی بات: /claim برای امتیاز رایگان!"]
    txt="\n".join(lines)
    for gid in GROUP_IDS:
        try: await ctx.bot.send_message(chat_id=gid,text=txt,parse_mode="Markdown")
        except Exception as e: logger.error(f"lb error {gid}: {e}")
    # ریست ققنوس
    c=get_conn(); c.execute("UPDATE users SET daily_phoenix_used=0"); c.commit(); c.close()

# ════════════════════════════════════════════
#  MAIN COMMANDS
# ════════════════════════════════════════════
async def start_cmd(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    u=update.effective_user; create_user(u.id,u.username,u.first_name)
    if update.effective_chat.type=="private":
        await update.message.reply_text(
            f"⚔️ *سلام {u.first_name}! به دنیای RPG خوش اومدی!*\n\n"
            f"🏪 /shop — فروشگاه\n🎁 /claim — امتیاز رایگان هر ۸ ساعت\n"
            f"🗡️ /stealth — حمله مخفیانه\n📊 /profile — پروفایل\n🏆 /top — لیدربورد\n\n"
            f"*در گروه:*\n⚔️ /duel — دوئل | /use [آیتم] — استفاده | /status — وضعیت\n\n"
            f"💡 اول /claim بزن و امتیاز رایگان بگیر!",parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚔️ {u.first_name} عضو بازی شد!\nبرای خرید: @{ctx.bot.username}")

async def profile_cmd(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    u=update.effective_user; create_user(u.id,u.username,u.first_name); ud=get_user(u.id)
    mhp,mma=calc_stats(u.id); re=get_rings(u.id); r1=get_item(re["ring1"]); r2=get_item(re["ring2"])
    await update.message.reply_text(
        f"👤 *{ud['first_name']}*\n\n💎 امتیاز: *{ud['points']}*\n❤️ HP: {ud['hp']}/{mhp}\n💧 مانا: {ud['mana']}/{mma}\n"
        f"⚔️ برد: *{ud['wins']}* | 💀 باخت: *{ud['losses']}*\n🗡️ مخفیانه: *{ud['stealth_kills']}*\n"
        f"💍 {r1['name'] if r1 else '—'} / {r2['name'] if r2 else '—'}",parse_mode="Markdown")

async def top_cmd(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    lb=get_leaderboard(10); md=["🥇","🥈","🥉"]
    lines=["🏆 *برترین مبارزان:*\n"]+[f"{md[i] if i<3 else str(i+1)+'.'} {u['first_name']} — 💎{u['points']} | ⚔️{u['wins']}W" for i,u in enumerate(lb)]
    await update.message.reply_text("\n".join(lines),parse_mode="Markdown")

async def set_cmds(app):
    await app.bot.set_my_commands([
        BotCommand("start","شروع بازی"), BotCommand("shop","فروشگاه"),
        BotCommand("claim","امتیاز رایگان هر ۸ ساعت"), BotCommand("profile","پروفایل"),
        BotCommand("top","لیدربورد"), BotCommand("stealth","حمله مخفیانه"),
        BotCommand("duel","دوئل در گروه"), BotCommand("use","استفاده آیتم در دوئل"),
        BotCommand("status","وضعیت دوئل"), BotCommand("cancel","لغو"),
        BotCommand("admin","پنل ادمین")])

def main():
    init_db()
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start_cmd))
    app.add_handler(CommandHandler("shop",shop_start))
    app.add_handler(CommandHandler("claim",claim_cmd))
    app.add_handler(CommandHandler("profile",profile_cmd))
    app.add_handler(CommandHandler("top",top_cmd))
    app.add_handler(CommandHandler("stealth",stealth_cmd))
    app.add_handler(CommandHandler("cancel",cancel_cmd))
    app.add_handler(CommandHandler("duel",duel_cmd))
    app.add_handler(CommandHandler("use",use_cmd))
    app.add_handler(CommandHandler("status",status_cmd))
    app.add_handler(CommandHandler("admin",admin_cmd))

    app.add_handler(CallbackQueryHandler(cb_shop_cat,   pattern="^sc_"))
    app.add_handler(CallbackQueryHandler(cb_shop_item,  pattern="^si_"))
    app.add_handler(CallbackQueryHandler(cb_buy,        pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(cb_equip_ring, pattern="^er_"))
    app.add_handler(CallbackQueryHandler(cb_inv,        pattern="^inv$"))
    app.add_handler(CallbackQueryHandler(cb_myprof,     pattern="^myprof$"))
    app.add_handler(CallbackQueryHandler(cb_sb,         pattern="^sb$"))
    app.add_handler(CallbackQueryHandler(cb_claimst,    pattern="^claimst$"))
    app.add_handler(CallbackQueryHandler(cb_accept_duel,pattern="^ad_"))
    app.add_handler(CallbackQueryHandler(cb_reject_duel,pattern="^rd_"))
    app.add_handler(CallbackQueryHandler(cb_confirm_stealth,pattern="^cst_"))
    app.add_handler(CallbackQueryHandler(cb_cancel_stealth,pattern="^cst$"))
    app.add_handler(CallbackQueryHandler(cb_admin,      pattern="^aa_"))
    app.add_handler(CallbackQueryHandler(lambda u,c: u.callback_query.answer(), pattern="^nop$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, priv_msg))

    jq=app.job_queue
    jq.run_daily(daily_lb, time=dtime(4,30), name="daily_lb")

    app.post_init=set_cmds
    logger.info("🤖 RPG Bot starting...")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
