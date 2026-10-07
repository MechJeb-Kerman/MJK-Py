# -*- coding: utf-8 -*-
"""
Black Hole · 黑洞吞噬 v0.4.6.w  (Web / pygbag 版)
v0.4.6 全部内容 + Web 兼容：
  - IS_WEB 检测（emscripten）
  - localStorage 存档
  - 打包字体 assets/NotoSansSC-Regular.ttf
  - async 主循环
  - 显示器模式固定为浏览器

打包：
  pip install -U pygbag
  cd HELLO
  pygbag --build game_blackhole_v0.4.6.w.py
本地测试：
  pygbag game_blackhole_v0.4.6.w.py
  浏览器打开 http://localhost:8000
"""
import os, sys, math, random, json, array, asyncio

# =========================================================
# 平台检测
# =========================================================
IS_WEB = sys.platform == "emscripten"

if not IS_WEB:
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")

import pygame

# =========================================================
# 常量
# =========================================================
W, H = 1080, 720
WORLD_W, WORLD_H = 3200, 2400
FPS = 60
BODY_COUNT = 46
G_RANGE = 700

ZOOM_START_MASS = 2000.0
ZOOM_END_MASS   = 20000.0
ZOOM_MIN_SCALE  = 0.40

BONUS_INTERVAL  = 3
BONUS_DURATION  = 15.0
BONUS_SCORE_MULT = 2.5
BONUS_END_MASS  = 30.0

if IS_WEB:
    DISPLAY_MODES = [("浏览器", (W, H), False)]
else:
    DISPLAY_MODES = [
        ("窗口 1080×720",  (1080, 720),  False),
        ("窗口 1280×720",  (1280, 720),  False),
        ("窗口 1600×900",  (1600, 900),  False),
        ("窗口 1920×1080", (1920, 1080), False),
        ("全屏",           (0, 0),       True),
    ]
current_display_idx = 0

# =========================================================
# 初始化 pygame
# =========================================================
if not IS_WEB:
    pygame.mixer.pre_init(22050, -16, 1, 256)
pygame.init()

if IS_WEB:
    AUDIO_OK = False          # Web 强制静音，绕过浏览器音频策略
else:
    AUDIO_OK = pygame.mixer.get_init() is not None
    if not AUDIO_OK:
        try:
            pygame.mixer.init(22050, -16, 1, 256)
            AUDIO_OK = True
        except Exception:
            AUDIO_OK = Falsepygame.display.set_caption("Black Hole · 黑洞吞噬 v0.4.6.w")
clock = pygame.time.Clock()
canvas = pygame.Surface((W, H))
screen = canvas
display_surf = None

# =========================================================
# 工具
# =========================================================
def clamp(v, a, b):
    return max(a, min(b, v))

def hsv_to_rgb(h, s, v):
    i = int(h * 6); f = h * 6 - i
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    i %= 6
    r, g, b = [(v, t, p), (q, v, p), (p, v, t),
               (p, q, v), (t, p, v), (v, p, q)][i]
    return int(r * 255), int(g * 255), int(b * 255)

def mass_color(mass):
    t = clamp(math.log(max(mass, 1) / 6 + 1) / math.log(70), 0, 1)
    return hsv_to_rgb(0.45 - 0.45 * t, 0.72, 0.58)

_font_cache = {}
def get_font(size, bold=False):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]

    # 1. 打包字体（web 首选）
    candidates = [
        "assets/NotoSansSC-Regular.ttf",
        "assets/NotoSansSC-Regular.otf",
        "assets/NotoSansCJKsc-Regular.otf",
        "assets/msyh.ttc",
        "assets/simhei.ttf",
        "NotoSansSC-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                _font_cache[key] = pygame.font.Font(p, size)
                return _font_cache[key]
            except Exception:
                pass

    # 2. 桌面系统字体
    if not IS_WEB:
        for name in ("notosanscjksc", "notosanscjk", "wenquanyimicrohei",
                     "wenquanyizenhei", "microsoftyahei", "simhei",
                     "dejavusans", "arial"):
            path = pygame.font.match_font(name, bold=bold)
            if path:
                try:
                    _font_cache[key] = pygame.font.Font(path, size)
                    return _font_cache[key]
                except Exception:
                    pass

    # 3. 兜底
    _font_cache[key] = pygame.font.Font(None, size)
    return _font_cache[key]

def next_mode(cur):
    keys = list(GAME_MODES.keys())
    return keys[(keys.index(cur) + 1) % len(keys)]

# =========================================================
# 存档 / 关卡文件（web 用 localStorage）
# =========================================================
def _default_save():
    return {"best_mass": 0.0, "best_score": 0.0, "unlocked": [], "skin": 0,
            "display_idx": 0, "audio": True,
            "core_xp": 0.0, "core_level": 1, "mode": "classic",
            "no_shake": False, "seen_tutorial": False, "volume": 0.7,
            "colorblind": False, "show_minimap": True,
            "stat_plays": 0, "stat_eaten": 0, "stat_time": 0.0,
            "stat_boss": 0, "stat_evolve": 0}

if IS_WEB:
    from platform import window

    def load_save():
        try:
            raw = window.localStorage.getItem("blackhole_save")
            if raw:
                d = json.loads(raw)
                base = _default_save()
                base.update(d)
                return base
        except Exception:
            pass
        return _default_save()

    def write_save(d):
        try:
            window.localStorage.setItem(
                "blackhole_save", json.dumps(d, ensure_ascii=False))
        except Exception:
            pass

    def level_save(bodies):
        try:
            window.localStorage.setItem(
                "blackhole_levels", json.dumps(bodies, ensure_ascii=False))
            return True
        except Exception:
            return False

    def level_load():
        try:
            raw = window.localStorage.getItem("blackhole_levels")
            return json.loads(raw) if raw else []
        except Exception:
            return []
else:
    SAVE_FILE = "blackhole_save.json"
    LEVEL_FILE = "custom_levels.json"

    def load_save():
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    d = json.load(f)
                base = _default_save()
                base.update(d)
                return base
            except Exception:
                pass
        return _default_save()

    def write_save(d):
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def level_save(bodies):
        try:
            with open(LEVEL_FILE, "w", encoding="utf-8") as f:
                json.dump(bodies, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def level_load():
        if os.path.exists(LEVEL_FILE):
            try:
                with open(LEVEL_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

# =========================================================
# 皮肤
# =========================================================
SKINS = [
    {"name": "经典", "inner": (0, 0, 0), "ring": (160, 100, 255),
     "halo": (150, 90, 255),
     "accretion": [(255, 170, 80), (255, 120, 160), (170, 110, 255)]},
    {"name": "星云", "inner": (12, 0, 30), "ring": (255, 120, 200),
     "halo": (200, 100, 255),
     "accretion": [(200, 100, 255), (100, 200, 255), (255, 150, 200)]},
    {"name": "电弧", "inner": (0, 10, 22), "ring": (100, 220, 255),
     "halo": (80, 200, 255),
     "accretion": [(100, 220, 255), (200, 255, 255), (150, 200, 255)]},
    {"name": "奇点", "inner": (255, 255, 255), "ring": (255, 255, 255),
     "halo": (200, 200, 255),
     "accretion": [(255, 255, 255), (200, 200, 255), (150, 150, 255)]},
]
def unlocked_skins(save):
    return 4 if save.get("core_level", 0) >= 20 else 3

# =========================================================
# 音效
# =========================================================
class Audio:
    def __init__(self):
        self.ok = AUDIO_OK
        self.enabled = True
        self.master_vol = 0.7
        self.sounds = {}
        if not self.ok:
            return
        try:
            self.sounds["eat"]   = self._tone(660, 0.08, "sine", 0.30)
            self.sounds["big"]   = self._tone(150, 0.30, "saw",  0.35)
            self.sounds["dead"]  = self._tone(80,  0.90, "saw",  0.45)
            self.sounds["level"] = self._tone(880, 0.35, "sine", 0.40)
            self.sounds["heart"] = self._tone(60,  0.10, "sine", 0.35)
            self.sounds["ach"]   = self._tone(1040, 0.25, "sine", 0.35)
            self.sounds["skill"] = self._tone(520, 0.18, "sine", 0.38)
            self.sounds["boss"]  = self._tone(200, 0.60, "saw",  0.50)
            self.sounds["ui"]    = self._tone(740, 0.06, "sine", 0.30)
            self.sounds["coin"]  = self._tone(1200, 0.12, "sine", 0.35)
            self.sounds["pow"]   = self._tone(980, 0.20, "sine", 0.40)
            self.sounds["boom"]  = self._tone(120, 0.50, "saw",  0.55)
            self.sounds["evolve"]= self._tone(660, 0.40, "sine", 0.45)
            self.sounds["nova"]  = self._tone(400, 0.80, "saw",  0.55)
        except Exception:
            self.ok = False

    def _tone(self, freq, dur, wave, vol, sr=22050):
        n = int(sr * dur)
        buf = array.array("h")
        for i in range(n):
            t = i / sr
            env = min(1.0, t * 50) * math.exp(-t * (3.0 / dur))
            if wave == "sine":
                v = math.sin(2 * math.pi * freq * t)
            elif wave == "saw":
                v = 2 * ((freq * t) % 1) - 1
            else:
                v = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0
            buf.append(int(clamp(v * env * vol, -1, 1) * 32767))
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, name, vol=1.0):
        if not self.ok or not self.enabled:
            return
        s = self.sounds.get(name)
        if s:
            s.set_volume(clamp(vol * self.master_vol, 0, 1))
            s.play()

audio = Audio()

# =========================================================
# 元成长
# =========================================================
def core_xp_needed(level):
    return 100 * level

def add_core_xp(save, amount, toasts=None):
    save["core_xp"] += amount
    while save["core_xp"] >= core_xp_needed(save["core_level"]):
        save["core_xp"] -= core_xp_needed(save["core_level"])
        save["core_level"] += 1
        if toasts is not None:
            toasts.append(Toast(f"🌌 黑洞核心等级 → {save['core_level']}", 3.5))
            audio.play("evolve", 0.8)
    write_save(save)

# =========================================================
# 成就
# =========================================================
ACHIEVEMENTS = {
    "first_blood": "初次吞噬",
    "mass_50":     "质量达到 50",
    "mass_100":    "质量达到 100",
    "mass_200":    "质量达到 200",
    "mass_400":    "质量达到 400",
    "mass_800":    "质量达到 800",
    "level_3":     "抵达第 3 关",
    "level_5":     "抵达第 5 关",
    "level_10":    "抵达第 10 关",
    "boss_kill":   "击杀 BOSS",
    "score_500":   "单局得分 500",
    "score_2000":  "单局得分 2000",
    "survive_60":  "存活 60 秒",
    "survive_180": "存活 180 秒",
    "use_skill":   "使用技能",
    "editor_save": "编辑器保存关卡",
    "evolve":      "进化一次",
    "powerup_3":   "一次使用 3 种道具",
    "combo_10":    "10 连噬",
    "collector":   "累计吃掉 200 个球",
    "bonus_clear": "完成一次奖励关",
}

class Toast:
    def __init__(self, text, life=3.0):
        self.text = text
        self.life = life
        self.max_life = life

def unlock(save, key, toasts):
    if key in save["unlocked"] or key not in ACHIEVEMENTS:
        return
    save["unlocked"].append(key)
    write_save(save)
    toasts.append(Toast("🏆 " + ACHIEVEMENTS[key], 3.2))
    audio.play("ach", 0.7)

# =========================================================
# 特殊球
# =========================================================
BODY_KINDS = {
    "normal":    {"weight": 60, "tint": None},
    "ice":       {"weight": 8,  "tint": (120, 200, 255)},
    "fire":      {"weight": 8,  "tint": (255, 130, 70)},
    "split":     {"weight": 6,  "tint": (190, 110, 255)},
    "gold":      {"weight": 6,  "tint": (255, 220, 80)},
    "bomb":      {"weight": 4,  "tint": (220, 60, 90)},
    "magnet":    {"weight": 4,  "tint": (180, 220, 255)},
    "invisible": {"weight": 4,  "tint": (110, 110, 130)},
}
KIND_LIST = list(BODY_KINDS.keys())
KIND_WEIGHTS = [BODY_KINDS[k]["weight"] for k in KIND_LIST]

def pick_kind(level):
    if level < 2:
        return "normal"
    p_special = clamp(0.08 + (level - 2) * 0.03, 0, 0.35)
    if random.random() > p_special:
        return "normal"
    return random.choices(KIND_LIST[1:], weights=KIND_WEIGHTS[1:], k=1)[0]

# =========================================================
# 道具
# =========================================================
POWERUPS = ["shield", "time", "bomb", "crystal"]
POWERUP_COLORS = {
    "shield":  (120, 220, 255),
    "time":    (200, 255, 180),
    "bomb":    (255, 140, 80),
    "crystal": (255, 220, 120),
}

# =========================================================
# 进化树
# =========================================================
EVOLUTIONS = [
    (3,  [("⚡ 疾行", "移动速度 +15%",     "speed"),
          ("🧲 引潮", "引力范围 +20%",     "grav")]),
    (6,  [("💥 掠食", "吞噬得分 ×1.5",   "score"),
          ("🛡 壁垒", "无敌时间 +1 秒",     "invuln")]),
    (9,  [("🌀 吸积", "大球靠近时缓慢掉质量", "accretion"),
          ("⭐ 复苏", "每关开始 +10 质量",   "revive")]),
    (12, [("👁 洞察", "显示所有大球轨迹",   "vision"),
          ("💨 瞬步", "冲刺冷却 -2 秒",     "dash")]),
    (15, [("🕳 深渊", "引力强度 +25%",    "grav_pow"),
          ("💰 贪婪", "金币球得分 ×3",     "greed")]),
]

def apply_evolution(hole_state, key):
    e = hole_state["evo"]
    if key == "speed":       e["speed"]     *= 1.15
    elif key == "grav":      e["grav_range"]*= 1.20
    elif key == "score":     e["score_mult"]*= 1.5
    elif key == "invuln":    e["invuln_bonus"] += 1.0
    elif key == "accretion": e["accretion"] = True
    elif key == "revive":    e["revive"]    = True
    elif key == "vision":    e["vision"]    = True
    elif key == "dash":      e["dash_cd_bonus"] += 2.0
    elif key == "grav_pow":  e["grav_power"]*= 1.25
    elif key == "greed":     e["greed"]     = True

def new_evo_state():
    return {
        "speed": 1.0, "grav_range": 1.0, "score_mult": 1.0,
        "invuln_bonus": 0.0, "accretion": False, "revive": False,
        "vision": False, "dash_cd_bonus": 0.0, "grav_power": 1.0,
        "greed": False,
    }

# =========================================================
# 模式
# =========================================================
GAME_MODES = {
    "classic":   {"name": "经典", "desc": "无尽吞噬"},
    "timed":     {"name": "限时", "desc": "3 分钟冲最高质量"},
    "survival":  {"name": "生存", "desc": "球越来越多"},
    "precision": {"name": "精准", "desc": "只吃指定颜色"},
    "chaos":     {"name": "混乱", "desc": "所有球都很快，事件频繁"},
}

# =========================================================
# 实体
# =========================================================
class Hole:
    def __init__(self, x, y, mass=22):
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.mass = float(mass)
        self.flash = 0.0

    @property
    def radius(self):
        return math.sqrt(self.mass) * 2.8

class Body:
    def __init__(self, x, y, mass, hunter=False, kind="normal", ai="chaser"):
        self.x, self.y = x, y
        self.mass = mass
        self.radius = math.sqrt(mass) * 2.6
        a, s = random.uniform(0, math.tau), random.uniform(5, 45)
        self.vx = math.cos(a) * s
        self.vy = math.sin(a) * s
        self.color = mass_color(mass)
        self.kind = kind
        self.ai = ai
        self.hunter = hunter
        self.is_boss = False
        self.invis_phase = random.uniform(0, math.tau)

    def update_ai(self, hole, dt, pack_count=0):
        if not self.hunter:
            return
        if not self.is_boss and self.mass <= hole.mass:
            self.hunter = False
            return
        dx, dy = hole.x - self.x, hole.y - self.y
        d = math.hypot(dx, dy)
        if d < 1 or d > 1200:
            return
        if self.ai == "flanker":
            ang = math.atan2(dy, dx) + 0.9
            tx = hole.x + math.cos(ang) * 220
            ty = hole.y + math.sin(ang) * 220
            dx, dy = tx - self.x, ty - self.y
            d = max(1, math.hypot(dx, dy))
        elif self.ai == "pack":
            boost = 1.0 + min(pack_count, 4) * 0.15
        elif self.ai == "disguise":
            if d > 260:
                return
        spd = 380 if self.is_boss else 340
        if self.ai == "pack":
            spd *= boost
        acc = spd * (1 - d / 1200)
        self.vx += dx / d * acc * dt
        self.vy += dy / d * acc * dt

class Boss(Body):
    def __init__(self, x, y, mass):
        super().__init__(x, y, mass, hunter=True, ai="chaser")
        self.is_boss = True

class Powerup:
    def __init__(self, x, y, kind):
        self.x, self.y = x, y
        self.kind = kind
        self.radius = 16
        self.life = 20.0
        self.phase = random.uniform(0, math.tau)

class Particle:
    def __init__(self, x, y, vx, vy, life, size, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.size = size
        self.color = color

class FloatText:
    def __init__(self, x, y, text, color, life=1.0):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = self.max_life = life
        self.vy = -50

class Comet:
    def __init__(self):
        self.x = random.uniform(0, W)
        self.y = random.uniform(0, H * 0.5)
        self.vx = random.uniform(180, 360)
        self.vy = random.uniform(80, 180)
        self.life = 3.0

# =========================================================
# 技能
# =========================================================
class Skill:
    def __init__(self, name, cooldown, duration, cost=0.0):
        self.name = name
        self.cd_max = cooldown
        self.dur_max = duration
        self.cost = cost
        self.cd_timer = 0.0
        self.active_timer = 0.0

    @property
    def ready(self): return self.cd_timer <= 0
    @property
    def active(self): return self.active_timer > 0
    @property
    def cd_ratio(self): return clamp(self.cd_timer / self.cd_max, 0, 1)

    def activate(self, hole):
        if not self.ready: return False
        if self.cost > 0 and hole.mass * (1 - self.cost) < 22: return False
        if self.cost > 0: hole.mass *= (1 - self.cost)
        self.cd_timer = self.cd_max
        self.active_timer = self.dur_max
        return True

    def update(self, dt):
        if self.cd_timer > 0: self.cd_timer = max(0, self.cd_timer - dt)
        if self.active_timer > 0: self.active_timer = max(0, self.active_timer - dt)

# =========================================================
# 背景
# =========================================================
STARS = [{
    "x": random.uniform(0, 5000),
    "y": random.uniform(0, 5000),
    "r": random.uniform(0.5, 2.0),
    "b": random.randint(70, 200),
    "p": random.choice([0.22, 0.42, 0.65])
} for _ in range(460)]

NEBULAS = [{
    "x": random.uniform(0, 5000),
    "y": random.uniform(0, 5000),
    "r": random.uniform(600, 1200),
    "c": random.choice([(80, 40, 140), (40, 80, 140),
                        (120, 40, 100), (40, 120, 100)]),
    "p": 0.35,
} for _ in range(6)]

# =========================================================
# 生成
# =========================================================
def spawn_body(hole, level_mult=1.0, hunter_chance=0.0, level=1, chaos=False):
    x = y = 0.0
    for _ in range(40):
        ang = random.uniform(0, math.tau)
        d = random.uniform(760, 1350)
        x, y = hole.x + math.cos(ang) * d, hole.y + math.sin(ang) * d
        if 90 < x < WORLD_W - 90 and 90 < y < WORLD_H - 90:
            break
    else:
        x = random.uniform(90, WORLD_W - 90)
        y = random.uniform(90, WORLD_H - 90)
    k = random.random() ** 2.2
    mass = max(3.0, hole.mass * (0.05 + k * 0.85) * level_mult)
    kind = pick_kind(level)
    hunter = random.random() < hunter_chance and mass > hole.mass * 1.15
    ai = "chaser"
    if hunter:
        ai = random.choices(["chaser", "flanker", "pack", "disguise"],
                            weights=[50, 20, 20, 10], k=1)[0]
    b = Body(x, y, mass, hunter, kind, ai)
    if chaos:
        b.vx *= 1.6; b.vy *= 1.6
    return b

def spawn_bonus_body(hole):
    x = y = 0.0
    for _ in range(40):
        ang = random.uniform(0, math.tau)
        d = random.uniform(500, 1000)
        x, y = hole.x + math.cos(ang) * d, hole.y + math.sin(ang) * d
        if 90 < x < WORLD_W - 90 and 90 < y < WORLD_H - 90:
            break
    else:
        x = random.uniform(90, WORLD_W - 90)
        y = random.uniform(90, WORLD_H - 90)
    mass = max(2.0, hole.mass * random.uniform(0.03, 0.12))
    return Body(x, y, mass, hunter=False, kind="gold", ai="chaser")

def spawn_powerup(hole):
    ang = random.uniform(0, math.tau)
    d = random.uniform(400, 1100)
    x = clamp(hole.x + math.cos(ang) * d, 80, WORLD_W - 80)
    y = clamp(hole.y + math.sin(ang) * d, 80, WORLD_H - 80)
    return Powerup(x, y, random.choice(POWERUPS))

def burst(particles, x, y, color, count, speed, base_vx=0, base_vy=0):
    bright = (min(255, color[0] * 1.25 + 55),
              min(255, color[1] * 1.25 + 55),
              min(255, color[2] * 1.25 + 55))
    for _ in range(count):
        a = random.uniform(0, math.tau)
        s = random.uniform(0.25, 1.0) * speed
        particles.append(Particle(
            x + random.uniform(-6, 6), y + random.uniform(-6, 6),
            math.cos(a) * s + base_vx * 0.3,
            math.sin(a) * s + base_vy * 0.3,
            random.uniform(0.35, 0.95),
            random.uniform(1.5, 4.2), bright))

# =========================================================
# 显示
# =========================================================
def apply_display(idx):
    global display_surf, current_display_idx
    if IS_WEB:
        display_surf = pygame.display.set_mode((W, H))
        current_display_idx = 0
        return
    current_display_idx = idx % len(DISPLAY_MODES)
    name, size, fs = DISPLAY_MODES[current_display_idx]
    if fs:
        info = pygame.display.Info()
        display_surf = pygame.display.set_mode(
            (info.current_w, info.current_h),
            pygame.FULLSCREEN | pygame.SCALED)
    else:
        try:
            display_surf = pygame.display.set_mode(
                size, pygame.SCALED | pygame.RESIZABLE)
        except Exception:
            display_surf = pygame.display.set_mode(size)

def screen_to_logical(pos):
    mx, my = pos
    sw, sh = display_surf.get_size()
    if sw == 0 or sh == 0: return 0, 0
    return int(mx * W / sw), int(my * H / sh)

_present_cache = {"surf": None, "size": None}

def present():
    sw, sh = display_surf.get_size()
    if (sw, sh) == (W, H):
        display_surf.blit(canvas, (0, 0))
    else:
        if _present_cache["size"] != (sw, sh):
            _present_cache["surf"] = pygame.Surface((sw, sh)).convert()
            _present_cache["size"] = (sw, sh)
        pygame.transform.smoothscale(canvas, (sw, sh), _present_cache["surf"])
        display_surf.blit(_present_cache["surf"], (0, 0))
    pygame.display.flip()

apply_display(0)

# =========================================================
# 帮助页内容
# =========================================================
HELP_SECTIONS = [
    ("🎮 基础操作", [
        ("移动",       "WASD / 方向键 / 左下摇杆"),
        ("冲刺",       "Space（6s CD）"),
        ("无敌",       "Q（25s CD，2 秒）"),
        ("引力爆发",   "E（22s CD，消耗 15% 质量）"),
        ("引力炸弹",   "F（拾取后可用）"),
        ("暂停",       "P"),
        ("帮助",       "F3"),
        ("选项菜单",   "ESC"),
        ("重开",       "R"),
        ("切皮肤",     "F1"),
        ("关卡编辑器", "F2"),
        ("加载关卡",   "L"),
    ]),
    ("🌀 特殊球（8 种）", [
        ("冰球",     "吃完 2 秒减速 50%"),
        ("火球",     "吃完 2 秒加速 80%"),
        ("分裂球",   "分裂成 3 个小球"),
        ("金币球",   "得分 ×5"),
        ("炸弹球",   "范围震开大球"),
        ("磁铁球",   "3 秒引力范围 ×3"),
        ("隐形球",   "周期性透明"),
        ("普通球",   "普通吞噬"),
    ]),
    ("💎 道具（4 种）", [
        ("护盾碎片", "集 3 个免费无敌"),
        ("时间胶囊", "慢动作 3 秒"),
        ("引力炸弹", "拾取后按 F 释放"),
        ("质量结晶", "直接 +20 质量"),
    ]),
    ("👾 敌人 AI（4 种）", [
        ("追踪者",   "橙圈，直线追你"),
        ("迂回者",   "粉圈，绕到前方拦截"),
        ("群猎",     "黄圈，多个一起加速"),
        ("伪装者",   "紫圈，靠近才暴露"),
        ("BOSS",     "金圈，每 5 关出现"),
    ]),
    ("🎯 游戏模式（5 种）", [
        ("经典",   "无尽吞噬"),
        ("限时",   "3 分钟冲最高质量"),
        ("生存",   "球越来越多"),
        ("精准",   "只吃指定颜色"),
        ("混乱",   "球速快，事件频繁"),
    ]),
    ("🌟 进化树（5 节点）", [
        ("3 关",  "疾行 / 引潮"),
        ("6 关",  "掠食 / 壁垒"),
        ("9 关",  "吸积 / 复苏"),
        ("12 关", "洞察 / 瞬步"),
        ("15 关", "深渊 / 贪婪"),
    ]),
    ("🌍 环境事件（4 种）", [
        ("流星雨",     "天上掉小球冲击"),
        ("引力反转",   "所有球被推开"),
        ("黑洞潮汐",   "球被挤向中心"),
        ("暗物质云",   "视野变暗"),
    ]),
    ("🌌 元成长", [
        ("核心等级",  "每局得分 → XP，永久累积"),
        ("初始质量",  "22 + (核心等级-1) × 1.5"),
        ("奇点皮肤",  "核心 20 级解锁"),
        ("奖励关",    "每 3 关触发，15 秒金币狂欢"),
    ]),
]

# =========================================================
# 选项菜单
# =========================================================
def option_layout():
    bw, bh = 460, 40
    x = (W - bw) // 2
    y = 90
    gap = 6
    return bw, bh, x, y, gap

def get_option_buttons(save):
    bw, bh, x, y, gap = option_layout()
    items = []
    name = DISPLAY_MODES[current_display_idx][0]
    items.append((pygame.Rect(x, y, bw, bh), f"显示模式：{name}", "cycle_display")); y += bh + gap
    items.append((pygame.Rect(x, y, bw, bh), f"音效：{'开' if audio.enabled else '关'}", "toggle_audio")); y += bh + gap
    items.append((pygame.Rect(x, y, bw, bh),
                  f"屏幕震动：{'关' if save.get('no_shake', False) else '开'}",
                  "toggle_shake")); y += bh + gap
    items.append((pygame.Rect(x, y, bw, bh),
                  f"色盲辅助：{'开' if save.get('colorblind', False) else '关'}",
                  "toggle_cb")); y += bh + gap
    items.append((pygame.Rect(x, y, bw, bh),
                  f"小地图：{'开' if save.get('show_minimap', True) else '关'}",
                  "toggle_map")); y += bh + gap
    items.append((pygame.Rect(x, y, bw, bh), "帮助 (F3)", "help")); y += bh + gap
    items.append((pygame.Rect(x, y, bw, bh), "返回主菜单", "menu")); y += bh + gap
    items.append((pygame.Rect(x, y, bw, bh), "继续游戏 (ESC)", "resume")); y += bh + gap
    items.append((pygame.Rect(x, y, bw, bh), "退出游戏", "quit"))
    return items

def volume_slider_rect():
    return pygame.Rect(W // 2 - 200, 500, 400, 8)

def draw_options_menu(save):
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 190)); screen.blit(ov, (0, 0))
    title = get_font(48, True).render("选 项", True, (235, 235, 255))
    screen.blit(title, (W // 2 - title.get_width() // 2, 24))

    mx, my = screen_to_logical(pygame.mouse.get_pos())
    for rect, label, action in get_option_buttons(save):
        hover = rect.collidepoint(mx, my)
        bg = (55, 55, 110) if hover else (30, 30, 60)
        border = (180, 200, 255) if hover else (120, 120, 200)
        pygame.draw.rect(screen, bg, rect, border_radius=8)
        pygame.draw.rect(screen, border, rect, 2, border_radius=8)
        txt = get_font(18, True).render(label, True,
                                        (255, 255, 255) if hover else (225, 225, 240))
        screen.blit(txt, (rect.x + (rect.w - txt.get_width()) // 2,
                          rect.y + (rect.h - txt.get_height()) // 2))

    slider = volume_slider_rect()
    label = get_font(16).render(
        f"音量 {int(audio.master_vol * 100)}%", True, (200, 210, 240))
    screen.blit(label, (slider.x, slider.y - 24))
    pygame.draw.rect(screen, (50, 50, 80), slider, border_radius=4)
    fill_w = int(slider.w * audio.master_vol)
    pygame.draw.rect(screen, (120, 200, 255),
                     (slider.x, slider.y, fill_w, slider.h), border_radius=4)
    knob_x = slider.x + fill_w
    pygame.draw.circle(screen, (220, 240, 255),
                       (knob_x, slider.y + slider.h // 2), 10)

# =========================================================
# 帮助页
# =========================================================
def help_back_rect():
    return pygame.Rect(W // 2 - 130, H - 80, 260, 44)

def draw_help_page(save):
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 235)); screen.blit(ov, (0, 0))

    title = get_font(44, True).render("帮 助 · 功 能 一 览", True, (235, 235, 255))
    screen.blit(title, (W // 2 - title.get_width() // 2, 18))

    stat = (f"核心 Lv.{save['core_level']}   "
            f"游玩 {save['stat_plays']} 次   "
            f"累计吞噬 {save['stat_eaten']}   "
            f"击杀 BOSS {save['stat_boss']}   "
            f"进化 {save['stat_evolve']}   "
            f"时长 {int(save['stat_time'] // 60)} 分钟")
    st = get_font(15).render(stat, True, (170, 190, 230))
    screen.blit(st, (W // 2 - st.get_width() // 2, 68))

    col_x = [20, W // 2 + 6]
    col_y = [100, 100]
    col_max_y = [H - 110, H - 110]

    f_h = get_font(20, True)
    f_b = get_font(15)

    for i, (head, items) in enumerate(HELP_SECTIONS):
        col = 0 if i < 4 else 1
        x = col_x[col]
        y = col_y[col]

        if y > col_max_y[col] - 40:
            continue

        h_surf = f_h.render(head, True, (255, 220, 140))
        screen.blit(h_surf, (x, y))
        y += 26

        for name, desc in items:
            n = f_b.render(f"· {name}", True, (200, 220, 255))
            d = f_b.render(desc, True, (150, 170, 210))
            screen.blit(n, (x, y))
            screen.blit(d, (x + 130, y))
            y += 20

        y += 8
        col_y[col] = y

    back = help_back_rect()
    mx, my = screen_to_logical(pygame.mouse.get_pos())
    hover = back.collidepoint(mx, my)
    bg = (60, 60, 110) if hover else (30, 30, 60)
    border = (180, 200, 255) if hover else (120, 120, 200)
    pygame.draw.rect(screen, bg, back, border_radius=10)
    pygame.draw.rect(screen, border, back, 2, border_radius=10)
    txt = get_font(20, True).render("返回选项菜单 (ESC)", True,
                                    (255, 255, 255) if hover else (225, 225, 240))
    screen.blit(txt, (back.x + (back.w - txt.get_width()) // 2,
                      back.y + (back.h - txt.get_height()) // 2))

# =========================================================
# 模式菜单
# =========================================================
def get_mode_buttons():
    bw, bh = 420, 62
    x = (W - bw) // 2
    y = 180
    gap = 12
    buttons = []
    for key, info in GAME_MODES.items():
        buttons.append((pygame.Rect(x, y, bw, bh), key, info))
        y += bh + gap
    return buttons

def draw_mode_menu(save):
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 210)); screen.blit(ov, (0, 0))
    title = get_font(48, True).render("选择游戏模式", True, (235, 235, 255))
    screen.blit(title, (W // 2 - title.get_width() // 2, 60))
    core = get_font(20).render(
        f"黑洞核心 Lv.{save['core_level']}  "
        f"(XP {int(save['core_xp'])}/{core_xp_needed(save['core_level'])})",
        True, (200, 180, 255))
    screen.blit(core, (W // 2 - core.get_width() // 2, 122))

    mx, my = screen_to_logical(pygame.mouse.get_pos())
    for r, key, info in get_mode_buttons():
        hover = r.collidepoint(mx, my)
        is_cur = save.get("mode", "classic") == key
        bg = (60, 60, 120) if hover else (30, 30, 60)
        if is_cur: bg = (40, 80, 60) if not hover else (60, 110, 80)
        border = (255, 220, 120) if is_cur else ((180, 200, 255) if hover else (120, 120, 200))
        pygame.draw.rect(screen, bg, r, border_radius=10)
        pygame.draw.rect(screen, border, r, 2, border_radius=10)
        n = get_font(22, True).render(info["name"], True, (245, 245, 255))
        d = get_font(15).render(info["desc"], True, (180, 190, 220))
        screen.blit(n, (r.x + 18, r.y + 10))
        screen.blit(d, (r.x + 18, r.y + 38))
        if is_cur:
            badge = get_font(14, True).render("当前", True, (255, 220, 120))
            screen.blit(badge, (r.x + r.w - 60, r.y + 20))
    hint = get_font(15).render("点击选择模式  ·  ESC 返回选项",
                               True, (150, 160, 200))
    screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 40))

# =========================================================
# 进化菜单
# =========================================================
_EVO_CURRENT = []

def get_evo_buttons():
    bw, bh = 380, 220
    gap = 60
    total = bw * 2 + gap
    x0 = (W - total) // 2
    y0 = 250
    return [(pygame.Rect(x0 + i * (bw + gap), y0, bw, bh), i, k)
            for i, (n, d, k) in enumerate(_EVO_CURRENT)]

def draw_evolution_menu(choices):
    global _EVO_CURRENT
    _EVO_CURRENT = choices
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 220)); screen.blit(ov, (0, 0))
    title = get_font(48, True).render("进 化", True, (255, 220, 120))
    screen.blit(title, (W // 2 - title.get_width() // 2, 100))
    sub = get_font(20).render("选择一种进化，永久生效",
                              True, (200, 200, 230))
    screen.blit(sub, (W // 2 - sub.get_width() // 2, 168))

    mx, my = screen_to_logical(pygame.mouse.get_pos())
    for r, i, key in get_evo_buttons():
        name, desc, _ = choices[i]
        hover = r.collidepoint(mx, my)
        bg = (60, 60, 120) if hover else (30, 30, 60)
        border = (255, 220, 120) if hover else (120, 120, 200)
        pygame.draw.rect(screen, bg, r, border_radius=14)
        pygame.draw.rect(screen, border, r, 3, border_radius=14)
        n = get_font(36, True).render(name, True, (255, 255, 255))
        screen.blit(n, (r.x + (r.w - n.get_width()) // 2, r.y + 50))
        d = get_font(20).render(desc, True, (200, 210, 240))
        screen.blit(d, (r.x + (r.w - d.get_width()) // 2, r.y + 130))
        kh = get_font(15).render(f"按 {i+1} 或点击", True, (150, 160, 200))
        screen.blit(kh, (r.x + (r.w - kh.get_width()) // 2, r.y + r.h - 30))

# =========================================================
# 关卡编辑器（async）
# =========================================================
async def run_editor(init_cam=(0, 0), save=None, toasts=None):
    if save is None: save = load_save()
    if toasts is None: toasts = []
    bodies = level_load()
    cam_x, cam_y = init_cam
    preset_mass = 30
    msg, msg_timer = "", 0.0
    def set_msg(t):
        nonlocal msg, msg_timer
        msg, msg_timer = t, 2.0

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "quit"
            if event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                if event.key in (pygame.K_F2, pygame.K_ESCAPE): return None
                elif event.key == pygame.K_1: preset_mass = 20; set_msg("小 20")
                elif event.key == pygame.K_2: preset_mass = 60; set_msg("中 60")
                elif event.key == pygame.K_3: preset_mass = 150; set_msg("大 150")
                elif event.key == pygame.K_c and not (mods & pygame.KMOD_CTRL):
                    bodies = []; set_msg("已清空")
                elif event.key == pygame.K_s and (mods & pygame.KMOD_CTRL):
                    ok = level_save(bodies)
                    set_msg(f"已保存 {len(bodies)} 个球体" if ok else "保存失败")
                    if ok: unlock(save, "editor_save", toasts)
                elif event.key == pygame.K_l and (mods & pygame.KMOD_CTRL):
                    bodies = level_load()
                    set_msg(f"已加载 {len(bodies)} 个球体" if bodies else "没有存档")
            if event.type == pygame.MOUSEBUTTONDOWN:
                lx, ly = screen_to_logical(event.pos)
                wx, wy = lx + cam_x, ly + cam_y
                if event.button == 1:
                    bodies.append({"x": wx, "y": wy, "mass": preset_mass})
                elif event.button == 3:
                    for i in range(len(bodies) - 1, -1, -1):
                        b = bodies[i]
                        dx, dy = b["x"] - wx, b["y"] - wy
                        r = math.sqrt(b["mass"]) * 2.6
                        if dx * dx + dy * dy < r * r:
                            bodies.pop(i); break

        keys = pygame.key.get_pressed()
        spd = 700 * dt
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  cam_x -= spd
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: cam_x += spd
        if keys[pygame.K_w] or keys[pygame.K_UP]:    cam_y -= spd
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  cam_y += spd
        cam_x = clamp(cam_x, -400, WORLD_W - W + 400)
        cam_y = clamp(cam_y, -400, WORLD_H - H + 400)
        if msg_timer > 0: msg_timer -= dt

        screen.fill((8, 8, 20))
        step = 100
        start_x = int(cam_x // step) * step
        start_y = int(cam_y // step) * step
        for gx in range(start_x, start_x + W + step, step):
            sx = gx - cam_x
            pygame.draw.line(screen, (30, 30, 60), (sx, 0), (sx, H))
        for gy in range(start_y, start_y + H + step, step):
            sy = gy - cam_y
            pygame.draw.line(screen, (30, 30, 60), (0, sy), (W, sy))
        pygame.draw.rect(screen, (90, 70, 180),
                         (int(-cam_x), int(-cam_y), WORLD_W, WORLD_H), 3)
        for b in bodies:
            sx, sy = b["x"] - cam_x, b["y"] - cam_y
            if -100 < sx < W + 100 and -100 < sy < H + 100:
                r = max(2, int(math.sqrt(b["mass"]) * 2.6))
                pygame.draw.circle(screen, mass_color(b["mass"]),
                                   (int(sx), int(sy)), r)
                pygame.draw.circle(screen, (255, 255, 255),
                                   (int(sx), int(sy)), r, 1)
        mx, my = screen_to_logical(pygame.mouse.get_pos())
        pygame.draw.circle(screen, (100, 255, 200), (mx, my),
                           int(math.sqrt(preset_mass) * 2.6), 2)
        panel = pygame.Surface((W, 90), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150)); screen.blit(panel, (0, 0))
        f_lg = get_font(22, True); f_md = get_font(16)
        screen.blit(f_lg.render(
            f"编辑器  预设 {preset_mass}  数量 {len(bodies)}",
            True, (200, 220, 255)), (20, 12))
        screen.blit(f_md.render(
            "左键放置 / 右键删除  ·  1/2/3 预设  ·  WASD 滚动  ·  "
            "Ctrl+S 保存  ·  Ctrl+L 加载  ·  C 清空  ·  F2/ESC 返回",
            True, (150, 170, 220)), (20, 50))
        if msg_timer > 0:
            surf = f_lg.render(msg, True, (255, 230, 140))
            surf.set_alpha(int(255 * clamp(msg_timer / 0.5, 0, 1)))
            screen.blit(surf, (20, H - 40))
        present()
        await asyncio.sleep(0)

# =========================================================
# 绘制
# =========================================================
def draw_nebula(cam_x, cam_y, cam_scale):
    for n in NEBULAS:
        sx = ((n["x"] - cam_x * n["p"]) * cam_scale % (W + n["r"] * 2)) - n["r"]
        sy = ((n["y"] - cam_y * n["p"]) * cam_scale % (H + n["r"] * 2)) - n["r"]
        for i in range(4):
            r = int(n["r"] * (0.4 + i * 0.18) * cam_scale)
            a = max(2, 18 - i * 4)
            if r < 4: continue
            gs = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*n["c"], a), (r, r), r)
            screen.blit(gs, (sx - r, sy - r))

def draw_comets(comets):
    for c in comets:
        alpha = clamp(c.life / 1.2, 0, 1)
        col = (int(255 * alpha), int(230 * alpha), int(255 * alpha))
        ex = c.x - c.vx * 0.12
        ey = c.y - c.vy * 0.12
        pygame.draw.line(screen, col, (ex, ey), (c.x, c.y), 2)
        pygame.draw.circle(screen, col, (int(c.x), int(c.y)), 2)

def draw_hole(hx, hy, hr, skin, t, flash, invuln_active, trail,
              cam_x, cam_y, cam_scale):
    for (tx_w, ty_w, life) in trail:
        a = life / 0.4
        if a <= 0: continue
        tx = (tx_w - cam_x) * cam_scale
        ty = (ty_w - cam_y) * cam_scale
        r = int(hr * (0.5 + a * 0.5))
        if r < 2: continue
        gs = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*skin["halo"], int(50 * a)), (r, r), r)
        screen.blit(gs, (tx - r, ty - r))
    for i in range(4, 0, -1):
        gr = int(hr * (1.5 + i * 0.5))
        if gr < 2: continue
        gs = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*skin["halo"], 26 // i), (gr, gr), gr)
        screen.blit(gs, (hx - gr, hy - gr))
    for i in range(3):
        rr = hr * (1.32 + i * 0.30)
        if rr < 3: continue
        a0 = t * (2.0 + i * 0.8) + i * 1.6
        rect = pygame.Rect(hx - rr, hy - rr, rr * 2, rr * 2)
        try:
            pygame.draw.arc(screen, skin["accretion"][i], rect,
                            a0, a0 + 1.8, max(1, 3 - i))
        except Exception:
            pass
    pygame.draw.circle(screen, skin["ring"], (int(hx), int(hy)), int(hr * 1.16), 2)
    pygame.draw.circle(screen, skin["inner"], (int(hx), int(hy)), int(hr))
    pygame.draw.circle(screen, skin["ring"], (int(hx), int(hy)), int(hr), 2)
    if invuln_active:
        pulse = 0.5 + 0.5 * math.sin(t * 14)
        pygame.draw.circle(screen, (120, 255, 200),
                           (int(hx), int(hy)), int(hr * (1.5 + 0.2 * pulse)), 3)
    if flash > 0:
        pygame.draw.circle(screen, (255, 240, 200),
                           (int(hx), int(hy)),
                           int(hr * (1.3 + (1 - flash) * 0.7)), 3)

def draw_body(b, sx, sy, r, state, hole, vision_on, colorblind,
              cam_x, cam_y, cam_scale):
    if b.kind == "invisible":
        b.invis_phase += 0.05
        a = 0.25 + 0.25 * math.sin(b.invis_phase)
        if a < 0.2 and state == "play":
            return
    glow = (b.color[0] // 3, b.color[1] // 3, b.color[2] // 3)
    pygame.draw.circle(screen, glow, (int(sx), int(sy)), int(r * 1.8))
    pygame.draw.circle(screen, b.color, (int(sx), int(sy)), r)
    hl = (min(255, b.color[0] + 80),
          min(255, b.color[1] + 80),
          min(255, b.color[2] + 80))
    pygame.draw.circle(screen, hl,
                       (int(sx - r * 0.3), int(sy - r * 0.3)),
                       max(1, int(r * 0.34)))

    if b.kind != "normal" and not b.is_boss:
        tint = BODY_KINDS[b.kind]["tint"]
        if tint:
            pygame.draw.circle(screen, tint, (int(sx), int(sy)), r, 2)
        if colorblind:
            kcx, kcy = int(sx), int(sy)
            kr = max(3, r // 3)
            white = (255, 255, 255)
            if b.kind == "ice":
                pygame.draw.line(screen, white, (kcx - kr, kcy), (kcx + kr, kcy), 2)
                pygame.draw.line(screen, white, (kcx, kcy - kr), (kcx, kcy + kr), 2)
            elif b.kind == "fire":
                pts = [(kcx, kcy - kr), (kcx - kr, kcy + kr), (kcx + kr, kcy + kr)]
                pygame.draw.polygon(screen, white, pts, 2)
            elif b.kind == "split":
                pygame.draw.line(screen, white, (kcx - kr, kcy - kr),
                                 (kcx - kr, kcy + kr), 2)
                pygame.draw.line(screen, white, (kcx + kr, kcy - kr),
                                 (kcx + kr, kcy + kr), 2)
            elif b.kind == "gold":
                pts = [(kcx, kcy - kr), (kcx + kr, kcy),
                       (kcx, kcy + kr), (kcx - kr, kcy)]
                pygame.draw.polygon(screen, white, pts, 2)
            elif b.kind == "bomb":
                pygame.draw.rect(screen, white,
                                 (kcx - kr, kcy - kr, kr * 2, kr * 2), 2)
            elif b.kind == "magnet":
                pygame.draw.circle(screen, white, (kcx, kcy), kr, 2)
            elif b.kind == "invisible":
                pygame.draw.circle(screen, white, (kcx, kcy), 2)

    if b.is_boss:
        pygame.draw.circle(screen, (255, 220, 100), (int(sx), int(sy)), r + 10, 3)
        pygame.draw.circle(screen, (255, 160, 60), (int(sx), int(sy)), r + 16, 2)
    elif b.hunter:
        col = {"chaser": (255, 150, 40), "flanker": (255, 80, 160),
               "pack": (255, 200, 40), "disguise": (180, 120, 220)}.get(
                   b.ai, (255, 150, 40))
        pygame.draw.circle(screen, col, (int(sx), int(sy)), r + 3, 2)
        if vision_on:
            dx = (hole.x - cam_x) * cam_scale - sx
            dy = (hole.y - cam_y) * cam_scale - sy
            d = math.hypot(dx, dy)
            if d > 1:
                tx = sx + dx / d * min(d, 160)
                ty = sy + dy / d * min(d, 160)
                pygame.draw.line(screen, col, (sx, sy), (tx, ty), 1)

    if state == "play" and b.mass > hole.mass and not b.is_boss:
        pygame.draw.circle(screen, (255, 70, 70), (int(sx), int(sy)), r + 6, 2)

def draw_minimap(hole, bodies, powerups, cam_x, cam_y, cam_scale):
    mm_w, mm_h = 200, 150
    mm_x = W - mm_w - 20
    mm_y = 20
    pad = 6

    surf = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
    surf.fill((10, 10, 25, 180))
    pygame.draw.rect(surf, (100, 120, 200, 200),
                     (0, 0, mm_w, mm_h), 2, border_radius=6)

    inner_w = mm_w - pad * 2
    inner_h = mm_h - pad * 2
    sx = inner_w / WORLD_W
    sy = inner_h / WORLD_H

    vx1 = cam_x * sx + pad
    vy1 = cam_y * sy + pad
    vw = (W / cam_scale) * sx
    vh = (H / cam_scale) * sy
    pygame.draw.rect(surf, (255, 255, 255, 60),
                     (vx1, vy1, vw, vh), 1)

    for b in bodies:
        bx = b.x * sx + pad
        by = b.y * sy + pad
        if b.is_boss:
            pygame.draw.circle(surf, (255, 200, 60), (int(bx), int(by)), 3)
        elif b.mass > hole.mass:
            pygame.draw.circle(surf, (255, 80, 80), (int(bx), int(by)), 2)
        elif b.hunter:
            pygame.draw.circle(surf, (255, 150, 40), (int(bx), int(by)), 2)
        else:
            pygame.draw.circle(surf, (120, 200, 120), (int(bx), int(by)), 1)

    for p in powerups:
        px = p.x * sx + pad
        py = p.y * sy + pad
        pygame.draw.circle(surf, POWERUP_COLORS[p.kind], (int(px), int(py)), 3)

    hx = hole.x * sx + pad
    hy = hole.y * sy + pad
    pygame.draw.circle(surf, (200, 130, 255), (int(hx), int(hy)), 4)
    pygame.draw.circle(surf, (255, 255, 255), (int(hx), int(hy)), 4, 1)

    screen.blit(surf, (mm_x, mm_y))
    return pygame.Rect(mm_x, mm_y, mm_w, mm_h)

# =========================================================
# 主游戏（async）
# =========================================================
async def run_game():
    save = load_save()
    if not IS_WEB and save["display_idx"] != current_display_idx:
        apply_display(save["display_idx"])
    audio.enabled = save["audio"]
    audio.master_vol = save.get("volume", 0.7)

    no_shake = save.get("no_shake", False)
    colorblind = save.get("colorblind", False)
    show_minimap = save.get("show_minimap", True)

    mode = save.get("mode", "classic")
    chaos = (mode == "chaos")
    timed = (mode == "timed")
    survival = (mode == "survival")
    precision = (mode == "precision")

    base_mass = 22 + (save["core_level"] - 1) * 1.5
    hole = Hole(WORLD_W * 0.5, WORLD_H * 0.5, base_mass)
    evo = new_evo_state()

    level = 1
    level_target = 70.0
    hunter_chance = 0.0
    level_mult = 1.0
    boss_spawned_for_level = 0

    bonus_active = False
    bonus_timer = 0.0
    bonus_score_start = 0.0

    bodies = [spawn_body(hole, level_mult, hunter_chance, level, chaos)
              for _ in range(BODY_COUNT)]
    particles = []
    float_texts = []
    toasts = []
    powerups = []
    comets = []

    cam_x = cam_y = 0.0
    cam_scale = 1.0
    shake = 0.0

    danger = 0.0
    score = 0.0
    time = 0.0
    spawn_timer = 0.0
    powerup_timer = 8.0
    heart_cd = 0.0
    state = "play"
    death_timer = 0.0
    saved_this_round = False
    level_up_cd = 0.0
    combo = 0
    combo_timer = 0.0
    total_eaten = 0

    buff_ice = 0.0
    buff_fire = 0.0
    buff_magnet = 0.0
    bomb_charges = 0
    shield_frags = 0
    time_slow = 0.0

    event_timer = 30.0 if not chaos else 15.0
    event_name = None
    event_dur = 0.0

    target_color = random.choice(["ice", "fire", "split", "gold", "magnet"])
    time_left = 180.0 if timed else None

    options_open = False
    mode_menu_open = False
    evo_menu_open = False
    evo_choices = []
    paused_manual = False
    tutorial_open = not save.get("seen_tutorial", False)
    help_open = False
    dragging_vol = False

    trail = []
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)

    JOY_CX, JOY_CY = 130, H - 130
    JOY_R_OUT = 80
    JOY_R_IN = 34
    joystick_active = False
    joystick_vec = (0.0, 0.0)

    BTN_PAUSE = pygame.Rect(W - 130, H - 60, 110, 40)
    BTN_MENU  = pygame.Rect(W - 260, H - 60, 110, 40)

    dash     = Skill("冲刺",     6.0, 0.20)
    invuln   = Skill("无敌",    25.0, 2.0)
    burst_sk = Skill("引力爆发", 22.0, 2.5, cost=0.15)
    skills = [dash, invuln, burst_sk]

    SKILL_KEYS = [
        ("Space", "冲刺",     dash),
        ("Q",     "无敌",     invuln),
        ("E",     "引力爆发", burst_sk),
    ]
    SKILL_BOX_W, SKILL_BOX_H = 118, 62
    SKILL_BOX_X0, SKILL_BOX_Y = 26, 230
    SKILL_GAP = 12

    def skill_box(i):
        return pygame.Rect(SKILL_BOX_X0 + i * (SKILL_BOX_W + SKILL_GAP),
                           SKILL_BOX_Y, SKILL_BOX_W, SKILL_BOX_H)

    def set_shake(amount):
        nonlocal shake
        if not no_shake:
            shake = max(shake, amount)

    def try_use_skill(sk):
        if state != "play" or options_open or evo_menu_open or \
           mode_menu_open or paused_manual or tutorial_open or help_open:
            return
        if not sk.activate(hole): return
        if sk is dash:
            toasts.append(Toast("⚡ 冲刺！", 1.0)); audio.play("skill", 0.7)
        elif sk is invuln:
            toasts.append(Toast("🛡 无敌！", 1.0)); audio.play("skill", 0.8)
        elif sk is burst_sk:
            toasts.append(Toast("💥 引力爆发！", 1.2)); audio.play("level", 0.7)
        unlock(save, "use_skill", toasts)

    while True:
        ticks = clock.tick(FPS)
        paused = (options_open or evo_menu_open or mode_menu_open or
                  paused_manual or tutorial_open or help_open)
        dt = 0.0 if paused else min(ticks / 1000.0, 0.05)
        time += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save["stat_time"] += time
                write_save(save)
                return "quit"

            if tutorial_open:
                if event.type == pygame.KEYDOWN or \
                   (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                    tutorial_open = False
                    save["seen_tutorial"] = True
                    write_save(save)
                    audio.play("ui", 0.5)
                continue

            if help_open:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F3:
                        help_open = False
                        audio.play("ui", 0.5)
                    elif event.key == pygame.K_ESCAPE:
                        help_open = False
                        options_open = True
                        audio.play("ui", 0.5)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    lx, ly = screen_to_logical(event.pos)
                    if help_back_rect().collidepoint(lx, ly):
                        help_open = False
                        options_open = True
                        audio.play("ui", 0.5)
                continue

            if options_open:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    options_open = False; audio.play("ui", 0.5); continue
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    lx, ly = screen_to_logical(event.pos)
                    slider = volume_slider_rect()
                    slider_hit = pygame.Rect(slider.x - 6, slider.y - 14,
                                             slider.w + 12, slider.h + 28)
                    if slider_hit.collidepoint(lx, ly):
                        dragging_vol = True
                        v = clamp((lx - slider.x) / slider.w, 0, 1)
                        audio.master_vol = v
                        save["volume"] = v
                        write_save(save)
                        continue
                    for rect, label, action in get_option_buttons(save):
                        if rect.collidepoint(lx, ly):
                            audio.play("ui", 0.5)
                            if action == "cycle_display":
                                if not IS_WEB:
                                    apply_display(current_display_idx + 1)
                                    save["display_idx"] = current_display_idx
                                    write_save(save)
                            elif action == "toggle_audio":
                                audio.enabled = not audio.enabled
                                save["audio"] = audio.enabled
                                write_save(save)
                            elif action == "toggle_shake":
                                save["no_shake"] = not save.get("no_shake", False)
                                no_shake = save["no_shake"]
                                write_save(save)
                            elif action == "toggle_cb":
                                save["colorblind"] = not save.get("colorblind", False)
                                colorblind = save["colorblind"]
                                write_save(save)
                            elif action == "toggle_map":
                                save["show_minimap"] = not save.get("show_minimap", True)
                                show_minimap = save["show_minimap"]
                                write_save(save)
                            elif action == "help":
                                help_open = True; options_open = False
                            elif action == "menu":
                                mode_menu_open = True; options_open = False
                            elif action == "resume":
                                options_open = False
                            elif action == "quit":
                                save["stat_time"] += time
                                write_save(save)
                                return "quit"
                            break
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    dragging_vol = False
                continue

            if mode_menu_open:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    mode_menu_open = False; continue
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    lx, ly = screen_to_logical(event.pos)
                    for r, key, info in get_mode_buttons():
                        if r.collidepoint(lx, ly):
                            save["mode"] = key
                            write_save(save)
                            audio.play("ui", 0.6)
                            return "restart"
                continue

            if evo_menu_open:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_1, pygame.K_KP1) and len(evo_choices) > 0:
                        apply_evolution({"evo": evo}, evo_choices[0][2])
                        evo_menu_open = False; audio.play("evolve", 0.8)
                        toasts.append(Toast(f"✨ 进化：{evo_choices[0][0]}", 2.5))
                        save["stat_evolve"] += 1
                        unlock(save, "evolve", toasts)
                    elif event.key in (pygame.K_2, pygame.K_KP2) and len(evo_choices) > 1:
                        apply_evolution({"evo": evo}, evo_choices[1][2])
                        evo_menu_open = False; audio.play("evolve", 0.8)
                        toasts.append(Toast(f"✨ 进化：{evo_choices[1][0]}", 2.5))
                        save["stat_evolve"] += 1
                        unlock(save, "evolve", toasts)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    lx, ly = screen_to_logical(event.pos)
                    for r, i, key in get_evo_buttons():
                        if r.collidepoint(lx, ly):
                            apply_evolution({"evo": evo}, key)
                            evo_menu_open = False; audio.play("evolve", 0.8)
                            toasts.append(Toast(f"✨ 进化：{evo_choices[i][0]}", 2.5))
                            save["stat_evolve"] += 1
                            unlock(save, "evolve", toasts)
                            break
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    options_open = True; audio.play("ui", 0.5); continue
                if event.key == pygame.K_F3:
                    help_open = True; audio.play("ui", 0.5); continue
                if event.key == pygame.K_p:
                    paused_manual = not paused_manual
                    audio.play("ui", 0.5); continue
                if event.key == pygame.K_F2:
                    return "editor"
                if state == "dead" and event.key == pygame.K_r:
                    return "restart"
                if state == "play":
                    if event.key == pygame.K_SPACE: try_use_skill(dash)
                    elif event.key == pygame.K_q:   try_use_skill(invuln)
                    elif event.key == pygame.K_e:   try_use_skill(burst_sk)
                    elif event.key == pygame.K_f and bomb_charges > 0:
                        bomb_charges -= 1
                        audio.play("boom", 0.9)
                        set_shake(28)
                        burst(particles, hole.x, hole.y,
                              (255, 180, 80), 140, 700)
                        for b in bodies:
                            dx, dy = b.x - hole.x, b.y - hole.y
                            d = max(1, math.hypot(dx, dy))
                            if d < 900:
                                force = 1200 * (1 - d / 900)
                                b.vx += dx / d * force
                                b.vy += dy / d * force
                        toasts.append(Toast("💣 引力炸弹！", 1.5))
                    elif event.key == pygame.K_F1:
                        n = unlocked_skins(save)
                        save["skin"] = (save["skin"] + 1) % n
                        write_save(save)
                        toasts.append(Toast(
                            f"皮肤：{SKINS[save['skin']]['name']}", 1.5))
                    elif event.key == pygame.K_l:
                        data = level_load()
                        if data:
                            bodies = [Body(d["x"], d["y"], d["mass"])
                                      for d in data]
                            toasts.append(Toast(
                                f"已加载关卡：{len(bodies)} 球", 2.5))
                            audio.play("level", 0.7)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = screen_to_logical(event.pos)

                if state == "play":
                    if BTN_PAUSE.collidepoint(mx, my):
                        paused_manual = not paused_manual
                        audio.play("ui", 0.5)
                        continue
                    if BTN_MENU.collidepoint(mx, my):
                        options_open = True
                        audio.play("ui", 0.5)
                        continue

                    hit_skill = False
                    for i, (k, name, sk) in enumerate(SKILL_KEYS):
                        if skill_box(i).collidepoint(mx, my):
                            try_use_skill(sk)
                            hit_skill = True
                            break

                    if not hit_skill and not paused:
                        dx = mx - JOY_CX
                        dy = my - JOY_CY
                        if dx * dx + dy * dy < JOY_R_OUT * JOY_R_OUT:
                            joystick_active = True
                            jd = max(1, math.hypot(dx, dy))
                            mag = min(jd, JOY_R_OUT) / JOY_R_OUT
                            joystick_vec = (dx / jd * mag, dy / jd * mag)

                elif state == "dead" and death_timer > 0.45:
                    bw2, bh2 = 220, 56
                    r1 = pygame.Rect(W//2 - bw2 - 20, H//2 + 180, bw2, bh2)
                    r2 = pygame.Rect(W//2 + 20, H//2 + 180, bw2, bh2)
                    if r1.collidepoint(mx, my):
                        return "restart"
                    if r2.collidepoint(mx, my):
                        save["mode"] = next_mode(save.get("mode", "classic"))
                        write_save(save)
                        return "restart"

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if joystick_active:
                    joystick_active = False
                    joystick_vec = (0.0, 0.0)

        if dragging_vol:
            lx, ly = screen_to_logical(pygame.mouse.get_pos())
            slider = volume_slider_rect()
            v = clamp((lx - slider.x) / slider.w, 0, 1)
            audio.master_vol = v
            save["volume"] = v
            write_save(save)

        if joystick_active and state == "play":
            lx, ly = screen_to_logical(pygame.mouse.get_pos())
            jx = lx - JOY_CX
            jy = ly - JOY_CY
            jd = math.hypot(jx, jy)
            if jd > 1:
                mag = min(jd, JOY_R_OUT) / JOY_R_OUT
                joystick_vec = (jx / jd * mag, jy / jd * mag)
            else:
                joystick_vec = (0.0, 0.0)

        for s in skills: s.update(dt)

        if bonus_active:
            bonus_timer -= dt
            if bonus_timer <= 0:
                bonus_active = False
                earned = int(score - bonus_score_start)
                toasts.append(Toast(f"💰 奖励关结束！本轮 +{earned}", 3.0))
                audio.play("ach", 1.0)
                hole.mass += BONUS_END_MASS
                toasts.append(Toast(f"🎁 额外 +{int(BONUS_END_MASS)} 质量", 2.0))
                unlock(save, "bonus_clear", toasts)

        if level_up_cd > 0: level_up_cd -= dt
        if combo_timer > 0:
            combo_timer -= dt
            if combo_timer <= 0: combo = 0
        if buff_ice > 0: buff_ice -= dt
        if buff_fire > 0: buff_fire -= dt
        if buff_magnet > 0: buff_magnet -= dt
        if time_slow > 0: time_slow -= dt

        if state == "play" and not paused:
            event_timer -= dt
            if event_timer <= 0 and event_name is None:
                event_timer = 30.0 if not chaos else 15.0
                event_name = random.choice(["meteor", "reverse", "tide", "dark"])
                event_dur = random.uniform(5.0, 8.0)
                audio.play("evolve", 0.6)
                toasts.append(Toast({
                    "meteor":  "☄ 流星雨降临",
                    "reverse": "🔄 引力反转",
                    "tide":    "🌊 黑洞潮汐",
                    "dark":    "🌑 暗物质云",
                }[event_name], 3.0))
            if event_name is not None:
                event_dur -= dt
                if event_dur <= 0:
                    event_name = None

        reverse = (event_name == "reverse")
        dark = (event_name == "dark")
        keys = pygame.key.get_pressed()

        if state == "play" and not paused:
            kdx = kdy = 0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:  kdx -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]: kdx += 1
            if keys[pygame.K_w] or keys[pygame.K_UP]:    kdy -= 1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:  kdy += 1

            jx, jy = joystick_vec
            if abs(jx) > 0.08 or abs(jy) > 0.08:
                dx, dy = jx, jy
            else:
                dx, dy = kdx, kdy

            tvx = tvy = 0.0
            if dx or dy:
                L = math.hypot(dx, dy)
                max_spd = 430 * (22 / hole.mass) ** 0.18 * evo["speed"]
                if dash.active: max_spd *= 2.6
                if buff_ice > 0: max_spd *= 0.5
                if buff_fire > 0: max_spd *= 1.8
                if time_slow > 0: max_spd *= 0.6
                strength = min(1.0, L)
                tvx = dx / L * max_spd * strength
                tvy = dy / L * max_spd * strength

            k = min(1.0, 12 * dt)
            hole.vx += (tvx - hole.vx) * k
            hole.vy += (tvy - hole.vy) * k
            hole.x += hole.vx * dt
            hole.y += hole.vy * dt

            hr = hole.radius
            hole.x = clamp(hole.x, hr, WORLD_W - hr)
            hole.y = clamp(hole.y, hr, WORLD_H - hr)
            trail.append((hole.x, hole.y, 0.4))

        trail = [(x, y, l - dt) for (x, y, l) in trail if l - dt > 0]
        if len(trail) > 24: trail = trail[-24:]

        g_range = G_RANGE * evo["grav_range"]
        g_power = evo["grav_power"]
        if burst_sk.active:
            g_range *= 1.8; g_power *= 1.5
        if buff_magnet > 0: g_range *= 3.0
        if reverse: g_range = 0

        if not paused:
            pack_count = sum(1 for b in bodies if b.hunter and b.ai == "pack")
            survivors = []
            for b in bodies:
                b.update_ai(hole, dt, pack_count)
                if reverse:
                    dx, dy = b.x - hole.x, b.y - hole.y
                    d = max(1, math.hypot(dx, dy))
                    if d < 900:
                        f = 500 * (1 - d / 900)
                        b.vx += dx / d * f * dt
                        b.vy += dy / d * f * dt
                else:
                    dx, dy = hole.x - b.x, hole.y - b.y
                    dist = max(math.hypot(dx, dy), 1e-4)
                    if dist < g_range:
                        infl = 1 - dist / g_range
                        acc = 1700 * (infl ** 1.6) * (1 + hole.mass / 150) * g_power
                        b.vx += dx / dist * acc * dt
                        b.vy += dy / dist * acc * dt

                if event_name == "meteor" and random.random() < 0.01:
                    b.vx += random.uniform(-200, 200)
                    b.vy += random.uniform(-200, 200)

                b.vx *= (1 - 0.35 * dt)
                b.vy *= (1 - 0.35 * dt)
                b.x += b.vx * dt
                b.y += b.vy * dt

                if event_name == "tide":
                    cx, cy = WORLD_W / 2, WORLD_H / 2
                    dxc, dyc = cx - b.x, cy - b.y
                    dc = max(1, math.hypot(dxc, dyc))
                    b.vx += dxc / dc * 120 * dt
                    b.vy += dyc / dc * 120 * dt

                m = b.radius
                if b.x < m: b.x, b.vx = m, abs(b.vx) * 0.6
                elif b.x > WORLD_W - m: b.x, b.vx = WORLD_W - m, -abs(b.vx) * 0.6
                if b.y < m: b.y, b.vy = m, abs(b.vy) * 0.6
                elif b.y > WORLD_H - m: b.y, b.vy = WORLD_H - m, -abs(b.vy) * 0.6

                dx, dy = hole.x - b.x, hole.y - b.y
                dist = max(math.hypot(dx, dy), 1e-4)

                if evo["accretion"] and b.mass > hole.mass:
                    if dist < hole.radius * 4:
                        b.mass = max(3, b.mass - 2 * dt)
                        b.radius = math.sqrt(b.mass) * 2.6

                if state == "play" and dist < hole.radius + b.radius * 0.35:
                    if precision and b.kind != target_color and b.kind != "normal":
                        if invuln.active:
                            survivors.append(b); continue
                        state = "dead"
                        audio.play("dead", 0.8)
                        break

                    if b.mass <= hole.mass * 1.02:
                        eat_mult = 0.5 if burst_sk.active else 1.0
                        gain = b.mass * 0.7 * eat_mult
                        hole.mass += gain
                        total_eaten += 1
                        save["stat_eaten"] += 1
                        combo += 1; combo_timer = 2.0
                        if combo >= 10 and combo % 10 == 0:
                            unlock(save, "combo_10", toasts)

                        smult = evo["score_mult"]
                        if b.kind == "gold":
                            smult *= (3 if evo["greed"] else 5)
                        if bonus_active:
                            smult *= BONUS_SCORE_MULT
                        score += b.mass * smult

                        if total_eaten >= 200:
                            unlock(save, "collector", toasts)

                        dy_off = -b.radius - 12
                        float_texts.append(FloatText(
                            b.x, b.y + dy_off, f"+{int(gain)}",
                            (200, 255, 200), 0.9))
                        if b.kind == "gold":
                            txt_mul = 5 * (BONUS_SCORE_MULT if bonus_active else 1)
                            float_texts.append(FloatText(
                                b.x, b.y + dy_off - 18,
                                f"💰 ×{txt_mul:.1f}".rstrip("0").rstrip("."),
                                (255, 220, 80), 1.2))
                        if combo >= 3 and combo % 3 == 0:
                            float_texts.append(FloatText(
                                b.x, b.y + dy_off - 36, f"×{combo} 连噬!",
                                (255, 200, 100), 1.2))

                        hole.flash = 1.0
                        set_shake(2 + b.radius * 0.4)
                        burst(particles, b.x, b.y, b.color,
                              min(70, int(5 + b.radius * 0.9)),
                              280, b.vx, b.vy)

                        if b.kind == "ice":
                            buff_ice = 2.0; toasts.append(Toast("❄ 减速", 1.0))
                        elif b.kind == "fire":
                            buff_fire = 2.0; toasts.append(Toast("🔥 加速", 1.0))
                        elif b.kind == "magnet":
                            buff_magnet = 3.0; toasts.append(Toast("🧲 磁力", 1.2))
                        elif b.kind == "split":
                            for _ in range(3):
                                a = random.uniform(0, math.tau)
                                d = random.uniform(60, 140)
                                fb = Body(b.x + math.cos(a) * d,
                                          b.y + math.sin(a) * d,
                                          b.mass * 0.3)
                                fb.vx = math.cos(a) * 200
                                fb.vy = math.sin(a) * 200
                                survivors.append(fb)
                        elif b.kind == "bomb":
                            audio.play("boom", 0.7); set_shake(26)
                            for other in bodies:
                                if other is b: continue
                                ddx, ddy = other.x - b.x, other.y - b.y
                                dd = max(1, math.hypot(ddx, ddy))
                                if dd < 500:
                                    f = 1000 * (1 - dd / 500)
                                    other.vx += ddx / dd * f
                                    other.vy += ddy / dd * f
                        elif b.kind == "gold":
                            audio.play("coin", 0.5)

                        if b.radius > 26:
                            audio.play("big", 0.5)
                        else:
                            audio.play("eat", 0.35)
                        unlock(save, "first_blood", toasts)

                        if b.is_boss:
                            audio.play("nova", 1.0)
                            save["stat_boss"] += 1
                            frag_mass = b.mass / 5.0
                            for i in range(4):
                                ang = random.uniform(0, math.tau)
                                d = random.uniform(100, 220)
                                frag = Body(b.x + math.cos(ang) * d,
                                            b.y + math.sin(ang) * d,
                                            frag_mass, hunter=True)
                                frag.vx = math.cos(ang) * 220
                                frag.vy = math.sin(ang) * 220
                                survivors.append(frag)
                            toasts.append(Toast("💥 BOSS 分裂！", 2.2))
                            set_shake(22)
                            burst(particles, b.x, b.y, (255, 220, 100), 120, 520)
                            unlock(save, "boss_kill", toasts)
                        continue
                    elif invuln.active:
                        survivors.append(b); continue
                    else:
                        state = "dead"
                        death_timer = 0.0
                        set_shake(24)
                        audio.play("dead", 0.8)
                        burst(particles, hole.x, hole.y,
                              (255, 120, 90), 130, 480)
                        continue
                survivors.append(b)
            bodies = survivors

            alive_pw = []
            for p in powerups:
                p.life -= dt; p.phase += dt * 3
                if p.life <= 0: continue
                dx, dy = hole.x - p.x, hole.y - p.y
                d = math.hypot(dx, dy)
                if d < hole.radius + p.radius:
                    audio.play("pow", 0.7)
                    if p.kind == "shield":
                        shield_frags += 1
                        if shield_frags >= 3:
                            shield_frags = 0
                            invuln.cd_timer = 0
                            invuln.active_timer = 3.0
                            toasts.append(Toast("🛡 护盾激活！", 2.0))
                    elif p.kind == "time":
                        time_slow = 3.0
                        toasts.append(Toast("⏳ 时间减缓！", 2.0))
                    elif p.kind == "bomb":
                        bomb_charges += 1
                        toasts.append(Toast("💣 获得炸弹 (按 F)", 2.0))
                    elif p.kind == "crystal":
                        hole.mass += 20
                        toasts.append(Toast("💎 +20 质量", 1.5))
                    continue
                alive_pw.append(p)
            powerups = alive_pw

            powerup_timer -= dt
            if powerup_timer <= 0 and len(powerups) < 3:
                powerup_timer = random.uniform(10, 18)
                powerups.append(spawn_powerup(hole))

            if state == "play" and level_up_cd <= 0 and hole.mass >= level_target:
                level += 1
                level_target *= 1.9
                level_up_cd = 0.8
                hunter_chance = min(0.06 * (level - 1), 0.30)
                level_mult = 1.0 + (level - 1) * 0.18
                set_shake(10)
                audio.play("level", 0.75)
                toasts.append(Toast(f"★ 第 {level} 关", 2.5))
                burst(particles, hole.x, hole.y, (255, 220, 120), 90, 420)
                if evo["revive"]:
                    hole.mass += 10
                    toasts.append(Toast("⭐ 复苏 +10", 1.5))
                if level >= 3:  unlock(save, "level_3", toasts)
                if level >= 5:  unlock(save, "level_5", toasts)
                if level >= 10: unlock(save, "level_10", toasts)

                if level % BONUS_INTERVAL == 0 and not bonus_active:
                    bonus_active = True
                    bonus_timer = BONUS_DURATION
                    bonus_score_start = score
                    toasts.append(Toast("🎉 奖励关！全是金币球！", 3.0))
                    audio.play("level", 1.0)
                    set_shake(8)
                    bodies = [b for b in bodies if b.mass <= hole.mass]

                for threshold, choices in EVOLUTIONS:
                    if level == threshold:
                        evo_choices = choices
                        evo_menu_open = True
                        break

            if state == "play" and not bonus_active:
                boss_exists = any(b.is_boss for b in bodies)
                if level % 5 == 0 and not boss_exists \
                        and boss_spawned_for_level < level:
                    boss_spawned_for_level = level
                    boss_mass = hole.mass * 2.6
                    ang = random.uniform(0, math.tau)
                    bx = clamp(hole.x + math.cos(ang) * 900, 200, WORLD_W - 200)
                    by = clamp(hole.y + math.sin(ang) * 900, 200, WORLD_H - 200)
                    bodies.append(Boss(bx, by, boss_mass))
                    toasts.append(Toast(f"⚠ BOSS 出现！质量 {int(boss_mass)}", 3.2))
                    set_shake(20)
                    audio.play("boss", 1.0)

            if state == "play":
                if bonus_active:
                    if len(bodies) < 35:
                        spawn_timer += dt
                        if spawn_timer > 0.05:
                            spawn_timer = 0
                            bodies.append(spawn_bonus_body(hole))
                    else:
                        spawn_timer = 0
                else:
                    target_count = BODY_COUNT
                    if survival:
                        target_count = min(120, BODY_COUNT + int(time / 6))
                    if len(bodies) < target_count:
                        spawn_timer += dt
                        rate = 0.06 if survival else 0.12
                        if spawn_timer > rate:
                            spawn_timer = 0
                            bodies.append(spawn_body(hole, level_mult,
                                                     hunter_chance, level, chaos))
                    else:
                        spawn_timer = 0

            alive = []
            for p in particles:
                p.life -= dt
                if p.life <= 0: continue
                p.x += p.vx * dt; p.y += p.vy * dt
                p.vx *= (1 - 1.8 * dt); p.vy *= (1 - 1.8 * dt)
                alive.append(p)
            particles = alive

            alive_ft = []
            for ft in float_texts:
                ft.life -= dt
                if ft.life <= 0: continue
                ft.y += ft.vy * dt
                ft.vy *= (1 - 1.5 * dt)
                alive_ft.append(ft)
            float_texts = alive_ft

            if random.random() < 0.004 and len(comets) < 3:
                comets.append(Comet())
            for c in comets:
                c.x += c.vx * dt; c.y += c.vy * dt; c.life -= dt
            comets = [c for c in comets if c.life > 0 and c.x < W + 200 and c.y < H + 200]

            danger = 0.0
            if state == "play":
                for b in bodies:
                    if b.mass > hole.mass:
                        d = math.hypot(b.x - hole.x, b.y - hole.y)
                        if d < 520:
                            danger = max(danger, 1 - d / 520)
            if state == "play" and danger > 0.45:
                heart_cd -= dt
                if heart_cd <= 0:
                    audio.play("heart", 0.25 + danger * 0.35)
                    heart_cd = 0.55
            else:
                heart_cd = 0.0

            if state == "play":
                if hole.mass >= 50:  unlock(save, "mass_50", toasts)
                if hole.mass >= 100: unlock(save, "mass_100", toasts)
                if hole.mass >= 200: unlock(save, "mass_200", toasts)
                if hole.mass >= 400: unlock(save, "mass_400", toasts)
                if hole.mass >= 800: unlock(save, "mass_800", toasts)
                if score >= 500:     unlock(save, "score_500", toasts)
                if score >= 2000:    unlock(save, "score_2000", toasts)
                if time >= 60:       unlock(save, "survive_60", toasts)
                if time >= 180:      unlock(save, "survive_180", toasts)

            if timed:
                time_left -= dt
                if time_left <= 0:
                    state = "dead"; death_timer = 0.0
                    audio.play("dead", 0.9)

            if state == "dead":
                death_timer += dt
                if not saved_this_round:
                    saved_this_round = True
                    save["best_mass"] = max(save["best_mass"], hole.mass)
                    save["best_score"] = max(save["best_score"], score)
                    save["stat_plays"] += 1
                    save["stat_time"] += time
                    add_core_xp(save, score / 10.0, toasts)
                    write_save(save)

            toasts = [t for t in toasts if t.life > 0]
            for t in toasts:
                t.life -= dt

        # 相机
        if hole.mass <= ZOOM_START_MASS:
            z_target = 1.0
        elif hole.mass >= ZOOM_END_MASS:
            z_target = ZOOM_MIN_SCALE
        else:
            t = (hole.mass - ZOOM_START_MASS) / (ZOOM_END_MASS - ZOOM_START_MASS)
            z_target = 1.0 - (1.0 - ZOOM_MIN_SCALE) * t
        cam_scale += (z_target - cam_scale) * min(1.0, 2.0 * dt)

        view_w = min(W / cam_scale, WORLD_W)
        view_h = min(H / cam_scale, WORLD_H)
        cam_cx = clamp(hole.x, view_w * 0.5, WORLD_W - view_w * 0.5)
        cam_cy = clamp(hole.y, view_h * 0.5, WORLD_H - view_h * 0.5)
        cam_x = cam_cx - view_w * 0.5
        cam_y = cam_cy - view_h * 0.5

        if shake > 0.2:
            cam_x += random.uniform(-shake, shake) / cam_scale
            cam_y += random.uniform(-shake, shake) / cam_scale
            shake = max(0, shake - 30 * dt)
        else:
            shake = 0.0
        if hole.flash > 0:
            hole.flash = max(0, hole.flash - dt * 3)

        # 渲染
        screen.fill((5, 5, 15))
        draw_nebula(cam_x, cam_y, cam_scale)

        for s in STARS:
            x = (s["x"] - cam_x * s["p"]) * cam_scale % W
            y = (s["y"] - cam_y * s["p"]) * cam_scale % H
            b = s["b"]
            pygame.draw.circle(screen, (b, b, min(255, b + 55)),
                               (int(x), int(y)), max(1, int(s["r"] * cam_scale)))

        if dark:
            ds = pygame.Surface((W, H), pygame.SRCALPHA)
            ds.fill((0, 0, 0, 180))
            hx_l = int((hole.x - cam_x) * cam_scale)
            hy_l = int((hole.y - cam_y) * cam_scale)
            pygame.draw.circle(ds, (0, 0, 0, 0), (hx_l, hy_l),
                               int(hole.radius * cam_scale * 6))
            screen.blit(ds, (0, 0))

        if bonus_active:
            warm = pygame.Surface((W, H), pygame.SRCALPHA)
            warm.fill((255, 200, 60, 18))
            screen.blit(warm, (0, 0))

        pygame.draw.rect(screen, (90, 70, 180),
                         (int(-cam_x * cam_scale), int(-cam_y * cam_scale),
                          int(WORLD_W * cam_scale),
                          int(WORLD_H * cam_scale)), 4)

        if event_name == "tide":
            cx_l = (WORLD_W / 2 - cam_x) * cam_scale
            cy_l = (WORLD_H / 2 - cam_y) * cam_scale
            for i in range(3):
                r = int((200 + i * 80 + math.sin(time * 2 + i) * 30) * cam_scale)
                if r < 4: continue
                pygame.draw.circle(screen, (100, 180, 255),
                                   (int(cx_l), int(cy_l)), r, 2)

        draw_comets(comets)

        if state == "play":
            for b in bodies:
                dx = hole.x - b.x
                dy = hole.y - b.y
                dist = math.hypot(dx, dy)
                if dist < g_range * 0.8 and dist > 1:
                    sx = (b.x - cam_x) * cam_scale
                    sy = (b.y - cam_y) * cam_scale
                    if sx < -100 or sx > W + 100 or sy < -100 or sy > H + 100:
                        continue
                    a = (1 - dist / (g_range * 0.8)) * 60
                    tx = (hole.x - cam_x) * cam_scale
                    ty = (hole.y - cam_y) * cam_scale
                    pygame.draw.line(screen, (140, 90, 255, int(a)),
                                     (sx, sy),
                                     (sx + (tx - sx) * 0.25,
                                      sy + (ty - sy) * 0.25), 1)

        for b in bodies:
            sx = (b.x - cam_x) * cam_scale
            sy = (b.y - cam_y) * cam_scale
            if sx < -150 or sx > W + 150 or sy < -150 or sy > H + 150:
                continue
            r = max(1, int(b.radius * cam_scale))
            draw_body(b, sx, sy, r, state, hole, evo["vision"], colorblind,
                      cam_x, cam_y, cam_scale)

        for p in powerups:
            sx = (p.x - cam_x) * cam_scale
            sy = (p.y - cam_y) * cam_scale
            if sx < -50 or sx > W + 50 or sy < -50 or sy > H + 50:
                continue
            col = POWERUP_COLORS[p.kind]
            bob = math.sin(p.phase) * 3 * cam_scale
            pr = max(4, int(p.radius * cam_scale))
            gs = pygame.Surface((pr * 4, pr * 4), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*col, 70), (pr * 2, pr * 2), pr * 2)
            screen.blit(gs, (sx - pr * 2, sy - pr * 2 + bob))
            pygame.draw.circle(screen, col, (int(sx), int(sy + bob)), pr)
            pygame.draw.circle(screen, (255, 255, 255),
                               (int(sx), int(sy + bob)), pr, 2)
            pygame.draw.circle(screen, (0, 0, 0),
                               (int(sx), int(sy + bob)), max(1, pr - 6), 1)

        for p in particles:
            sx = (p.x - cam_x) * cam_scale
            sy = (p.y - cam_y) * cam_scale
            if sx < -30 or sx > W + 30 or sy < -30 or sy > H + 30: continue
            a = p.life / p.max_life
            pygame.draw.circle(screen, p.color, (int(sx), int(sy)),
                               max(1, int(p.size * a * cam_scale)))

        hx = int((hole.x - cam_x) * cam_scale)
        hy = int((hole.y - cam_y) * cam_scale)
        hr = max(3, int(hole.radius * cam_scale))
        skin = SKINS[save["skin"] % len(SKINS)]
        draw_hole(hx, hy, hr, skin, time, hole.flash, invuln.active, trail,
                  cam_x, cam_y, cam_scale)

        if burst_sk.active:
            wave = int(hr * 3 +
                       (1 - burst_sk.active_timer / burst_sk.dur_max) * 400)
            pygame.draw.circle(screen, (255, 200, 100), (hx, hy), wave, 2)

        for ft in float_texts:
            sx = (ft.x - cam_x) * cam_scale
            sy = (ft.y - cam_y) * cam_scale
            a = clamp(ft.life / ft.max_life, 0, 1)
            surf = get_font(18, True).render(ft.text, True, ft.color)
            surf.set_alpha(int(255 * a))
            screen.blit(surf, (int(sx - surf.get_width() // 2), int(sy)))

        if state == "play":
            for b in bodies:
                if b.mass <= hole.mass: continue
                bx_l = (b.x - cam_x) * cam_scale
                by_l = (b.y - cam_y) * cam_scale
                margin = 40
                if margin < bx_l < W - margin and margin < by_l < H - margin:
                    continue
                cx = clamp(bx_l, margin, W - margin)
                cy = clamp(by_l, margin, H - margin)
                ang = math.atan2(by_l - cy, bx_l - cx)
                pts = []
                for da, r in [(0, 14), (2.5, 9), (-2.5, 9)]:
                    pts.append((cx + math.cos(ang + da) * r,
                                cy + math.sin(ang + da) * r))
                col = (255, 80, 80) if not b.is_boss else (255, 200, 60)
                pygame.draw.polygon(screen, col, pts)
                pygame.draw.polygon(screen, (0, 0, 0), pts, 2)

        if state == "play" and danger > 0.02:
            overlay.fill((255, 30, 30, int(danger * 90)))
            screen.blit(overlay, (0, 0))

        # HUD
        f_lg = get_font(26, True)
        f_md = get_font(20)
        f_sm = get_font(15)
        f_xs = get_font(13)

        screen.blit(f_lg.render(f"质量 {int(hole.mass)}", True,
                                (235, 235, 255)), (26, 26))
        screen.blit(f_lg.render(f"得分 {int(score)}", True,
                                (150, 220, 255)), (26, 62))
        screen.blit(f_md.render(
            f"关卡 {level}  ·  {GAME_MODES[mode]['name']}  ·  "
            f"核心 Lv.{save['core_level']}",
            True, (200, 180, 255)), (26, 100))

        if cam_scale < 0.98:
            zoom_pct = int(cam_scale * 100)
            screen.blit(f_xs.render(f"视角 {zoom_pct}%", True,
                                    (150, 180, 230)), (240, 104))

        if bonus_active:
            banner_h = 56
            banner = pygame.Surface((W, banner_h), pygame.SRCALPHA)
            for i in range(banner_h):
                a = int(70 * (1 - i / banner_h))
                pygame.draw.line(banner, (255, 200, 50, a),
                                 (0, i), (W, i))
            screen.blit(banner, (0, 0))

            pulse = 0.7 + 0.3 * math.sin(time * 8)
            bt = get_font(34, True).render(
                "🎉 奖励关！", True,
                (int(255 * pulse), int(220 * pulse), int(70 * pulse)))
            screen.blit(bt, (W // 2 - bt.get_width() // 2 - 70, 8))

            t_surf = get_font(30, True).render(
                f"{bonus_timer:.1f}s", True, (255, 240, 160))
            screen.blit(t_surf, (W // 2 + 130, 10))

            bar_w = 360
            ratio_b = max(0, bonus_timer / BONUS_DURATION)
            bar_x = W // 2 - bar_w // 2
            pygame.draw.rect(screen, (60, 40, 10),
                             (bar_x, 44, bar_w, 6), border_radius=3)
            pygame.draw.rect(screen, (255, 210, 60),
                             (bar_x, 44, int(bar_w * ratio_b), 6),
                             border_radius=3)

            earn = int(score - bonus_score_start)
            et = get_font(16, True).render(f"+{earn}", True, (255, 230, 120))
            screen.blit(et, (W - 80, 10))

        prev_t = level_target / 1.9 if level > 1 else 22.0
        ratio = clamp((hole.mass - prev_t) / max(1, level_target - prev_t), 0, 1)
        bw, bh = 220, 8
        pygame.draw.rect(screen, (255, 255, 255), (26, 134, bw, bh), 1)
        for i in range(int(bw * ratio)):
            t = i / bw
            col = (int(56 + 199 * t), int(224 - 164 * t), int(176 - 86 * t))
            pygame.draw.line(screen, col, (26 + i, 134), (26 + i, 134 + bh))

        y_off = 152
        badges = []
        if combo >= 3:      badges.append((f"×{combo} 连噬", (255, 200, 100)))
        if buff_ice > 0:    badges.append((f"❄ {buff_ice:.1f}s", (120, 200, 255)))
        if buff_fire > 0:   badges.append((f"🔥 {buff_fire:.1f}s", (255, 130, 70)))
        if buff_magnet > 0: badges.append((f"🧲 {buff_magnet:.1f}s", (180, 220, 255)))
        if time_slow > 0:   badges.append((f"⏳ {time_slow:.1f}s", (200, 255, 180)))
        if bomb_charges > 0:badges.append((f"💣 ×{bomb_charges}", (255, 140, 80)))
        if shield_frags > 0:badges.append((f"🛡 {shield_frags}/3", (120, 220, 255)))
        bx = 26
        for text, col in badges:
            surf = f_xs.render(text, True, col)
            r = pygame.Rect(bx, y_off, surf.get_width() + 12, 20)
            pygame.draw.rect(screen, (30, 30, 50), r, border_radius=4)
            pygame.draw.rect(screen, col, r, 1, border_radius=4)
            screen.blit(surf, (r.x + 6, r.y + 3))
            bx += r.w + 6
            if bx > W - 400: break

        mouse_lx, mouse_ly = screen_to_logical(pygame.mouse.get_pos())
        for i, (key_name, name, sk) in enumerate(SKILL_KEYS):
            box = skill_box(i)
            ready = sk.ready
            hover = box.collidepoint(mouse_lx, mouse_ly) and state == "play" \
                    and not paused
            bg_col = (30, 30, 60) if ready else (50, 20, 20)
            border = (120, 120, 200) if ready else (150, 60, 60)
            if hover and ready:
                bg_col = (50, 50, 100); border = (180, 200, 255)
            pygame.draw.rect(screen, bg_col, box, border_radius=8)
            pygame.draw.rect(screen, border, box, 2, border_radius=8)
            text_col = (230, 230, 255) if ready else (150, 100, 100)
            if hover and ready: text_col = (255, 255, 255)
            screen.blit(f_sm.render(f"[{key_name}] {name}", True, text_col),
                        (box.x + 8, box.y + 6))
            if not ready:
                cd_txt = f"{sk.cd_timer:.1f}s"
                screen.blit(f_sm.render(cd_txt, True, (255, 180, 120)),
                            (box.x + 8, box.y + 32))
                bar = pygame.Rect(box.x + 4, box.y + box.h - 8, box.w - 8, 4)
                pygame.draw.rect(screen, (80, 30, 30), bar)
                pygame.draw.rect(screen, (255, 120, 80),
                                 (bar.x, bar.y,
                                  int(bar.w * (1 - sk.cd_ratio)), bar.h))
            else:
                label = "点击 / 按键" if hover else "就绪"
                screen.blit(f_sm.render(label, True, (150, 255, 180)),
                            (box.x + 8, box.y + 32))

        if state == "play" and not (options_open or evo_menu_open or
                                    mode_menu_open or tutorial_open or help_open):
            base_alpha = 130 if joystick_active else 70
            base_surf = pygame.Surface((JOY_R_OUT * 2 + 8,
                                        JOY_R_OUT * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(base_surf, (30, 30, 60, base_alpha),
                               (JOY_R_OUT + 4, JOY_R_OUT + 4), JOY_R_OUT)
            pygame.draw.circle(base_surf, (100, 120, 200, 180),
                               (JOY_R_OUT + 4, JOY_R_OUT + 4),
                               JOY_R_OUT, 2)
            screen.blit(base_surf,
                        (JOY_CX - JOY_R_OUT - 4, JOY_CY - JOY_R_OUT - 4))
            pygame.draw.line(screen, (60, 60, 100),
                             (JOY_CX - 22, JOY_CY), (JOY_CX + 22, JOY_CY), 1)
            pygame.draw.line(screen, (60, 60, 100),
                             (JOY_CX, JOY_CY - 22), (JOY_CX, JOY_CY + 22), 1)
            jx, jy = joystick_vec
            knob_x = JOY_CX + int(jx * (JOY_R_OUT - JOY_R_IN))
            knob_y = JOY_CY + int(jy * (JOY_R_OUT - JOY_R_IN))
            knob_col = (140, 160, 255) if joystick_active else (90, 100, 160)
            pygame.draw.circle(screen, knob_col, (knob_x, knob_y), JOY_R_IN)
            pygame.draw.circle(screen, (200, 220, 255),
                               (knob_x, knob_y), JOY_R_IN, 2)

        if state == "play" and not (options_open or evo_menu_open or
                                    mode_menu_open or tutorial_open or help_open):
            for rect, label in [(BTN_PAUSE, "暂停 P" if not paused_manual else "继续 P"),
                                (BTN_MENU, "菜单 ESC")]:
                hover = rect.collidepoint(mouse_lx, mouse_ly)
                bg = (55, 55, 100) if hover else (25, 25, 50)
                border = (180, 200, 255) if hover else (110, 120, 180)
                pygame.draw.rect(screen, bg, rect, border_radius=8)
                pygame.draw.rect(screen, border, rect, 2, border_radius=8)
                txt = f_sm.render(label, True,
                                  (255, 255, 255) if hover else (200, 210, 240))
                screen.blit(txt, (rect.x + (rect.w - txt.get_width()) // 2,
                                  rect.y + (rect.h - txt.get_height()) // 2))

        # 小地图
        if show_minimap and state == "play":
            draw_minimap(hole, bodies, powerups, cam_x, cam_y, cam_scale)

        # Toast（小地图之后，从下方开始）
        ty = 24
        if show_minimap and state == "play":
            ty = 20 + 150 + 14

        for t in toasts:
            a = clamp(t.life / min(0.5, t.max_life), 0, 1)
            surf = f_md.render(t.text, True, (255, 230, 140))
            surf.set_alpha(int(255 * a))
            bg = pygame.Surface((surf.get_width() + 24,
                                 surf.get_height() + 12), pygame.SRCALPHA)
            bg.fill((30, 20, 60, int(180 * a)))
            pygame.draw.rect(bg, (255, 210, 100, int(200 * a)),
                             bg.get_rect(), 1, border_radius=6)
            screen.blit(bg, (W - bg.get_width() - 26, ty))
            screen.blit(surf, (W - bg.get_width() - 14, ty + 6))
            ty += bg.get_height() + 8

        if timed and time_left is not None:
            tl = max(0, time_left)
            m, s = divmod(int(tl), 60)
            col = (255, 100, 100) if tl < 30 else (235, 235, 255)
            screen.blit(f_lg.render(f"⏱ {m:02d}:{s:02d}", True, col),
                        (W - 200, 200))

        if precision:
            tc = {"ice": (120, 200, 255), "fire": (255, 130, 70),
                  "split": (190, 110, 255), "gold": (255, 220, 80),
                  "magnet": (180, 220, 255)}[target_color]
            screen.blit(f_md.render(
                f"目标：{target_color.upper()} 色球",
                True, tc), (W - 260, 240 if timed else 200))

        if event_name:
            label = {"meteor":  "☄ 流星雨", "reverse": "🔄 引力反转",
                     "tide":    "🌊 黑洞潮汐", "dark":    "🌑 暗物质云"}[event_name]
            ev = get_font(22, True).render(label, True, (255, 200, 100))
            screen.blit(ev, (W // 2 - ev.get_width() // 2, 24))

        if paused_manual:
            pt = get_font(64, True).render("暂停中", True, (235, 235, 255))
            pt.set_alpha(220)
            screen.blit(pt, (W // 2 - pt.get_width() // 2, H // 2 - 60))
            sub = get_font(22).render("按 P 或点击按钮继续",
                                      True, (170, 180, 220))
            sub.set_alpha(200)
            screen.blit(sub, (W // 2 - sub.get_width() // 2, H // 2 + 20))

        screen.blit(f_sm.render(
            "WASD 移动 · 摇杆拖动 · Space 冲刺 · Q 无敌 · E 爆发 · F 炸弹 · "
            "P 暂停 · F3 帮助 · ESC 选项",
            True, (140, 140, 190)), (26, H - 24))

        if state == "dead":
            alpha = min(180, int(death_timer * 180))
            overlay.fill((0, 0, 0, alpha))
            screen.blit(overlay, (0, 0))
            if death_timer > 0.45:
                fade = min(1, (death_timer - 0.45) * 2.2)
                title = get_font(76, True).render(
                    "被 吞 噬 了", True, (255, 90, 90))
                title.set_alpha(int(255 * fade))
                screen.blit(title, (W // 2 - title.get_width() // 2, H // 2 - 180))
                info = f_lg.render(
                    f"最终质量 {int(hole.mass)}  ·  得分 {int(score)}  ·  关卡 {level}",
                    True, (235, 235, 255))
                info.set_alpha(int(255 * fade))
                screen.blit(info, (W // 2 - info.get_width() // 2, H // 2 - 40))
                xp = int(score / 10)
                xp_txt = f_md.render(
                    f"获得核心 XP +{xp}  （Lv.{save['core_level']}  "
                    f"{int(save['core_xp'])}/{core_xp_needed(save['core_level'])}）",
                    True, (200, 180, 255))
                xp_txt.set_alpha(int(255 * fade))
                screen.blit(xp_txt, (W // 2 - xp_txt.get_width() // 2, H // 2 + 6))
                best = f_md.render(
                    f"历史最高质量 {int(save['best_mass'])}  ·  "
                    f"最高得分 {int(save['best_score'])}",
                    True, (180, 200, 255))
                best.set_alpha(int(255 * fade))
                screen.blit(best, (W // 2 - best.get_width() // 2, H // 2 + 46))
                ach = f_md.render(
                    f"成就 {len(save['unlocked'])}/{len(ACHIEVEMENTS)}",
                    True, (255, 220, 140))
                ach.set_alpha(int(255 * fade))
                screen.blit(ach, (W // 2 - ach.get_width() // 2, H // 2 + 84))

                bw2, bh2 = 220, 56
                bx1 = W // 2 - bw2 - 20
                bx2 = W // 2 + 20
                by = H // 2 + 180
                r1 = pygame.Rect(bx1, by, bw2, bh2)
                r2 = pygame.Rect(bx2, by, bw2, bh2)
                h1 = r1.collidepoint(mouse_lx, mouse_ly)
                h2 = r2.collidepoint(mouse_lx, mouse_ly)
                pygame.draw.rect(screen, (60, 100, 60) if h1 else (30, 60, 40),
                                 r1, border_radius=10)
                pygame.draw.rect(screen, (150, 255, 180) if h1 else (100, 180, 120),
                                 r1, 2, border_radius=10)
                t1 = get_font(24, True).render("再来一局", True, (255, 255, 255))
                screen.blit(t1, (r1.x + (r1.w - t1.get_width()) // 2,
                                 r1.y + (r1.h - t1.get_height()) // 2))
                pygame.draw.rect(screen, (60, 60, 120) if h2 else (30, 30, 60),
                                 r2, border_radius=10)
                pygame.draw.rect(screen, (180, 200, 255) if h2 else (120, 120, 200),
                                 r2, 2, border_radius=10)
                t2 = get_font(24, True).render("换模式", True, (255, 255, 255))
                screen.blit(t2, (r2.x + (r2.w - t2.get_width()) // 2,
                                 r2.y + (r2.h - t2.get_height()) // 2))

                hint = f_md.render("R 重新开始  ·  F3 帮助  ·  ESC 选项",
                                   True, (170, 170, 215))
                hint.set_alpha(int(255 * fade *
                                   (0.6 + 0.4 * math.sin(time * 5))))
                screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 60))

        if tutorial_open:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 215)); screen.blit(ov, (0, 0))
            title = get_font(52, True).render("欢 迎 来 到 黑 洞",
                                              True, (235, 235, 255))
            screen.blit(title, (W // 2 - title.get_width() // 2, 60))
            lines = [
                ("移动",       "WASD / 方向键 / 左下摇杆"),
                ("冲刺",       "Space"),
                ("无敌",       "Q"),
                ("引力爆发",   "E"),
                ("引力炸弹",   "F（拾取后可用）"),
                ("暂停",       "P"),
                ("帮助",       "F3 ← 完整功能列表"),
                ("选项菜单",   "ESC"),
                ("重开",       "R"),
                ("切皮肤",     "F1"),
                ("关卡编辑器", "F2"),
            ]
            y = 140
            for name, key in lines:
                n = get_font(22, True).render(name, True, (200, 220, 255))
                k = get_font(22, True).render(key, True, (255, 220, 140))
                screen.blit(n, (W // 2 - 280, y))
                screen.blit(k, (W // 2 + 20, y))
                y += 36
            hint = get_font(20).render("按任意键开始游戏", True, (170, 200, 255))
            hint.set_alpha(int(180 + 75 * math.sin(time * 4)))
            screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 60))

        if options_open:    draw_options_menu(save)
        if evo_menu_open:   draw_evolution_menu(evo_choices)
        if mode_menu_open:  draw_mode_menu(save)
        if help_open:       draw_help_page(save)

        present()
        await asyncio.sleep(0)

# =========================================================
# 主程序（async）
# =========================================================
async def main():
    while True:
        r = await run_game()
        if r == "quit":
            break
        if r == "editor":
            save = load_save()
            toasts = []
            er = await run_editor((0, 0), save, toasts)
            if er == "quit":
                break
    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())