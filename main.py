import pygame
import random
import math
from pygame.locals import *

# --- Configuration Constants ---
SCREEN_WIDTH, SCREEN_HEIGHT = 864, 936
FPS = 60
GROUND_LEVEL = 768
PIPE_GAP, PIPE_FREQ = 150, 1.5
SCROLL_SPEED, BG_SCROLL_SPEED = 240, 60
GRAVITY, JUMP_STRENGTH = 30, -8
SHAKE_INTENSITY, SHAKE_DURATION = 15, 0.4
FLAP_SPEED = 0.1

WHITE, BLACK, RED, BLUE, GREEN, ORANGE = (
    255,)*3, (0,)*3, (255, 0, 0), (30, 80, 250), (0, 150, 0), (255, 140, 0)

# --- Initialization ---
import os
try:
    platform = pygame.system.get_platform()
except AttributeError:
    platform = "unknown"
IS_ANDROID = 'android' in platform.lower() or 'ANDROID_ARGUMENT' in os.environ

pygame.mixer.pre_init(48000, -16, 2, 4096)
pygame.init()
clock = pygame.time.Clock()

# Use SCALED to automatically handle different resolutions and aspect ratios
flags = pygame.SCALED | (pygame.FULLSCREEN if IS_ANDROID else 0)
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags, vsync=1)
render_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Flappy Bird")
font = pygame.font.Font('04B_19.ttf', 60)

# Game States
STATE_MENU, STATE_PLAYING, STATE_GAMEOVER, STATE_PAUSED = 0, 1, 2, 3
game_state = STATE_MENU

# --- Utility Functions ---


def render_score(score_val, color=WHITE):
    """Renders text with a simple drop shadow."""
    text = str(score_val)
    main_surf = font.render(text, True, color)
    shadow_surf = font.render(text, True, BLACK)
    w, h = main_surf.get_size()
    surf = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
    surf.blit(shadow_surf, (2, 2))
    surf.blit(main_surf, (0, 0))
    return surf.convert_alpha()


def get_shrunk_mask(image, factor=0.92):
    """Creates a slightly smaller collision mask for more 'fair' gameplay."""
    mask = pygame.mask.from_surface(image)
    if factor >= 1.0:
        return mask
    size = mask.get_size()
    shrunk_size = (max(1, int(size[0] * factor)),
                   max(1, int(size[1] * factor)))
    shrunk_mask = mask.scale(shrunk_size)
    full_mask = pygame.mask.Mask(size)
    full_mask.draw(
        shrunk_mask, ((size[0] - shrunk_size[0]) // 2, (size[1] - shrunk_size[1]) // 2))
    return full_mask


# --- Asset Loading ---
bg_day = pygame.image.load('img/bg_day.png').convert()
bg_night = pygame.image.load('img/bg_night.png').convert()
bg_long_day = pygame.image.load('img/bglong_day.png').convert()
bg_long_night = pygame.image.load('img/bglong_night.png').convert()
ground = pygame.image.load('img/ground.png').convert()
button_img = pygame.image.load('img/restart.png').convert()
pipe_img = pygame.image.load('img/pipe.png').convert_alpha()
pipe_img_flipped = pygame.transform.flip(pipe_img, False, True)
BIRD_IMAGES = [pygame.image.load(
    f'img/bird{i}.png').convert_alpha() for i in range(1, 4)]
BIRD_MASKS = [get_shrunk_mask(img, 0.98) for img in BIRD_IMAGES]
pipe_mask = get_shrunk_mask(pipe_img, 0.98)
pipe_mask_flipped = get_shrunk_mask(pipe_img_flipped, 0.98)

# Audio
flap_fx = pygame.mixer.Sound('audio/sfx_wing.wav')
hit_fx = pygame.mixer.Sound('audio/sfx_hit.wav')
point_fx = pygame.mixer.Sound('audio/sfx_point.wav')
die_fx = pygame.mixer.Sound('audio/sfx_die.wav')
swoosh_fx = pygame.mixer.Sound('audio/sfx_swooshing.wav')
music_fx = pygame.mixer.Sound('audio/bg_music.mp3')
music_channel = pygame.mixer.Channel(0)
music_channel.set_volume(0.5)

# High Score persistence
try:
    with open('highscore.txt', 'r') as f:
        high_score = int(f.read())
except:
    high_score = 0


def reset_game():
    """Resets all game variables for a new round."""
    global score, score_surface, score_rect, game_state, hit_played, die_played, pipe_timer, new_record_set
    global shake_duration, flash_alpha, run_timer, current_scroll_speed, current_pipe_gap, current_pipe_freq
    global bg_long_scroll, game_over_surf, pipe_move_speed, restart_delay, bg_scroll, ground_scroll

    pipe_group.empty()
    particle_group.empty()

    flappy.rect.center = [100, SCREEN_HEIGHT // 2]
    flappy.vel = flappy.vel_x = flappy.angle = score = run_timer = bg_long_scroll = bg_scroll = ground_scroll = pipe_move_speed = shake_duration = flash_alpha = restart_delay = 0
    pipe_timer = PIPE_FREQ - 0.5

    score_surface = render_score(score, WHITE)
    score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, 50))
    current_scroll_speed, current_pipe_gap, current_pipe_freq = SCROLL_SPEED, PIPE_GAP, PIPE_FREQ
    music_channel.stop()
    if hasattr(music_channel, "speed"):
        music_channel.speed = 1.0
    game_state, hit_played, die_played, new_record_set, game_over_surf = STATE_MENU, False, False, False, None

# --- Game Classes ---


class Bird(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.images, self.masks = BIRD_IMAGES, BIRD_MASKS
        self.index = self.animation_timer = self.hover_timer = self.vel = self.vel_x = self.angle = 0
        self.image, self.mask = self.images[0], self.masks[0]
        self.rect = self.image.get_rect(center=(x, y))
        self.rotation_cache, self.mask_cache = {}, {}
        # Pre-cache common flight angles
        for idx in range(len(self.images)):
            for ang in range(-85, 25):
                img = pygame.transform.rotate(self.images[idx], ang)
                self.rotation_cache[(idx, ang)], self.mask_cache[(
                    idx, ang)] = img, get_shrunk_mask(img)

    def update(self, dt):
        if game_state == STATE_MENU:
            self.hover_timer += dt
            self.rect.centery = (SCREEN_HEIGHT / 2) + \
                math.sin(self.hover_timer * 8) * 15
            self.angle = 0
        else:
            self.vel = min(self.vel + GRAVITY * dt, 15)
            if self.rect.bottom < GROUND_LEVEL:
                self.rect.y += self.vel
                self.rect.x += self.vel_x
                # Apply "air resistance" to horizontal movement
                if game_state == STATE_GAMEOVER:
                    self.vel_x *= (1.0 - 1.0 * dt)
            else:
                self.rect.bottom, self.vel, self.vel_x = GROUND_LEVEL, 0, 0

        if game_state == STATE_PLAYING:
            if self.vel < 0:
                dynamic_flap_speed = max(0.04, 0.1 + (self.vel / 50.0))
            else:
                dynamic_flap_speed = min(0.15, 0.1 + (self.vel / 100.0))

            self.animation_timer += dt
            if self.animation_timer > dynamic_flap_speed:
                self.animation_timer, self.index = 0, (
                    self.index + 1) % len(self.images)
            if self.vel > 7:
                self.index, self.animation_timer = 1, 0

            target_angle = 20 if self.vel < 0 else 20 - (self.vel / 15) * 100
            lerp_speed = 5.0 if target_angle > self.angle else 3.0
            self.angle += (target_angle - self.angle) * lerp_speed * dt
            snapped_angle = max(-80, min(20, int(self.angle)))
        elif game_state == STATE_GAMEOVER:
            if self.rect.bottom < GROUND_LEVEL:
                # Tumble effect: spin rapidly while falling
                self.angle -= 800 * dt
                self.index = 1  # Keep wings in a mid-flap position during tumble
            else:
                # Stop tumbling and face down/slightly angled when on ground
                self.angle += (-90 - self.angle) * 10.0 * dt
            snapped_angle = int(self.angle) % 360
            if snapped_angle > 180:
                snapped_angle -= 360
        else:
            snapped_angle = 0

        cache_key = (self.index, snapped_angle)
        if cache_key not in self.rotation_cache:
            img = pygame.transform.rotate(
                self.images[self.index], snapped_angle)
            self.rotation_cache[cache_key], self.mask_cache[cache_key] = img, get_shrunk_mask(
                img)
        self.image, self.mask = self.rotation_cache[cache_key], self.mask_cache[cache_key]


class Pipe(pygame.sprite.Sprite):
    def __init__(self, x, y, position, img, mask, gap, offset, freq):
        super().__init__()
        self.image, self.mask, self.position = img, mask, position
        self.rect = self.image.get_rect()
        if position == 1:
            self.rect.bottomleft = [x, y - gap / 2]
        else:
            self.rect.topleft = [x, y + gap / 2]
        self.phase, self.freq, self.base_y = offset, freq, self.rect.y
        self.current_amplitude, self.scored = 0.0, False

    def update(self, dt, scroll_speed):
        self.rect.x -= scroll_speed * dt
        if score >= 20:
            target_amplitude = min((score - 20) * 5 + 10, 50)
            if self.current_amplitude < target_amplitude:
                self.current_amplitude += 20 * dt
            self.phase += dt * self.freq * 1.5
            self.rect.y = self.base_y + \
                math.sin(self.phase) * self.current_amplitude
        if self.rect.right < 0:
            self.kill()


class Button:
    def __init__(self, x, y, image):
        self.img = image
        self.hover_img = pygame.transform.scale(
            image, (int(image.get_width()*1.1), int(image.get_height()*1.1)))
        self.rect = self.img.get_rect(topleft=(x, y))
        self.hover_rect = self.hover_img.get_rect(center=self.rect.center)

    def draw(self, surface, forced=False):
        res = False
        if self.rect.collidepoint(pygame.mouse.get_pos()) or forced:
            surface.blit(self.hover_img, self.hover_rect)
            if pygame.mouse.get_pressed()[0]:
                res = True
        else:
            surface.blit(self.img, self.rect)
        return res


class Particle(pygame.sprite.Sprite):
    CACHE = {}

    def __init__(self):
        super().__init__()
        self.active = False
        self.image = pygame.Surface((1, 1))
        self.rect = self.image.get_rect()

    def reset(self, x, y, color):
        size = random.randint(4, 8)
        key = (size, color)
        if key not in Particle.CACHE:
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (size//2, size//2), size//2)
            Particle.CACHE[key] = surf
        
        self.image = Particle.CACHE[key]
        self.rect = self.image.get_rect(center=(x, y))
        self.vx, self.vy = random.uniform(-150, 150), random.uniform(-150, 150)
        self.life = 1.0
        self.active = True

    def update(self, dt):
        if not self.active:
            return
        self.life -= dt
        self.rect.x += self.vx * dt
        self.rect.y += self.vy * dt
        if self.life <= 0:
            self.active = False
            self.kill()
        else:
            self.image.set_alpha(int(255 * self.life))


# --- Object Instantiation ---
# Particle Pool
PARTICLE_POOL_SIZE = 100
particle_pool = [Particle() for _ in range(PARTICLE_POOL_SIZE)]


def spawn_particles(x, y, color, count):
    spawned = 0
    for p in particle_pool:
        if not p.active:
            p.reset(x, y, color)
            particle_group.add(p)
            spawned += 1
            if spawned >= count:
                break


bird_group = pygame.sprite.GroupSingle(Bird(100, SCREEN_HEIGHT//2))
pipe_group = pygame.sprite.Group()
particle_group = pygame.sprite.Group()
flappy = bird_group.sprite
button = Button(SCREEN_WIDTH//2 - 50, SCREEN_HEIGHT//2 - 100, button_img)

# Global State
exit_timer = 0
ground_scroll = bg_scroll = bg_long_scroll = run_timer = score = shake_duration = flash_alpha = restart_delay = 0
pipe_timer = PIPE_FREQ - 0.5
current_scroll_speed, current_bg_speed, bg_long_speed, current_pipe_gap, current_pipe_freq, score_scale = SCROLL_SPEED, BG_SCROLL_SPEED, BG_SCROLL_SPEED/2, PIPE_GAP, PIPE_FREQ, 1.0
score_surface = render_score(score)
score_rect = score_surface.get_rect(center=(SCREEN_WIDTH//2, 50))
menu_text_surf = render_score("PRESS SPACE TO FLAP", ORANGE)
paused_text_surf = render_score("PAUSED", ORANGE)
hit_played = die_played = new_record_set = False
game_over_surf = None

# Android specific: Try to keep the screen on
if IS_ANDROID:
    try:
        import android
        android.wakelock(True)
    except ImportError:
        pass

# --- Main Game Loop ---
run = True
while run:
    dt = min(clock.tick(FPS) / 1000.0, 0.05)
    evs = pygame.event.get()
    if exit_timer > 0:
        exit_timer -= dt

    ox = oy = 0
    if shake_duration > 0:
        intense = int(SHAKE_INTENSITY * (shake_duration / SHAKE_DURATION))
        shake_duration -= dt
        if intense > 0:
            ox, oy = random.randint(-intense,
                                    intense), random.randint(-intense, intense)

    # --- Day/Night Cycle Logic ---
    cycle_val = (math.sin(run_timer * 0.03 - math.pi/2) + 1) / 2
    night_alpha = int(cycle_val * 255)

    bg_long_night.set_alpha(night_alpha)
    bg_night.set_alpha(night_alpha)

    # Use actual widths to ensure correct scrolling
    bg_w = bg_day.get_width()
    bg_long_w = bg_long_day.get_width()

    # Draw Parallax Background (Long)
    render_surface.blit(bg_long_day, (bg_long_scroll, 0))
    render_surface.blit(bg_long_night, (bg_long_scroll, 0))
    render_surface.blit(bg_long_day, (bg_long_scroll + bg_long_w, 0))
    render_surface.blit(bg_long_night, (bg_long_scroll + bg_long_w, 0))

    # Draw Main Background
    render_surface.blit(bg_day, (bg_scroll, 0))
    render_surface.blit(bg_night, (bg_scroll, 0))
    render_surface.blit(bg_day, (bg_scroll + bg_w, 0))
    render_surface.blit(bg_night, (bg_scroll + bg_w, 0))

    pipe_group.draw(render_surface)
    particle_group.draw(render_surface)
    bird_group.draw(render_surface)
    if game_state != STATE_PAUSED:
        bird_group.update(dt)
        particle_group.update(dt)
    render_surface.blit(ground, (ground_scroll, GROUND_LEVEL))

    if game_state == STATE_PLAYING:
        run_timer += dt
        # Faster ramp-up: Time constant reduced to 180s (3 mins).
        # Reaches ~63% difficulty at 3 mins, ~86% at 6 mins.
        scale = 1.0 - math.exp(-run_timer / 180.0)

        # Increased maximum caps for higher difficulty
        current_scroll_speed = SCROLL_SPEED + scale * 160
        current_pipe_gap = PIPE_GAP - scale * 55
        current_pipe_freq = PIPE_FREQ - scale * 0.75

        # Perfect synchronization: BG speeds are now proportional to the main scroll speed
        current_bg_speed = current_scroll_speed * \
            0.25      # Front BG layer (1/4 speed)
        bg_long_speed = current_scroll_speed * \
            0.125       # Back BG layer (1/8 speed)

        # Sync music speed with game speed (Requires pygame-ce)
        if hasattr(music_channel, "speed"):
            music_channel.speed = current_scroll_speed / SCROLL_SPEED

        for p in pipe_group:
            if not p.scored and flappy.rect.left > p.rect.right and p.position == -1:
                score += 1
                if score > high_score:
                    new_record_set = True
                score_surface = render_score(
                    score, RED if new_record_set else WHITE)
                score_rect, score_scale = score_surface.get_rect(
                    center=(SCREEN_WIDTH // 2, 50)), 1.4
                point_fx.play()
                p.scored = True

        hit_pipe = pygame.sprite.spritecollide(
            flappy, pipe_group, False, pygame.sprite.collide_mask)
        hit_top = flappy.rect.top < 0
        hit_ground = flappy.rect.bottom >= GROUND_LEVEL

        if hit_ground or hit_top or hit_pipe:
            game_state = STATE_GAMEOVER
            if not hit_played:
                # Dynamic intensity based on speed
                intensity = current_scroll_speed / SCROLL_SPEED
                particle_count = int(15 * intensity)

                spawn_particles(flappy.rect.centerx, flappy.rect.centery, WHITE, particle_count)

                shake_duration, flash_alpha, hit_played = SHAKE_DURATION * intensity, 255, True

                if not hit_ground:
                    hit_fx.play()
                    swoosh_fx.play()
                    if hit_pipe:
                        # Only apply the dramatic "projectile" motion if hitting a pipe
                        flappy.vel = -8 * intensity
                        flappy.vel_x = -5 * intensity
                    else:
                        # If hitting the top, just ensure it stops moving up so it falls
                        flappy.vel = 0

                die_fx.play()
                music_channel.stop()
                game_over_surf = render_score(
                    f'NEW RECORD: {score}!' if new_record_set else f'HIGH SCORE: {high_score}', GREEN if new_record_set else BLUE)
                if score > high_score:
                    high_score = score
                    with open('highscore.txt', 'w') as f:
                        f.write(str(high_score))

        pipe_group.update(dt, current_scroll_speed)
        pipe_timer += dt
        if pipe_timer > current_pipe_freq:
            h, off, f = random.randint(-100, 100), random.uniform(0,
                                                                  math.pi*2), random.uniform(0.8, 1.2)
            # Increased randomness and allows for significantly tighter gaps
            random_gap = max(80, current_pipe_gap + random.randint(-40, 20))
            pipe_group.add(Pipe(SCREEN_WIDTH, SCREEN_HEIGHT//2 +
                           h, -1, pipe_img, pipe_mask, random_gap, off, f))
            pipe_group.add(Pipe(SCREEN_WIDTH, SCREEN_HEIGHT//2+h, 1,
                           pipe_img_flipped, pipe_mask_flipped, random_gap, off, f))
            pipe_timer = 0

    if game_state != STATE_GAMEOVER and game_state != STATE_PAUSED:
        ground_scroll = (ground_scroll - current_scroll_speed*dt) % -35
        bg_scroll = (bg_scroll - current_bg_speed*dt) % -SCREEN_WIDTH
        bg_long_scroll = (bg_long_scroll - bg_long_speed*dt) % -1280

    if game_state != STATE_MENU:
        if score_scale > 1.0:
            score_scale = max(1.0, score_scale - 2.0*dt)
            s = pygame.transform.scale(score_surface, (int(score_surface.get_width(
            )*score_scale), int(score_surface.get_height()*score_scale)))
            render_surface.blit(s, s.get_rect(center=(SCREEN_WIDTH//2, 50)))
        else:
            render_surface.blit(score_surface, score_rect)

    if game_state == STATE_MENU:
        # Floating effect instead of scaling
        float_offset = math.sin(pygame.time.get_ticks() * 0.005) * 10
        render_surface.blit(menu_text_surf, menu_text_surf.get_rect(
            center=(SCREEN_WIDTH//2, 150 + float_offset)))
    elif game_state == STATE_PAUSED:
        render_surface.blit(paused_text_surf, paused_text_surf.get_rect(
            center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50)))
    elif game_state == STATE_GAMEOVER:
        if game_over_surf:
            render_surface.blit(game_over_surf, game_over_surf.get_rect(
                center=(SCREEN_WIDTH//2, 120)))
        if restart_delay > 0:
            button.draw(render_surface, True)
            restart_delay -= 1
            if restart_delay == 0:
                reset_game()
                swoosh_fx.play()
        elif button.draw(render_surface):
            reset_game()
            swoosh_fx.play()

    if flash_alpha > 0:
        fs = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        fs.fill(WHITE)
        fs.set_alpha(flash_alpha)
        render_surface.blit(fs, (0, 0))
        flash_alpha = max(0, flash_alpha - 1500*dt)

    screen.fill(BLACK)
    screen.blit(render_surface, (ox, oy))

    for e in evs:
        if e.type == QUIT:
            run = False

        # Input Handling (Keyboard + Touch)
        jump_triggered = False
        if e.type == KEYDOWN and e.key == K_SPACE:
            jump_triggered = True
        if e.type == MOUSEBUTTONDOWN:
            jump_triggered = True

        if jump_triggered:
            if game_state == STATE_MENU:
                game_state = STATE_PLAYING
                swoosh_fx.play()
                music_channel.play(music_fx, loops=-1)
                flappy.vel = JUMP_STRENGTH
                flap_fx.play()
            elif game_state == STATE_PLAYING:
                flappy.vel = JUMP_STRENGTH
                flap_fx.play()
            elif game_state == STATE_PAUSED:
                game_state = STATE_PLAYING
                music_channel.unpause()
                flappy.vel = JUMP_STRENGTH
                flap_fx.play()

        if e.type == KEYDOWN:
            if e.key == K_ESCAPE:
                if game_state == STATE_PLAYING:
                    game_state = STATE_PAUSED
                    music_channel.pause()
                elif game_state == STATE_PAUSED:
                    game_state = STATE_PLAYING
                    music_channel.unpause()
                elif game_state == STATE_MENU:
                    if exit_timer > 0:
                        run = False
                    else:
                        exit_timer = 2.0  # Show exit message for 2 seconds
                elif game_state == STATE_GAMEOVER:
                    reset_game()
            if e.key in (K_RETURN, K_KP_ENTER):
                if game_state == STATE_GAMEOVER:
                    reset_game()
                    swoosh_fx.play()
    
    if exit_timer > 0 and game_state == STATE_MENU:
        exit_msg = font.render("TAP BACK AGAIN TO EXIT", True, WHITE)
        render_surface.blit(exit_msg, exit_msg.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 100)))

    pygame.display.flip()
pygame.quit()
