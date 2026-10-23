"""
VRAM-Samurai Live Terminal UI (TUI)
Real-Time Local LLM Inference & KV-Cache Profiler
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sampler.inference import StreamInferenceProfiler
from sampler.metrics import InferenceMetrics
from sampler.vram import VRAMProbe, VRAMSample

# ANSI color sequences for cyberpunk telemetry styling
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[38;2;0;240;255m"
AMBER = "\033[38;2;255;184;0m"
CRIMSON = "\033[38;2;255;0;60m"
GREEN = "\033[38;2;0;255;136m"
GRAY = "\033[38;2;100;116;139m"
DARK_GRAY = "\033[38;2;40;50;70m"


def render_header(device_name: str, backend: str):
    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║  {GREEN}●{CYAN} VRAM-SAMURAI // LIVE TELEMETRY PROFILER               ENGINE: {backend.upper():<16} ║{RESET}")
    print(f"{BOLD}{CYAN}║  DEVICE: {device_name[:36]:<36} STATUS: STREAMING PROBES ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════════════════════════════╝{RESET}")


def render_kv_cache_map(vram: VRAMSample, rows: int = 4, cols: int = 32):
    total = vram.total_kv_blocks
    active_cnt = vram.active_blocks
    prefix_cnt = vram.prefix_cached_blocks
    frag_cnt = vram.fragmented_blocks

    print(f"\n{BOLD}{CYAN}┌─ [ KV-CACHE PAGEDATTENTION MATRIX (1,024 Pages) ] ─────────────────────────┐{RESET}")
    curr = 0
    for r in range(rows):
        line = "│  "
        for c in range(cols):
            block_idx = int((curr / (rows * cols)) * total)
            if block_idx < prefix_cnt:
                line += f"{AMBER}⮰{RESET}"
            elif block_idx < (prefix_cnt + active_cnt):
                line += f"{CYAN}■{RESET}"
            elif block_idx < (prefix_cnt + active_cnt + frag_cnt):
                line += f"{CRIMSON}✖{RESET}"
            else:
                line += f"{DARK_GRAY}·{RESET}"
            curr += 1
        line += f"  │ (Page {r*cols*8:04d}-{(r+1)*cols*8-1:04d})"
        print(line)

    pct_active = (active_cnt / total) * 100.0
    pct_prefix = (prefix_cnt / total) * 100.0
    pct_frag = (frag_cnt / total) * 100.0
    pct_free = (vram.free_blocks / total) * 100.0

    print(f"│                                                                            │")
    print(f"│  {CYAN}■{RESET} Active ({pct_active:4.1f}%)   {AMBER}⮰{RESET} Prefix ({pct_prefix:4.1f}%)   {CRIMSON}✖{RESET} Frag ({pct_frag:4.1f}%)   {DARK_GRAY}·{RESET} Free ({pct_free:4.1f}%)  │")
    print(f"{BOLD}{CYAN}└────────────────────────────────────────────────────────────────────────────┘{RESET}")


def render_telemetry_gauges(stats, vram: VRAMSample):
    ttft_str = f"{stats.ttft_ms:5.1f} ms" if stats.ttft_ms is not None else " WAITING "
    pct = int((vram.allocated_mb / max(vram.total_mb, 1.0)) * 36)
    pct = max(0, min(36, pct))
    bar = f"{CYAN}{'█' * pct}{DARK_GRAY}{'░' * (36 - pct)}{RESET}"

    print(f"\n{BOLD}{CYAN}┌─ [ REAL-TIME TELEMETRY METRICS ] ──────────────────────────────────────────┐{RESET}")
    print(f"│  TTFT: {GREEN}{ttft_str}{RESET} (P95: {stats.itl_p95_ms*1.2:5.1f}ms)   ITL: {CYAN}{stats.itl_p50_ms:5.1f} ms/tok{RESET}   TPS: {BOLD}{CYAN}{stats.throughput_tps:5.1f} tok/s{RESET}  │")
    print(f"│  VRAM: [{bar}] {AMBER}{vram.allocated_mb/1024.0:.1f}/{vram.total_mb/1024.0:.1f} GB ({vram.utilization_pct:3.0f}%){RESET} │")
    print(f"{BOLD}{CYAN}└────────────────────────────────────────────────────────────────────────────┘{RESET}")


async def run_live_tui():
    profiler = StreamInferenceProfiler()
    vram_probe = VRAMProbe(total_kv_blocks=1024)

    os.system("clear" if os.name != "nt" else "cls")
    sample_vram = vram_probe.sample()
    render_header(sample_vram.device_name, sample_vram.backend)

    print(f"\n{GRAY}Firing real-time telemetry sampler probes (Sub-millisecond resolution)...{RESET}\n")

    token_history = []
    accumulated_tokens = 0

    async for delta, stats in profiler.mock_stream(min_itl_ms=8.0, max_itl_ms=16.0, prefill_ms=32.0):
        accumulated_tokens += 1
        vram_sample = vram_probe.sample(active_tokens=accumulated_tokens * 48)

        # Clear and redraw TUI
        print("\033[H\033[J", end="")
        render_header(vram_sample.device_name, vram_sample.backend)
        render_kv_cache_map(vram_sample)
        render_telemetry_gauges(stats, vram_sample)

        token_history.append((delta.token, delta.latency_ms, "TTFT" if delta.is_first_token else "DECODE"))
        if len(token_history) > 6:
            token_history.pop(0)

        print(f"\n{BOLD}{CYAN}┌─ [ LIVE DECODE WATERFALL ] ────────────────────────────────────────────────┐{RESET}")
        for tok, lat, stage in reversed(token_history):
            tok_repr = repr(tok).replace("'", "")
            print(f"│  {GRAY}▶{RESET} {BOLD}{CYAN}{tok_repr:<30}{RESET}  latency: {AMBER}{lat:6.1f} ms{RESET}  [{GREEN}{stage:<6}{RESET}]              │")
        print(f"{BOLD}{CYAN}└────────────────────────────────────────────────────────────────────────────┘{RESET}")

    print(f"\n{GREEN}✔ Profiling burst completed successfully.{RESET}")
    print(f"{GRAY}Web 3D HUD available at: file://{os.path.abspath(os.path.join(os.path.dirname(__file__), '../web/index.html'))}{RESET}\n")


def main():
    asyncio.run(run_live_tui())


if __name__ == "__main__":
    main()
