import os
import pygame
import random
import math
import gc
from pygame.locals import *

# --- Configuration Constants ---
SCREEN_WIDTH, SCREEN_HEIGHT = 720, 1280
FPS = 60
SCALE = SCREEN_WIDTH / 720.0

WHITE, BLACK, RED, BLUE, GREEN, ORANGE = (
    255,)*3, (0,)*3, (255, 0, 0), (30, 80, 250), (0, 150, 0), (255, 140, 0)

# --- Initialization ---
os.environ['PYGAME_BLEND_ALPHA_SDL2'] = '1'
IS_ANDROID = 'ANDROID_ARGUMENT' in os.environ or 'ANDROID_PRIVATE' in os.environ
BASE_PATH = os.path.dirname(os.path.abspath(__file__))


def get_path(relative_path):
    return os.path.join(BASE_PATH, relative_path)


pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
clock = pygame.time.Clock()

if IS_ANDROID:
    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.FULLSCREEN)
else:
    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE)

pygame.display.set_caption("Flappy Bird Precision")

# --- Constants ---
GROUND_LEVEL = int(SCREEN_HEIGHT * 0.85)
PIPE_GAP = int(SCREEN_HEIGHT * 0.18)
PIPE_FREQ = 1.5
SCROLL_SPEED = 300.0
BG_SCROLL_SPEED = 80.0
GRAVITY = 2500.0
JUMP_STRENGTH = -750.0
SHAKE_INTENSITY = 15.0
SHAKE_DURATION = 0.4
MAX_FALL_SPEED = 1500.0

try:
    font_path = get_path('04B_19.ttf')
    font = pygame.font.Font(font_path, 80)
    ui_font = pygame.font.Font(font_path, 45)
except:
    font = pygame.font.SysFont('Arial', 80)
    ui_font = pygame.font.SysFont('Arial', 45)

STATE_PLAYING, STATE_GAMEOVER, STATE_PAUSED, STATE_INIT = 0, 1, 2, 3
game_state = STATE_INIT


def render_score(score_val, color=WHITE, small=False):
    text = str(score_val)
    f = ui_font if small else font
    main_surf = f.render(text, True, color)
    shadow_surf = f.render(text, True, BLACK)
    w, h = main_surf.get_size()
    off = 4
    surf = pygame.Surface((w + off, h + off), pygame.SRCALPHA)
    surf.blit(shadow_surf, (off, off))
    surf.blit(main_surf, (0, 0))
    return surf.convert_alpha()


def get_shrunk_mask(image, factor=0.9):
    mask = pygame.mask.from_surface(image)
    if factor >= 1.0:
        return mask
    size = mask.get_size()
    sw, sh = max(1, int(size[0] * factor)), max(1, int(size[1] * factor))
    s_mask = mask.scale((sw, sh))
    f_mask = pygame.mask.Mask(size)
    f_mask.draw(s_mask, ((size[0]-sw)//2, (size[1]-sh)//2))
    return f_mask


def enhance_sprite(surf):
    w, h = surf.get_size()
    out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
    mask = pygame.mask.from_surface(surf)
    mask_surf = mask.to_surface(
        setcolor=(0, 0, 0, 180), unsetcolor=(0, 0, 0, 0))
    for off in [(0, 1), (2, 1), (1, 0), (1, 2)]:
        out.blit(mask_surf, off)
    out.blit(surf, (1, 1))
    return out.convert_alpha()


def load_img(path, alpha=False, scale_to_h=None, scale_to_w=None, smooth=True, enhance=False):
    abs_path = get_path(path)
    try:
        img = pygame.image.load(abs_path)
        img = img.convert_alpha() if alpha else img.convert()
        if scale_to_h:
            ratio = scale_to_h / img.get_height()
            w, h = int(img.get_width() * ratio), int(scale_to_h)
            img = pygame.transform.smoothscale(
                img, (w, h)) if smooth else pygame.transform.scale(img, (w, h))
        elif scale_to_w:
            ratio = scale_to_w / img.get_width()
            w, h = int(scale_to_w), int(img.get_height() * ratio)
            img = pygame.transform.smoothscale(
                img, (w, h)) if smooth else pygame.transform.scale(img, (w, h))
        if enhance:
            img = enhance_sprite(img)
        return img
    except:
        return pygame.Surface((10, 10))


def load_sound(path):
    abs_path = get_path(path)
    try:
        return pygame.mixer.Sound(abs_path)
    except:
        return None


# Assets
selected_theme = 'day'
bg_day = load_img('img/bg_day.png', scale_to_h=GROUND_LEVEL)
bg_night = load_img('img/bg_night.png', scale_to_h=GROUND_LEVEL)
bg_long_day = load_img('img/bglong_day.png', scale_to_h=SCREEN_HEIGHT)
bg_long_night = load_img('img/bglong_night.png', scale_to_h=SCREEN_HEIGHT)
ground = load_img('img/ground.png',
                  scale_to_h=SCREEN_HEIGHT - GROUND_LEVEL + 100)

pipe_img = load_img('img/pipe.png', True,
                    scale_to_w=int(SCREEN_WIDTH * 0.16), smooth=False, enhance=True)
pipe_img_flipped = pygame.transform.flip(pipe_img, False, True)
pipe_mask = get_shrunk_mask(pipe_img, 0.95)
pipe_mask_flipped = get_shrunk_mask(pipe_img_flipped, 0.95)

BIRD_SOURCES = [load_img(f'img/bird{i}.png', True, scale_to_w=int(
    SCREEN_WIDTH * 0.108), enhance=True) for i in range(1, 4)]
_bw, _bh = BIRD_SOURCES[0].get_size()
BIRD_PAD_SIZE = int(math.ceil(math.sqrt(_bw**2 + _bh**2))) + 4
BIRD_ROTATION_CACHE = []
BIRD_MASK_CACHE = []
for i in range(len(BIRD_SOURCES)):
    rots, msks = [], []
    for a in range(360):
        rt = pygame.transform.rotate(BIRD_SOURCES[i], a)
        sq = pygame.Surface((BIRD_PAD_SIZE, BIRD_PAD_SIZE), pygame.SRCALPHA)
        sq.blit(rt, (BIRD_PAD_SIZE//2 - rt.get_width() // 
                2, BIRD_PAD_SIZE//2 - rt.get_height()//2))
        rots.append(sq.convert_alpha())
        rm = get_shrunk_mask(rt, 0.88)
        fm = pygame.mask.Mask((BIRD_PAD_SIZE, BIRD_PAD_SIZE))
        fm.draw(rm, (BIRD_PAD_SIZE//2 - rm.get_size()
                [0]//2, BIRD_PAD_SIZE//2 - rm.get_size()[1]//2))
        msks.append(fm)
    BIRD_ROTATION_CACHE.append(rots)
    BIRD_MASK_CACHE.append(msks)


def create_pause_button(size):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, (144, 238, 144), (size//2, size//2), size//2)
    pygame.draw.circle(surf, (100, 200, 100),
                       (size//2, size//2), size//2, int(4 * SCALE))
    pw, ph = size // 6, size // 2
    pygame.draw.rect(surf, WHITE, (size//2 - pw - int(5*SCALE),
                     size//2 - ph//2, pw, ph), border_radius=2)
    pygame.draw.rect(surf, WHITE, (size//2 + int(5*SCALE),
                     size//2 - ph//2, pw, ph), border_radius=2)
    return surf.convert_alpha()


def create_text_button(text, width, color=ORANGE):
    text_surf = ui_font.render(text, True, WHITE)
    tw, th = text_surf.get_size()
    bw, bh = width, th + 40
    surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
    pygame.draw.rect(surf, BLACK, (0, 0, bw, bh), border_radius=10)
    pygame.draw.rect(surf, color, (4, 4, bw-8, bh-8), border_radius=8)
    surf.blit(text_surf, (bw//2 - tw//2, bh//2 - th//2))
    return surf.convert_alpha()


pause_img = create_pause_button(int(SCREEN_WIDTH * 0.12))
restart_img = create_text_button("RESTART", int(SCREEN_WIDTH * 0.5))
menu_img = create_text_button("MENU", int(SCREEN_WIDTH * 0.5), color=BLUE)
quit_img = create_text_button("QUIT", int(SCREEN_WIDTH * 0.3), color=RED)
theme_img = create_text_button("THEME", int(SCREEN_WIDTH * 0.4), color=GREEN)

flap_fx = load_sound('audio/sfx_wing.wav')
hit_fx = load_sound('audio/sfx_hit.wav')
point_fx = load_sound('audio/sfx_point.wav')
die_fx = load_sound('audio/sfx_die.wav')
swoosh_fx = load_sound('audio/sfx_swooshing.wav')
music_fx = load_sound('audio/bg_music.mp3')
music_channel = pygame.mixer.Channel(0)
music_channel.set_volume(0.5)

try:
    with open(get_path('highscore.txt'), 'r') as f:
        high_score = int(f.read())
except:
    high_score = 0


def reset_game(from_menu=True):
    global score, score_surface, score_rect, game_state, hit_played, die_played, pipe_timer, new_record_set
    global shake_duration, flash_alpha, run_timer, current_scroll_speed, current_pipe_gap, current_pipe_freq
    global bg_long_scroll, game_over_surf, restart_delay, bg_scroll, ground_scroll, trigger_timer, grace_timer
    global current_bg_speed, bg_long_speed
    gc.collect()
    pipe_group.empty()
    particle_group.empty()
    # Correctly reset bird position using its class attributes
    flappy.px = 100.0
    flappy.py = (SCREEN_HEIGHT / 2.0) - (BIRD_PAD_SIZE / 2.0)
    flappy.rect.topleft = (int(flappy.px), int(flappy.py))
    flappy.vel = flappy.vel_x = flappy.angle = 0.0
    score = 0
    run_timer = bg_long_scroll = bg_scroll = ground_scroll = 0.0
    shake_duration = flash_alpha = restart_delay = 0.0
    global flap_cooldown
    flap_cooldown = 0.0
    pipe_timer = PIPE_FREQ - 0.5
    score_surface = render_score(score, WHITE)
    score_rect = score_surface.get_rect(
        center=(SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.1)))
    current_scroll_speed, current_pipe_gap, current_pipe_freq = SCROLL_SPEED, PIPE_GAP, PIPE_FREQ
    current_bg_speed, bg_long_speed = current_scroll_speed * 0.25, current_scroll_speed * 0.125
    music_channel.stop()
    if from_menu:
        game_state = STATE_INIT
        grace_timer = 0
    else:
        game_state = STATE_PLAYING
        grace_timer = 1.5
        music_channel.play(music_fx, loops=-1)
    hit_played = die_played = new_record_set = False
    game_over_surf = None
    swoosh_fx.play()


class Bird(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.index = self.animation_timer = self.hover_timer = self.vel = self.vel_x = self.angle = 0
        self.image = BIRD_ROTATION_CACHE[0][0]
        self.mask = BIRD_MASK_CACHE[0][0]
        self.rect = self.image.get_rect(center=(x, y))
        self.px, self.py = float(self.rect.x), float(self.rect.y)

    def update(self, dt):
        if game_state == STATE_INIT:
            self.hover_timer += dt
            self.py = (SCREEN_HEIGHT / 2.0) + math.sin(self.hover_timer * 8.0) * 15.0 - (BIRD_PAD_SIZE / 2.0)
            self.animation_timer += dt
            if self.animation_timer > 0.1:
                self.animation_timer, self.index = 0.0, (self.index + 1) % 3
        else:
            eff_g = GRAVITY * (0.25 if grace_timer > 0 else 1.0)
            self.vel = min(self.vel + eff_g * dt, MAX_FALL_SPEED)
            if self.rect.bottom < GROUND_LEVEL:
                self.py += self.vel * dt
                self.px += self.vel_x * dt
                if game_state == STATE_GAMEOVER:
                    self.vel_x *= (1.0 - 5.0 * dt)
            else:
                self.rect.bottom = GROUND_LEVEL
                self.py = float(self.rect.y)
                self.vel = self.vel_x = 0

        if game_state == STATE_PLAYING:
            fs = max(0.04, 0.1 + (self.vel / 3000.0)
                     ) if self.vel < 0 else min(0.15, 0.1 + (self.vel / 6000.0))
            self.animation_timer += dt
            if self.animation_timer > fs:
                self.animation_timer, self.index = 0, (self.index + 1) % 3
            if self.vel > 420:
                self.index = 1
            target_a = 20 if self.vel < 0 else 20 - (self.vel / MAX_FALL_SPEED) * 100
            ls = 10.0 if target_a > self.angle else 5.0
            self.angle += (target_a - self.angle) * ls * dt
            self.angle = max(-80, min(20, self.angle))
        elif game_state == STATE_GAMEOVER:
            if self.rect.bottom < GROUND_LEVEL:
                self.angle -= 800 * dt
            else:
                self.angle += (-90 - self.angle) * 10.0 * dt

        sa = int(self.angle) % 360
        self.image = BIRD_ROTATION_CACHE[self.index][sa]
        self.mask = BIRD_MASK_CACHE[self.index][sa]
        self.rect.x, self.rect.y = int(self.px), int(self.py)


class Pipe(pygame.sprite.Sprite):
    def __init__(self, x, y, pos, img, mask, gap, offset, freq):
        super().__init__()
        self.image, self.mask, self.pos = img, mask, pos
        if pos == 1:
            self.rect = self.image.get_rect(bottomleft=(x, y - gap / 2))
        else:
            self.rect = self.image.get_rect(topleft=(x, y + gap / 2))
        self.px, self.py = float(self.rect.x), float(self.rect.y)
        self.phase, self.freq, self.base_y = offset, freq, self.py
        self.amp, self.scored = 0.0, False

    def update(self, dt, speed):
        self.px -= speed * dt
        if score >= 20 and self.rect.left < SCREEN_WIDTH:
            t_amp = min((score - 20) * 5 + 10, 50)
            if self.amp < t_amp:
                self.amp += 20 * dt
            self.phase += dt * self.freq * 1.5
            self.py = self.base_y + math.sin(self.phase) * self.amp
        self.rect.x, self.rect.y = int(self.px), int(self.py)
        if self.rect.right < 0:
            self.kill()


class Button:
    def __init__(self, x, y, image):
        self.img = image
        self.rect = self.img.get_rect(topleft=(x, y))
        self.p_img = pygame.transform.scale(
            image, (int(image.get_width()*0.9), int(image.get_height()*0.9)))
        self.p_rect = self.p_img.get_rect(center=self.rect.center)
        self.pressed = False

    def handle_event(self, e):
        triggered = False
        ev_pos = getattr(e, 'pos', pygame.mouse.get_pos())
        if e.type in (pygame.FINGERDOWN, pygame.FINGERUP):
            ev_pos = (int(e.x * SCREEN_WIDTH), int(e.y * SCREEN_HEIGHT))
        over = self.rect.collidepoint(ev_pos)
        if e.type in (MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            if over:
                self.pressed = True
        if e.type in (MOUSEBUTTONUP, pygame.FINGERUP):
            if self.pressed and over:
                triggered = True
            self.pressed = False
        return triggered

    def draw(self, surf, ox, oy):
        over = self.rect.collidepoint(pygame.mouse.get_pos())
        img, rect = (self.p_img, self.p_rect) if (
            self.pressed and over) else (self.img, self.rect)
        surf.blit(img, (rect.x + ox, rect.y + oy))


class Particle(pygame.sprite.Sprite):
    CACHE = {}

    def __init__(self):
        super().__init__()
        self.active = False
        self.image = pygame.Surface((1, 1))
        self.rect = self.image.get_rect()
        self.px = self.py = 0.0

    def reset(self, x, y, color):
        size = random.randint(4, 8)
        key = (size, color)
        if key not in Particle.CACHE:
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (size//2, size//2), size//2)
            Particle.CACHE[key] = s
        self.image = Particle.CACHE[key]
        self.rect = self.image.get_rect(center=(x, y))
        self.px, self.py = float(self.rect.x), float(self.rect.y)
        self.vx, self.vy = random.uniform(-150, 150), random.uniform(-150, 150)
        self.life = 1.0
        self.active = True

    def update(self, dt):
        if not self.active:
            return
        self.life -= dt
        self.px += self.vx * dt
        self.py += self.vy * dt
        self.rect.x, self.rect.y = int(self.px), int(self.py)
        if self.life <= 0:
            self.active = False
            self.kill()
        else:
            self.image.set_alpha(int(255 * self.life))


# --- Setup ---
particle_pool = [Particle() for _ in range(100)]


def spawn_particles(x, y, color, count):
    s = 0
    for p in particle_pool:
        if not p.active:
            p.reset(x, y, color)
            particle_group.add(p)
            s += 1
        if s >= count:
            break


bird_group = pygame.sprite.GroupSingle(Bird(100, SCREEN_HEIGHT//2))
pipe_group = pygame.sprite.Group()
particle_group = pygame.sprite.Group()
flappy = bird_group.sprite
restart_btn = Button(SCREEN_WIDTH//2 - restart_img.get_width() //
                     2, SCREEN_HEIGHT//2 - int(100 * SCALE), restart_img)
menu_btn = Button(SCREEN_WIDTH//2 - menu_img.get_width() //
                  2, SCREEN_HEIGHT//2 + int(20 * SCALE), menu_img)
quit_btn = Button(SCREEN_WIDTH//2 - quit_img.get_width() //
                  2, SCREEN_HEIGHT - int(130 * SCALE), quit_img)
theme_btn = Button(SCREEN_WIDTH//2 - theme_img.get_width() //
                   2, SCREEN_HEIGHT - int(240 * SCALE), theme_img)
pause_btn = Button(int(20 * SCALE), int(20 * SCALE), pause_img)
# Global State
exit_timer = ground_scroll = bg_scroll = bg_long_scroll = run_timer = score = shake_duration = flash_alpha = restart_delay = 0
trigger_timer = frame_count = grace_timer = flap_cooldown = 0
next_action = None
screen_touch_start_on_button = False
SINE_TABLE = [math.sin(i * math.pi / 180) for i in range(360)]

# UI Layout
MENU_CENTER = (SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.25))
PAUSED_CENTER = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100)
SCORE_Y = int(SCREEN_HEIGHT * 0.1)
GAMEOVER_Y_OFFSET = 120

menu_text_surf = render_score("TAP TO FLAP", ORANGE)
menu_text_rect = menu_text_surf.get_rect(center=MENU_CENTER)
paused_text_surf = render_score("PAUSED", ORANGE)
paused_text_rect = paused_text_surf.get_rect(center=PAUSED_CENTER)


def handle_jump():
    global game_state, grace_timer, flap_cooldown
    if flap_cooldown <= 0:
        grace_timer = 0
        flap_cooldown = 0.01
        if game_state == STATE_INIT:
            game_state = STATE_PLAYING
            music_channel.play(music_fx, loops=-1)
            swoosh_fx.play()
        elif game_state == STATE_PAUSED:
            game_state = STATE_PLAYING
            music_channel.unpause()
            swoosh_fx.play()
        if game_state == STATE_PLAYING:
            flappy.vel = JUMP_STRENGTH
            flap_fx.play()


reset_game()
gc.disable()
run = True
while run:
    dt = min(clock.tick(FPS) / 1000.0, 0.05)
    frame_count += 1
    ox = oy = 0
    if shake_duration > 0:
        it = int(SHAKE_INTENSITY * (shake_duration / SHAKE_DURATION))
        shake_duration -= dt
        if it > 0:
            ox, oy = random.randint(-it, it), random.randint(-it, it)

    pos = pygame.mouse.get_pos()
    for e in pygame.event.get():
        if e.type == QUIT:
            run = False
        
        # Handle interaction start
        if e.type in (MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            screen_touch_start_on_button = False
            
            # Check if any button is pressed
            if game_state == STATE_PLAYING:
                pause_btn.handle_event(e)
                if pause_btn.pressed: screen_touch_start_on_button = True
            elif game_state == STATE_INIT:
                quit_btn.handle_event(e); theme_btn.handle_event(e)
                if quit_btn.pressed or theme_btn.pressed: 
                    screen_touch_start_on_button = True
            elif game_state == STATE_GAMEOVER:
                restart_btn.handle_event(e); menu_btn.handle_event(e)
                if restart_btn.pressed or menu_btn.pressed:
                    screen_touch_start_on_button = True
            
            # INSTANT JUMP/START for gameplay
            if not screen_touch_start_on_button:
                if game_state in (STATE_PLAYING, STATE_INIT, STATE_PAUSED):
                    handle_jump()

        # Handle interaction end (Lift)
        if e.type in (MOUSEBUTTONUP, pygame.FINGERUP):
            if game_state == STATE_PLAYING:
                if pause_btn.handle_event(e):
                    trigger_timer, next_action = 0.05, "PAUSE"
                    swoosh_fx.play()
            
            elif game_state == STATE_INIT:
                q_trig = quit_btn.handle_event(e)
                t_trig = theme_btn.handle_event(e)
                if q_trig:
                    trigger_timer, next_action = 0.1, "QUIT"
                    swoosh_fx.play()
                elif t_trig:
                    trigger_timer, next_action = 0.05, "THEME"
                    swoosh_fx.play()
            
            elif game_state == STATE_GAMEOVER:
                r_trig = restart_btn.handle_event(e)
                m_trig = menu_btn.handle_event(e)
                if r_trig:
                    trigger_timer, next_action = 0.1, "RESTART"
                    swoosh_fx.play()
                elif m_trig:
                    trigger_timer, next_action = 0.1, "MENU"
                    swoosh_fx.play()

        # Keyboard support
        if e.type == KEYDOWN:
            if e.key in (K_ESCAPE, K_AC_BACK):
                if game_state == STATE_PLAYING:
                    game_state = STATE_PAUSED
                    music_channel.pause()
                    swoosh_fx.play()
                elif game_state == STATE_PAUSED:
                    handle_jump()
                elif game_state == STATE_INIT:
                    if exit_timer > 0: run = False
                    else: exit_timer = 2.0
                elif game_state == STATE_GAMEOVER:
                    reset_game()
            elif e.key == K_SPACE:
                handle_jump()

    # Process delayed actions
    if trigger_timer > 0:
        trigger_timer -= dt
        if trigger_timer <= 0:
            if next_action == "RESTART":
                reset_game(from_menu=False)
            elif next_action == "MENU":
                reset_game(from_menu=True)
            elif next_action == "QUIT":
                run = False
            elif next_action == "THEME":
                selected_theme = 'night' if selected_theme == 'day' else 'day'
            elif next_action == "PAUSE":
                game_state = STATE_PAUSED
                music_channel.pause()

    # Update timers
    if exit_timer > 0:
        exit_timer -= dt
    if flap_cooldown > 0:
        flap_cooldown -= dt

    if ox != 0 or oy != 0:
        screen.fill(BLACK)
    
    # Draw Background based on selected theme
    bg_w, bl_w = bg_day.get_width(), bg_long_day.get_width()
    if selected_theme == 'day':
        screen.blit(bg_long_day, (bg_long_scroll + ox, oy))
        screen.blit(bg_long_day, (bg_long_scroll + bl_w + ox, oy))
        screen.blit(bg_day, (bg_scroll + ox, oy))
        screen.blit(bg_day, (bg_scroll + bg_w + ox, oy))
    else:
        screen.blit(bg_long_night, (bg_long_scroll + ox, oy))
        screen.blit(bg_long_night, (bg_long_scroll + bl_w + ox, oy))
        screen.blit(bg_night, (bg_scroll + ox, oy))
        screen.blit(bg_night, (bg_scroll + bg_w + ox, oy))

    for p in pipe_group:
        screen.blit(p.image, (p.rect.x + ox, p.rect.y + oy))
    for p in particle_group:
        screen.blit(p.image, (p.rect.x + ox, p.rect.y + oy))
    screen.blit(flappy.image, (flappy.rect.x + ox, flappy.rect.y + oy))

    if game_state != STATE_PAUSED:
        sub_steps = 4
        sub_dt = dt / float(sub_steps)
        for _ in range(sub_steps):
            bird_group.update(sub_dt)
            if game_state in (STATE_INIT, STATE_PLAYING, STATE_GAMEOVER):
                ground_scroll = (ground_scroll - current_bg_speed * sub_dt) % -float(bg_w)
                bg_scroll = (bg_scroll - current_bg_speed * sub_dt) % -float(bg_w)
                bg_long_scroll = (bg_long_scroll - bg_long_speed * sub_dt) % -float(bl_w)
            
            if game_state == STATE_PLAYING:
                pipe_group.update(sub_dt, current_scroll_speed)
                cols = pygame.sprite.spritecollide(flappy, pipe_group, False)
                if cols:
                    hit = False
                    for p in cols:
                        if pygame.sprite.collide_mask(flappy, p):
                            hit = True
                            break
                    if hit:
                        game_state = STATE_GAMEOVER
                        break
                if flappy.rect.top < 0 or flappy.rect.bottom >= GROUND_LEVEL:
                    game_state = STATE_GAMEOVER
                    break

    if game_state == STATE_GAMEOVER and not hit_played:
        restart_delay = 0.16
        intensity = current_scroll_speed / SCROLL_SPEED
        spawn_particles(flappy.rect.centerx, flappy.rect.centery,
                        WHITE, int(15 * intensity))
        shake_duration, flash_alpha, hit_played = SHAKE_DURATION * intensity, 255.0, True
        if flappy.rect.bottom < GROUND_LEVEL:
            hit_fx.play()
            swoosh_fx.play()
            if flappy.rect.top > 0:
                flappy.vel, flappy.vel_x = -1200.0 * intensity, -600.0 * intensity
            else:
                flappy.vel = 0.0
        die_fx.play()
        music_channel.stop()
        game_over_surf = render_score(
            f'NEW RECORD: {score}!' if new_record_set else f'HIGH SCORE: {high_score}', GREEN if new_record_set else BLUE, small=True)
        game_over_rect = game_over_surf.get_rect(
            center=(SCREEN_WIDTH // 2, SCORE_Y + GAMEOVER_Y_OFFSET))
        if score > high_score:
            high_score = score
            try:
                with open(get_path('highscore.txt'), 'w') as f:
                    f.write(str(high_score))
            except:
                pass

    if game_state != STATE_PAUSED:
        particle_group.update(dt)
    
    screen.blit(ground, (ground_scroll + ox, GROUND_LEVEL + oy))
    if ground_scroll + bg_w < SCREEN_WIDTH:
        screen.blit(ground, (ground_scroll + bg_w + ox, GROUND_LEVEL + oy))

    if game_state == STATE_PLAYING:
        pause_btn.draw(screen, ox, oy)
        run_timer += dt
        if grace_timer > 0:
            grace_timer -= dt
        diff = 1.0 - math.exp(-run_timer / 180.0)
        current_scroll_speed = SCROLL_SPEED + diff * (160.0 * SCALE)
        current_pipe_gap = PIPE_GAP - diff * (55.0 * SCALE)
        current_pipe_freq = PIPE_FREQ - diff * 0.75
        current_bg_speed, bg_long_speed = current_scroll_speed * 0.25, current_scroll_speed * 0.125
        if hasattr(music_channel, "speed"):
            music_channel.speed = current_scroll_speed / SCROLL_SPEED
        for p in pipe_group:
            if not p.scored and flappy.rect.left > p.rect.right and p.pos == -1:
                score += 1
                score_surface = render_score(score)
                score_rect = score_surface.get_rect(
                    center=(SCREEN_WIDTH // 2, SCORE_Y))
                point_fx.play()
                p.scored = True
        pipe_timer += dt
        if pipe_timer > current_pipe_freq:
            h = random.uniform(-150.0 * SCALE, 150.0 * SCALE)
            gap = max(200.0 * SCALE, current_pipe_gap +
                      random.uniform(-50.0 * SCALE, 50.0 * SCALE))
            pipe_group.add(Pipe(SCREEN_WIDTH, SCREEN_HEIGHT / 2.0 + 
                           h, -1, pipe_img, pipe_mask, gap, 0.0, 1.0))
            pipe_group.add(Pipe(SCREEN_WIDTH, SCREEN_HEIGHT / 2.0 + h,
                           1, pipe_img_flipped, pipe_mask_flipped, gap, 0.0, 1.0))
            pipe_timer = 0.0

    if game_state != STATE_PAUSED:
        screen.blit(score_surface, (score_rect.x + ox, score_rect.y + oy))

    if game_state == STATE_INIT:
        fo = SINE_TABLE[(frame_count * 2) % 360] * (20 * SCALE)
        screen.blit(menu_text_surf, (menu_text_rect.x + 
                    ox, menu_text_rect.y + oy + fo))
        quit_btn.draw(screen, ox, oy)
        theme_btn.draw(screen, ox, oy)
    elif game_state == STATE_PAUSED:
        screen.blit(paused_text_surf, (paused_text_rect.x + 
                    ox, paused_text_rect.y + oy))
    elif game_state == STATE_GAMEOVER:
        if game_over_surf:
            screen.blit(game_over_surf, (game_over_rect.x + 
                        ox, game_over_rect.y + oy))
        restart_btn.draw(screen, ox, oy)
        menu_btn.draw(screen, ox, oy)
        if restart_delay > 0:
            restart_delay -= dt

    if flash_alpha > 0:
        fs = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        fs.fill(WHITE)
        fs.set_alpha(flash_alpha)
        screen.blit(fs, (0, 0))
        flash_alpha = max(0, flash_alpha - 1500*dt)

    pygame.display.flip()
    if exit_timer > 0 and game_state == STATE_INIT:
        em = ui_font.render("TAP BACK AGAIN TO EXIT", True, WHITE)
        er = em.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 100))
        screen.blit(em, er)

pygame.quit()
gc.enable()