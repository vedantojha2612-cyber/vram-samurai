import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

f_title = ImageFont.truetype(FONT_SANS, 24)
f_sub = ImageFont.truetype(FONT_MONO, 14)
f_tui = ImageFont.truetype(FONT_MONO, 12)
f_stat = ImageFont.truetype(FONT_SANS, 18)
f_stat_val = ImageFont.truetype(FONT_MONO, 22)
f_badge = ImageFont.truetype(FONT_MONO, 13)

WIDTH = 1000
HEIGHT = 560
FRAMES = 36  # ~3.6s at 100ms per frame
FPS = 10

images = []

for frame_idx in range(FRAMES):
    t = frame_idx / FRAMES
    im = Image.new("RGBA", (WIDTH, HEIGHT), (6, 9, 17, 255))
    draw = ImageDraw.Draw(im)

    # Background subtle grid
    for x in range(0, WIDTH, 40):
        draw.line([(x, 0), (x, HEIGHT)], fill=(12, 18, 30, 255), width=1)
    for y in range(0, HEIGHT, 40):
        draw.line([(0, y), (WIDTH, y)], fill=(12, 18, 30, 255), width=1)

    # Header Bar
    draw.rectangle([(16, 14), (WIDTH - 16, 56)], fill=(10, 16, 28, 220), outline=(0, 240, 255, 100), width=1)
    draw.ellipse([(30, 28), (42, 40)], fill=(0, 255, 136, 255))
    draw.text((52, 24), "VRAM-SAMURAI // DUAL TELEMETRY HUD & TUI", font=f_title, fill=(0, 240, 255, 255))
    draw.text((WIDTH - 300, 28), "STATUS: WS LIVE 8765 | 3.15 µs", font=f_badge, fill=(0, 255, 136, 255))

    # LEFT PANEL: Terminal TUI Simulator (x: 16 to 480)
    draw.rectangle([(16, 70), (480, HEIGHT - 20)], fill=(8, 12, 22, 240), outline=(0, 240, 255, 60), width=1)
    draw.rectangle([(16, 70), (480, 98)], fill=(14, 22, 38, 255))
    draw.ellipse([(26, 80), (34, 88)], fill=(255, 95, 86, 255))
    draw.ellipse([(40, 80), (48, 88)], fill=(255, 189, 46, 255))
    draw.ellipse([(54, 80), (62, 88)], fill=(39, 201, 63, 255))
    draw.text((72, 77), "Terminal: python3 vram-samurai/tui/app.py", font=f_sub, fill=(160, 180, 210, 255))

    tui_y = 110
    draw.text((28, tui_y), "┌─ [ KV-CACHE PAGEDATTENTION MATRIX (1,024 Pages) ] ─┐", font=f_tui, fill=(0, 240, 255, 255))
    tui_y += 20

    # Draw simulated ANSI block matrix
    phase = (math.sin(t * math.pi * 2) + 1) / 2
    for r in range(6):
        row_str = "│ "
        draw.text((28, tui_y), "│ ", font=f_tui, fill=(0, 240, 255, 255))
        col_x = 42
        for c in range(24):
            idx = r * 24 + c
            if idx < 45:
                char, col = "⮰", (255, 184, 0, 255)  # Prefix cached (amber)
            elif idx < 45 + int(40 + phase * 40):
                char, col = "■", (0, 240, 255, 255)  # Active (cyan)
            elif idx < 45 + int(40 + phase * 40) + (18 if phase > 0.6 else 4):
                char, col = "✖", (255, 0, 60, 255)   # Fragmented (crimson)
            else:
                char, col = "·", (45, 60, 85, 255)   # Free
            draw.text((col_x, tui_y), char, font=f_tui, fill=col)
            col_x += 16
        draw.text((430, tui_y), "│", font=f_tui, fill=(0, 240, 255, 255))
        tui_y += 18

    draw.text((28, tui_y), "└────────────────────────────────────────────────────┘", font=f_tui, fill=(0, 240, 255, 255))
    tui_y += 30

    tokens_sec = int(68 + math.sin(t * math.pi * 4) * 14)
    p95_val = round(1.24 + math.cos(t * math.pi * 4) * 0.22, 2)
    ttft_val = round(14.8 + math.sin(t * math.pi * 2) * 1.5, 1)

    draw.text((28, tui_y), f"THROUGHPUT: {tokens_sec} tokens/sec", font=f_sub, fill=(0, 255, 136, 255))
    tui_y += 24
    draw.text((28, tui_y), f"TTFT: {ttft_val} ms  |  ITL P95: {p95_val} ms", font=f_sub, fill=(0, 240, 255, 255))
    tui_y += 24
    draw.text((28, tui_y), "PROFILER OVERHEAD: 3.15 µs (0.003 ms)", font=f_sub, fill=(255, 184, 0, 255))
    tui_y += 30

    # Mini sparkline
    draw.text((28, tui_y), "LIVE STREAM DELTAS:", font=f_tui, fill=(100, 120, 150, 255))
    tui_y += 18
    pts = []
    for i in range(30):
        sx = 28 + i * 14
        sy = tui_y + 40 - int(math.sin((t * 20 + i) * 0.5) * 15 + 18)
        pts.append((sx, sy))
    if len(pts) > 1:
        draw.line(pts, fill=(0, 240, 255, 255), width=2)

    # RIGHT PANEL: 3D Web HUD Spatial Matrix (x: 496 to WIDTH-16)
    draw.rectangle([(496, 70), (WIDTH - 16, HEIGHT - 20)], fill=(8, 12, 22, 240), outline=(0, 240, 255, 60), width=1)
    draw.rectangle([(496, 70), (WIDTH - 16, 98)], fill=(14, 22, 38, 255))
    draw.text((512, 77), "WebGL: 3D Spatial Memory Matrix (16x16x4)", font=f_sub, fill=(0, 240, 255, 255))

    # Center of right panel: (732, 280)
    cx, cy = 732, 280
    angle = t * math.pi * 2
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    # Render pseudo-3D rotating cube grid of blocks
    grid_size = 5
    spacing = 26
    for gz in range(-2, 3):
        for gy in range(-2, 3):
            for gx in range(-2, 3):
                # 3D rotation around Y
                rx = gx * cos_a - gz * sin_a
                rz = gx * sin_a + gz * cos_a
                ry = gy

                # Perspective projection
                focal = 280
                proj_z = rz * spacing + 400
                scale = focal / proj_z
                px = int(cx + rx * spacing * scale)
                py = int(cy + ry * spacing * scale * 0.85)

                sz = max(2, int(6 * scale))

                # Color logic
                dist_orig = math.sqrt(gx**2 + gy**2 + gz**2)
                if dist_orig < 1.2:
                    col = (255, 184, 0, int(220 * scale)) # amber
                elif phase > 0.65 and (gx > 1 or gy < -1):
                    col = (255, 0, 60, int(255 * scale))  # crimson spike
                elif dist_orig < 2.5:
                    col = (0, 240, 255, int(240 * scale)) # cyan
                else:
                    col = (30, 45, 70, int(150 * scale))  # muted dark

                draw.rectangle([(px - sz, py - sz), (px + sz, py + sz)], fill=col)

    # 3D Panel telemetry badges
    draw.rectangle([(512, HEIGHT - 90), (660, HEIGHT - 35)], fill=(12, 20, 36, 255), outline=(0, 240, 255, 80))
    draw.text((522, HEIGHT - 85), "ACTIVE PAGES", font=f_stat, fill=(0, 240, 255, 255))
    draw.text((522, HEIGHT - 62), f"{int(512 + phase * 256)} / 1024", font=f_stat_val, fill=(255, 255, 255, 255))

    draw.rectangle([(680, HEIGHT - 90), (WIDTH - 30, HEIGHT - 35)], fill=(12, 20, 36, 255), outline=(255, 0, 60, 120) if phase > 0.65 else (0, 255, 136, 80))
    alert_col = (255, 0, 60, 255) if phase > 0.65 else (0, 255, 136, 255)
    alert_txt = "FRAGMENTATION SPIKE!" if phase > 0.65 else "KV-CACHE HEALTHY"
    draw.text((690, HEIGHT - 85), "CACHE STATE", font=f_stat, fill=alert_col)
    draw.text((690, HEIGHT - 62), alert_txt, font=f_stat_val, fill=alert_col)

    images.append(im.convert("RGB"))

# Save animated GIF
gif_path = os.path.join(ASSETS_DIR, "vram_samurai_demo.gif")
images[0].save(gif_path, save_all=True, append_images=images[1:], optimize=False, duration=100, loop=0)
print(f"Created GIF: {gif_path} ({os.path.getsize(gif_path)} bytes)")

# Save poster PNG
png_path = os.path.join(ASSETS_DIR, "vram_samurai_preview.png")
images[12].save(png_path)
print(f"Created Preview: {png_path} ({os.path.getsize(png_path)} bytes)")
