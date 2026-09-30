# -*- coding: utf-8 -*-
"""
Black Hole · 黑洞吞噬 v4
新增：特殊球 / 道具 / 进化树 / 环境事件 / 智能AI / 多模式 / 元成长 / 氛围
操作：
  移动 WASD/方向键  冲刺 Space  无敌 Q  引力爆发 E
  释放引力炸弹 F（拾取后可用）
  切皮肤 F1  编辑器 F2  加载关卡 L
  选项 ESC  重开 R
"""
import pygame, math, random, sys, json, os, array
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# =========================================================
# 常量
# =========================================================
W, H = 1080, 720
WORLD_W, WORLD_H = 3200, 2400
FPS = 60
BODY_COUNT = 46
G_RANGE = 700
SAVE_FILE = "blackhole_save.json"
LEVEL_FILE = "custom_levels.json"

DISPLAY_MODES = [
    ("窗口 1080×720",  (1080, 720),  False),
    ("窗口 1280×720",  (1280, 720),  False),
    ("窗口 1600×900",  (1600, 900),  False),
    ("窗口 1920×1080", (1920, 1080), False),
    ("全屏",           (0, 0),       True),
]
current_display_idx = 0

# =========================================================
# 初始化
# =========================================================
pygame.mixer.pre_init(22050, -16, 1, 256)
pygame.init()
AUDIO_OK = pygame.mixer.get_init() is not None
if not AUDIO_OK:
    try:
        pygame.mixer.init(22050, -16, 1, 256)
        AUDIO_OK = True
    except Exception:
        AUDIO_OK = False

pygame.display.set_caption("Black Hole · 黑洞吞噬 v4")
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

def lerp(a, b, t):
    return a + (b - a) * t

def mix_color(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)),
            int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))

_font_cache = {}
def get_font(size, bold=False):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    for name in ("notosanscjksc", "notosanscjk", "wenquanyimicrohei",
                 "wenquanyizenhei", "microsoftyahei", "simhei",
                 "dejavusans", "arial"):
        path = pygame.font.match_font(name, bold=bold)
        if path:
            _font_cache[key] = pygame.font.Font(path, size)
            return _font_cache[key]
    _font_cache[key] = pygame.font.Font(None, size)
    return _font_cache[key]

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
    """核心等级 >= 20 解锁奇点"""
    return 4 if save.get("core_level", 0) >= 20 else 3

# =========================================================
# 音效
# =========================================================
class Audio:
    def __init__(self):
        self.ok = AUDIO_OK
        self.enabled = True
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
            s.set_volume(clamp(vol, 0, 1))
            s.play()

audio = Audio()

# =========================================================
# 存档 + 元成长
# =========================================================
def load_save():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            return {
                "best_mass": float(d.get("best_mass", 0)),
                "best_score": float(d.get("best_score", 0)),
                "unlocked": list(d.get("unlocked", [])),
                "skin": int(d.get("skin", 0)),
                "display_idx": int(d.get("display_idx", 0)) % len(DISPLAY_MODES),
                "audio": bool(d.get("audio", True)),
                "core_xp": float(d.get("core_xp", 0)),
                "core_level": int(d.get("core_level", 1)),
                "mode": str(d.get("mode", "classic")),
            }
        except Exception:
            pass
    return {"best_mass": 0.0, "best_score": 0.0, "unlocked": [], "skin": 0,
            "display_idx": 0, "audio": True,
            "core_xp": 0.0, "core_level": 1, "mode": "classic"}

def write_save(d):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

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
# 特殊球定义
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
    """关卡越高，特殊球概率越大"""
    if level < 2:
        return "normal"
    p_special = clamp(0.08 + (level - 2) * 0.03, 0, 0.35)
    if random.random() > p_special:
        return "normal"
    return random.choices(KIND_LIST[1:],
                          weights=KIND_WEIGHTS[1:], k=1)[0]

# =========================================================
# 道具定义
# =========================================================
POWERUPS = ["shield", "time", "bomb", "crystal"]
POWERUP_COLORS = {
    "shield":  (120, 220, 255),
    "time":    (200, 255, 180),
    "bomb":    (255, 140, 80),
    "crystal": (255, 220, 120),
}
POWERUP_NAMES = {
    "shield":  "护盾碎片",
    "time":    "时间胶囊",
    "bomb":    "引力炸弹",
    "crystal": "质量结晶",
}

# =========================================================
# 进化树
# =========================================================
EVOLUTIONS = [
    # (关卡门槛, 选项A, 选项B) —— 选项是 (名称, 描述, key)
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
    """把进化效果应用到 hole_state 字典里（保存加成倍率）"""
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
# 游戏模式
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
    def __init__(self, x, y, mass, hunter=False,
                 kind="normal", ai="chaser"):
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
            # 绕到黑洞前方拦截
            ang = math.atan2(dy, dx) + 0.9
            tx = hole.x + math.cos(ang) * 220
            ty = hole.y + math.sin(ang) * 220
            dx, dy = tx - self.x, ty - self.y
            d = max(1, math.hypot(dx, dy))
        elif self.ai == "pack":
            # 群体加速
            boost = 1.0 + min(pack_count, 4) * 0.15
        elif self.ai == "disguise":
            # 假装普通球直到接近
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

class Comet:
    def __init__(self):
        self.x = random.uniform(0, W)
        self.y = random.uniform(0, H * 0.5)
        self.vx = random.uniform(180, 360)
        self.vy = random.uniform(80, 180)
        self.life = 3.0
        self.len = random.uniform(40, 90)

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
        if not self.ready:
            return False
        if self.cost > 0 and hole.mass * (1 - self.cost) < 22:
            return False
        if self.cost > 0:
            hole.mass *= (1 - self.cost)
        self.cd_timer = self.cd_max
        self.active_timer = self.dur_max
        return True

    def update(self, dt):
        if self.cd_timer > 0:
            self.cd_timer = max(0, self.cd_timer - dt)
        if self.active_timer > 0:
            self.active_timer = max(0, self.active_timer - dt)

# =========================================================
# 星空 + 星云 + 彗星
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
    "c": random.choice([(80, 40, 140), (40, 80, 140), (120, 40, 100), (40, 120, 100)]),
    "p": 0.35,
    "rot": random.uniform(0, math.tau),
} for _ in range(6)]

# =========================================================
# 生成 / 特效
# =========================================================
def spawn_body(hole, level_mult=1.0, hunter_chance=0.0, level=1,
               chaos=False):
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
        ai = random.choices(
            ["chaser", "flanker", "pack", "disguise"],
            weights=[50, 20, 20, 10], k=1)[0]

    b = Body(x, y, mass, hunter, kind, ai)
    if chaos:
        b.vx *= 1.6; b.vy *= 1.6
    return b

def spawn_powerup(hole):
    ang = random.uniform(0, math.tau)
    d = random.uniform(400, 1100)
    x = clamp(hole.x + math.cos(ang) * d, 80, WORLD_W - 80)
    y = clamp(hole.y + math.sin(ang) * d, 80, WORLD_H - 80)
    kind = random.choice(POWERUPS)
    return Powerup(x, y, kind)

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
# 显示管理
# =========================================================
def apply_display(idx):
    global display_surf, current_display_idx
    current_display_idx = idx % len(DISPLAY_MODES)
    name, size, fs = DISPLAY_MODES[current_display_idx]
    if fs:
        info = pygame.display.Info()
        display_surf = pygame.display.set_mode(
            (info.current_w, info.current_h), pygame.FULLSCREEN)
    else:
        display_surf = pygame.display.set_mode(size)

def screen_to_logical(pos):
    mx, my = pos
    sw, sh = display_surf.get_size()
    if sw == 0 or sh == 0:
        return 0, 0
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
        pygame.transform.smoothscale(
            canvas, (sw, sh), _present_cache["surf"])
        display_surf.blit(_present_cache["surf"], (0, 0))
    pygame.display.flip()

apply_display(0)

# =========================================================
# 选项菜单
# =========================================================
def get_option_buttons():
    items = []
    bw, bh = 480, 54
    x = (W - bw) // 2
    y = 140
    gap = 12
    name = DISPLAY_MODES[current_display_idx][0]
    items.append((pygame.Rect(x, y, bw, bh), f"显示模式：{name}", "cycle_display")); y += bh + gap
    items.append((pygame.Rect(x, y, bw, bh), f"音效：{'开' if audio.enabled else '关'}", "toggle_audio")); y += bh + gap
    items.append((pygame.Rect(x, y, bw, bh), "返回主菜单", "menu")); y += bh + gap
    items.append((pygame.Rect(x, y, bw, bh), "继续游戏 (ESC)", "resume")); y += bh + gap
    items.append((pygame.Rect(x, y, bw, bh), "退出游戏", "quit"))
    return items

def draw_options_menu():
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 190)); screen.blit(ov, (0, 0))
    title = get_font(56, True).render("选 项", True, (235, 235, 255))
    screen.blit(title, (W // 2 - title.get_width() // 2, 60))
    mx, my = screen_to_logical(pygame.mouse.get_pos())
    for rect, label, action in get_option_buttons():
        hover = rect.collidepoint(mx, my)
        bg = (55, 55, 110) if hover else (30, 30, 60)
        border = (180, 200, 255) if hover else (120, 120, 200)
        pygame.draw.rect(screen, bg, rect, border_radius=10)
        pygame.draw.rect(screen, border, rect, 2, border_radius=10)
        txt = get_font(22, True).render(label, True,
                                        (255, 255, 255) if hover else (225, 225, 240))
        screen.blit(txt, (rect.x + (rect.w - txt.get_width()) // 2,
                          rect.y + (rect.h - txt.get_height()) // 2))

# =========================================================
# 模式选择菜单
# =========================================================
def draw_mode_menu(save):
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 210)); screen.blit(ov, (0, 0))

    title = get_font(50, True).render("选择游戏模式", True, (235, 235, 255))
    screen.blit(title, (W // 2 - title.get_width() // 2, 60))

    core = get_font(20).render(
        f"黑洞核心 Lv.{save['core_level']}  "
        f"(XP {int(save['core_xp'])}/{core_xp_needed(save['core_level'])})",
        True, (200, 180, 255))
    screen.blit(core, (W // 2 - core.get_width() // 2, 122))

    bw, bh = 420, 68
    x = (W - bw) // 2
    y = 180
    gap = 14
    buttons = []
    for key, info in GAME_MODES.items():
        r = pygame.Rect(x, y, bw, bh)
        buttons.append((r, key, info))
        y += bh + gap

    mx, my = screen_to_logical(pygame.mouse.get_pos())
    for r, key, info in buttons:
        hover = r.collidepoint(mx, my)
        is_cur = save.get("mode", "classic") == key
        bg = (60, 60, 120) if hover else (30, 30, 60)
        if is_cur: bg = (40, 80, 60) if not hover else (60, 110, 80)
        border = (255, 220, 120) if is_cur else ((180, 200, 255) if hover else (120, 120, 200))
        pygame.draw.rect(screen, bg, r, border_radius=10)
        pygame.draw.rect(screen, border, r, 2, border_radius=10)

        n = get_font(24, True).render(info["name"], True, (245, 245, 255))
        d = get_font(16).render(info["desc"], True, (180, 190, 220))
        screen.blit(n, (r.x + 18, r.y + 12))
        screen.blit(d, (r.x + 18, r.y + 42))
        if is_cur:
            badge = get_font(14, True).render("当前", True, (255, 220, 120))
            screen.blit(badge, (r.x + r.w - 60, r.y + 22))

    hint = get_font(16).render("点击选择模式  ·  ESC 返回选项",
                               True, (150, 160, 200))
    screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 40))
    return buttons

# =========================================================
# 进化选择菜单
# =========================================================
def draw_evolution_menu(choices):
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 220)); screen.blit(ov, (0, 0))

    title = get_font(48, True).render("进 化", True, (255, 220, 120))
    screen.blit(title, (W // 2 - title.get_width() // 2, 100))
    sub = get_font(20).render("选择一种进化，永久生效",
                              True, (200, 200, 230))
    screen.blit(sub, (W // 2 - sub.get_width() // 2, 168))

    bw, bh = 380, 220
    gap = 60
    total = bw * 2 + gap
    x0 = (W - total) // 2
    y0 = 250

    mx, my = screen_to_logical(pygame.mouse.get_pos())
    buttons = []
    for i, (name, desc, key) in enumerate(choices):
        r = pygame.Rect(x0 + i * (bw + gap), y0, bw, bh)
        buttons.append((r, i, key))
        hover = r.collidepoint(mx, my)
        bg = (60, 60, 120) if hover else (30, 30, 60)
        border = (255, 220, 120) if hover else (120, 120, 200)
        pygame.draw.rect(screen, bg, r, border_radius=14)
        pygame.draw.rect(screen, border, r, 3, border_radius=14)

        n = get_font(36, True).render(name, True, (255, 255, 255))
        screen.blit(n, (r.x + (r.w - n.get_width()) // 2, r.y + 50))
        d = get_font(20).render(desc, True, (200, 210, 240))
        screen.blit(d, (r.x + (r.w - d.get_width()) // 2, r.y + 130))

        keyhint = get_font(15).render(f"按 {i+1} 或点击", True, (150, 160, 200))
        screen.blit(keyhint, (r.x + (r.w - keyhint.get_width()) // 2, r.y + bh - 30))

    return buttons

# =========================================================
# 关卡编辑器
# =========================================================
def run_editor(init_cam=(0, 0), save=None, toasts=None):
    if save is None: save = load_save()
    if toasts is None: toasts = []

    bodies = []
    cam_x, cam_y = init_cam
    preset_mass = 30
    if os.path.exists(LEVEL_FILE):
        try:
            with open(LEVEL_FILE, "r", encoding="utf-8") as f:
                bodies = json.load(f)
        except Exception:
            bodies = []
    msg, msg_timer = "", 0.0
    def set_msg(t):
        nonlocal msg, msg_timer
        msg, msg_timer = t, 2.0

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                if event.key in (pygame.K_F2, pygame.K_ESCAPE):
                    return None
                elif event.key == pygame.K_1: preset_mass = 20; set_msg("小 20")
                elif event.key == pygame.K_2: preset_mass = 60; set_msg("中 60")
                elif event.key == pygame.K_3: preset_mass = 150; set_msg("大 150")
                elif event.key == pygame.K_c and not (mods & pygame.KMOD_CTRL):
                    bodies = []; set_msg("已清空")
                elif event.key == pygame.K_s and (mods & pygame.KMOD_CTRL):
                    try:
                        with open(LEVEL_FILE, "w", encoding="utf-8") as f:
                            json.dump(bodies, f, ensure_ascii=False, indent=2)
                        set_msg(f"已保存 {len(bodies)} 个球体")
                        unlock(save, "editor_save", toasts)
                    except Exception as e:
                        set_msg(f"保存失败：{e}")
                elif event.key == pygame.K_l and (mods & pygame.KMOD_CTRL):
                    if os.path.exists(LEVEL_FILE):
                        try:
                            with open(LEVEL_FILE, "r", encoding="utf-8") as f:
                                bodies = json.load(f)
                            set_msg(f"已加载 {len(bodies)} 个球体")
                        except Exception as e:
                            set_msg(f"加载失败：{e}")
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

# =========================================================
# 绘制：黑洞 / 星云 / 彗星
# =========================================================
def draw_nebula(cam_x, cam_y, t):
    for n in NEBULAS:
        sx = ((n["x"] - cam_x * n["p"]) % (W + n["r"] * 2)) - n["r"]
        sy = ((n["y"] - cam_y * n["p"]) % (H + n["r"] * 2)) - n["r"]
        # 简化：圆叠加
        for i in range(4):
            r = int(n["r"] * (0.4 + i * 0.18))
            a = max(2, 18 - i * 4)
            gs = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*n["c"], a), (r, r), r)
            screen.blit(gs, (sx - r, sy - r))

def draw_comets(comets, cam_x, cam_y):
    for c in comets:
        alpha = clamp(c.life / 1.2, 0, 1)
        col = (int(255 * alpha), int(230 * alpha), int(255 * alpha))
        ex = c.x - c.vx * 0.12
        ey = c.y - c.vy * 0.12
        pygame.draw.line(screen, col, (ex, ey), (c.x, c.y), 2)
        pygame.draw.circle(screen, col, (int(c.x), int(c.y)), 2)

def draw_hole(hx, hy, hr, skin, t, flash, invuln_active, trail):
    # 质量尾迹
    for i, (tx, ty, life) in enumerate(trail):
        a = life / 0.4
        if a <= 0: continue
        r = int(hr * (0.5 + a * 0.5))
        gs = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*skin["halo"], int(50 * a)), (r, r), r)
        screen.blit(gs, (tx - r, ty - r))

    # 光环
    for i in range(4, 0, -1):
        gr = int(hr * (1.5 + i * 0.5))
        if gr < 2: continue
        gs = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*skin["halo"], 26 // i), (gr, gr), gr)
        screen.blit(gs, (hx - gr, hy - gr))

    # 吸积盘
    for i in range(3):
        rr = hr * (1.32 + i * 0.30)
        a0 = t * (2.0 + i * 0.8) + i * 1.6
        rect = pygame.Rect(hx - rr, hy - rr, rr * 2, rr * 2)
        pygame.draw.arc(screen, skin["accretion"][i], rect,
                        a0, a0 + 1.8, max(1, 3 - i))

    pygame.draw.circle(screen, skin["ring"], (int(hx), int(hy)), int(hr * 1.16), 2)
    pygame.draw.circle(screen, skin["inner"], (int(hx), int(hy)), int(hr))
    pygame.draw.circle(screen, skin["ring"], (int(hx), int(hy)), int(hr), 2)

    if invuln_active:
        pulse = 0.5 + 0.5 * math.sin(t * 14)
        pygame.draw.circle(screen, (120, 255, 200),
                           (int(hx), int(hy)),
                           int(hr * (1.5 + 0.2 * pulse)), 3)
    if flash > 0:
        pygame.draw.circle(screen, (255, 240, 200),
                           (int(hx), int(hy)),
                           int(hr * (1.3 + (1 - flash) * 0.7)), 3)

def draw_body(b, sx, sy, r, state, hole, save, vision_on):
    if b.kind == "invisible":
        b.invis_phase += 0.05
        a = 0.25 + 0.25 * math.sin(b.invis_phase)
        if a < 0.2 and state == "play":
            return
    # 外发光
    glow = (b.color[0] // 3, b.color[1] // 3, b.color[2] // 3)
    pygame.draw.circle(screen, glow, (int(sx), int(sy)), int(r * 1.8))
    # 本体
    pygame.draw.circle(screen, b.color, (int(sx), int(sy)), r)
    # 高光
    hl = (min(255, b.color[0] + 80),
          min(255, b.color[1] + 80),
          min(255, b.color[2] + 80))
    pygame.draw.circle(screen, hl,
                       (int(sx - r * 0.3), int(sy - r * 0.3)),
                        max(1, int(r * 0.34)))
    # 特殊球标识
    if b.kind != "normal" and not b.is_boss:
        tint = BODY_KINDS[b.kind]["tint"]
        if tint:
            pygame.draw.circle(screen, tint, (int(sx), int(sy)), r, 2)
    # 追踪者
    if b.is_boss:
        pygame.draw.circle(screen, (255, 220, 100), (int(sx), int(sy)), r + 10, 3)
        pygame.draw.circle(screen, (255, 160, 60), (int(sx), int(sy)), r + 16, 2)
    elif b.hunter:
        col = {"chaser": (255, 150, 40), "flanker": (255, 80, 160),
               "pack": (255, 200, 40), "disguise": (180, 120, 220)}.get(
                   b.ai, (255, 150, 40))
        pygame.draw.circle(screen, col, (int(sx), int(sy)), r + 3, 2)
        # 视野轨迹
        if vision_on:
            dx, dy = hole.x - b.x, hole.y - b.y
            d = math.hypot(dx, dy)
            if d > 1:
                tx = sx + dx / d * min(d, 160)
                ty = sy + dy / d * min(d, 160)
                pygame.draw.line(screen, col, (sx, sy), (tx, ty), 1)

    # 危险环
    if state == "play" and b.mass > hole.mass and not b.is_boss:
        pygame.draw.circle(screen, (255, 70, 70), (int(sx), int(sy)), r + 6, 2)

# =========================================================
# 主游戏
# =========================================================
def run_game():
    save = load_save()
    if save["display_idx"] != current_display_idx:
        apply_display(save["display_idx"])
    audio.enabled = save["audio"]

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

    bodies = [spawn_body(hole, level_mult, hunter_chance, level, chaos)
              for _ in range(BODY_COUNT)]
    particles = []
    toasts = []
    powerups = []
    comets = []

    cam_x = cam_y = 0.0
    shake = 0.0
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

    # Buff 状态
    buff_ice = 0.0
    buff_fire = 0.0
    buff_magnet = 0.0
    bomb_charges = 0
    shield_frags = 0
    time_slow = 0.0

    # 环境事件
    event_timer = 30.0 if not chaos else 15.0
    event_name = None
    event_dur = 0.0

    # 精准模式：目标颜色
    target_color = random.choice(["ice", "fire", "split", "gold", "magnet"])

    # 计时模式
    time_left = 180.0 if timed else None

    options_open = False
    mode_menu_open = False
    evo_menu_open = False
    evo_choices = []
    pending_evo_level = 0
    evo_triggered = set()

    # 尾迹
    trail = []

    overlay = pygame.Surface((W, H), pygame.SRCALPHA)

    # 技能
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
        return pygame.Rect(
            SKILL_BOX_X0 + i * (SKILL_BOX_W + SKILL_GAP),
            SKILL_BOX_Y, SKILL_BOX_W, SKILL_BOX_H)

    def try_use_skill(sk):
        if state != "play" or options_open or evo_menu_open or mode_menu_open:
            return
        if not sk.activate(hole):
            return
        if sk is dash:
            toasts.append(Toast("⚡ 冲刺！", 1.0))
            audio.play("skill", 0.7)
        elif sk is invuln:
            toasts.append(Toast("🛡 无敌！", 1.0))
            audio.play("skill", 0.8)
        elif sk is burst_sk:
            toasts.append(Toast("💥 引力爆发！", 1.2))
            audio.play("level", 0.7)
        unlock(save, "use_skill", toasts)

    while True:
        ticks = clock.tick(FPS)
        paused = options_open or evo_menu_open or mode_menu_open
        dt = 0.0 if paused else min(ticks / 1000.0, 0.05)
        time += dt

        # ============ 事件 ============
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            if options_open:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        options_open = False; audio.play("ui", 0.5)
                    continue
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    lx, ly = screen_to_logical(event.pos)
                    for rect, label, action in get_option_buttons():
                        if rect.collidepoint(lx, ly):
                            audio.play("ui", 0.5)
                            if action == "cycle_display":
                                apply_display(current_display_idx + 1)
                                save["display_idx"] = current_display_idx
                                write_save(save)
                            elif action == "toggle_audio":
                                audio.enabled = not audio.enabled
                                save["audio"] = audio.enabled
                                write_save(save)
                            elif action == "menu":
                                mode_menu_open = True; options_open = False
                            elif action == "resume":
                                options_open = False
                            elif action == "quit":
                                return "quit"
                            break
                continue

            if mode_menu_open:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    mode_menu_open = False; continue
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    lx, ly = screen_to_logical(event.pos)
                    for r, key, info in draw_mode_menu(save):
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
                        unlock(save, "evolve", toasts)
                    elif event.key in (pygame.K_2, pygame.K_KP2) and len(evo_choices) > 1:
                        apply_evolution({"evo": evo}, evo_choices[1][2])
                        evo_menu_open = False; audio.play("evolve", 0.8)
                        toasts.append(Toast(f"✨ 进化：{evo_choices[1][0]}", 2.5))
                        unlock(save, "evolve", toasts)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    lx, ly = screen_to_logical(event.pos)
                    for r, i, key in draw_evolution_menu(evo_choices):
                        if r.collidepoint(lx, ly):
                            apply_evolution({"evo": evo}, key)
                            evo_menu_open = False; audio.play("evolve", 0.8)
                            toasts.append(Toast(f"✨ 进化：{evo_choices[i][0]}", 2.5))
                            unlock(save, "evolve", toasts)
                            break
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    options_open = True; audio.play("ui", 0.5); continue
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
                        shake = 28
                        burst(particles, hole.x, hole.y, (255, 180, 80), 140, 700)
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
                        if os.path.exists(LEVEL_FILE):
                            try:
                                with open(LEVEL_FILE, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                bodies = [Body(d["x"], d["y"], d["mass"])
                                          for d in data]
                                toasts.append(Toast(
                                    f"已加载关卡：{len(bodies)} 球", 2.5))
                                audio.play("level", 0.7)
                            except Exception:
                                pass

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "play":
                    mx, my = screen_to_logical(event.pos)
                    for i, (k, name, sk) in enumerate(SKILL_KEYS):
                        if skill_box(i).collidepoint(mx, my):
                            try_use_skill(sk)
                            break

        for s in skills:
            s.update(dt)
        if level_up_cd > 0: level_up_cd -= dt
        if combo_timer > 0:
            combo_timer -= dt
            if combo_timer <= 0: combo = 0
        if buff_ice > 0: buff_ice -= dt
        if buff_fire > 0: buff_fire -= dt
        if buff_magnet > 0: buff_magnet -= dt
        if time_slow > 0: time_slow -= dt

        # 环境事件 tick
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

        # 事件效果
        reverse = (event_name == "reverse")
        dark = (event_name == "dark")

        keys = pygame.key.get_pressed()

        # ============ 玩家移动 ============
        if state == "play" and not paused:
            dx = dy = 0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
            if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1

            tvx = tvy = 0.0
            if dx or dy:
                L = math.hypot(dx, dy)
                max_spd = 430 * (22 / hole.mass) ** 0.18 * evo["speed"]
                if dash.active: max_spd *= 2.6
                if buff_ice > 0: max_spd *= 0.5
                if buff_fire > 0: max_spd *= 1.8
                if time_slow > 0: max_spd *= 0.6
                tvx, tvy = dx / L * max_spd, dy / L * max_spd

            k = min(1.0, 12 * dt)
            hole.vx += (tvx - hole.vx) * k
            hole.vy += (tvy - hole.vy) * k
            hole.x += hole.vx * dt
            hole.y += hole.vy * dt

            hr = hole.radius
            hole.x = clamp(hole.x, hr, WORLD_W - hr)
            hole.y = clamp(hole.y, hr, WORLD_H - hr)

            # 尾迹
            trail.append((hole.x - cam_x, hole.y - cam_y, 0.4))

        # 尾迹衰减
        trail = [(x, y, l - dt) for (x, y, l) in trail if l - dt > 0]
        if len(trail) > 24: trail = trail[-24:]

        # 引力爆发 + 进化
        g_range = G_RANGE * evo["grav_range"]
        g_power = evo["grav_power"]
        if burst_sk.active:
            g_range *= 1.8
            g_power *= 1.5
        if buff_magnet > 0:
            g_range *= 3.0
        if reverse:
            g_range = 0  # 反转时关闭引力

        # ============ 物理 & 吞噬 ============
        if not paused:
            pack_count = sum(1 for b in bodies if b.hunter and b.ai == "pack")
            survivors = []
            for b in bodies:
                b.update_ai(hole, dt, pack_count)
                if reverse:
                    # 推开
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

                # 事件：流星雨对球的影响
                if event_name == "meteor" and random.random() < 0.01:
                    b.vx += random.uniform(-200, 200)
                    b.vy += random.uniform(-200, 200)

                b.vx *= (1 - 0.35 * dt)
                b.vy *= (1 - 0.35 * dt)
                b.x += b.vx * dt
                b.y += b.vy * dt

                # 潮汐：向中心拉
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

                # 吸积（进化）
                if evo["accretion"] and b.mass > hole.mass:
                    if dist < hole.radius * 4:
                        b.mass = max(3, b.mass - 2 * dt)
                        b.radius = math.sqrt(b.mass) * 2.6

                # 吞噬
                if state == "play" and dist < hole.radius + b.radius * 0.35:
                    # 精准模式检查
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
                        combo += 1; combo_timer = 2.0
                        if combo >= 10 and combo % 10 == 0:
                            unlock(save, "combo_10", toasts)

                        smult = evo["score_mult"]
                        if b.kind == "gold":
                            smult *= (3 if evo["greed"] else 5)
                        score += b.mass * smult

                        if total_eaten >= 200:
                            unlock(save, "collector", toasts)

                        hole.flash = 1.0
                        shake = min(shake + 2 + b.radius * 0.4, 16)
                        burst(particles, b.x, b.y, b.color,
                              min(70, int(5 + b.radius * 0.9)),
                              280, b.vx, b.vy)

                        # 特殊球效果
                        if b.kind == "ice":
                            buff_ice = 2.0
                            toasts.append(Toast("❄ 减速", 1.0))
                        elif b.kind == "fire":
                            buff_fire = 2.0
                            toasts.append(Toast("🔥 加速", 1.0))
                        elif b.kind == "magnet":
                            buff_magnet = 3.0
                            toasts.append(Toast("🧲 磁力", 1.2))
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
                            audio.play("boom", 0.7)
                            shake = 26
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

                        # BOSS 分裂
                        if b.is_boss:
                            audio.play("nova", 1.0)
                            # 超新星白光
                            flash_surf = pygame.Surface((W, H))
                            flash_surf.fill((255, 255, 255))
                            for a in (220, 160, 100, 50):
                                flash_surf.set_alpha(a)
                                screen.blit(flash_surf, (0, 0))
                                present()
                                pygame.time.delay(30)
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
                            shake = 22
                            burst(particles, b.x, b.y, (255, 220, 100), 120, 520)
                            unlock(save, "boss_kill", toasts)
                        continue

                    elif invuln.active:
                        survivors.append(b); continue
                    else:
                        state = "dead"
                        death_timer = 0.0
                        shake = 24
                        audio.play("dead", 0.8)
                        burst(particles, hole.x, hole.y, (255, 120, 90), 130, 480)
                        continue

                survivors.append(b)

            bodies = survivors

            # ============ 道具拾取 ============
            alive_pw = []
            for p in powerups:
                p.life -= dt
                p.phase += dt * 3
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
                        toasts.append(Toast("💣 获得炸弹 (按 F 释放)", 2.0))
                    elif p.kind == "crystal":
                        hole.mass += 20
                        toasts.append(Toast("💎 +20 质量", 1.5))
                    # 追踪用
                    if "powerup_3" not in save["unlocked"]:
                        pass
                    continue
                alive_pw.append(p)
            powerups = alive_pw

            # 随机生成道具
            powerup_timer -= dt
            if powerup_timer <= 0 and len(powerups) < 3:
                powerup_timer = random.uniform(10, 18)
                powerups.append(spawn_powerup(hole))

            # ============ 关卡升级 ============
            if state == "play" and level_up_cd <= 0 and hole.mass >= level_target:
                level += 1
                level_target *= 1.9
                level_up_cd = 0.8
                hunter_chance = min(0.06 * (level - 1), 0.30)
                level_mult = 1.0 + (level - 1) * 0.18
                shake = min(shake + 10, 22)
                audio.play("level", 0.75)
                toasts.append(Toast(f"★ 第 {level} 关", 2.5))
                burst(particles, hole.x, hole.y, (255, 220, 120), 90, 420)

                if evo["revive"]:
                    hole.mass += 10
                    toasts.append(Toast("⭐ 复苏 +10", 1.5))

                if level >= 3:  unlock(save, "level_3", toasts)
                if level >= 5:  unlock(save, "level_5", toasts)
                if level >= 10: unlock(save, "level_10", toasts)

                # 进化触发
                for threshold, choices in EVOLUTIONS:
                    if level == threshold and threshold not in evo_triggered:
                        evo_triggered.add(threshold)
                        evo_choices = choices
                        evo_menu_open = True
                        pending_evo_level = threshold
                        break

            # ============ BOSS 生成 ============
            if state == "play":
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
                    shake = 20
                    audio.play("boss", 1.0)

            # ============ 补充球 ============
            if state == "play":
                target_count = BODY_COUNT
                if survival:
                    # 随时间增加
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

            # ============ 粒子 ============
            alive = []
            for p in particles:
                p.life -= dt
                if p.life <= 0: continue
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.vx *= (1 - 1.8 * dt)
                p.vy *= (1 - 1.8 * dt)
                alive.append(p)
            particles = alive

            # ============ 彗星 ============
            if random.random() < 0.004 and len(comets) < 3:
                comets.append(Comet())
            for c in comets:
                c.x += c.vx * dt
                c.y += c.vy * dt
                c.life -= dt
            comets = [c for c in comets if c.life > 0 and c.x < W + 200 and c.y < H + 200]

            # ============ 危险度 ============
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

            # ============ 成就 ============
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

            # ============ 计时模式 ============
            if timed:
                time_left -= dt
                if time_left <= 0:
                    state = "dead"
                    death_timer = 0.0
                    audio.play("dead", 0.9)

            # ============ 死亡存档 ============
            if state == "dead":
                death_timer += dt
                if not saved_this_round:
                    saved_this_round = True
                    save["best_mass"] = max(save["best_mass"], hole.mass)
                    save["best_score"] = max(save["best_score"], score)
                    # 元成长：每局获得核心 XP
                    add_core_xp(save, score / 10.0, toasts)
                    write_save(save)

            # ============ Toast ============
            toasts = [t for t in toasts if t.life > 0]
            for t in toasts:
                t.life -= dt

        # ============ 摄像机 ============
        cam_x = clamp(hole.x - W * 0.5, 0, WORLD_W - W)
        cam_y = clamp(hole.y - H * 0.5, 0, WORLD_H - H)
        if shake > 0.2:
            cam_x += random.uniform(-shake, shake)
            cam_y += random.uniform(-shake, shake)
            shake = max(0, shake - 30 * dt)
        else:
            shake = 0.0
        if hole.flash > 0:
            hole.flash = max(0, hole.flash - dt * 3)

        # =====================================================
        # 渲染
        # =====================================================
        screen.fill((5, 5, 15))

        # 星云
        draw_nebula(cam_x, cam_y, time)

        # 星空
        for s in STARS:
            x = (s["x"] - cam_x * s["p"]) % W
            y = (s["y"] - cam_y * s["p"]) % H
            b = s["b"]
            pygame.draw.circle(screen, (b, b, min(255, b + 55)),
                               (int(x), int(y)), max(1, int(s["r"])))

        # 暗物质云
        if dark:
            dark_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            dark_surf.fill((0, 0, 0, 180))
            # 黑洞周围挖个亮洞
            hx_l = int(hole.x - cam_x)
            hy_l = int(hole.y - cam_y)
            pygame.draw.circle(dark_surf, (0, 0, 0, 0),
                               (hx_l, hy_l), int(hole.radius * 6))
            screen.blit(dark_surf, (0, 0))

        # 世界边界
        pygame.draw.rect(screen, (90, 70, 180),
                         (int(-cam_x), int(-cam_y), WORLD_W, WORLD_H), 4)

        # 潮汐效果：中心圈
        if event_name == "tide":
            cx_l = WORLD_W / 2 - cam_x
            cy_l = WORLD_H / 2 - cam_y
            for i in range(3):
                r = int(200 + i * 80 + math.sin(time * 2 + i) * 30)
                pygame.draw.circle(screen, (100, 180, 255),
                                   (int(cx_l), int(cy_l)), r, 2)

        # 彗星
        draw_comets(comets, cam_x, cam_y)

        # 球
        for b in bodies:
            sx, sy = b.x - cam_x, b.y - cam_y
            if sx < -150 or sx > W + 150 or sy < -150 or sy > H + 150:
                continue
            r = max(1, int(b.radius))
            draw_body(b, sx, sy, r, state, hole, save, evo["vision"])

        # 道具
        for p in powerups:
            sx, sy = p.x - cam_x, p.y - cam_y
            if sx < -50 or sx > W + 50 or sy < -50 or sy > H + 50:
                continue
            col = POWERUP_COLORS[p.kind]
            bob = math.sin(p.phase) * 3
            # 光晕
            gs = pygame.Surface((p.radius * 4, p.radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*col, 70),
                               (p.radius * 2, p.radius * 2), p.radius * 2)
            screen.blit(gs, (sx - p.radius * 2, sy - p.radius * 2 + bob))
            pygame.draw.circle(screen, col, (int(sx), int(sy + bob)), p.radius)
            pygame.draw.circle(screen, (255, 255, 255),
                               (int(sx), int(sy + bob)), p.radius, 2)
            # 内部符号
            pygame.draw.circle(screen, (0, 0, 0),
                               (int(sx), int(sy + bob)), p.radius - 6, 1)

        # 粒子
        for p in particles:
            sx, sy = p.x - cam_x, p.y - cam_y
            if sx < -30 or sx > W + 30 or sy < -30 or sy > H + 30: continue
            a = p.life / p.max_life
            pygame.draw.circle(screen, p.color, (int(sx), int(sy)),
                               max(1, int(p.size * a)))

        # 黑洞
        hx, hy = int(hole.x - cam_x), int(hole.y - cam_y)
        hr = max(3, int(hole.radius))
        skin = SKINS[save["skin"] % len(SKINS)]
        draw_hole(hx, hy, hr, skin, time, hole.flash, invuln.active, trail)

        if burst_sk.active:
            wave = int(hr * 3 +
                       (1 - burst_sk.active_timer / burst_sk.dur_max) * 400)
            pygame.draw.circle(screen, (255, 200, 100), (hx, hy), wave, 2)

        # 危险红晕
        if state == "play" and danger > 0.02:
            overlay.fill((255, 30, 30, int(danger * 90)))
            screen.blit(overlay, (0, 0))

        # ============ HUD ============
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

        # 关卡进度
        prev_t = level_target / 1.9 if level > 1 else 22.0
        ratio = clamp((hole.mass - prev_t) / max(1, level_target - prev_t), 0, 1)
        bw, bh = 220, 8
        pygame.draw.rect(screen, (255, 255, 255), (26, 134, bw, bh), 1)
        for i in range(int(bw * ratio)):
            t = i / bw
            col = (int(56 + 199 * t), int(224 - 164 * t), int(176 - 86 * t))
            pygame.draw.line(screen, col, (26 + i, 134), (26 + i, 134 + bh))

        # 状态徽章
        y_off = 152
        badges = []
        if combo >= 3:
            badges.append((f"×{combo} 连噬", (255, 200, 100)))
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

        # 技能栏
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

        # 计时 / 精准模式提示
        if timed and time_left is not None:
            tl = max(0, time_left)
            m, s = divmod(int(tl), 60)
            col = (255, 100, 100) if tl < 30 else (235, 235, 255)
            screen.blit(f_lg.render(f"⏱ {m:02d}:{s:02d}", True, col),
                        (W - 200, 26))

        if precision:
            tc = {"ice": (120, 200, 255), "fire": (255, 130, 70),
                  "split": (190, 110, 255), "gold": (255, 220, 80),
                  "magnet": (180, 220, 255)}[target_color]
            screen.blit(f_md.render(
                f"目标：{target_color.upper()} 色球（其余球吃错会死）",
                True, tc), (W - 420, 70))

        # 事件提示
        if event_name:
            label = {
                "meteor":  "☄ 流星雨",
                "reverse": "🔄 引力反转",
                "tide":    "🌊 黑洞潮汐",
                "dark":    "🌑 暗物质云",
            }[event_name]
            ev = get_font(22, True).render(label, True, (255, 200, 100))
            screen.blit(ev, (W // 2 - ev.get_width() // 2, 24))

        # 底部提示
        screen.blit(f_sm.render(
            "WASD 移动 · Space 冲刺 · Q 无敌 · E 引力爆发 · F 炸弹 · "
            "F1 皮肤 · F2 编辑器 · L 加载 · ESC 选项 · R 重开",
            True, (140, 140, 190)), (26, H - 24))

        # Toast
        ty = 24
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

        # 死亡界面
        if state == "dead":
            alpha = min(180, int(death_timer * 180))
            overlay.fill((0, 0, 0, alpha))
            screen.blit(overlay, (0, 0))

            if death_timer > 0.45:
                fade = min(1, (death_timer - 0.45) * 2.2)
                title = get_font(76, True).render(
                    "被 吞 噬 了", True, (255, 90, 90))
                title.set_alpha(int(255 * fade))
                screen.blit(title, (W // 2 - title.get_width() // 2, H // 2 - 160))

                info = f_lg.render(
                    f"最终质量 {int(hole.mass)}  ·  得分 {int(score)}  ·  关卡 {level}",
                    True, (235, 235, 255))
                info.set_alpha(int(255 * fade))
                screen.blit(info, (W // 2 - info.get_width() // 2, H // 2 - 30))

                # 获得 XP
                xp = int(score / 10)
                xp_txt = f_md.render(
                    f"获得核心 XP +{xp}  （Lv.{save['core_level']}  "
                    f"{int(save['core_xp'])}/{core_xp_needed(save['core_level'])}）",
                    True, (200, 180, 255))
                xp_txt.set_alpha(int(255 * fade))
                screen.blit(xp_txt, (W // 2 - xp_txt.get_width() // 2, H // 2 + 16))

                best = f_md.render(
                    f"历史最高质量 {int(save['best_mass'])}  ·  "
                    f"最高得分 {int(save['best_score'])}",
                    True, (180, 200, 255))
                best.set_alpha(int(255 * fade))
                screen.blit(best, (W // 2 - best.get_width() // 2, H // 2 + 56))

                ach = f_md.render(
                    f"成就 {len(save['unlocked'])}/{len(ACHIEVEMENTS)}",
                    True, (255, 220, 140))
                ach.set_alpha(int(255 * fade))
                screen.blit(ach, (W // 2 - ach.get_width() // 2, H // 2 + 94))

                hint = f_md.render(
                    "R 重新开始  ·  ESC 选项  ·  F2 编辑器",
                    True, (170, 170, 215))
                hint.set_alpha(int(255 * fade *
                                   (0.6 + 0.4 * math.sin(time * 5))))
                screen.blit(hint, (W // 2 - hint.get_width() // 2, H // 2 + 146))

        # 覆盖菜单
        if options_open:
            draw_options_menu()
        if evo_menu_open:
            draw_evolution_menu(evo_choices)
        if mode_menu_open:
            draw_mode_menu(save)

        present()

# =========================================================
# 主程序
# =========================================================
def main():
    while True:
        r = run_game()
        if r == "quit":
            break
        if r == "editor":
            save = load_save()
            toasts = []
            er = run_editor((0, 0), save, toasts)
            if er == "quit":
                break
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()