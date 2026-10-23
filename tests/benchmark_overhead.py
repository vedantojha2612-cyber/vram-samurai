"""
Telemetry sampling overhead & jitter benchmark.
Measures the CPU overhead per token record call to verify <0.5ms SLA.
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sampler.metrics import InferenceMetrics
from sampler.vram import VRAMProbe


def benchmark_record_token_overhead(iterations: int = 50_000) -> float:
    metrics = InferenceMetrics(window_size=256)
    metrics.start_request()

    start_ns = time.perf_counter_ns()
    for i in range(iterations):
        metrics.record_token(f"t_{i}")
    total_ns = time.perf_counter_ns() - start_ns

    avg_ns = total_ns / iterations
    avg_us = avg_ns / 1_000.0
    avg_ms = avg_us / 1_000.0

    print("=" * 60)
    print("VRAM-SAMURAI TELEMETRY OVERHEAD BENCHMARK")
    print("=" * 60)
    print(f"Iterations:             {iterations:,}")
    print(f"Total CPU time:         {total_ns / 1_000_000.0:.2f} ms")
    print(f"Average cost per token: {avg_us:.3f} µs ({avg_ms:.6f} ms)")
    print(f"Target SLA:             < 500.0 µs (0.5 ms)")
    status = "PASSED (<0.5ms)" if avg_ms < 0.5 else "FAILED"
    print(f"Benchmark Status:       {status}")
    print("=" * 60)
    return avg_ms


def benchmark_vram_probe_overhead(iterations: int = 1_000) -> float:
    probe = VRAMProbe(total_kv_blocks=1024)

    start_ns = time.perf_counter_ns()
    for i in range(iterations):
        probe.sample(active_tokens=1024)
    total_ns = time.perf_counter_ns() - start_ns

    avg_us = (total_ns / iterations) / 1_000.0
    print(f"VRAM Probe poll cost:   {avg_us:.2f} µs per poll")
    print("=" * 60)
    return avg_us


def run_benchmark() -> None:
    benchmark_record_token_overhead()
    benchmark_vram_probe_overhead()


if __name__ == "__main__":
    run_benchmark()
