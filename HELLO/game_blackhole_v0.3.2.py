# -*- coding: utf-8 -*-
"""
Black Hole · 黑洞吞噬 v3.2
新增：内置屏幕交互选项（ESC 打开菜单：分辨率 / 全屏 / 音效）
修复：跳关漏洞 / Q+E 指数爆炸 / 无敌弹飞大球
新增：技能按钮鼠标可点击

按键：
  移动 WASD/方向键  冲刺 Space  无敌 Q  引力爆发 E
  切皮肤 F1  编辑器 F2  加载自定义关卡 L
  选项菜单 ESC  重开 R
"""
import pygame, math, random, sys, json, os, array

# =========================================================
# 逻辑分辨率（所有渲染都在这个尺寸上进行）
# =========================================================
W, H = 1080, 720
WORLD_W, WORLD_H = 3200, 2400
FPS = 60
BODY_COUNT = 46
G_RANGE = 700
SAVE_FILE = "blackhole_save.json"
LEVEL_FILE = "custom_levels.json"

# 显示模式（逻辑分辨率恒定 1080x720，窗口大小可变）
DISPLAY_MODES = [
    ("窗口 720×480",  (720, 480),  False),
    ("窗口 1280×720",  (1280, 720),  False),
    ("窗口 1080×720",  (1080, 720),  False),
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

pygame.display.set_caption("Black Hole · 黑洞吞噬 v3.2")
clock = pygame.time.Clock()
# 逻辑画布：所有游戏渲染都画在这上面
canvas = pygame.Surface((W, H))
screen = canvas          # 兼容旧代码：screen 就是逻辑画布
display_surf = None      # 真实窗口

# =========================================================
# 显示管理
# =========================================================
def apply_display(idx):
    """切换显示模式，idx 会对 len(DISPLAY_MODES) 取模"""
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
    """把窗口坐标（鼠标事件/事件坐标）转换为逻辑坐标"""
    mx, my = pos
    sw, sh = display_surf.get_size()
    if sw == 0 or sh == 0:
        return 0, 0
    return int(mx * W / sw), int(my * H / sh)

_present_cache = {"surf": None, "size": None}

def present():
    """把逻辑画布缩放到窗口并翻转"""
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

# 初始化显示
apply_display(0)

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
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont(
            "microsoftyahei,simhei,simsun,arial", size, bold=bold)
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
]

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
# 存档
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
                "skin": int(d.get("skin", 0)) % len(SKINS),
                "display_idx": int(d.get("display_idx", 0)) % len(DISPLAY_MODES),
                "audio": bool(d.get("audio", True)),
            }
        except Exception:
            pass
    return {"best_mass": 0.0, "best_score": 0.0, "unlocked": [],
            "skin": 0, "display_idx": 0, "audio": True}

def write_save(d):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# 启动时按存档恢复显示/音效
_init_save = load_save()
if _init_save["display_idx"] != 0:
    apply_display(_init_save["display_idx"])
audio.enabled = _init_save["audio"]

# =========================================================
# 成就
# =========================================================
ACHIEVEMENTS = {
    "first_blood": "初次吞噬",
    "mass_50":     "质量达到 50",
    "mass_100":    "质量达到 100",
    "mass_200":    "质量达到 200",
    "mass_400":    "质量达到 400",
    "level_3":     "抵达第 3 关",
    "level_5":     "抵达第 5 关",
    "boss_kill":   "击杀 BOSS",
    "score_500":   "单局得分 500",
    "survive_60":  "存活 60 秒",
    "use_skill":   "使用技能",
    "editor_save": "编辑器保存关卡",
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
# 实体
# =========================================================
class Hole:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.mass = 22.0
        self.flash = 0.0

    @property
    def radius(self):
        return math.sqrt(self.mass) * 2.8

class Body:
    def __init__(self, x, y, mass, hunter=False):
        self.x, self.y = x, y
        self.mass = mass
        self.radius = math.sqrt(mass) * 2.6
        a, s = random.uniform(0, math.tau), random.uniform(5, 45)
        self.vx = math.cos(a) * s
        self.vy = math.sin(a) * s
        self.color = mass_color(mass)
        self.hunter = hunter
        self.is_boss = False

    def update_ai(self, hole, dt):
        if not self.hunter:
            return
        if not self.is_boss and self.mass <= hole.mass:
            self.hunter = False
            return
        dx, dy = hole.x - self.x, hole.y - self.y
        d = math.hypot(dx, dy)
        if 1 < d < 1100:
            spd = 380 if self.is_boss else 340
            acc = spd * (1 - d / 1100)
            self.vx += dx / d * acc * dt
            self.vy += dy / d * acc * dt

class Boss(Body):
    def __init__(self, x, y, mass):
        super().__init__(x, y, mass, hunter=True)
        self.is_boss = True

class Particle:
    def __init__(self, x, y, vx, vy, life, size, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.size = size
        self.color = color

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
# 星空
# =========================================================
STARS = [{
    "x": random.uniform(0, 5000),
    "y": random.uniform(0, 5000),
    "r": random.uniform(0.5, 2.0),
    "b": random.randint(70, 200),
    "p": random.choice([0.22, 0.42, 0.65])
} for _ in range(460)]

# =========================================================
# 生成 / 特效
# =========================================================
def spawn_body(hole, level_mult=1.0, hunter_chance=0.0):
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
    hunter = random.random() < hunter_chance and mass > hole.mass * 1.15
    return Body(x, y, mass, hunter)

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
# 选项菜单（悬浮覆盖层）
# =========================================================
def get_option_buttons():
    items = []
    bw, bh = 480, 64
    x = (W - bw) // 2
    y = 210
    gap = 18

    name = DISPLAY_MODES[current_display_idx][0]
    items.append((pygame.Rect(x, y, bw, bh),
                  f"显示模式：{name}",
                  "cycle_display"))
    y += bh + gap

    items.append((pygame.Rect(x, y, bw, bh),
                  f"音效：{'开' if audio.enabled else '关'}",
                  "toggle_audio"))
    y += bh + gap

    items.append((pygame.Rect(x, y, bw, bh),
                  "继续游戏 (ESC)",
                  "resume"))
    y += bh + gap

    items.append((pygame.Rect(x, y, bw, bh),
                  "退出游戏",
                  "quit"))
    return items

def draw_options_menu():
    # 遮罩
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 180))
    screen.blit(ov, (0, 0))

    # 标题
    title = get_font(56, True).render("选 项", True, (235, 235, 255))
    screen.blit(title, (W // 2 - title.get_width() // 2, 100))

    sub = get_font(18).render(
        "点击按钮切换  ·  按 ESC 返回游戏", True, (160, 170, 200))
    screen.blit(sub, (W // 2 - sub.get_width() // 2, 170))

    # 鼠标逻辑坐标
    mx, my = screen_to_logical(pygame.mouse.get_pos())

    for rect, label, action in get_option_buttons():
        hover = rect.collidepoint(mx, my)
        bg = (55, 55, 110) if hover else (30, 30, 60)
        border = (180, 200, 255) if hover else (120, 120, 200)
        pygame.draw.rect(screen, bg, rect, border_radius=10)
        pygame.draw.rect(screen, border, rect, 2, border_radius=10)

        txt = get_font(24, True).render(label, True,
                                        (255, 255, 255) if hover else (225, 225, 240))
        screen.blit(txt, (rect.x + (rect.w - txt.get_width()) // 2,
                          rect.y + (rect.h - txt.get_height()) // 2))

    # 底部提示
    hint = get_font(16).render(
        f"当前逻辑分辨率 {W}×{H}  ·  窗口 {display_surf.get_size()[0]}×{display_surf.get_size()[1]}",
        True, (150, 160, 200))
    screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 60))

# =========================================================
# 关卡编辑器
# =========================================================
def run_editor(init_cam=(0, 0), save=None, toasts=None):
    if save is None:
        save = load_save()
    if toasts is None:
        toasts = []

    bodies = []
    cam_x, cam_y = init_cam
    preset_mass = 30
    skin_idx = save.get("skin", 0)

    if os.path.exists(LEVEL_FILE):
        try:
            with open(LEVEL_FILE, "r", encoding="utf-8") as f:
                bodies = json.load(f)
        except Exception:
            bodies = []

    msg, msg_timer = "", 0.0

    def set_msg(t):
        nonlocal msg, msg_timer
        msg = t
        msg_timer = 2.0

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                if event.key in (pygame.K_F2, pygame.K_ESCAPE):
                    return None
                elif event.key == pygame.K_1:
                    preset_mass = 20; set_msg("质量预设：小 (20)")
                elif event.key == pygame.K_2:
                    preset_mass = 60; set_msg("质量预设：中 (60)")
                elif event.key == pygame.K_3:
                    preset_mass = 150; set_msg("质量预设：大 (150)")
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
                    else:
                        set_msg("没有找到存档文件")
                elif event.key == pygame.K_F1:
                    skin_idx = (skin_idx + 1) % len(SKINS)

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

        if msg_timer > 0:
            msg_timer -= dt

        # ---- 渲染 ----
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
                col = mass_color(b["mass"])
                pygame.draw.circle(screen, col, (int(sx), int(sy)), r)
                pygame.draw.circle(screen, (255, 255, 255),
                                   (int(sx), int(sy)), r, 1)

        mx, my = screen_to_logical(pygame.mouse.get_pos())
        pygame.draw.circle(screen, (100, 255, 200), (mx, my),
                           int(math.sqrt(preset_mass) * 2.6), 2)

        panel = pygame.Surface((W, 90), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150))
        screen.blit(panel, (0, 0))

        f_lg = get_font(22, True)
        f_md = get_font(16)

        screen.blit(f_lg.render(
            f"关卡编辑器  当前预设质量 {preset_mass}  球体数量 {len(bodies)}",
            True, (200, 220, 255)), (20, 12))

        screen.blit(f_md.render(
            "左键放置 / 右键删除  ·  1/2/3 预设  ·  WASD 滚动  ·  "
            "Ctrl+S 保存  ·  Ctrl+L 加载  ·  C 清空  ·  F2/ESC 返回",
            True, (150, 170, 220)), (20, 50))

        if msg_timer > 0:
            surf = f_lg.render(msg, True, (255, 230, 140))
            surf.set_alpha(int(255 * clamp(msg_timer / 0.5, 0, 1)))
            screen.blit(surf, (20, H - 40))

        screen.blit(f_md.render("按 F2 返回游戏", True, (255, 200, 100)),
                    (W - 200, H - 30))

        present()

# =========================================================
# 绘制黑洞
# =========================================================
def draw_hole(hx, hy, hr, skin, time, flash, invuln_active):
    for i in range(4, 0, -1):
        gr = int(hr * (1.5 + i * 0.5))
        if gr < 2:
            continue
        gs = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*skin["halo"], 26 // i), (gr, gr), gr)
        screen.blit(gs, (hx - gr, hy - gr))

    for i in range(3):
        rr = hr * (1.32 + i * 0.30)
        a0 = time * (2.0 + i * 0.8) + i * 1.6
        rect = pygame.Rect(hx - rr, hy - rr, rr * 2, rr * 2)
        pygame.draw.arc(screen, skin["accretion"][i], rect,
                        a0, a0 + 1.8, max(1, 3 - i))

    pygame.draw.circle(screen, skin["ring"],
                       (int(hx), int(hy)), int(hr * 1.16), 2)
    pygame.draw.circle(screen, skin["inner"],
                       (int(hx), int(hy)), int(hr))
    pygame.draw.circle(screen, skin["ring"],
                       (int(hx), int(hy)), int(hr), 2)

    if invuln_active:
        pulse = 0.5 + 0.5 * math.sin(time * 14)
        pygame.draw.circle(screen, (120, 255, 200),
                           (int(hx), int(hy)),
                           int(hr * (1.5 + 0.2 * pulse)), 3)

    if flash > 0:
        pygame.draw.circle(screen, (255, 240, 200),
                           (int(hx), int(hy)),
                           int(hr * (1.3 + (1 - flash) * 0.7)), 3)

# =========================================================
# 主游戏
# =========================================================
def run_game():
    save = load_save()
    # 应用存档中的显示设置
    if save["display_idx"] != current_display_idx:
        apply_display(save["display_idx"])
    audio.enabled = save["audio"]

    hole = Hole(WORLD_W * 0.5, WORLD_H * 0.5)
    level = 1
    level_target = 70.0
    hunter_chance = 0.0
    level_mult = 1.0
    boss_spawned_for_level = 0

    bodies = [spawn_body(hole, level_mult, hunter_chance)
              for _ in range(BODY_COUNT)]
    particles = []
    toasts = []

    cam_x = cam_y = 0.0
    shake = 0.0
    score = 0.0
    time = 0.0
    spawn_timer = 0.0
    heart_cd = 0.0
    state = "play"
    death_timer = 0.0
    saved_this_round = False
    level_up_cd = 0.0

    options_open = False

    overlay = pygame.Surface((W, H), pygame.SRCALPHA)

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
    SKILL_BOX_X0, SKILL_BOX_Y = 26, 160
    SKILL_GAP = 12

    def skill_box(i):
        return pygame.Rect(
            SKILL_BOX_X0 + i * (SKILL_BOX_W + SKILL_GAP),
            SKILL_BOX_Y, SKILL_BOX_W, SKILL_BOX_H)

    def try_use_skill(sk):
        nonlocal state
        if state != "play" or options_open:
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
        # 选项打开时暂停游戏物理
        dt = 0.0 if options_open else min(ticks / 1000.0, 0.05)
        time += dt

        # ---------------- 事件 ----------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            # ============ 选项菜单事件 ============
            if options_open:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        options_open = False
                        audio.play("ui", 0.5)
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
                            elif action == "resume":
                                options_open = False
                            elif action == "quit":
                                return "quit"
                            break
                continue

            # ============ 游戏事件 ============
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    options_open = True
                    audio.play("ui", 0.5)
                    continue
                if event.key == pygame.K_F2:
                    return "editor"
                if state == "dead" and event.key == pygame.K_r:
                    return "restart"
                if state == "play":
                    if event.key == pygame.K_SPACE:
                        try_use_skill(dash)
                    elif event.key == pygame.K_q:
                        try_use_skill(invuln)
                    elif event.key == pygame.K_e:
                        try_use_skill(burst_sk)
                    elif event.key == pygame.K_F1:
                        save["skin"] = (save["skin"] + 1) % len(SKINS)
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
                                    f"已加载自定义关卡：{len(bodies)} 个球", 2.5))
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
        if level_up_cd > 0:
            level_up_cd -= dt

        keys = pygame.key.get_pressed()

        # ---------------- 玩家移动 ----------------
        if state == "play" and not options_open:
            dx = dy = 0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
            if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1

            tvx = tvy = 0.0
            if dx or dy:
                L = math.hypot(dx, dy)
                max_spd = 430 * (22 / hole.mass) ** 0.18
                if dash.active:
                    max_spd *= 2.6
                tvx, tvy = dx / L * max_spd, dy / L * max_spd

            k = min(1.0, 12 * dt)
            hole.vx += (tvx - hole.vx) * k
            hole.vy += (tvy - hole.vy) * k
            hole.x += hole.vx * dt
            hole.y += hole.vy * dt

            hr = hole.radius
            hole.x = clamp(hole.x, hr, WORLD_W - hr)
            hole.y = clamp(hole.y, hr, WORLD_H - hr)

        g_range = G_RANGE
        g_power = 1.0
        if burst_sk.active:
            g_range = G_RANGE * 1.8
            g_power = 1.5

        # ---------------- 物理 & 吞噬 ----------------
        if not options_open:
            survivors = []
            for b in bodies:
                b.update_ai(hole, dt)

                dx, dy = hole.x - b.x, hole.y - b.y
                dist = max(math.hypot(dx, dy), 1e-4)

                if dist < g_range:
                    infl = 1 - dist / g_range
                    acc = 1700 * (infl ** 1.6) * (1 + hole.mass / 150) * g_power
                    b.vx += dx / dist * acc * dt
                    b.vy += dy / dist * acc * dt

                b.vx *= (1 - 0.35 * dt)
                b.vy *= (1 - 0.35 * dt)
                b.x += b.vx * dt
                b.y += b.vy * dt

                m = b.radius
                if b.x < m: b.x, b.vx = m, abs(b.vx) * 0.6
                elif b.x > WORLD_W - m: b.x, b.vx = WORLD_W - m, -abs(b.vx) * 0.6
                if b.y < m: b.y, b.vy = m, abs(b.vy) * 0.6
                elif b.y > WORLD_H - m: b.y, b.vy = WORLD_H - m, -abs(b.vy) * 0.6

                if state == "play" and dist < hole.radius + b.radius * 0.35:
                    if b.mass <= hole.mass * 1.02:
                        eat_mult = 0.5 if burst_sk.active else 1.0
                        hole.mass += b.mass * 0.7 * eat_mult
                        score += b.mass
                        hole.flash = 1.0
                        shake = min(shake + 2 + b.radius * 0.4, 16)
                        burst(particles, b.x, b.y, b.color,
                              min(70, int(5 + b.radius * 0.9)),
                              280, b.vx, b.vy)
                        if b.radius > 26:
                            audio.play("big", 0.5)
                        else:
                            audio.play("eat", 0.35)
                        unlock(save, "first_blood", toasts)

                        if b.is_boss:
                            frag_mass = b.mass / 5.0
                            for i in range(4):
                                a = random.uniform(0, math.tau)
                                d = random.uniform(100, 220)
                                frag = Body(b.x + math.cos(a) * d,
                                            b.y + math.sin(a) * d,
                                            frag_mass, hunter=True)
                                frag.vx = math.cos(a) * 220
                                frag.vy = math.sin(a) * 220
                                survivors.append(frag)
                            toasts.append(Toast("💥 BOSS 分裂！", 2.2))
                            shake = 22
                            burst(particles, b.x, b.y, (255, 220, 100), 120, 520)
                            unlock(save, "boss_kill", toasts)
                            audio.play("boss", 0.9)
                        continue

                    elif invuln.active:
                        survivors.append(b)
                        continue

                    else:
                        state = "dead"
                        death_timer = 0.0
                        shake = 24
                        audio.play("dead", 0.8)
                        burst(particles, hole.x, hole.y, (255, 120, 90), 130, 480)
                        continue

                survivors.append(b)

            bodies = survivors

            # ---------------- 关卡升级 ----------------
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
                if level >= 3:
                    unlock(save, "level_3", toasts)
                if level >= 5:
                    unlock(save, "level_5", toasts)

            # ---------------- Boss 生成 ----------------
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
                    toasts.append(Toast(
                        f"⚠ BOSS 出现！质量 {int(boss_mass)}", 3.2))
                    shake = 20
                    audio.play("boss", 1.0)

            # ---------------- 补充物体 ----------------
            if state == "play":
                if len(bodies) < BODY_COUNT:
                    spawn_timer += dt
                    if spawn_timer > 0.12:
                        spawn_timer = 0
                        bodies.append(spawn_body(hole, level_mult, hunter_chance))
                else:
                    spawn_timer = 0

            # ---------------- 粒子 ----------------
            alive = []
            for p in particles:
                p.life -= dt
                if p.life <= 0:
                    continue
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.vx *= (1 - 1.8 * dt)
                p.vy *= (1 - 1.8 * dt)
                alive.append(p)
            particles = alive

            # ---------------- 危险度 ----------------
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

            # ---------------- 成就 ----------------
            if state == "play":
                if hole.mass >= 50:  unlock(save, "mass_50", toasts)
                if hole.mass >= 100: unlock(save, "mass_100", toasts)
                if hole.mass >= 200: unlock(save, "mass_200", toasts)
                if hole.mass >= 400: unlock(save, "mass_400", toasts)
                if score >= 500:     unlock(save, "score_500", toasts)
                if time >= 60:       unlock(save, "survive_60", toasts)

            # ---------------- 死亡存档 ----------------
            if state == "dead":
                death_timer += dt
                if not saved_this_round:
                    saved_this_round = True
                    save["best_mass"] = max(save["best_mass"], hole.mass)
                    save["best_score"] = max(save["best_score"], score)
                    write_save(save)

            # ---------------- Toast 更新 ----------------
            toasts = [t for t in toasts if t.life > 0]
            for t in toasts:
                t.life -= dt

        # ---------------- 摄像机 ----------------
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

        for s in STARS:
            x = (s["x"] - cam_x * s["p"]) % W
            y = (s["y"] - cam_y * s["p"]) % H
            b = s["b"]
            pygame.draw.circle(screen, (b, b, min(255, b + 55)),
                               (int(x), int(y)), max(1, int(s["r"])))

        pygame.draw.rect(screen, (90, 70, 180),
                         (int(-cam_x), int(-cam_y), WORLD_W, WORLD_H), 4)

        # 物体
        for b in bodies:
            sx, sy = b.x - cam_x, b.y - cam_y
            if sx < -150 or sx > W + 150 or sy < -150 or sy > H + 150:
                continue
            r = max(1, int(b.radius))

            glow = (b.color[0] // 3, b.color[1] // 3, b.color[2] // 3)
            pygame.draw.circle(screen, glow, (int(sx), int(sy)), int(r * 1.8))
            pygame.draw.circle(screen, b.color, (int(sx), int(sy)), r)

            hl = (min(255, b.color[0] + 80),
                  min(255, b.color[1] + 80),
                  min(255, b.color[2] + 80))
            pygame.draw.circle(screen, hl,
                               (int(sx - r * 0.3), int(sy - r * 0.3)),
                               max(1, int(r * 0.34)))

            if b.is_boss:
                pygame.draw.circle(screen, (255, 220, 100),
                                   (int(sx), int(sy)), r + 10, 3)
                pygame.draw.circle(screen, (255, 160, 60),
                                   (int(sx), int(sy)), r + 16, 2)
            elif b.hunter:
                pygame.draw.circle(screen, (255, 150, 40),
                                   (int(sx), int(sy)), r + 3, 2)

            if state == "play" and b.mass > hole.mass and not b.is_boss:
                pygame.draw.circle(screen, (255, 70, 70),
                                   (int(sx), int(sy)), r + 6, 2)

        # 粒子
        for p in particles:
            sx, sy = p.x - cam_x, p.y - cam_y
            if sx < -30 or sx > W + 30 or sy < -30 or sy > H + 30:
                continue
            a = p.life / p.max_life
            pygame.draw.circle(screen, p.color, (int(sx), int(sy)),
                               max(1, int(p.size * a)))

        # 黑洞
        hx, hy = int(hole.x - cam_x), int(hole.y - cam_y)
        hr = max(3, int(hole.radius))
        skin = SKINS[save["skin"]]
        draw_hole(hx, hy, hr, skin, time, hole.flash, invuln.active)

        if burst_sk.active:
            wave = int(hr * 3 +
                       (1 - burst_sk.active_timer / burst_sk.dur_max) * 400)
            pygame.draw.circle(screen, (255, 200, 100),
                               (hx, hy), wave, 2)

        # 危险红晕
        if state == "play" and danger > 0.02:
            overlay.fill((255, 30, 30, int(danger * 90)))
            screen.blit(overlay, (0, 0))

        # ---------------- HUD ----------------
        f_lg = get_font(26, True)
        f_md = get_font(20)
        f_sm = get_font(15)

        screen.blit(f_lg.render(f"质量 {int(hole.mass)}", True,
                                (235, 235, 255)), (26, 26))
        screen.blit(f_lg.render(f"得分 {int(score)}", True,
                                (150, 220, 255)), (26, 62))
        screen.blit(f_md.render(
            f"关卡 {level}  皮肤 {skin['name']}  "
            f"最高质量 {int(save['best_mass'])}",
            True, (200, 180, 255)), (26, 100))

        prev_t = level_target / 1.9 if level > 1 else 22.0
        ratio = clamp((hole.mass - prev_t) / max(1, level_target - prev_t), 0, 1)
        bw, bh = 220, 8
        pygame.draw.rect(screen, (255, 255, 255), (26, 134, bw, bh), 1)
        for i in range(int(bw * ratio)):
            t = i / bw
            col = (int(56 + 199 * t), int(224 - 164 * t), int(176 - 86 * t))
            pygame.draw.line(screen, col, (26 + i, 134), (26 + i, 134 + bh))

        # ---------------- 技能栏 ----------------
        mouse_lx, mouse_ly = screen_to_logical(pygame.mouse.get_pos())
        for i, (key_name, name, sk) in enumerate(SKILL_KEYS):
            box = skill_box(i)
            ready = sk.ready
            hover = box.collidepoint(mouse_lx, mouse_ly) and state == "play" \
                    and not options_open

            if ready:
                bg_col = (30, 30, 60)
                border = (120, 120, 200)
            else:
                bg_col = (50, 20, 20)
                border = (150, 60, 60)

            if hover and ready:
                bg_col = (50, 50, 100)
                border = (180, 200, 255)

            pygame.draw.rect(screen, bg_col, box, border_radius=8)
            pygame.draw.rect(screen, border, box, 2, border_radius=8)

            text_col = (230, 230, 255) if ready else (150, 100, 100)
            if hover and ready:
                text_col = (255, 255, 255)

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

        screen.blit(f_sm.render(
            "WASD 移动 · Space 冲刺 · Q 无敌 · E 引力爆发 · F1 皮肤 · "
            "F2 编辑器 · L 加载关卡 · ESC 选项 · R 重开",
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
                screen.blit(title,
                            (W // 2 - title.get_width() // 2, H // 2 - 140))

                info = f_lg.render(
                    f"最终质量 {int(hole.mass)}  ·  得分 {int(score)}  ·  关卡 {level}",
                    True, (235, 235, 255))
                info.set_alpha(int(255 * fade))
                screen.blit(info,
                            (W // 2 - info.get_width() // 2, H // 2 - 10))

                best = f_md.render(
                    f"历史最高质量 {int(save['best_mass'])}  ·  "
                    f"最高得分 {int(save['best_score'])}",
                    True, (180, 200, 255))
                best.set_alpha(int(255 * fade))
                screen.blit(best,
                            (W // 2 - best.get_width() // 2, H // 2 + 40))

                ach = f_md.render(
                    f"成就 {len(save['unlocked'])}/{len(ACHIEVEMENTS)}",
                    True, (255, 220, 140))
                ach.set_alpha(int(255 * fade))
                screen.blit(ach,
                            (W // 2 - ach.get_width() // 2, H // 2 + 78))

                hint = f_md.render("按 R 重新开始  ·  ESC 打开选项  ·  F2 编辑器",
                                   True, (170, 170, 215))
                hint.set_alpha(int(255 * fade *
                                   (0.6 + 0.4 * math.sin(time * 5))))
                screen.blit(hint,
                            (W // 2 - hint.get_width() // 2, H // 2 + 130))

        # ---------------- 选项菜单（覆盖在最上层） ----------------
        if options_open:
            draw_options_menu()

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