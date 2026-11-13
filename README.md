# 🌀 Teleport Hole — 👌 OK Sign Edition (Viral VFX)

A real-time Python computer vision application inspired by the viral **"Teleport Hole" / Portal Illusion Meme**.

**CREATE HOLES WITH YOUR HAND GESTURE:** Simply form the **👌 OK Hand Sign** to open cosmic teleport wormholes right in the air!

---

## ⚡ How the 👌 OK Sign Creates the Holes

1. **👌 Gesture Detection**:
   - Touch your **thumb tip and index finger tip** together to form a ring / circle.
   - Keep your **other three fingers (middle, ring, pinky) extended**.
   - An animated glowing cyan cosmic energy ring appears **directly inside your finger circle**: `[👌 CREATING HOLE...]`!

2. **Cosmic Explosion & Hole A Opening**:
   - Hold the 👌 sign for **~0.2 seconds** at Spot 1 (ceiling / door / wall):
     - **Molten sparks** spray out from your finger ring!
     - **Industrial hammer drill roar** (`drill_sound.wav`) & **portal opening whoosh** (`portal_open.wav`)!
     - **Reality fracture cracks** spiderweb outward from your fingers!
     - **Camera vibration / screen rumble**!
     - The hole expands open into a **3D cosmic wormhole funnel** right where your fingers made the circle!
     - That is **Hole A**!

3. **Drill Hole B**:
   - Move your hand to **Spot 2** (e.g. side wall next to your friend or dad).
   - Form the **👌 OK sign again**:
     - Another burst of sparks, drill sound, and cracks!
     - **Hole B** bursts open, quantum-entangled with Hole A!

4. **The Teleport Illusion**:
   - Push your hand, your electric drill, or a coffee mug into **Hole A**:
   - It seamlessly vanishes into Hole A and **shoots out of Hole B** in real time!
   - An emissive neon cyan plasma seam illuminates the object as it penetrates the dimensional rift.

---

## 🚀 Quick Step-by-Step Instructions

1. **Launch**:
   - Double-click **`run.bat`** or run:
     ```bash
     python teleport_portal.py
     ```
2. **Room Background**:
   - Step out of frame for 1 second and press **`B`** to capture your clean room plate.
3. **Spawn Hole A**:
   - Aim your hand at the ceiling/top and make the **👌 OK sign** $\rightarrow$ Hole A opens!
4. **Spawn Hole B**:
   - Move your hand to the side wall and make the **👌 OK sign** $\rightarrow$ Hole B opens!
5. **Record Your Video**:
   - Press **`W`** to start recording (`● REC` on screen).
   - Perform the prank!
   - Press **`W`** again to stop and automatically save the MP4 video in `recordings/`.

---

## 🎮 Controls Summary

| Key / Action | Function |
| :--- | :--- |
| **`B`** | **Capture Clean Room Background Plate** (Do this first) |
| **👌 OK Sign** | **Create Hole A (Entrance) then Hole B (Exit)** |
| **Left Click Drag** | **Move / Reposition any hole anywhere interactively** |
| **Scroll Wheel** | **Scale / Resize hole dynamically** |
| **`C`** | **Clear Holes** (Reset to make new holes) |
| **`P`** | **Cycle Presets** (1: Ceiling+Wall, 2: Facing Walls, 3: Loop) |
| **`R`** | **Rotate Selected Hole Orientation** (0° ➔ 45° ➔ 90°...) |
| **`V`** | **Toggle OBS Virtual Camera Output** (Live stream to OBS / Discord) |
| **`W` / `G`** | **Start / Stop Recording Video to MP4** |
| **`H`** | **Toggle HUD Overlay** (Hide UI for clean movie recording & stream) |
| **`T`** | **Rotate Camera** (0° ➔ 90° ➔ 180° ➔ 270° for TikTok / Reels 9:16) |
| **`F`** | **Toggle Horizontal Mirror Flip** (Selfie vs Rear camera) |
| **`S`** | **Toggle Sound Effects** (Mute / Unmute) |
| **`Q` / `ESC`** | **Quit** |
| *(Fallback: `D`/`Space`)* | *(Optional manual keyboard trigger)* |

---

## 🎥 OBS Studio Integration

The script now features built-in **OBS Virtual Camera** support powered by `pyvirtualcam`!

### Mode 1: Send Live VFX Directly to OBS Studio / TikTok Live / Discord
1. Launch the script:
   ```bash
   python teleport_portal.py
   ```
   *(OBS Virtual Camera output is enabled automatically by default!)*
2. In **OBS Studio**:
   - In your Scene, click **Sources (+)** $\rightarrow$ **Video Capture Device**.
   - Select **"OBS Virtual Camera"** as the device.
   - You will instantly see the live teleport hole VFX directly inside OBS!
3. **Controls during stream**:
   - Press **`V`** to pause/resume the virtual camera output at any time.
   - Press **`H`** to hide the HUD on-screen so your OBS feed is 100% clean cinematic video.
   - To disable the virtual camera entirely, run:
     ```bash
     python teleport_portal.py --no-vcam
     ```

### Mode 2: Use OBS Studio as Input Camera
If you use OBS Studio to manage scenes, overlays, or filters and want to send that into the script:
1. In OBS Studio, click **"Start Virtual Camera"** in the bottom-right controls panel.
2. Launch the script targeting the OBS virtual camera index (typically `--cam 1` or `--cam 2`):
   ```bash
   python teleport_portal.py --cam 1 --no-vcam
   ```
   *(The script's multi-backend auto-fallback will automatically detect the active camera).*

---

## 📱 Camera Options

- **Default Webcam (with auto-detection)**: `python teleport_portal.py`
- **OBS Virtual Camera Output (Default)**: Automatically broadcasts live to OBS Studio
- **Phone Cam via DroidCam / Iriun**: `python teleport_portal.py --cam 1`
- **IP Webcam Wi-Fi Stream**: `python teleport_portal.py --cam http://192.168.1.50:8080/video`
- **Pre-Recorded Video**: `python teleport_portal.py --video path/to/video.mp4`
