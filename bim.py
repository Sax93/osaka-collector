import math
import os
import random
import sys
import platform
import pygame

pygame.init()
pygame.mixer.init()

# --- DEVICE DETECTION UTILITY ---
def detect_mobile_or_portable():
    """Detects if the platform is likely Android, iOS, or a portable mobile environment."""
    is_android = 'ANDROID_ARGUMENT' in os.environ or 'ANDROID_BOOTLOGO' in os.environ
    is_ios = sys.platform == 'darwin' and 'iOS' in platform.platform()
    plat_sys = platform.system().lower()
    is_mobile_os = any(term in plat_sys for term in ['android', 'ios', 'iphone', 'ipad'])
    
    return is_android or is_ios or is_mobile_os

# --- CONSTANTS & CONFIGURATION ---
WIDTH, HEIGHT = 1080, 720
FPS = 60

# --- GAME STATES ---
STATE_MENU = "menu"
STATE_SETTINGS = "settings"
STATE_SKINS = "skins"
STATE_INFO = "info"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_GAME_OVER = "game_over"
STATE_SECRET_OSAKA = "secret_osaka"

# --- ASSET CACHING ---
HAS_MUSIC = os.path.exists("coolADmusic.mp3")
HAS_GAMEOVER = os.path.exists("gameover.mp3")
HAS_OSAKA_MUSIC = os.path.exists("osaka.mp3")

# Sprite Placeholders
PLAYER_IMGS = {}
TARGET_IMG = None
HAZARD_IMG = None
POWERUP_OVERDRIVE_IMG = None
POWERUP_WIPE_IMG = None
EVERYNYAN_IMG = None
YUKARI_CAR_IMG = None

def load_sprite(filename, size, color):
    if os.path.exists(filename):
        img = pygame.image.load(filename).convert_alpha()
        return pygame.transform.scale(img, size)
    else:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.ellipse(surf, color, (0, 0, size[0], size[1]))
        return surf

# Audio Cache
OMAIGA_SOUND = pygame.mixer.Sound("omg.mp3") if os.path.exists("omg.mp3") else None
EVERYNYAN_SOUND = pygame.mixer.Sound("everynyan.mp3") if os.path.exists("everynyan.mp3") else None
SCREECH_SOUND = pygame.mixer.Sound("screech.mp3") if os.path.exists("screech.mp3") else None

if OMAIGA_SOUND:
    OMAIGA_SOUND.set_volume(0.5)

# --- HIGH SCORE SYSTEM ---
def load_high_score():
    if os.path.exists("highscore.txt"):
        try:
            with open("highscore.txt", "r") as f:
                return int(f.read().strip())
        except ValueError:
            return 0
    return 0

def save_high_score(new_high):
    with open("highscore.txt", "w") as f:
        f.write(str(new_high))

# --- CHARACTER STATS ---
SKIN_DATA = {
    "osaka":  {"file": "player.png",  "color": (80, 180, 255),  "base_spd": 300, "boost_spd": 540, "stam": 100, "drain": 72, "regen": 30, "buff": "Balanced (Default)"},
    "chiyo":  {"file": "player2.png", "color": (255, 180, 200), "base_spd": 280, "boost_spd": 520, "stam": 180, "drain": 50, "regen": 45, "buff": "Most Boost"},
    "kagura": {"file": "player3.png", "color": (255, 100, 100), "base_spd": 360, "boost_spd": 650, "stam": 90,  "drain": 85, "regen": 20, "buff": "Fastest"},
    "sakaki": {"file": "player4.png", "color": (100, 100, 255), "base_spd": 340, "boost_spd": 610, "stam": 130, "drain": 60, "regen": 35, "buff": "Fastest and Durable"},
    "tomo":   {"file": "player5.png", "color": (255, 140, 0),   "base_spd": 420, "boost_spd": 680, "stam": 110, "drain": 70, "regen": 50, "buff": "Hyperactive Speed"}
}

# --- UI HELPER FUNCTIONS ---
def draw_button(surf, rect, text, font, hover, is_pressed=False, alpha=255, locked=False):
    """Draws a modern tactile button with a drop shadow and a press animation."""
    if locked:
        color = (40, 45, 50, alpha)
        border_color = (80, 85, 90, alpha)
        text_color = (120, 120, 120)
    elif is_pressed:
        color = (25, 70, 160, alpha)
        border_color = (120, 160, 220, alpha)
        text_color = (255, 255, 255)
    elif hover:
        color = (60, 110, 210, alpha)
        border_color = (180, 210, 255, alpha)
        text_color = (255, 255, 255)
    else:
        color = (35, 55, 90, alpha)
        border_color = (150, 180, 240, alpha)
        text_color = (230, 240, 255)

    # Surface size increased slightly to accommodate the drop shadow
    s = pygame.Surface((rect.width, rect.height + 6), pygame.SRCALPHA)
    
    # Drop shadow
    if not is_pressed and not locked:
        pygame.draw.rect(s, (10, 15, 20, min(150, alpha)), (0, 4, rect.width, rect.height), border_radius=12)
    
    # Y-offset for physical press down effect
    y_off = 4 if is_pressed else 0
    btn_rect = pygame.Rect(0, y_off, rect.width, rect.height)
    
    # Main button body
    pygame.draw.rect(s, color, btn_rect, border_radius=12)
    pygame.draw.rect(s, border_color, btn_rect, 2, border_radius=12)
    
    # Text rendering inside button
    txt_surf = font.render(text, True, text_color)
    txt_surf.set_alpha(alpha)
    s.blit(txt_surf, ((rect.width - txt_surf.get_width()) // 2, y_off + (rect.height - txt_surf.get_height()) // 2))
    
    # Blit to main surface
    surf.blit(s, rect.topleft)

def draw_text_with_shadow(surf, text, font, color, pos, shadow_color=(15, 15, 20), offset=(2, 2), center=False):
    """Helper to render text with a clean drop shadow."""
    txt_surf = font.render(text, True, color)
    shd_surf = font.render(text, True, shadow_color)
    
    if center:
        rect = txt_surf.get_rect(center=pos)
    else:
        rect = txt_surf.get_rect(topleft=pos)
        
    surf.blit(shd_surf, (rect.x + offset[0], rect.y + offset[1]))
    surf.blit(txt_surf, rect)

# --- VIRTUAL JOYSTICK CLASS ---
class VirtualJoystick:
    def __init__(self, x, y, radius=60, knob_radius=25):
        self.center = pygame.Vector2(x, y)
        self.knob_pos = pygame.Vector2(x, y)
        self.radius = radius
        self.knob_radius = knob_radius
        self.is_active = False
        self.touch_id = None
        self.value = pygame.Vector2(0, 0)

    def handle_event(self, event, mouse_pressed):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            m_pos = pygame.Vector2(event.pos)
            if m_pos.distance_to(self.center) <= self.radius:
                self.is_active = True
                self.update_knob(m_pos)

        elif event.type == pygame.MOUSEMOTION and self.is_active:
            if mouse_pressed[0]:
                self.update_knob(pygame.Vector2(event.pos))
            else:
                self.reset()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.reset()

    def update_knob(self, pos):
        diff = pos - self.center
        dist = diff.length()
        if dist > self.radius:
            diff = diff.normalize() * self.radius
        self.knob_pos = self.center + diff
        self.value = diff / self.radius if self.radius > 0 else pygame.Vector2(0, 0)

    def reset(self):
        self.is_active = False
        self.knob_pos = pygame.Vector2(self.center)
        self.value = pygame.Vector2(0, 0)

    def draw(self, surf):
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, 30), (self.radius, self.radius), self.radius)
        pygame.draw.circle(s, (255, 255, 255, 100), (self.radius, self.radius), self.radius, 2)
        surf.blit(s, (self.center.x - self.radius, self.center.y - self.radius))

        ks = pygame.Surface((self.knob_radius * 2, self.knob_radius * 2), pygame.SRCALPHA)
        # Drop shadow for knob
        pygame.draw.circle(ks, (0, 0, 0, 50), (self.knob_radius, self.knob_radius + 3), self.knob_radius)
        pygame.draw.circle(ks, (200, 220, 255, 200), (self.knob_radius, self.knob_radius), self.knob_radius)
        pygame.draw.circle(ks, (255, 255, 255, 255), (self.knob_radius, self.knob_radius), self.knob_radius, 2)
        surf.blit(ks, (self.knob_pos.x - self.knob_radius, self.knob_pos.y - self.knob_radius))


# --- SPRITE CLASSES ---
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, skin_name):
        super().__init__()
        self.skin_name = skin_name
        stats = SKIN_DATA[skin_name]
        self.image_orig = PLAYER_IMGS[skin_name]
        self.image = self.image_orig
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.Vector2(x, y)
        self.radius = 18
        self.facing_left = False

        self.base_speed = stats["base_spd"]
        self.boost_speed = stats["boost_spd"]
        self.max_stamina = float(stats["stam"])
        self.stamina = self.max_stamina
        self.stamina_drain = float(stats["drain"])
        self.stamina_regen = float(stats["regen"])
        
        self.is_boosting = False
        self.overdrive_timer = 0.0
        self.stun_timer = 0.0
        self.pigtails_detached = False

    def detach_pigtails(self):
        if self.skin_name == "chiyo" and not self.pigtails_detached:
            self.pigtails_detached = True
            self.image_orig = load_sprite("player2e.png", (36, 36), SKIN_DATA["chiyo"]["color"])
            self.image = self.image_orig
            self.base_speed = 450
            self.boost_speed = 700
            self.max_stamina = 50.0
            self.stamina = min(self.stamina, self.max_stamina)
            return True
        return False

    def update(self, dt, keys, joystick_vec, virtual_boost_pressed, boost_particles, global_speed_mult):
        if self.stun_timer > 0:
            self.stun_timer -= dt
            return

        if self.overdrive_timer > 0:
            self.overdrive_timer -= dt
            self.stamina = self.max_stamina

        eff_base = self.base_speed * global_speed_mult
        eff_boost = self.boost_speed * global_speed_mult

        if (keys[pygame.K_LSHIFT] or virtual_boost_pressed) and self.stamina > 0:
            current_speed = eff_boost
            if self.overdrive_timer <= 0:
                self.stamina = max(0.0, self.stamina - self.stamina_drain * dt)
            self.is_boosting = True
            boost_particles.append({"pos": pygame.Vector2(self.pos), "size": 12.0})
        else:
            current_speed = eff_base
            self.stamina = min(self.max_stamina, self.stamina + self.stamina_regen * dt)
            self.is_boosting = False

        move_vec = pygame.Vector2(0, 0)
        
        if joystick_vec.length_squared() > 0.01:
            move_vec = pygame.Vector2(joystick_vec)
            if move_vec.x != 0:
                self.facing_left = move_vec.x < 0
        else:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                move_vec.x -= 1
                self.facing_left = True
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                move_vec.x += 1
                self.facing_left = False
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                move_vec.y -= 1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                move_vec.y += 1
            if move_vec.length_squared() > 0:
                move_vec = move_vec.normalize()

        self.pos += move_vec * current_speed * dt
        self.pos.x = max(self.radius, min(WIDTH - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(HEIGHT - self.radius, self.pos.y))
        
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.image = pygame.transform.flip(self.image_orig, True, False) if self.facing_left else self.image_orig

class DetachedPigtail(pygame.sprite.Sprite):
    def __init__(self, pos, angle):
        super().__init__()
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * 350
        self.radius = 8
        self.image = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (255, 180, 200), (0, 0, 16, 8))
        pygame.draw.ellipse(self.image, (100, 50, 50), (2, 2, 12, 4))
        self.rect = self.image.get_rect(center=(int(pos.x), int(pos.y)))
        self.life = 3.0

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.kill()
            return
        self.pos += self.vel * dt
        self.vel *= 0.95
        self.rect.center = (int(self.pos.x), int(self.pos.y))

class Target(pygame.sprite.Sprite):
    def __init__(self, player_skin):
        super().__init__()
        self.type = "normal"
        self.player_skin = player_skin
        self.image = TARGET_IMG
        self.radius = 14
        self.pos = pygame.Vector2(0, 0)
        self.rect = self.image.get_rect()
        self.reposition(player_skin)

    def reposition(self, player_skin):
        self.player_skin = player_skin
        self.pos = pygame.Vector2(random.randint(40, WIDTH - 40), random.randint(40, HEIGHT - 40))
        
        if self.player_skin == "sakaki":
            rand_val = random.random()
            if rand_val < 0.25:
                self.type = "kamineko"
                self.image = load_sprite("kamineko.png", (30, 30), (160, 160, 160))
            elif rand_val < 0.35:
                self.type = "maya"
                self.image = load_sprite("maya.png", (32, 32), (220, 140, 50))
            else:
                self.type = "normal"
                self.image = TARGET_IMG
        else:
            self.type = "normal"
            self.image = TARGET_IMG

        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))

    def update(self, dt):
        float_offset = math.sin(pygame.time.get_ticks() * 0.005) * 4
        self.rect.center = (int(self.pos.x), int(self.pos.y + float_offset))

class Hazard(pygame.sprite.Sprite):
    def __init__(self, pos, vel, hazard_type, speed_mult):
        super().__init__()
        self.type = hazard_type
        if self.type == "yukari_mobile":
            self.image = YUKARI_CAR_IMG
        else:
            self.image = HAZARD_IMG

        self.rect = self.image.get_rect(center=(int(pos.x), int(pos.y)))
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.radius = 18 if self.type == "yukari_mobile" else 15
        self.speed_mult = speed_mult

    def update(self, dt, player_pos):
        if self.type == "bird":
            self.pos += self.vel * dt
            self.rect.center = (int(self.pos.x), int(self.pos.y))
            if self.pos.y < -30:
                self.kill()
            return

        if self.type == "homing":
            dir_to_player = player_pos - self.pos
            if dir_to_player.length() > 0:
                desired_vel = dir_to_player.normalize() * 180 * self.speed_mult
                self.vel = self.vel.lerp(desired_vel, 1.5 * dt)

        self.pos += self.vel * dt

        if self.pos.x - self.radius <= 0 or self.pos.x + self.radius >= WIDTH:
            self.vel.x *= -1
            self.pos.x = max(self.radius, min(WIDTH - self.radius, self.pos.x))
        if self.pos.y - self.radius <= 0 or self.pos.y + self.radius >= HEIGHT:
            self.vel.y *= -1
            self.pos.y = max(self.radius, min(HEIGHT - self.radius, self.pos.y))

        self.rect.center = (int(self.pos.x), int(self.pos.y))

class HazardWarning:
    def __init__(self, target_pos, delay=0.8):
        self.pos = pygame.Vector2(target_pos)
        self.timer = delay
        self.max_delay = delay
        self.is_ready = False

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            self.is_ready = True

    def draw(self, surf):
        alpha = int((1.0 - (self.timer / self.max_delay)) * 255)
        pulse = math.sin(pygame.time.get_ticks() * 0.02) * 4
        warn_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(warn_surf, (255, 60, 80, min(255, max(50, alpha))), (20, 20), int(15 + pulse), 2)
        surf.blit(warn_surf, warn_surf.get_rect(center=(int(self.pos.x), int(self.pos.y))))

class Powerup(pygame.sprite.Sprite):
    def __init__(self, pos, p_type):
        super().__init__()
        self.type = p_type
        if p_type == "everynyan":
            self.image = EVERYNYAN_IMG
        elif p_type == "overdrive":
            self.image = POWERUP_OVERDRIVE_IMG
        else:
            self.image = POWERUP_WIPE_IMG

        self.rect = self.image.get_rect(center=(int(pos.x), int(pos.y)))
        self.pos = pygame.Vector2(pos)
        self.radius = 12
        self.life = 8.0

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.kill()
            return
        float_offset = math.sin(pygame.time.get_ticks() * 0.005) * 4
        self.rect.center = (int(self.pos.x), int(self.pos.y + float_offset))


# --- MAIN GAME CLASS ---
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Osaka Collector - Enhanced UI!")

        global PLAYER_IMGS, TARGET_IMG, HAZARD_IMG, POWERUP_OVERDRIVE_IMG, POWERUP_WIPE_IMG, EVERYNYAN_IMG, YUKARI_CAR_IMG
        
        for name, data in SKIN_DATA.items():
            PLAYER_IMGS[name] = load_sprite(data["file"], (36, 36), data["color"])
            
        TARGET_IMG = load_sprite("target.png", (28, 28), (50, 255, 150))
        HAZARD_IMG = load_sprite("hazard.png", (30, 30), (255, 60, 80))
        POWERUP_OVERDRIVE_IMG = load_sprite("overdrive.png", (24, 24), (255, 215, 0))
        POWERUP_WIPE_IMG = load_sprite("wipe.png", (24, 24), (200, 200, 255))
        EVERYNYAN_IMG = load_sprite("everynyan.png", (32, 32), (255, 80, 80))
        YUKARI_CAR_IMG = load_sprite("yukari_car.png", (42, 26), (240, 220, 40))

        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Verdana", 28, bold=True)
        self.small_font = pygame.font.SysFont("Verdana", 18)
        self.title_font = pygame.font.SysFont("Impact", 72)

        self.current_state = STATE_MENU
        self.high_score = load_high_score()
        self.selected_skin = "osaka"

        # Secret Easter Egg Variables
        self.secret_input_buffer = ""
        self.dvd_pos = pygame.Vector2(WIDTH // 2, HEIGHT // 2)
        self.dvd_vel = pygame.Vector2(250, 250)
        self.dvd_image = load_sprite("player.png", (120, 120), (80, 180, 255))

        # Gameplay Tuning
        self.global_speed_mult = 1.0
        self.hazard_spawn_rate = 3

        # Mobile/Portable Joystick & Control Options
        self.show_touch_controls = detect_mobile_or_portable()
        self.joystick = VirtualJoystick(100, HEIGHT - 100, radius=65, knob_radius=25)

        # Idle Timer for "Tukurikake no Uta"
        self.menu_idle_timer = 0.0

        # Juice / Screen Shake
        self.shake_timer = 0.0
        self.shake_intensity = 0
        self.boost_particles = []
        self.pickup_particles = []
        self.hazard_warnings = []
        self.easter_egg_sprites = pygame.sprite.Group()

        # Touch Virtual Controls
        self.virtual_boost_btn = pygame.Rect(WIDTH - 140, HEIGHT - 140, 110, 110)

        # Dynamic Centralized UI Layouts
        cx = WIDTH // 2 - 120
        b_width, b_height = 240, 55
        self.play_btn = pygame.Rect(cx, 240, b_width, b_height)
        self.settings_btn = pygame.Rect(cx, 310, b_width, b_height)
        self.info_btn = pygame.Rect(cx, 380, b_width, b_height)
        self.exit_btn = pygame.Rect(cx, 450, b_width, b_height)

        self.resume_btn = pygame.Rect(cx, 280, b_width, b_height)
        self.menu_btn = pygame.Rect(cx, 360, b_width, b_height)

        # Settings Screen UI Elements
        set_x = 420
        self.speed_btn = pygame.Rect(set_x, 180, 260, 45)
        self.hazard_btn = pygame.Rect(set_x, 240, 260, 45)
        self.touch_toggle_btn = pygame.Rect(set_x, 300, 260, 45)
        self.go_skins_btn = pygame.Rect(set_x, 360, 260, 45)
        self.back_btn = pygame.Rect(cx, 480, b_width, b_height)

        # Skin Buttons
        sk_width, sk_height = 240, 45
        self.osaka_btn = pygame.Rect(cx, 160, sk_width, sk_height)
        self.chiyo_btn = pygame.Rect(cx, 220, sk_width, sk_height)
        self.kagura_btn = pygame.Rect(cx, 280, sk_width, sk_height)
        self.sakaki_btn = pygame.Rect(cx, 340, sk_width, sk_height)
        self.tomo_btn = pygame.Rect(cx, 400, sk_width, sk_height)

        # Entities
        self.player = Player(400, 300, self.selected_skin)
        self.target = Target(self.selected_skin)
        self.hazards = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()

        self.score = 0
        self.game_over_msg = ""

        if HAS_MUSIC:
            pygame.mixer.music.load("coolADmusic.mp3")
            pygame.mixer.music.play(loops=-1)

    def trigger_pickup_particles(self, pos, color=(50, 255, 150)):
        for _ in range(12):
            vel = pygame.Vector2(random.uniform(-150, 150), random.uniform(-150, 150))
            self.pickup_particles.append({
                "pos": pygame.Vector2(pos), 
                "vel": vel, 
                "radius": random.uniform(4, 8), 
                "life": 0.4, 
                "color": color
            })

    def queue_hazard_spawn(self):
        pos = pygame.Vector2(random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50))
        while pos.distance_to(self.player.pos) < 150:
            pos = pygame.Vector2(random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50))
        self.hazard_warnings.append(HazardWarning(pos))

    def create_hazard_at(self, pos):
        speed_multiplier = 1.0 + (self.score * 0.02)
        hazard_type = random.choices(["bouncer", "homing", "sweeper", "yukari_mobile"], weights=[55, 20, 10, 15])[0]
        
        if hazard_type == "yukari_mobile":
            vx = random.choice([-750, 750]) * speed_multiplier
            vy = 0
            if SCREECH_SOUND:
                SCREECH_SOUND.play()
        elif hazard_type == "sweeper":
            if random.random() > 0.5:
                vx, vy = random.choice([-500, 500]) * speed_multiplier, 0
            else:
                vx, vy = 0, random.choice([-500, 500]) * speed_multiplier
        elif hazard_type == "homing":
            vx, vy = random.choice([-150, 150]) * speed_multiplier, random.choice([-150, 150]) * speed_multiplier
        else:
            vx, vy = random.choice([-240, 240]) * speed_multiplier, random.choice([-180, 180]) * speed_multiplier

        hazard = Hazard(pos, (vx, vy), hazard_type, speed_multiplier)
        self.hazards.add(hazard)

    def spawn_powerup(self):
        pos = pygame.Vector2(random.randint(40, WIDTH - 40), random.randint(40, HEIGHT - 40))
        p_type = random.choices(["overdrive", "wipe", "everynyan"], weights=[45, 45, 10])[0]
        self.powerups.add(Powerup(pos, p_type))

    def reset_game(self):
        self.score = 0
        self.hazards.empty()
        self.powerups.empty()
        self.easter_egg_sprites.empty()
        self.hazard_warnings.clear()
        self.boost_particles.clear()
        self.pickup_particles.clear()
        self.player = Player(400, 300, self.selected_skin)
        self.target.reposition(self.selected_skin)
        self.joystick.reset()
        self.shake_timer = 0.0
        self.queue_hazard_spawn()
        self.queue_hazard_spawn()
        self.game_over_msg = ""

    def update_dynamic_audio(self):
        if not HAS_MUSIC or self.current_state == STATE_SECRET_OSAKA:
            return
        if self.player.is_boosting:
            pygame.mixer.music.set_volume(0.9)
        else:
            pygame.mixer.music.set_volume(0.67)

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if self.current_state == STATE_PLAYING and self.show_touch_controls:
                self.joystick.handle_event(event, mouse_pressed)

            if self.current_state == STATE_MENU:
                self.menu_idle_timer = 0.0
                if event.type == pygame.KEYDOWN:
                    if event.unicode.isalpha():
                        self.secret_input_buffer += event.unicode.lower()
                        if len(self.secret_input_buffer) > 5:
                            self.secret_input_buffer = self.secret_input_buffer[-5:]
                        
                        if self.secret_input_buffer == "osaka":
                            self.secret_input_buffer = ""
                            self.dvd_pos = pygame.Vector2(random.randint(100, WIDTH - 100), random.randint(100, HEIGHT - 100))
                            vx = random.choice([-250, 250])
                            vy = random.choice([-250, 250])
                            self.dvd_vel = pygame.Vector2(vx, vy)
                            self.current_state = STATE_SECRET_OSAKA

                            if HAS_OSAKA_MUSIC:
                                pygame.mixer.music.load("osaka.mp3")
                                pygame.mixer.music.play(loops=-1)

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.play_btn.collidepoint(mouse_pos):
                        self.reset_game()
                        self.current_state = STATE_PLAYING
                        if HAS_MUSIC:
                            pygame.mixer.music.load("coolADmusic.mp3")
                            pygame.mixer.music.play(loops=-1)
                    elif self.settings_btn.collidepoint(mouse_pos):
                        self.current_state = STATE_SETTINGS
                    elif self.info_btn.collidepoint(mouse_pos):
                        self.current_state = STATE_INFO
                    elif self.exit_btn.collidepoint(mouse_pos):
                        return False

            elif self.current_state == STATE_SECRET_OSAKA:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    dvd_rect = self.dvd_image.get_rect(topleft=(int(self.dvd_pos.x), int(self.dvd_pos.y)))
                    if dvd_rect.collidepoint(mouse_pos):
                        if OMAIGA_SOUND:
                            OMAIGA_SOUND.play()

                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.current_state = STATE_MENU
                    if HAS_MUSIC:
                        pygame.mixer.music.load("coolADmusic.mp3")
                        pygame.mixer.music.play(loops=-1)

            elif self.current_state == STATE_SETTINGS:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.speed_btn.collidepoint(mouse_pos):
                        self.global_speed_mult = 1.4 if self.global_speed_mult == 1.0 else 1.0
                    elif self.hazard_btn.collidepoint(mouse_pos):
                        self.hazard_spawn_rate = 2 if self.hazard_spawn_rate == 3 else 3
                    elif self.touch_toggle_btn.collidepoint(mouse_pos):
                        self.show_touch_controls = not self.show_touch_controls
                    elif self.go_skins_btn.collidepoint(mouse_pos):
                        self.current_state = STATE_SKINS
                    elif self.back_btn.collidepoint(mouse_pos):
                        self.current_state = STATE_MENU

            elif self.current_state == STATE_SKINS:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.osaka_btn.collidepoint(mouse_pos):
                        self.selected_skin = "osaka"
                    elif self.chiyo_btn.collidepoint(mouse_pos) and self.high_score >= 25:
                        self.selected_skin = "chiyo"
                    elif self.kagura_btn.collidepoint(mouse_pos) and self.high_score >= 50:
                        self.selected_skin = "kagura"
                    elif self.sakaki_btn.collidepoint(mouse_pos) and self.high_score >= 80:
                        self.selected_skin = "sakaki"
                    elif self.tomo_btn.collidepoint(mouse_pos) and self.high_score >= 100:
                        self.selected_skin = "tomo"
                    elif self.back_btn.collidepoint(mouse_pos):
                        self.current_state = STATE_SETTINGS

            elif self.current_state == STATE_INFO:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.back_btn.collidepoint(mouse_pos):
                        self.current_state = STATE_MENU

            elif self.current_state == STATE_PLAYING:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_1] and keys[pygame.K_2]:
                    if self.player.detach_pigtails():
                        self.shake_timer = 0.4
                        self.shake_intensity = 8
                        self.easter_egg_sprites.add(DetachedPigtail(self.player.pos, math.pi * 0.75))
                        self.easter_egg_sprites.add(DetachedPigtail(self.player.pos, math.pi * 0.25))

                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                    self.current_state = STATE_PAUSED

            elif self.current_state == STATE_PAUSED:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                    self.current_state = STATE_PLAYING
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.resume_btn.collidepoint(mouse_pos):
                        self.current_state = STATE_PLAYING
                    elif self.menu_btn.collidepoint(mouse_pos):
                        self.current_state = STATE_MENU
                        if HAS_MUSIC:
                            pygame.mixer.music.load("coolADmusic.mp3")
                            pygame.mixer.music.play(loops=-1)

            elif self.current_state == STATE_GAME_OVER:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    self.reset_game()
                    self.current_state = STATE_PLAYING
                    if HAS_MUSIC:
                        pygame.mixer.music.load("coolADmusic.mp3")
                        pygame.mixer.music.play(loops=-1)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.current_state = STATE_MENU
                    if HAS_MUSIC:
                        pygame.mixer.music.load("coolADmusic.mp3")
                        pygame.mixer.music.play(loops=-1)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.reset_game()
                    self.current_state = STATE_PLAYING
                    if HAS_MUSIC:
                        pygame.mixer.music.load("coolADmusic.mp3")
                        pygame.mixer.music.play(loops=-1)

        return True

    def update(self, dt):
        if self.current_state == STATE_MENU:
            self.menu_idle_timer += dt
            return

        elif self.current_state == STATE_SECRET_OSAKA:
            w, h = self.dvd_image.get_width(), self.dvd_image.get_height()
            self.dvd_pos += self.dvd_vel * dt

            if self.dvd_pos.x <= 0:
                self.dvd_pos.x = 0
                self.dvd_vel.x *= -1
            elif self.dvd_pos.x + w >= WIDTH:
                self.dvd_pos.x = WIDTH - w
                self.dvd_vel.x *= -1

            if self.dvd_pos.y <= 0:
                self.dvd_pos.y = 0
                self.dvd_vel.y *= -1
            elif self.dvd_pos.y + h >= HEIGHT:
                self.dvd_pos.y = HEIGHT - h
                self.dvd_vel.y *= -1
            return

        if self.current_state != STATE_PLAYING:
            return

        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        
        virtual_boost_pressed = (
            self.show_touch_controls and 
            mouse_pressed[0] and 
            self.virtual_boost_btn.collidepoint(mouse_pos)
        )

        joystick_vec = self.joystick.value if self.show_touch_controls else pygame.Vector2(0, 0)

        # Update Player
        self.player.update(dt, keys, joystick_vec, virtual_boost_pressed,
                           self.boost_particles, self.global_speed_mult)
        
        self.update_dynamic_audio()
        self.target.update(dt)

        # Target Collection Check
        if pygame.sprite.collide_circle(self.player, self.target):
            if self.target.type == "kamineko":
                self.player.stun_timer = 0.5
                self.player.stamina = max(0.0, self.player.stamina - 30.0)
                self.trigger_pickup_particles(self.target.pos, (255, 60, 60))
            elif self.target.type == "maya":
                self.score += 3
                self.player.overdrive_timer = 3.0
                self.trigger_pickup_particles(self.target.pos, (255, 200, 50))
            else:
                if OMAIGA_SOUND: 
                    OMAIGA_SOUND.play()
                self.trigger_pickup_particles(self.target.pos)
                self.score += 1

            if self.score > self.high_score:
                self.high_score = self.score
                save_high_score(self.high_score)
                self.shake_timer = 0.2
                self.shake_intensity = 5

            self.target.reposition(self.selected_skin)
            if self.score % self.hazard_spawn_rate == 0:
                self.queue_hazard_spawn()

            if self.score > 2 and random.random() < 0.25 and len(self.powerups) < 2:
                self.spawn_powerup()

        # Process Spawn Warnings
        for warn in self.hazard_warnings[:]:
            warn.update(dt)
            if warn.is_ready:
                self.create_hazard_at(warn.pos)
                self.hazard_warnings.remove(warn)

        self.hazards.update(dt, self.player.pos)

        # Hazard Collisions
        if pygame.sprite.spritecollide(self.player, self.hazards, False, pygame.sprite.collide_circle):
            self.current_state = STATE_GAME_OVER
            self.shake_timer = 0.3
            self.shake_intensity = 10
            if OMAIGA_SOUND: 
                OMAIGA_SOUND.stop()
            if HAS_GAMEOVER:
                pygame.mixer.music.load("gameover.mp3")
                pygame.mixer.music.play(loops=0)

            motl = ["That's not Azumanga DaCOOL :(", "Omaigaa!", "whers ur kboard", 
                    "i am a fking architect", "sataa andagi", "osaka mirando pa un lao", 
                    "move da dam osaka", "afk?", "0.0000001% poss will he make it",
                    "skill issue", "Chiyo's pigtails flew away!", "I wish I were a bird!",
                    "Hello Everynyan!", "Yukari-sensei took the wheel!", "Kamineko bit your hand!",
                    "Tukurikake no song~", "lets larp", "larpgod"]
            self.game_over_msg = random.choice(motl)

        # Update Powerups
        self.powerups.update(dt)
        p_collisions = pygame.sprite.spritecollide(self.player, self.powerups, True, pygame.sprite.collide_circle)
        for p in p_collisions:
            if p.type == "everynyan":
                if EVERYNYAN_SOUND:
                    EVERYNYAN_SOUND.play()
                for h in self.hazards:
                    h.type = "bird"
                    h.vel = pygame.Vector2(0, -80)
                    h.image = load_sprite("bird.png", (24, 24), (200, 220, 255))
                self.trigger_pickup_particles(p.pos, (255, 100, 100))
            elif p.type == "overdrive":
                self.player.overdrive_timer = 5.0
                self.trigger_pickup_particles(p.pos, (255, 215, 0))
            elif p.type == "wipe":
                self.hazards.empty()
                self.hazard_warnings.clear()
                self.trigger_pickup_particles(p.pos, (255, 255, 255))
                self.shake_timer = 0.5
                self.shake_intensity = 15

        # Update Particle & Easter Egg Systems
        self.easter_egg_sprites.update(dt)

        for p in self.boost_particles: 
            p["size"] -= 36.0 * dt
        self.boost_particles = [p for p in self.boost_particles if p["size"] > 0]

        for p in self.pickup_particles:
            p["pos"] += p["vel"] * dt
            p["life"] -= dt
        self.pickup_particles = [p for p in self.pickup_particles if p["life"] > 0]

    def render(self, dt):
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()

        render_offset = pygame.Vector2(0, 0)
        if self.shake_timer > 0:
            self.shake_timer -= dt
            render_offset = pygame.Vector2(
                random.randint(-self.shake_intensity, self.shake_intensity), 
                random.randint(-self.shake_intensity, self.shake_intensity)
            )

        render_surf = pygame.Surface((WIDTH, HEIGHT))
        render_surf.fill((22, 28, 40)) # Slightly lighter and richer background

        if self.current_state == STATE_MENU:
            draw_text_with_shadow(render_surf, "OSAKA COLLECTOR", self.title_font, (255, 225, 60), (WIDTH // 2, 90), center=True)
            
            if self.menu_idle_timer > 15.0:
                draw_text_with_shadow(render_surf, "♪ Tukurikake no song... tukurikake no song... ♪", self.small_font, (200, 220, 255), (WIDTH // 2, 160), center=True)

            draw_button(render_surf, self.play_btn, "PLAY", self.font, self.play_btn.collidepoint(mouse_pos), mouse_pressed[0])
            draw_button(render_surf, self.settings_btn, "SETTINGS", self.font, self.settings_btn.collidepoint(mouse_pos), mouse_pressed[0])
            draw_button(render_surf, self.info_btn, "INFO", self.font, self.info_btn.collidepoint(mouse_pos), mouse_pressed[0])
            draw_button(render_surf, self.exit_btn, "EXIT", self.font, self.exit_btn.collidepoint(mouse_pos), mouse_pressed[0])

        elif self.current_state == STATE_SECRET_OSAKA:
            render_surf.fill((0, 0, 0))
            render_surf.blit(self.dvd_image, (int(self.dvd_pos.x), int(self.dvd_pos.y)))

        elif self.current_state == STATE_SETTINGS:
            draw_text_with_shadow(render_surf, "SETTINGS", self.title_font, (255, 225, 60), (WIDTH // 2, 80), center=True)
            
            draw_text_with_shadow(render_surf, "Speed Mult:", self.font, (240, 240, 255), (220, 185))
            spd_val = "1.4x FAST" if self.global_speed_mult > 1.0 else "1.0x NORMAL"
            draw_button(render_surf, self.speed_btn, spd_val, self.font, self.speed_btn.collidepoint(mouse_pos), mouse_pressed[0])
            
            draw_text_with_shadow(render_surf, "Hazard Rate:", self.font, (240, 240, 255), (220, 245))
            hz_val = "HARD (Every 2)" if self.hazard_spawn_rate == 2 else "NORMAL (Every 3)"
            draw_button(render_surf, self.hazard_btn, hz_val, self.font, self.hazard_btn.collidepoint(mouse_pos), mouse_pressed[0])

            draw_text_with_shadow(render_surf, "Touch UI:", self.font, (240, 240, 255), (220, 305))
            touch_val = "ON (VISIBLE)" if self.show_touch_controls else "OFF (HIDDEN)"
            draw_button(render_surf, self.touch_toggle_btn, touch_val, self.font, self.touch_toggle_btn.collidepoint(mouse_pos), mouse_pressed[0])

            draw_text_with_shadow(render_surf, "Character:", self.font, (240, 240, 255), (220, 365))
            draw_button(render_surf, self.go_skins_btn, "SELECT SKIN", self.font, self.go_skins_btn.collidepoint(mouse_pos), mouse_pressed[0])

            draw_button(render_surf, self.back_btn, "BACK", self.font, self.back_btn.collidepoint(mouse_pos), mouse_pressed[0])

        elif self.current_state == STATE_SKINS:
            draw_text_with_shadow(render_surf, "SELECT CHARACTER", self.title_font, (255, 225, 60), (WIDTH // 2, 70), center=True)

            def format_btn(name, req):
                sel = " [X]" if self.selected_skin == name.lower() else ""
                if self.high_score >= req:
                    return f"{name}{sel}", False
                return f"Locked (HS: {req})", True

            os_txt, os_lck = format_btn("Osaka", 0)
            ch_txt, ch_lck = format_btn("Chiyo", 25)
            ka_txt, ka_lck = format_btn("Kagura", 50)
            sa_txt, sa_lck = format_btn("Sakaki", 80)
            tm_txt, tm_lck = format_btn("Tomo", 100)

            draw_button(render_surf, self.osaka_btn, os_txt, self.font, self.osaka_btn.collidepoint(mouse_pos), mouse_pressed[0], locked=os_lck)
            draw_button(render_surf, self.chiyo_btn, ch_txt, self.font, self.chiyo_btn.collidepoint(mouse_pos), mouse_pressed[0], locked=ch_lck)
            draw_button(render_surf, self.kagura_btn, ka_txt, self.font, self.kagura_btn.collidepoint(mouse_pos), mouse_pressed[0], locked=ka_lck)
            draw_button(render_surf, self.sakaki_btn, sa_txt, self.font, self.sakaki_btn.collidepoint(mouse_pos), mouse_pressed[0], locked=sa_lck)
            draw_button(render_surf, self.tomo_btn, tm_txt, self.font, self.tomo_btn.collidepoint(mouse_pos), mouse_pressed[0], locked=tm_lck)

            draw_button(render_surf, self.back_btn, "BACK", self.font, self.back_btn.collidepoint(mouse_pos), mouse_pressed[0])

        elif self.current_state == STATE_INFO:
            draw_text_with_shadow(render_surf, "INFO & CHARACTERS", self.title_font, (255, 225, 60), (WIDTH // 2, 40), center=True)
            
            start_y, spacing = 110, 50
            
            mech_x, mech_txt_x = 80, 130
            render_surf.blit(TARGET_IMG, (mech_x, start_y))
            draw_text_with_shadow(render_surf, "TARGET: Collect to increase score.", self.small_font, (240, 240, 255), (mech_txt_x, start_y + 5))
            
            render_surf.blit(HAZARD_IMG, (mech_x, start_y + spacing))
            draw_text_with_shadow(render_surf, "HAZARDS: Bouncers, Homers, Yukari Mobile!", self.small_font, (255, 100, 100), (mech_txt_x, start_y + spacing + 5))

            render_surf.blit(POWERUP_OVERDRIVE_IMG, (mech_x, start_y + spacing * 2))
            draw_text_with_shadow(render_surf, "OVERDRIVE: Infinite stamina for 5s.", self.small_font, (255, 225, 60), (mech_txt_x, start_y + spacing * 2 + 5))

            render_surf.blit(EVERYNYAN_IMG, (mech_x, start_y + spacing * 3))
            draw_text_with_shadow(render_surf, "EVERYNYAN: Outnumbers hazards ig.", self.small_font, (255, 140, 220), (mech_txt_x, start_y + spacing * 3 + 5))

            char_x, char_txt_x = 550, 600
            render_surf.blit(PLAYER_IMGS["osaka"], (char_x, start_y))
            draw_text_with_shadow(render_surf, "Osaka: Balanced", self.small_font, (120, 200, 255), (char_txt_x, start_y + 10))

            render_surf.blit(PLAYER_IMGS["chiyo"], (char_x, start_y + spacing))
            draw_text_with_shadow(render_surf, "Chiyo: Most Boost", self.small_font, (255, 180, 200), (char_txt_x, start_y + spacing + 10))

            render_surf.blit(PLAYER_IMGS["kagura"], (char_x, start_y + spacing * 2))
            draw_text_with_shadow(render_surf, "Kagura: Fast Sprinter", self.small_font, (255, 120, 120), (char_txt_x, start_y + spacing * 2 + 10))

            render_surf.blit(PLAYER_IMGS["sakaki"], (char_x, start_y + spacing * 3))
            draw_text_with_shadow(render_surf, "Sakaki: Cat encounters (Kamineko/Maya)", self.small_font, (140, 140, 255), (char_txt_x, start_y + spacing * 3 + 10))

            render_surf.blit(PLAYER_IMGS["tomo"], (char_x, start_y + spacing * 4))
            draw_text_with_shadow(render_surf, "Tomo: Hyperactive Speed Demon (trust me)", self.small_font, (255, 160, 40), (char_txt_x, start_y + spacing * 4 + 10))

            # Dynamically push BACK button to bottom based on screen setup
            self.back_btn.top = start_y + spacing * 6
            draw_button(render_surf, self.back_btn, "BACK", self.font, self.back_btn.collidepoint(mouse_pos), mouse_pressed[0])

        elif self.current_state in (STATE_PLAYING, STATE_PAUSED):
            for p in self.boost_particles:
                pygame.draw.circle(render_surf, (255, 180, 50), (int(p["pos"].x), int(p["pos"].y)), int(p["size"]))

            for p in self.pickup_particles:
                alpha_ratio = max(0, p["life"] / 0.4)
                c = p.get("color", (50, 255, 150))
                color = (int(c[0] * alpha_ratio), int(c[1] * alpha_ratio), int(c[2] * alpha_ratio))
                pygame.draw.circle(render_surf, color, (int(p["pos"].x), int(p["pos"].y)), int(p["radius"]))

            for warn in self.hazard_warnings:
                warn.draw(render_surf)

            render_surf.blit(self.target.image, self.target.rect)
            self.powerups.draw(render_surf)
            self.hazards.draw(render_surf)
            self.easter_egg_sprites.draw(render_surf)
            render_surf.blit(self.player.image, self.player.rect)

            draw_text_with_shadow(render_surf, f"Score: {self.score}", self.font, (255, 255, 255), (20, 20))
            draw_text_with_shadow(render_surf, f"High Score: {self.high_score}", self.font, (255, 225, 60), (20, 55))

            if self.player.pigtails_detached:
                draw_text_with_shadow(render_surf, "CHIYO DETACHED PIGTAILS MODE!", self.small_font, (255, 140, 220), (20, 125))

            # Upgraded Stamina Bar Rendering
            bar_x, bar_y, bar_width, bar_height = 20, 95, 180, 20
            fill_width = int((self.player.stamina / self.player.max_stamina) * bar_width)
            
            if self.player.overdrive_timer > 0:
                bar_color = (255, 225, 60)
                fill_width = bar_width
            else:
                bar_color = (255, 180, 50) if self.player.is_boosting else (100, 200, 255)

            # Bar shadow, background, fill, and border with smooth rounded corners
            pygame.draw.rect(render_surf, (15, 15, 20), (bar_x + 2, bar_y + 3, bar_width, bar_height), border_radius=10)
            pygame.draw.rect(render_surf, (40, 45, 55), (bar_x, bar_y, bar_width, bar_height), border_radius=10)
            if fill_width > 0:
                pygame.draw.rect(render_surf, bar_color, (bar_x, bar_y, fill_width, bar_height), border_radius=10)
            pygame.draw.rect(render_surf, (220, 230, 240), (bar_x, bar_y, bar_width, bar_height), 2, border_radius=10)

            if self.show_touch_controls:
                self.joystick.draw(render_surf)
                draw_button(render_surf, self.virtual_boost_btn, "BOOST", self.font, self.virtual_boost_btn.collidepoint(mouse_pos), mouse_pressed[0], alpha=180)

            if self.current_state == STATE_PAUSED:
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((10, 15, 25, 200)) # Darker, richer overlay
                render_surf.blit(overlay, (0, 0))

                draw_text_with_shadow(render_surf, "PAUSED", self.title_font, (255, 225, 60), (WIDTH // 2, 160), center=True)

                draw_button(render_surf, self.resume_btn, "RESUME", self.font, self.resume_btn.collidepoint(mouse_pos), mouse_pressed[0])
                draw_button(render_surf, self.menu_btn, "MENU", self.font, self.menu_btn.collidepoint(mouse_pos), mouse_pressed[0])

        elif self.current_state == STATE_GAME_OVER:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((30, 10, 15, 210)) # Red-tinted dark overlay
            render_surf.blit(overlay, (0, 0))

            draw_text_with_shadow(render_surf, "GAME OVER!", self.title_font, (255, 100, 100), (WIDTH // 2, HEIGHT // 2 - 100), center=True)
            draw_text_with_shadow(render_surf, f"Final Score: {self.score}  |  Best: {self.high_score}", self.font, (255, 225, 60), (WIDTH // 2, HEIGHT // 2 - 20), center=True)
            draw_text_with_shadow(render_surf, f"- {self.game_over_msg} -", self.small_font, (255, 200, 150), (WIDTH // 2, HEIGHT // 2 + 25), center=True)
            
            draw_text_with_shadow(render_surf, "Press 'R' or Click to Restart", self.font, (240, 240, 255), (WIDTH // 2, HEIGHT // 2 + 80), center=True)
            draw_text_with_shadow(render_surf, "Press 'ESC' for Menu", self.small_font, (150, 160, 180), (WIDTH // 2, HEIGHT // 2 + 120), center=True)

        self.screen.blit(render_surf, render_offset)
        pygame.display.flip()

# --- GAME LOOP ---
if __name__ == "__main__":
    game = Game()
    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0
        running = game.handle_events()
        game.update(dt)
        game.render(dt)

    pygame.quit()