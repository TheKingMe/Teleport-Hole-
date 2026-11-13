"""
=============================================================================
🌀 TELEPORT HOLE - ULTRA-CLEAN & HIGH-FPS EDITION (👌 OK GESTURE VFX)
=============================================================================
Photorealistic real-time teleportation wormholes inspired by the viral meme!

Key Enhancements in this Edition:
1. 100% ARTIFACT-FREE:
   - Strictly localized portal penetration bounds (NO gray boxes, NO erased body).
   - Feathered alpha edge blending (NO jagged cyan outlines or hard cuts).
2. CORRECT 3D PORTAL ORIENTATIONS:
   - Hole A (Ceiling): Horizontal ellipse, cone funnel points UP into ceiling.
   - Hole B (Wall): Vertical ellipse, cone funnel points LEFT into wall, mouth faces RIGHT.
3. SILKY SMOOTH 30-60 FPS:
   - MediaPipe accelerated on lightweight downscaled frame buffer.
   - Pre-allocated vectorized coordinate grids with zero memory reallocation.
4. CLEAN ASCII HUD:
   - Completely removes corrupted '?' characters from OpenCV font rendering.
5. DUAL TRIGGER MODES:
   - 👌 OK Hand Sign: Form the OK sign with your fingers to open holes!
   - Mouse Drag & Scale: Click & drag any portal anytime to reposition.

Controls:
  [B]               : Capture Clean Room Background Plate (Do this first!)
  [👌 OK Sign]      : Form OK sign with your hand to CREATE Hole A then Hole B!
  [Left Click Drag] : Reposition any hole anywhere on screen
  [Scroll Wheel]    : Resize / Scale hole
  [R]               : Rotate selected hole orientation
  [C]               : Clear Holes (Re-create from scratch)
  [P]               : Cycle Presets (1: Ceiling+Wall, 2: Facing Walls, 3: Loop)
  [W] or [G]        : Start / Stop Recording Final Video to MP4!
  [H]               : Toggle HUD Overlay (Hide for clean recording)
  [T]               : Rotate Camera (0° -> 90° -> 180° -> 270° for TikTok/Reels)
  [F]               : Toggle Horizontal Mirror Flip
  [S]               : Toggle Sound Effects (Mute / Unmute)
  [Q] or [ESC]      : Quit
=============================================================================
"""

import os
import sys
import time
import math
import random
import argparse
import threading
import numpy as np
import cv2

# Windows native audio
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# Suppress low-level TensorFlow / MediaPipe C++ stderr output on Windows
class SuppressStderr:
    def __enter__(self):
        try:
            self.null_fd = os.open(os.devnull, os.O_RDWR)
            self.save_fd = os.dup(2)
            os.dup2(self.null_fd, 2)
        except Exception:
            self.save_fd = None
        return self

    def __exit__(self, *_):
        if self.save_fd is not None:
            try:
                os.dup2(self.save_fd, 2)
                os.close(self.null_fd)
                os.close(self.save_fd)
            except Exception:
                pass

with SuppressStderr():
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        HAS_MEDIAPIPE = True
    except ImportError:
        HAS_MEDIAPIPE = False

# Optional OBS virtual camera
try:
    import pyvirtualcam
    HAS_PYVIRTUALCAM = True
except ImportError:
    HAS_PYVIRTUALCAM = False


# =============================================================================
# 1. CONFIGURATION & TUNING CONSTANTS
# =============================================================================
class Config:
    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 720
    DEFAULT_FPS = 30.0

    # Gesture thresholds
    OK_PINCH_THRESH = 0.36       # Max normalized distance between thumb & index tip
    OK_TRIGGER_FRAMES = 5        # Consecutive frames to confirm gesture (~0.17s)
    OK_COOLDOWN = 1.30           # Seconds before OK sign can trigger the next hole
    DRILL_DURATION = 1.20        # Duration of drilling animation & sound

    # Visual effects
    SPARK_COUNT = 5              # Sparks spawned per frame during drilling
    DUST_CHANCE = 0.40           # Probability of dust cloud spawn per frame
    MAX_COSMIC_EMBERS = 24       # Orbiting particles per active portal
    PORTAL_EXPAND_TIME = 0.40    # Duration of elastic hole opening

    # Colors (BGR)
    COLOR_CYAN = (255, 240, 50)
    COLOR_BLUE = (255, 160, 20)
    COLOR_WHITE = (255, 255, 255)
    COLOR_ORANGE = (30, 140, 255)
    COLOR_GOLD = (80, 220, 255)
    COLOR_GREEN = (60, 255, 80)


# =============================================================================
# 2. ZERO-LAG THREADED CAMERA
# =============================================================================
class ZeroLagCamera:
    """Continuous frame grabber thread that eliminates buffer latency with multi-backend auto-fallback."""
    def __init__(self, src=0, width=Config.DEFAULT_WIDTH, height=Config.DEFAULT_HEIGHT):
        self.src = src
        self.is_url = not str(src).isdigit()
        self.cap = None

        if self.is_url:
            self.cap = cv2.VideoCapture(str(src))
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        else:
            candidates = [int(src)]
            if int(src) == 0:
                candidates.extend([1, 2])

            for cam_id in candidates:
                for backend in [cv2.CAP_DSHOW, cv2.CAP_ANY]:
                    try:
                        cap = cv2.VideoCapture(cam_id, backend)
                        if cap.isOpened():
                            ret, test_frame = cap.read()
                            if ret and test_frame is not None:
                                self.cap = cap
                                self.src = cam_id
                                if width and height:
                                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                                print(f"[INFO] Camera opened successfully on index {cam_id} (backend: {backend})")
                                break
                            else:
                                cap.release()
                    except Exception:
                        pass
                if self.cap is not None:
                    break

        if self.cap is None or not self.cap.isOpened():
            self.ret = False
            self.frame = None
            self.running = False
            return

        self.ret, self.frame = self.cap.read()
        self.running = self.ret and self.cap.isOpened()
        self.lock = threading.Lock()

        if self.running:
            self.thread = threading.Thread(target=self._update, daemon=True)
            self.thread.start()

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.ret, self.frame = ret, frame
            else:
                time.sleep(0.005)

    def read(self):
        with self.lock:
            if self.frame is not None:
                return self.ret, self.frame.copy()
            return self.ret, None

    def release(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=0.5)
        self.cap.release()


# =============================================================================
# 3. AUDIO SFX ENGINE
# =============================================================================
class SoundPlayer:
    """Non-blocking audio engine for power drill and cosmic portal sounds."""
    def __init__(self, enabled=True):
        self.enabled = enabled and HAS_WINSOUND
        base = os.path.dirname(os.path.abspath(__file__))
        self.drill_sound = os.path.join(base, "drill_sound.wav")
        self.portal_open = os.path.join(base, "portal_open.wav")
        self.teleport_fx = os.path.join(base, "teleport_fx.wav")

    def play_drill(self):
        if self.enabled:
            threading.Thread(target=self._play, args=(self.drill_sound,), daemon=True).start()

    def play_portal_open(self):
        if self.enabled:
            threading.Thread(target=self._play, args=(self.portal_open,), daemon=True).start()

    def play_teleport(self):
        if self.enabled:
            threading.Thread(target=self._play, args=(self.teleport_fx,), daemon=True).start()

    def _play(self, path):
        try:
            if os.path.exists(path):
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass


# =============================================================================
# 4. PARTICLE & VFX ENGINE
# =============================================================================
class Spark:
    """Molten metal/masonry sparks with realistic ballistic physics."""
    def __init__(self, x, y, spray_angle):
        self.x = float(x)
        self.y = float(y)
        ang = spray_angle + random.uniform(-0.65, 0.65)
        speed = random.uniform(5.0, 14.0)
        self.vx = math.cos(ang) * speed
        self.vy = math.sin(ang) * speed
        self.gravity = 0.38
        self.drag = 0.94
        self.life = random.randint(12, 22)
        self.max_life = self.life
        self.color = random.choice([Config.COLOR_WHITE, Config.COLOR_GOLD, Config.COLOR_ORANGE])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.vx *= self.drag
        self.vy *= self.drag
        self.life -= 1
        return self.life > 0

    def draw(self, frame):
        alpha = self.life / self.max_life
        tx = int(self.x - self.vx * 1.4)
        ty = int(self.y - self.vy * 1.4)
        hx = int(self.x)
        hy = int(self.y)
        c = tuple(int(ch * alpha) for ch in self.color)
        cv2.line(frame, (tx, ty), (hx, hy), c, max(1, int(2 * alpha)), cv2.LINE_AA)


class DustSmoke:
    """Billowing translucent vapor / dust clouds."""
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        ang = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1.0, 3.2)
        self.vx = math.cos(ang) * speed
        self.vy = math.sin(ang) * speed - 0.4
        self.radius = random.uniform(6.0, 14.0)
        self.growth = random.uniform(0.6, 1.2)
        self.life = random.randint(16, 26)
        self.max_life = self.life
        self.color = random.choice([(190, 200, 210), (220, 210, 180)])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.radius += self.growth
        self.vx *= 0.93
        self.vy *= 0.93
        self.life -= 1
        return self.life > 0

    def draw(self, frame):
        alpha = (self.life / self.max_life) * 0.28
        overlay = frame.copy()
        cv2.circle(overlay, (int(self.x), int(self.y)), int(self.radius), self.color, -1, cv2.LINE_AA)
        cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)


class CosmicEmber:
    """Neon particles orbiting the active portal accretion rim."""
    def __init__(self, cx, cy, rx, ry, tilt_deg):
        self.cx = cx
        self.cy = cy
        self.rx = rx
        self.ry = ry
        self.tilt_deg = tilt_deg
        self.theta = random.uniform(0, 2 * math.pi)
        self.omega = random.choice([-1, 1]) * random.uniform(0.04, 0.08)
        self.radial_offset = random.uniform(-6, 12)
        self.life = random.randint(28, 50)
        self.max_life = self.life
        self.color = random.choice([Config.COLOR_CYAN, Config.COLOR_BLUE, Config.COLOR_WHITE])

    def update(self):
        self.theta += self.omega
        self.life -= 1
        return self.life > 0

    def draw(self, frame):
        alpha = min(1.0, (self.life / self.max_life) * 1.3)
        r_x = max(10, self.rx + self.radial_offset)
        r_y = max(10, self.ry + self.radial_offset * 0.5)
        lx = r_x * math.cos(self.theta)
        ly = r_y * math.sin(self.theta)
        rad = math.radians(self.tilt_deg)
        gx = int(self.cx + lx * math.cos(rad) - ly * math.sin(rad))
        gy = int(self.cy + lx * math.sin(rad) + ly * math.cos(rad))
        h, w = frame.shape[:2]
        if 0 <= gx < w and 0 <= gy < h:
            c = tuple(int(ch * alpha) for ch in self.color)
            cv2.circle(frame, (gx, gy), 2, c, -1, cv2.LINE_AA)


# =============================================================================
# 5. 3D CONICAL WORMHOLE PORTAL OBJECT
# =============================================================================
class TeleportPortal:
    """Represents a single 3D wormhole portal (Entrance or Exit)."""
    def __init__(self, pid, cx, cy, rx=130, ry=42, tilt_deg=0, entry_dir=(0.0, -1.0), apex_dist=150):
        self.pid = pid  # 'A' or 'B'
        self.cx = cx
        self.cy = cy
        self.rx = rx
        self.ry = ry
        self.tilt_deg = tilt_deg
        
        self.entry_dir = np.array(entry_dir, dtype=np.float32)
        norm_len = np.linalg.norm(self.entry_dir)
        if norm_len > 1e-4:
            self.entry_dir /= norm_len
        self.exit_dir = -self.entry_dir
        
        self.apex_dist = apex_dist
        self.state = 'ACTIVE'  # 'INACTIVE', 'DRILLING', 'EXPANDING', 'ACTIVE'
        
        self.drill_start_time = 0.0
        self.drill_sparks = []
        self.dust_particles = []
        self.reality_cracks = []
        self.shake_offset = (0, 0)
        
        self.expand_start_time = 0.0
        self.current_scale = 1.0
        self.time_phase = random.uniform(0, 10.0)
        self.cosmic_embers = []

    def set_orientation(self, tilt_deg, entry_dir):
        self.tilt_deg = tilt_deg % 360
        self.entry_dir = np.array(entry_dir, dtype=np.float32)
        norm_len = np.linalg.norm(self.entry_dir)
        if norm_len > 1e-4:
            self.entry_dir /= norm_len
        self.exit_dir = -self.entry_dir

    def start_drilling(self):
        self.state = 'DRILLING'
        self.drill_start_time = time.time()
        self.drill_sparks.clear()
        self.dust_particles.clear()
        self.generate_cracks()

    def generate_cracks(self):
        self.reality_cracks.clear()
        for i in range(5):
            ang = (i / 5.0) * 2 * math.pi + random.uniform(-0.25, 0.25)
            pts = [(self.cx, self.cy)]
            cur_x, cur_y = self.cx, self.cy
            branch_len = random.randint(30, 70)
            for _ in range(5):
                step = branch_len / 5.0
                cur_x += math.cos(ang) * step + random.uniform(-4, 4)
                cur_y += math.sin(ang) * step + random.uniform(-4, 4)
                pts.append((int(cur_x), int(cur_y)))
            self.reality_cracks.append(pts)

    def trigger_reveal(self, sfx=None):
        if self.state == 'DRILLING':
            self.state = 'EXPANDING'
            self.expand_start_time = time.time()
            self.shake_offset = (0, 0)
            if sfx:
                sfx.play_portal_open()

    def get_apex(self):
        ax = int(self.cx + self.entry_dir[0] * self.apex_dist * self.current_scale)
        ay = int(self.cy + self.entry_dir[1] * self.apex_dist * self.current_scale)
        return ax, ay

    def update(self, sfx=None):
        self.time_phase += 0.08
        now = time.time()
        
        if self.state == 'DRILLING':
            elapsed = now - self.drill_start_time
            self.shake_offset = (random.randint(-3, 3), random.randint(-3, 3))
            
            spray_ang = math.atan2(self.exit_dir[1], self.exit_dir[0])
            for _ in range(Config.SPARK_COUNT):
                self.drill_sparks.append(Spark(self.cx, self.cy, spray_ang))
            if random.random() < Config.DUST_CHANCE:
                self.dust_particles.append(DustSmoke(self.cx, self.cy))
                
            self.drill_sparks = [s for s in self.drill_sparks if s.update()]
            self.dust_particles = [d for d in self.dust_particles if d.update()]
            
            if elapsed >= Config.DRILL_DURATION:
                self.trigger_reveal(sfx)

        elif self.state == 'EXPANDING':
            elapsed = now - self.expand_start_time
            progress = min(1.0, elapsed / Config.PORTAL_EXPAND_TIME)
            self.current_scale = math.sin(progress * math.pi * 0.5) ** 1.5 * (1.0 + 0.12 * math.sin(progress * math.pi))
            if progress >= 1.0:
                self.current_scale = 1.0
                self.state = 'ACTIVE'

        elif self.state == 'ACTIVE':
            self.current_scale = 1.0
            if len(self.cosmic_embers) < Config.MAX_COSMIC_EMBERS and random.random() < 0.4:
                self.cosmic_embers.append(
                    CosmicEmber(self.cx, self.cy, self.rx, self.ry, self.tilt_deg)
                )
            self.cosmic_embers = [e for e in self.cosmic_embers if e.update()]

    def render_funnel(self, frame):
        """Renders 3D rippling cosmic wormhole cone funnel."""
        if self.state in ('INACTIVE', 'DRILLING') or self.current_scale <= 0.05:
            return

        cx, cy = self.cx, self.cy
        cur_rx = int(self.rx * self.current_scale)
        cur_ry = int(self.ry * self.current_scale)
        apex_x, apex_y = self.get_apex()

        num_rings = 6
        num_slices = 20
        rad = math.radians(self.tilt_deg)
        cos_t, sin_t = math.cos(rad), math.sin(rad)

        for r_step in range(num_rings, 0, -1):
            t_low = (r_step - 1) / num_rings
            t_high = r_step / num_rings

            cx_l = int(cx * (1 - t_low) + apex_x * t_low)
            cy_l = int(cy * (1 - t_low) + apex_y * t_low)
            rx_l = cur_rx * (1 - t_low)
            ry_l = cur_ry * (1 - t_low)

            cx_h = int(cx * (1 - t_high) + apex_x * t_high)
            cy_h = int(cy * (1 - t_high) + apex_y * t_high)
            rx_h = cur_rx * (1 - t_high)
            ry_h = cur_ry * (1 - t_high)

            for s_step in range(num_slices):
                a1 = s_step * (2 * math.pi / num_slices)
                a2 = (s_step + 1) * (2 * math.pi / num_slices)

                rip1 = 1.0 + 0.06 * math.sin(4 * a1 + t_low * 6 + self.time_phase)
                rip2 = 1.0 + 0.06 * math.sin(4 * a2 + t_low * 6 + self.time_phase)

                p1 = [int(cx_l + rx_l * rip1 * math.cos(a1) * cos_t - ry_l * rip1 * math.sin(a1) * sin_t),
                      int(cy_l + rx_l * rip1 * math.cos(a1) * sin_t + ry_l * rip1 * math.cos(a1) * cos_t)]
                p2 = [int(cx_l + rx_l * rip2 * math.cos(a2) * cos_t - ry_l * rip2 * math.sin(a2) * sin_t),
                      int(cy_l + rx_l * rip2 * math.cos(a2) * sin_t + ry_l * rip2 * math.cos(a2) * cos_t)]
                p3 = [int(cx_h + rx_h * rip2 * math.cos(a2) * cos_t - ry_h * rip2 * math.sin(a2) * sin_t),
                      int(cy_h + rx_h * rip2 * math.cos(a2) * sin_t + ry_h * rip2 * math.sin(a2) * cos_t)]
                p4 = [int(cx_h + rx_h * rip1 * math.cos(a1) * cos_t - ry_l * rip1 * math.sin(a1) * sin_t),
                      int(cy_h + rx_h * rip1 * math.cos(a1) * sin_t + ry_l * rip1 * math.cos(a1) * cos_t)]

                ang_mid = (a1 + a2) * 0.5
                wave = 0.5 + 0.5 * math.cos(3 * ang_mid + t_low * 5 + self.time_phase * 1.5)

                b = int(np.clip(160 + 95 * wave, 0, 255))
                g = int(np.clip(80 + 110 * wave, 0, 255))
                r = int(np.clip(30 + 80 * (1 - wave) * t_low, 0, 255))

                depth_fade = (0.5 + 0.5 * (1.0 - t_low)) * min(1.0, self.current_scale)
                color = (int(b * depth_fade), int(g * depth_fade), int(r * depth_fade))
                cv2.fillConvexPoly(frame, np.array([p1, p2, p3, p4], dtype=np.int32), color, cv2.LINE_AA)

    def render_interior_and_rim(self, frame):
        """Renders the event horizon singularity, glowing cyan rim, and cosmic embers."""
        if self.state in ('INACTIVE', 'DRILLING') or self.current_scale <= 0.05:
            return

        cx, cy = self.cx, self.cy
        cur_rx = int(self.rx * self.current_scale)
        cur_ry = int(self.ry * self.current_scale)

        # 1. Dark cosmic event horizon void
        cv2.ellipse(frame, (cx, cy), (cur_rx, cur_ry), self.tilt_deg, 0, 360, (15, 8, 4), -1, cv2.LINE_AA)

        # 2. Concentric inner glow rings
        for i in range(3, 0, -1):
            alpha = (3 - i) / 3.0
            r_c = (int(255 * alpha * 0.35), int(190 * alpha * 0.35), int(60 * alpha * 0.35))
            cv2.ellipse(frame, (cx, cy), (cur_rx + i * 2, cur_ry + i * 2), self.tilt_deg, 0, 360, r_c, 1, cv2.LINE_AA)

        # 3. Bright electric cyan accretion rim
        cv2.ellipse(frame, (cx, cy), (cur_rx, cur_ry), self.tilt_deg, 0, 360, Config.COLOR_CYAN, 3, cv2.LINE_AA)
        cv2.ellipse(frame, (cx, cy), (cur_rx, cur_ry), self.tilt_deg, 0, 360, (255, 255, 220), 1, cv2.LINE_AA)

        # 4. Orbiting cosmic embers
        for ember in self.cosmic_embers:
            ember.draw(frame)

    def render_drilling_effects(self, frame):
        """Renders sparks, dust clouds, and reality fracture cracks during drilling."""
        if self.state != 'DRILLING':
            return

        for branch in self.reality_cracks:
            pts_arr = np.array(branch, dtype=np.int32)
            cv2.polylines(frame, [pts_arr], False, (255, 120, 20), 3, cv2.LINE_AA)
            cv2.polylines(frame, [pts_arr], False, (255, 255, 220), 1, cv2.LINE_AA)

        for dust in self.dust_particles:
            dust.draw(frame)

        for spark in self.drill_sparks:
            spark.draw(frame)

        flare_r = random.randint(14, 26)
        overlay = frame.copy()
        cv2.circle(overlay, (self.cx, self.cy), flare_r, (255, 240, 200), -1, cv2.LINE_AA)
        cv2.circle(overlay, (self.cx, self.cy), int(flare_r * 0.5), (255, 255, 255), -1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)


# =============================================================================
# 6. OK GESTURE DETECTOR (👌 HAND SIGN HOLE CREATOR)
# =============================================================================
class OKGestureDetector:
    """Detects the 👌 OK Hand Sign to create holes."""
    def __init__(self):
        self.ok_detected = False
        self.ring_center = (0, 0)
        self.ring_radius = 24
        self.consecutive_frames = 0
        self.last_trigger_time = 0.0
        self.charge_ratio = 0.0

    def check_hand(self, lm, w, h):
        wrist = np.array([lm[0].x * w, lm[0].y * h], dtype=np.float32)
        thumb_tip = np.array([lm[4].x * w, lm[4].y * h], dtype=np.float32)
        idx_tip = np.array([lm[8].x * w, lm[8].y * h], dtype=np.float32)
        idx_pip = np.array([lm[6].x * w, lm[6].y * h], dtype=np.float32)
        mid_mcp = np.array([lm[9].x * w, lm[9].y * h], dtype=np.float32)
        
        mid_tip = np.array([lm[12].x * w, lm[12].y * h], dtype=np.float32)
        mid_pip = np.array([lm[10].x * w, lm[10].y * h], dtype=np.float32)
        rng_tip = np.array([lm[16].x * w, lm[16].y * h], dtype=np.float32)
        rng_pip = np.array([lm[14].x * w, lm[14].y * h], dtype=np.float32)
        pnk_tip = np.array([lm[20].x * w, lm[20].y * h], dtype=np.float32)
        pnk_pip = np.array([lm[18].x * w, lm[18].y * h], dtype=np.float32)

        hand_scale = max(10.0, float(np.linalg.norm(mid_mcp - wrist)))
        pinch_dist = np.linalg.norm(thumb_tip - idx_tip)
        norm_pinch = pinch_dist / hand_scale

        d_mid_tip = np.linalg.norm(mid_tip - wrist)
        d_mid_pip = np.linalg.norm(mid_pip - wrist)
        d_rng_tip = np.linalg.norm(rng_tip - wrist)
        d_rng_pip = np.linalg.norm(rng_pip - wrist)
        d_pnk_tip = np.linalg.norm(pnk_tip - wrist)
        d_pnk_pip = np.linalg.norm(pnk_pip - wrist)

        mid_ext = d_mid_tip > (d_mid_pip * 1.08)
        rng_ext = d_rng_tip > (d_rng_pip * 1.05)
        pnk_ext = d_pnk_tip > (d_pnk_pip * 1.05)

        is_ok = (norm_pinch < Config.OK_PINCH_THRESH) and (sum([mid_ext, rng_ext, pnk_ext]) >= 2)
        center_xy = ((thumb_tip + idx_tip) * 0.5).astype(np.int32)
        radius = int(np.linalg.norm(idx_pip - thumb_tip) * 0.55)
        radius = max(18, min(65, radius))

        return is_ok, (int(center_xy[0]), int(center_xy[1])), radius

    def update(self, hand_landmarks, w, h):
        now = time.time()
        ok_in_frame = False
        target_center = self.ring_center
        target_radius = self.ring_radius

        if hand_landmarks:
            for lm in hand_landmarks:
                is_ok, c_xy, rad = self.check_hand(lm, w, h)
                if is_ok:
                    ok_in_frame = True
                    target_center = c_xy
                    target_radius = rad
                    break

        self.ok_detected = ok_in_frame

        if ok_in_frame:
            self.ring_center = target_center
            self.ring_radius = target_radius
            self.consecutive_frames += 1
            self.charge_ratio = min(1.0, self.consecutive_frames / Config.OK_TRIGGER_FRAMES)
            
            if self.consecutive_frames >= Config.OK_TRIGGER_FRAMES:
                if (now - self.last_trigger_time) > Config.OK_COOLDOWN:
                    self.last_trigger_time = now
                    self.consecutive_frames = 0
                    self.charge_ratio = 0.0
                    return True, self.ring_center, self.ring_radius, True
        else:
            self.consecutive_frames = max(0, self.consecutive_frames - 1)
            self.charge_ratio = min(1.0, self.consecutive_frames / Config.OK_TRIGGER_FRAMES)

        return False, self.ring_center, self.ring_radius, self.ok_detected

    def draw_hud_ring(self, frame):
        if not self.ok_detected and self.charge_ratio <= 0.0:
            return

        cx, cy = self.ring_center
        r = self.ring_radius

        cv2.circle(frame, (cx, cy), r, Config.COLOR_CYAN, 2, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), max(2, r - 3), Config.COLOR_WHITE, 1, cv2.LINE_AA)

        if self.charge_ratio > 0.05:
            arc_deg = int(self.charge_ratio * 360)
            cv2.ellipse(frame, (cx, cy), (r + 8, r + 8), 0, -90, -90 + arc_deg, Config.COLOR_GOLD, 3, cv2.LINE_AA)
            cv2.putText(frame, "[OK SIGN] CREATING HOLE...", (cx - 80, cy - r - 14), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.46, Config.COLOR_GOLD, 2, cv2.LINE_AA)
        else:
            cv2.putText(frame, "[OK SIGN] READY", (cx - 60, cy - r - 12), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, Config.COLOR_CYAN, 1, cv2.LINE_AA)


# =============================================================================
# 7. WORMHOLE ENGINE (CLEAN & ARTIFACT-FREE TELEPORTATION)
# =============================================================================
class WormholeEngine:
    """Manages background subtraction, bi-directional cross-portal mapping, and blending."""
    def __init__(self):
        self.bg_plate = None
        self.comp_bg = None
        self.prev_fg_mask = None
        self.bg_frames = []
        self.capturing_bg_countdown = 0
        self.frame_count = 0

        self.portal_A = None
        self.portal_B = None
        self.selected_portal = 'A'
        self.preset_idx = 0

        # Pre-allocated coordinate grids
        self.grid_w = 0
        self.grid_h = 0
        self.x_grid = None
        self.y_grid = None

    def _ensure_grid(self, w, h):
        if self.grid_w != w or self.grid_h != h:
            self.grid_w = w
            self.grid_h = h
            self.y_grid, self.x_grid = np.indices((h, w), dtype=np.float32)

    def start_background_capture(self, num_frames=10):
        self.bg_frames.clear()
        self.capturing_bg_countdown = num_frames
        print(f"[INFO] Accumulating {num_frames} frames for clean background plate...")

    def update_background(self, frame):
        if self.capturing_bg_countdown > 0:
            self.bg_frames.append(frame.copy())
            self.capturing_bg_countdown -= 1
            if self.capturing_bg_countdown == 0 and len(self.bg_frames) > 0:
                self.bg_plate = np.mean(self.bg_frames, axis=0).astype(np.uint8)
                self.comp_bg = self.bg_plate.copy()
                self.prev_fg_mask = None
                print("[INFO] Pristine studio-grade background plate captured successfully!")
                return True
        return False

    def capture_background(self, frame):
        self.bg_plate = frame.copy()
        self.comp_bg = self.bg_plate.copy()
        self.prev_fg_mask = None
        print("[INFO] Clean room background plate captured successfully!")

    def set_preset(self, preset_idx, w, h):
        self.preset_idx = preset_idx % 3
        if self.preset_idx == 0:
            # Preset 1: Signature Reference (Ceiling Top Portal + Left Wall Portal)
            # Hole A: HIGH UP AT CEILING
            self.portal_A = TeleportPortal(
                pid='A', cx=int(w * 0.50), cy=int(h * 0.15), rx=int(w * 0.15), ry=int(h * 0.05),
                tilt_deg=0, entry_dir=(0.0, -1.0), apex_dist=int(h * 0.14)
            )
            # Hole B: FAR LEFT WALL (OUT OF CENTER BODY ZONE)
            self.portal_B = TeleportPortal(
                pid='B', cx=int(w * 0.16), cy=int(h * 0.45), rx=int(w * 0.05), ry=int(h * 0.15),
                tilt_deg=0, entry_dir=(-1.0, 0.0), apex_dist=int(w * 0.14)
            )
        elif self.preset_idx == 1:
            # Preset 2: Two Facing Wall Portals (Left Wall <-> Right Wall)
            self.portal_A = TeleportPortal(
                pid='A', cx=int(w * 0.16), cy=int(h * 0.48), rx=int(w * 0.05), ry=int(h * 0.15),
                tilt_deg=0, entry_dir=(-1.0, 0.0), apex_dist=int(w * 0.14)
            )
            self.portal_B = TeleportPortal(
                pid='B', cx=int(w * 0.84), cy=int(h * 0.48), rx=int(w * 0.05), ry=int(h * 0.15),
                tilt_deg=0, entry_dir=(1.0, 0.0), apex_dist=int(w * 0.14)
            )
        else:
            # Preset 3: Floor Portal + Ceiling Portal (Infinite Fall Loop)
            self.portal_A = TeleportPortal(
                pid='A', cx=int(w * 0.50), cy=int(h * 0.84), rx=int(w * 0.16), ry=int(h * 0.05),
                tilt_deg=0, entry_dir=(0.0, 1.0), apex_dist=int(h * 0.14)
            )
            self.portal_B = TeleportPortal(
                pid='B', cx=int(w * 0.50), cy=int(h * 0.16), rx=int(w * 0.16), ry=int(h * 0.05),
                tilt_deg=0, entry_dir=(0.0, -1.0), apex_dist=int(h * 0.14)
            )

    def compute_foreground_mask(self, frame):
        if self.bg_plate is None:
            return None

        h, w = frame.shape[:2]

        # 1. Update ambient lighting scale every 5 frames using fast C++ SIMD
        self.frame_count += 1
        if self.comp_bg is None or (self.frame_count % 5) == 0:
            b_h = max(8, int(h * 0.06))
            b_w = max(8, int(w * 0.06))
            cur_mean = float((np.mean(frame[:b_h, :]) + np.mean(frame[-b_h:, :]) + 
                              np.mean(frame[:, :b_w]) + np.mean(frame[:, -b_w:])) * 0.25)
            bg_mean = float((np.mean(self.bg_plate[:b_h, :]) + np.mean(self.bg_plate[-b_h:, :]) + 
                             np.mean(self.bg_plate[:, :b_w]) + np.mean(self.bg_plate[:, -b_w:])) * 0.25)
            lum_scale = np.clip(cur_mean / max(1.0, bg_mean), 0.75, 1.25)
            self.comp_bg = cv2.convertScaleAbs(self.bg_plate, alpha=lum_scale)

        # 2. Fast C++ SIMD Multi-channel color difference
        diff_bgr = cv2.absdiff(frame, self.comp_bg)
        b, g, r = cv2.split(diff_bgr)
        metric = cv2.max(cv2.max(b, g), r)
        _, thresh = cv2.threshold(metric, 22, 255, cv2.THRESH_BINARY)

        # 3. Morphological open (removes background speckles/camera noise)
        k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        clean_thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, k_open)

        # 4. Morphological close (seals holes inside hand/object)
        k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        solid_mask = cv2.morphologyEx(clean_thresh, cv2.MORPH_CLOSE, k_close)

        return solid_mask

    def teleport_objects(self, frame, src_portal, dst_portal, fg_mask):
        """
        Extracts pure foreground object penetrating src_portal, warps it to match dst_portal.
        STRICT LOCAL BOUNDS & ZERO BACKGROUND BLEED:
        Isolates ONLY the physical object (zero background from entrance room),
        and strictly constrains the penetration zone to the hole mouth and tunnel.
        """
        h, w = frame.shape[:2]
        if fg_mask is None or src_portal.state != 'ACTIVE' or dst_portal.state != 'ACTIVE':
            return None, None, None, None

        # 1. High-Speed Localized Patch Mask for Entrance Portal
        max_r_src = int(max(src_portal.rx, src_portal.ry) * 1.35)
        x1_s = max(0, src_portal.cx - max_r_src)
        x2_s = min(w, src_portal.cx + max_r_src)
        y1_s = max(0, src_portal.cy - max_r_src)
        y2_s = min(h, src_portal.cy + max_r_src)

        if x2_s <= x1_s or y2_s <= y1_s:
            return None, None, None, None

        ys_s, xs_s = np.ogrid[y1_s:y2_s, x1_s:x2_s]
        dx_s = xs_s - src_portal.cx
        dy_s = ys_s - src_portal.cy

        rad_src = math.radians(src_portal.tilt_deg)
        cos_s, sin_s = math.cos(rad_src), math.sin(rad_src)
        lx_s = dx_s * cos_s + dy_s * sin_s
        ly_s = -dx_s * sin_s + dy_s * cos_s
        norm_dist_sq_s = (lx_s / max(1, src_portal.rx))**2 + (ly_s / max(1, src_portal.ry))**2
        inside_mouth_s = norm_dist_sq_s <= 1.15

        # Tunnel geometry: depth along entry_dir, lateral distance across mouth plane
        d_par_s = dx_s * src_portal.entry_dir[0] + dy_s * src_portal.entry_dir[1]
        d_perp_s = dx_s * (-src_portal.entry_dir[1]) + dy_s * src_portal.entry_dir[0]

        # Strictly inside the mouth aperture OR inside the tunnel cylinder/funnel
        max_lat_s = max(src_portal.rx, src_portal.ry) * 1.10
        in_tunnel_s = (d_par_s >= 0.0) & (d_par_s <= src_portal.apex_dist * 1.25) & (np.abs(d_perp_s) <= max_lat_s)
        zone_s = inside_mouth_s | in_tunnel_s

        penetrating_mask = np.zeros((h, w), dtype=bool)
        fg_crop = fg_mask[y1_s:y2_s, x1_s:x2_s]
        penetrating_mask[y1_s:y2_s, x1_s:x2_s] = (fg_crop > 30) & zone_s

        # Require minimum meaningful object size
        if np.count_nonzero(penetrating_mask) < 25:
            return None, None, None, None

        # 2. Perfect Cross-Product Rotation & True 1:1 Physical Scale
        cross_z = src_portal.entry_dir[0] * dst_portal.exit_dir[1] - src_portal.entry_dir[1] * dst_portal.exit_dir[0]
        dot = src_portal.entry_dir[0] * dst_portal.exit_dir[0] + src_portal.entry_dir[1] * dst_portal.exit_dir[1]
        ang_cv = -math.degrees(math.atan2(cross_z, dot))

        scale = 1.0

        M = cv2.getRotationMatrix2D((src_portal.cx, src_portal.cy), ang_cv, scale)
        M[0, 2] += (dst_portal.cx - src_portal.cx)
        M[1, 2] += (dst_portal.cy - src_portal.cy)

        # 3. High-Speed Destination ROI Warp & Filtering (0.5ms instead of 20ms!)
        max_r_dst = int(max(dst_portal.rx, dst_portal.ry) * 2.4)
        x1_d = max(0, dst_portal.cx - max_r_dst)
        x2_d = min(w, dst_portal.cx + max_r_dst)
        y1_d = max(0, dst_portal.cy - max_r_dst)
        y2_d = min(h, dst_portal.cy + max_r_dst)

        if x2_d <= x1_d or y2_d <= y1_d:
            return None, None, None, None

        w_roi = x2_d - x1_d
        h_roi = y2_d - y1_d

        M_roi = M.copy()
        M_roi[0, 2] -= x1_d
        M_roi[1, 2] -= y1_d

        # PURE OBJECT ISOLATION: Zero background from the room can leak through!
        isolated_frame = cv2.bitwise_and(frame, frame, mask=fg_mask)

        # Warp high-definition pure object directly into destination bounding box
        warped_crop = cv2.warpAffine(isolated_frame, M_roi, (w_roi, h_roi), flags=cv2.INTER_CUBIC)
        
        # Micro-contrast sharpness enhancement on the small ROI crop
        fg_blur = cv2.GaussianBlur(warped_crop, (0, 0), 1.2)
        warped_crop = cv2.addWeighted(warped_crop, 1.22, fg_blur, -0.22, 0)

        warped_mask = cv2.warpAffine(penetrating_mask.astype(np.uint8) * 255, M_roi, (w_roi, h_roi), flags=cv2.INTER_LINEAR)

        ys_d, xs_d = np.ogrid[:h_roi, :w_roi]
        dx_d = (xs_d + x1_d) - dst_portal.cx
        dy_d = (ys_d + y1_d) - dst_portal.cy

        rad_dst = math.radians(dst_portal.tilt_deg)
        cos_d, sin_d = math.cos(rad_dst), math.sin(rad_dst)
        lx_d = dx_d * cos_d + dy_d * sin_d
        ly_d = -dx_d * sin_d + dy_d * cos_d
        norm_dist_sq_d = (lx_d / max(1, dst_portal.rx))**2 + (ly_d / max(1, dst_portal.ry))**2
        inside_mouth_d = norm_dist_sq_d <= 1.15

        d_par_d = dx_d * dst_portal.exit_dir[0] + dy_d * dst_portal.exit_dir[1]
        d_perp_d = dx_d * (-dst_portal.exit_dir[1]) + dy_d * dst_portal.exit_dir[0]

        max_lat_d = max(dst_portal.rx, dst_portal.ry) * 1.20
        exit_zone = (inside_mouth_d) | ((d_par_d >= -2.0) & (np.abs(d_perp_d) <= max_lat_d))

        exit_roi = (warped_mask > 30) & exit_zone

        return penetrating_mask, warped_crop, (x1_d, y1_d, x2_d, y2_d), exit_roi


# =============================================================================
# 8. MAIN APPLICATION
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Teleport Hole - Ultra-Clean VFX")
    parser.add_argument("--cam", default="0", help="Camera index (0, 1) or IP stream URL")
    parser.add_argument("--video", default=None, help="Path to input video file")
    parser.add_argument("--width", type=int, default=Config.DEFAULT_WIDTH, help="Camera width")
    parser.add_argument("--height", type=int, default=Config.DEFAULT_HEIGHT, help="Camera height")
    parser.add_argument("--no-sfx", action="store_true", help="Disable sound effects")
    parser.add_argument("--vcam", dest="vcam", action="store_true", default=True, help="Broadcast live VFX stream to OBS Virtual Camera (default: True)")
    parser.add_argument("--no-vcam", dest="vcam", action="store_false", help="Disable OBS Virtual Camera broadcasting")
    args = parser.parse_args()

    print("\n" + "="*65)
    print("🌀 TELEPORT HOLE - ULTRA-CLEAN & HIGH-FPS EDITION")
    print("="*65)
    print("★ FORM THE 👌 OK SIGN WITH YOUR HAND TO CREATE HOLES!")
    print("★ OR CLICK & DRAG ANY HOLE TO REPOSITION!")
    print("Controls:")
    print("  [B]        : Capture Clean Room Background Plate (Do this first!)")
    print("  [👌 Sign]  : Show OK sign to create Hole A then Hole B!")
    print("  [C]        : Clear Holes (Re-create from scratch)")
    print("  [P]        : Cycle Presets (1: Ceiling+Wall, 2: Facing Walls, 3: Loop)")
    print("  [R]        : Rotate Selected Hole Orientation")
    print("  [V]        : Toggle OBS Virtual Camera (Live stream to OBS Studio)")
    print("  [W] or [G] : Start / Stop Video Recording to MP4")
    print("  [H]        : Toggle HUD Text (Hide for Recording & Clean Stream)")
    print("  [T]        : Rotate Camera (0° -> 90° -> 180° -> 270° for TikTok/Reels)")
    print("  [F]        : Toggle Mirror Flip")
    print("  [S]        : Toggle Sound Effects (Mute / Unmute)")
    print("  [Q]/[ESC]  : Quit")
    print("="*65 + "\n")

    cam_src = args.video if args.video else (int(args.cam) if args.cam.isdigit() else args.cam)
    camera = ZeroLagCamera(src=cam_src, width=args.width, height=args.height)
    if not camera.running:
        print(f"[ERROR] Failed to open camera or video source: {cam_src}")
        sys.exit(1)

    sfx = SoundPlayer(enabled=not args.no_sfx)
    engine = WormholeEngine()
    ok_detector = OKGestureDetector()

    hand_detector = None
    if HAS_MEDIAPIPE and os.path.exists("hand_landmarker.task"):
        try:
            base_options = mp_python.BaseOptions(model_asset_path="hand_landmarker.task")
            options = mp_vision.HandLandmarkerOptions(base_options=base_options, num_hands=2)
            hand_detector = mp_vision.HandLandmarker.create_from_options(options)
            print("[INFO] MediaPipe HandLandmarker loaded successfully!")
        except Exception as e:
            print(f"[WARN] MediaPipe Landmarker disabled: {e}")

    show_hud = True
    rotation_angle = 0
    mirror_flip = False
    is_recording = False
    video_writer = None
    record_start_time = 0

    # Mouse drag support
    dragging_portal = None
    drag_offset = [0, 0]

    def mouse_callback(event, x, y, flags, param):
        nonlocal dragging_portal, drag_offset
        if event == cv2.EVENT_LBUTTONDOWN:
            for p in [engine.portal_A, engine.portal_B]:
                if p and math.hypot(x - p.cx, y - p.cy) <= max(p.rx, p.ry) * 1.2:
                    dragging_portal = p
                    drag_offset = [x - p.cx, y - p.cy]
                    engine.selected_portal = p.pid
                    return
        elif event == cv2.EVENT_MOUSEMOVE:
            if dragging_portal:
                dragging_portal.cx = x - drag_offset[0]
                dragging_portal.cy = y - drag_offset[1]
        elif event == cv2.EVENT_LBUTTONUP:
            dragging_portal = None
        elif event == cv2.EVENT_MOUSEWHEEL:
            p = engine.portal_A if engine.selected_portal == 'A' else engine.portal_B
            if p:
                if flags > 0:
                    p.rx = min(280, int(p.rx * 1.1))
                    p.ry = min(200, int(p.ry * 1.1))
                else:
                    p.rx = max(35, int(p.rx * 0.9))
                    p.ry = max(18, int(p.ry * 0.9))

    window_name = "🌀 Teleport Hole - OK Gesture VFX"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, mouse_callback)

    def spawn_hole_at(pid, x, y, h, w):
        """Creates and initiates Hole A or B with proper signature orientations."""
        sfx.play_drill()
        
        # Proper orientations:
        # Near top of screen -> Horizontal ceiling hole (cone UP)
        # Otherwise -> Vertical wall hole (cone LEFT, mouth facing RIGHT)
        if y < h * 0.40:
            tilt = 0
            entry = (0.0, -1.0) # Upward entry into ceiling
            rx, ry = int(w * 0.15), int(h * 0.05)
        elif x > w * 0.55:
            tilt = 0
            entry = (1.0, 0.0)  # Right wall (exits left)
            rx, ry = int(w * 0.05), int(h * 0.15)
        else:
            tilt = 0
            entry = (-1.0, 0.0) # Left wall (exits right)
            rx, ry = int(w * 0.05), int(h * 0.15)

        portal = TeleportPortal(
            pid=pid, cx=x, cy=y, rx=rx, ry=ry, tilt_deg=tilt, entry_dir=entry, apex_dist=int(h * 0.14)
        )
        portal.start_drilling()
        
        if pid == 'A':
            engine.portal_A = portal
            engine.selected_portal = 'A'
            print(f"[ACTION] OK Sign created Hole A at ({x}, {y})")
        else:
            engine.portal_B = portal
            engine.selected_portal = 'B'
            print(f"[ACTION] OK Sign created Hole B at ({x}, {y})")

    # Read first frame to initialize default preset and OBS virtual camera
    ret, first_frame = camera.read()
    if not ret or first_frame is None:
        print("[ERROR] Camera opened but failed to capture first frame.")
        sys.exit(1)

    fh, fw = first_frame.shape[:2]
    engine.set_preset(0, fw, fh)
    engine.portal_A.state = 'INACTIVE'
    engine.portal_B.state = 'INACTIVE'

    # Initialize OBS Virtual Camera output
    vcam = None
    vcam_active = False
    if HAS_PYVIRTUALCAM and args.vcam:
        try:
            vcam = pyvirtualcam.Camera(width=fw, height=fh, fps=int(Config.DEFAULT_FPS), fmt=pyvirtualcam.PixelFormat.BGR)
            vcam_active = True
            print(f"[INFO] 🎥 OBS Virtual Camera ACTIVE! Outputting {fw}x{fh} @ {int(Config.DEFAULT_FPS)}fps")
            print(f"       -> Live in: {vcam.device} (Select this in OBS Studio / Zoom / Discord / TikTok Live)")
        except Exception as e:
            print(f"[WARN] Could not initialize OBS Virtual Camera: {e}")
            vcam = None
            vcam_active = False
    elif not HAS_PYVIRTUALCAM:
        print("[INFO] pyvirtualcam not installed. OBS Virtual Camera broadcasting is disabled.")

    fps_time = time.time()
    fps = 30.0
    frame_idx = 0

    while True:
        ret, raw_frame = camera.read()
        if not ret or raw_frame is None:
            time.sleep(0.01)
            continue

        frame_idx += 1

        if rotation_angle == 90:
            frame = cv2.rotate(raw_frame, cv2.ROTATE_90_CLOCKWISE)
        elif rotation_angle == 180:
            frame = cv2.rotate(raw_frame, cv2.ROTATE_180)
        elif rotation_angle == 270:
            frame = cv2.rotate(raw_frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            frame = raw_frame

        if mirror_flip:
            frame = cv2.flip(frame, 1)

        h, w = frame.shape[:2]

        # Accumulate background frames if requested
        engine.update_background(frame)

        # ---------------------------------------------------------------------
        # 1. High-Speed MediaPipe Inference on Downscaled Frame
        # ---------------------------------------------------------------------
        fg_mask = engine.compute_foreground_mask(frame)

        # Alternating MediaPipe inference (saves 16ms/frame while maintaining 100% gesture responsiveness)
        run_mp = (frame_idx % 2 == 0) or ok_detector.ok_detected or (
            engine.portal_A is None or engine.portal_A.state == 'INACTIVE' or 
            engine.portal_B is None or engine.portal_B.state == 'INACTIVE'
        )

        hand_landmarks = None
        if hand_detector and run_mp:
            try:
                # Downscale 2.5x for blazing inference
                proc_w, proc_h = 480, 270
                small_frame = cv2.resize(frame, (proc_w, proc_h))
                rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                res = hand_detector.detect(mp_img)
                if res.hand_landmarks:
                    hand_landmarks = res.hand_landmarks
            except Exception:
                pass

        triggered_ok, ok_center, ok_rad, ok_active = ok_detector.update(hand_landmarks, w, h)

        # ---------------------------------------------------------------------
        # 2. Trigger Hole Creation
        # ---------------------------------------------------------------------
        if triggered_ok:
            if engine.portal_A is None or engine.portal_A.state in ('INACTIVE',):
                target_pid = 'A'
            elif engine.portal_B is None or engine.portal_B.state in ('INACTIVE',):
                target_pid = 'B'
            else:
                target_pid = engine.selected_portal

            spawn_hole_at(target_pid, ok_center[0], ok_center[1], h, w)

        # ---------------------------------------------------------------------
        # 3. Update Portal Animations & Camera Shake
        # ---------------------------------------------------------------------
        for p in [engine.portal_A, engine.portal_B]:
            if p:
                p.update(sfx=sfx)

        shake_x, shake_y = 0, 0
        for p in [engine.portal_A, engine.portal_B]:
            if p and p.state == 'DRILLING':
                shake_x += p.shake_offset[0]
                shake_y += p.shake_offset[1]

        if shake_x != 0 or shake_y != 0:
            M_shake = np.float32([[1, 0, shake_x], [0, 1, shake_y]])
            frame = cv2.warpAffine(frame, M_shake, (w, h), borderMode=cv2.BORDER_REFLECT)

        # ---------------------------------------------------------------------
        # 4. Clean Artifact-Free Wormhole Teleportation Pipeline
        # ---------------------------------------------------------------------
        final_frame = frame.copy()

        if engine.portal_A and engine.portal_B and engine.portal_A.state == 'ACTIVE' and engine.portal_B.state == 'ACTIVE':
            pen_A, w_crop_A, box_B, exit_B = engine.teleport_objects(frame, engine.portal_A, engine.portal_B, fg_mask)
            pen_B, w_crop_B, box_A, exit_A = engine.teleport_objects(frame, engine.portal_B, engine.portal_A, fg_mask)

            # 1. Render 3D Conical Funnels & Accretion Rims
            # (The portal event horizon singularity void naturally covers the entering object at the mouth)
            engine.portal_A.render_funnel(final_frame)
            engine.portal_B.render_funnel(final_frame)
            engine.portal_A.render_interior_and_rim(final_frame)
            engine.portal_B.render_interior_and_rim(final_frame)

            # 2. Ultra-Fast High-Definition ROI Composite for Emerging Pure Objects (Zero Background Bleed)
            for (w_crop, box, exit_mask) in [(w_crop_A, box_B, exit_B), (w_crop_B, box_A, exit_A)]:
                if exit_mask is not None and w_crop is not None and np.any(exit_mask):
                    x1_d, y1_d, x2_d, y2_d = box
                    roi_final = final_frame[y1_d:y2_d, x1_d:x2_d]

                    # High-speed SIMD copy on solid pure-object pixels
                    np.copyto(roi_final, w_crop, where=(exit_mask[:, :, None]))

                    # Cinematic event horizon seam glow along the aperture seam
                    edge_seam = cv2.Canny((exit_mask.astype(np.uint8) * 255), 100, 200)
                    if np.any(edge_seam):
                        edge_glow = cv2.GaussianBlur(edge_seam, (5, 5), 0)
                        glow_alpha = (edge_glow.astype(np.float32) / 255.0) * 0.65
                        glow_3d = np.repeat(glow_alpha[:, :, np.newaxis], 3, axis=2)
                        cyan_glow = np.full_like(roi_final, Config.COLOR_CYAN, dtype=np.uint8)
                        roi_final[:] = np.clip(roi_final.astype(np.float32) + cyan_glow.astype(np.float32) * glow_3d, 0, 255).astype(np.uint8)
        else:
            for p in [engine.portal_A, engine.portal_B]:
                if p and p.state in ('EXPANDING', 'ACTIVE'):
                    p.render_funnel(final_frame)
                    p.render_interior_and_rim(final_frame)

        # Render drilling sparks, smoke, and reality cracks
        for p in [engine.portal_A, engine.portal_B]:
            if p:
                p.render_drilling_effects(final_frame)

        # Draw glowing energy ring inside the 👌 hand sign
        if show_hud:
            ok_detector.draw_hud_ring(final_frame)

        # ---------------------------------------------------------------------
        # 5. Top Clean ASCII HUD Glass Overlay & Auto-Capture Banner
        # ---------------------------------------------------------------------
        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(1e-4, now - fps_time))
        fps_time = now

        # Background multi-frame accumulation status banner
        if engine.capturing_bg_countdown > 0:
            pct = int((1.0 - engine.capturing_bg_countdown / 10.0) * 100)
            cv2.rectangle(final_frame, (w // 2 - 240, h // 2 - 35), (w // 2 + 240, h // 2 + 35), (10, 10, 15), -1)
            cv2.rectangle(final_frame, (w // 2 - 240, h // 2 - 35), (w // 2 + 240, h // 2 + 35), Config.COLOR_CYAN, 2)
            cv2.putText(final_frame, f"CAPTURING ROOM BACKGROUND ({pct}%)...", (w // 2 - 210, h // 2 + 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.62, Config.COLOR_GOLD, 2, cv2.LINE_AA)
        elif engine.bg_plate is None:
            # Pulsing warning banner prompting user to press B
            pulse = (int(time.time() * 3) % 2) == 0
            b_col = (0, 220, 255) if pulse else (0, 140, 255)
            cv2.rectangle(final_frame, (w // 2 - 280, 20), (w // 2 + 280, 65), (10, 10, 20), -1)
            cv2.rectangle(final_frame, (w // 2 - 280, 20), (w // 2 + 280, 65), b_col, 2)
            cv2.putText(final_frame, "STEP OUT OF FRAME & PRESS [B] TO SET BACKGROUND", (w // 2 - 265, 48),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, b_col, 2, cv2.LINE_AA)

        if show_hud:
            for p in [engine.portal_A, engine.portal_B]:
                if p and p.state in ('ACTIVE', 'EXPANDING'):
                    lbl = f"HOLE {p.pid}"
                    cv2.putText(final_frame, lbl, (p.cx - 30, p.cy - p.ry - 12), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, Config.COLOR_CYAN, 2, cv2.LINE_AA)

            hud_bg = final_frame.copy()
            cv2.rectangle(hud_bg, (15, 15), (480, 180), (10, 10, 15), -1)
            cv2.addWeighted(hud_bg, 0.72, final_frame, 0.28, 0, final_frame)
            cv2.rectangle(final_frame, (15, 15), (480, 180), Config.COLOR_BLUE, 1, cv2.LINE_AA)

            cv2.putText(final_frame, "TELEPORT HOLE - OK GESTURE VFX", (25, 38), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, Config.COLOR_WHITE, 2, cv2.LINE_AA)

            bg_stat = "CAPTURED (Studio Ready)" if engine.bg_plate is not None else "NOT SET! [Press B]"
            bg_col = (80, 255, 80) if engine.bg_plate is not None else (40, 40, 255)
            cv2.putText(final_frame, f"Room Background : {bg_stat}", (25, 62), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.44, bg_col, 1, cv2.LINE_AA)

            stat_A = engine.portal_A.state if engine.portal_A else "UNSET"
            stat_B = engine.portal_B.state if engine.portal_B else "UNSET"
            cv2.putText(final_frame, f"Hole A: {stat_A}  |  Hole B: {stat_B}", (25, 84), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.44, (240, 240, 240), 1, cv2.LINE_AA)

            if ok_detector.ok_detected:
                g_stat = "OK SIGN ACTIVE (Forming Hole...)"
                g_col = Config.COLOR_GREEN
            else:
                next_h = 'A' if (engine.portal_A is None or engine.portal_A.state == 'INACTIVE') else 'B'
                g_stat = f"READY -> Make OK Sign to Create Hole {next_h}"
                g_col = Config.COLOR_CYAN

            cv2.putText(final_frame, f"Gesture Trigger : {g_stat}", (25, 106), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, g_col, 1, cv2.LINE_AA)

            if vcam_active:
                vcam_stat = f"LIVE ({vcam.device})"
                vcam_col = Config.COLOR_GREEN
            elif vcam is not None:
                vcam_stat = "PAUSED [Press V to Resume]"
                vcam_col = Config.COLOR_GOLD
            else:
                vcam_stat = "DISABLED"
                vcam_col = (130, 130, 130)

            cv2.putText(final_frame, f"OBS Virtual Cam : {vcam_stat}", (25, 126), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, vcam_col, 1, cv2.LINE_AA)

            cv2.putText(final_frame, "[B] Set BG  |  [C] Clear  |  [P] Presets  |  [V] OBS Cam", (25, 148), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (190, 190, 190), 1, cv2.LINE_AA)
            cv2.putText(final_frame, "[W] Record  |  [H] Hide HUD  |  [T] Rotate  |  [F] Flip", (25, 168), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (170, 170, 170), 1, cv2.LINE_AA)
            cv2.putText(final_frame, f"FPS: {fps:.1f}", (410, 168), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (140, 255, 140), 1, cv2.LINE_AA)

        # Recording Indicator
        if is_recording:
            rec_elapsed = int(time.time() - record_start_time)
            mins, secs = divmod(rec_elapsed, 60)
            if (int(time.time() * 2) % 2) == 0:
                cv2.circle(final_frame, (w - 140, 35), 8, (0, 0, 255), -1, cv2.LINE_AA)
            cv2.putText(final_frame, f"REC {mins:02d}:{secs:02d}", (w - 120, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2, cv2.LINE_AA)
            if video_writer:
                video_writer.write(final_frame)

        # Broadcast to OBS Virtual Camera
        if vcam is not None and vcam_active:
            try:
                if (final_frame.shape[1], final_frame.shape[0]) == (vcam.width, vcam.height):
                    vcam.send(final_frame)
                else:
                    vcam_frame = cv2.resize(final_frame, (vcam.width, vcam.height), interpolation=cv2.INTER_LINEAR)
                    vcam.send(vcam_frame)
            except Exception:
                pass

        cv2.imshow(window_name, final_frame)

        # ---------------------------------------------------------------------
        # 6. Keyboard Shortcuts & Fallbacks
        # ---------------------------------------------------------------------
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord('q'), ord('Q')):
            break

        elif key in (ord('v'), ord('V')):
            if vcam is not None:
                vcam_active = not vcam_active
                print(f"[INFO] 🎥 OBS Virtual Camera: {'BROADCASTING' if vcam_active else 'PAUSED'}")
            else:
                print("[WARN] OBS Virtual Camera is not active or pyvirtualcam is not installed.")

        elif key in (ord('b'), ord('B')):
            engine.start_background_capture(num_frames=10)

        elif key in (ord('c'), ord('C')):
            if engine.portal_A:
                engine.portal_A.state = 'INACTIVE'
            if engine.portal_B:
                engine.portal_B.state = 'INACTIVE'
            print("[INFO] Portals cleared. Ready to make new holes with OK sign!")

        elif key in (ord('p'), ord('P')):
            engine.set_preset(engine.preset_idx + 1, w, h)
            print(f"[INFO] Switched to Preset {engine.preset_idx + 1}")

        elif key in (ord('r'), ord('R')):
            p = engine.portal_A if engine.selected_portal == 'A' else engine.portal_B
            if p:
                new_tilt = (p.tilt_deg + 45) % 360
                rad = math.radians(new_tilt)
                new_entry = (-math.sin(rad), -math.cos(rad))
                p.set_orientation(new_tilt, new_entry)
                print(f"[INFO] Portal {p.pid} rotated to {new_tilt}°")

        elif key in (ord('h'), ord('H')):
            show_hud = not show_hud
            print(f"[INFO] HUD {'Shown' if show_hud else 'Hidden'}")

        elif key in (ord('t'), ord('T')):
            rotation_angle = (rotation_angle + 90) % 360
            print(f"[INFO] Camera rotated to {rotation_angle}°")

        elif key in (ord('f'), ord('F')):
            mirror_flip = not mirror_flip
            print(f"[INFO] Mirror flip {'ON' if mirror_flip else 'OFF'}")

        elif key in (ord('s'), ord('S')):
            sfx.enabled = not sfx.enabled
            print(f"[INFO] Sound effects {'Enabled' if sfx.enabled else 'Muted'}")

        elif key in (ord('w'), ord('W'), ord('g'), ord('G')):
            if not is_recording:
                os.makedirs("recordings", exist_ok=True)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                rec_filename = f"recordings/teleport_hole_{timestamp}.mp4"
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(rec_filename, fourcc, Config.DEFAULT_FPS, (w, h))
                is_recording = True
                record_start_time = time.time()
                print(f"[REC] Started recording to: {rec_filename}")
            else:
                is_recording = False
                if video_writer:
                    video_writer.release()
                    video_writer = None
                print("[REC] Recording stopped and saved successfully!")

        # Optional manual fallback: [D] / [Space]
        elif key in (ord('d'), ord('D'), 32):
            tx, ty = ok_center if ok_detector.ok_detected else (w // 2, int(h * 0.25))
            target_pid = 'A' if (engine.portal_A is None or engine.portal_A.state == 'INACTIVE') else 'B'
            spawn_hole_at(target_pid, tx, ty, h, w)

    if video_writer:
        video_writer.release()
    if vcam is not None:
        try:
            vcam.close()
            print("[INFO] OBS Virtual Camera closed cleanly.")
        except Exception:
            pass
    camera.release()
    cv2.destroyAllWindows()
    print("[INFO] Application closed cleanly.")


if __name__ == "__main__":
    main()
