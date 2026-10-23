"""
VRAM-Samurai Terminal UI (TUI) Prototype / Mockup
Step 1: Side-by-Side Dual-Surface Layout Scaffold
"""

import sys
import time
import random
import os

# ANSI color sequences for zero-dependency terminal cyberpunk aesthetic
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[38;2;0;240;255m"
AMBER = "\033[38;2;255;184;0m"
CRIMSON = "\033[38;2;255;0;60m"
GREEN = "\033[38;2;0;255;136m"
GRAY = "\033[38;2;100;116;139m"
DARK_GRAY = "\033[38;2;40;50;70m"
BG_DARK = "\033[48;2;6;9;17m"

def draw_header():
    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║  {GREEN}●{CYAN} VRAM-SAMURAI // TERMINAL TELEMETRY HUD                 MODEL: QWEN-2.5-7B-INSTRUCT    ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════════════════════════════════╝{RESET}")

def render_kv_matrix(rows=6, cols=32):
    """Renders a 2D KV-cache page allocation block map."""
    print(f"\n{BOLD}{CYAN}┌─ [ KV-CACHE MEMORY PAGE MAP (PagedAttention Blocks) ] ───────────────────────────────┐{RESET}")
    chars = ["■", "▰", "▪", "·"]
    for r in range(rows):
        line = "│  "
        for c in range(cols):
            val = random.random()
            if val < 0.35:
                line += f"{AMBER}▰{RESET}"  # Cached prefix
            elif val < 0.70:
                line += f"{CYAN}■{RESET}"   # Active context
            elif val < 0.75:
                line += f"{CRIMSON}✖{RESET}" # Evicted / Fragmented
            else:
                line += f"{DARK_GRAY}·{RESET}" # Free headroom
        line += f"  │ (Page {r*cols:03d}-{(r+1)*cols-1:03d})"
        print(line)
    
    print(f"│                                                                                          │")
    print(f"│  {CYAN}■{RESET} Active ({CYAN}52.4%{RESET})   {AMBER}▰{RESET} Prefix Cache ({AMBER}28.1%{RESET})   {CRIMSON}✖{RESET} Fragmented ({CRIMSON}4.2%{RESET})   {DARK_GRAY}·{RESET} Free ({GRAY}15.3%{RESET})  │")
    print(f"{BOLD}{CYAN}└──────────────────────────────────────────────────────────────────────────────────────────┘{RESET}")

def render_gauges(ttft=41.2, itl=14.5, tps=68.9, vram_gb=10.8, vram_max=16.0):
    pct = int((vram_gb / vram_max) * 40)
    bar = f"{CYAN}{'█' * pct}{DARK_GRAY}{'░' * (40 - pct)}{RESET}"
    
    print(f"\n{BOLD}{CYAN}┌─ [ REAL-TIME TELEMETRY METRICS ] ────────────────────────────────────────────────────────┐{RESET}")
    print(f"│  TTFT: {GREEN}{ttft:5.1f} ms{RESET} (P95: 58.2ms)    ITL: {CYAN}{itl:4.1f} ms/tok{RESET} (P95: 18.0ms)    TPS: {BOLD}{CYAN}{tps:5.1f} tok/s{RESET}   │")
    print(f"│  VRAM: [{bar}] {AMBER}{vram_gb:.1f}/{vram_max:.1f} GB ({int(vram_gb/vram_max*100)}%){RESET} │")
    print(f"{BOLD}{CYAN}└──────────────────────────────────────────────────────────────────────────────────────────┘{RESET}")

def render_token_waterfall():
    print(f"\n{BOLD}{CYAN}┌─ [ LIVE TOKEN WATERFALL STREAM ] ────────────────────────────────────────────────────────┐{RESET}")
    stream_samples = [
        ("kv_cache_block_allocator()", "12.4ms", "ALLOC_PAGE"),
        ("prefill_duration_ms: 41.2", "41.2ms", "TTFT_REACHED"),
        ("decode_token('attention')", "14.1ms", "DECODE"),
        ("decode_token('head')", "13.9ms", "DECODE"),
        ("decode_token('projection')", "14.8ms", "DECODE"),
    ]
    for text, lat, stage in stream_samples:
        print(f"│  {GRAY}▶{RESET} {BOLD}{CYAN}{text:<40}{RESET} latency: {AMBER}{lat:>8}{RESET}  [{GREEN}{stage}{RESET}]           │")
    print(f"{BOLD}{CYAN}└──────────────────────────────────────────────────────────────────────────────────────────┘{RESET}\n")

def main():
    os.system("clear" if os.name != "nt" else "cls")
    draw_header()
    render_kv_matrix()
    render_gauges()
    render_token_waterfall()
    print(f"{GRAY}Dual-surface ready: Web 3D HUD at file://{os.path.abspath('../web/index.html')}{RESET}\n")

if __name__ == "__main__":
    main()
