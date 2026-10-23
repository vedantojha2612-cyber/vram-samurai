"""
Unit and benchmark tests for VRAM-Samurai telemetry sampler.
Audits zero-allocation bounds, TTFT/ITL math, and memory safety.
Compatible with standard library unittest and pytest.
"""

import asyncio
import os
import sys
import time
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sampler.metrics import InferenceMetrics, MetricStats, TokenDelta
from sampler.vram import VRAMProbe, VRAMSample
from sampler.inference import StreamInferenceProfiler


class TestSampler(unittest.TestCase):

    def test_metrics_ring_buffer_bounds(self):
        """Verify that ring buffer memory stays strictly bounded under heavy load."""
        metrics = InferenceMetrics(window_size=32)
        metrics.start_request()

        for i in range(500):
            metrics.record_token(f"tok_{i}")

        # Latencies deque must not exceed maxlen
        self.assertEqual(len(metrics._latencies), 32)
        self.assertEqual(metrics.total_tokens, 500)

        stats = metrics.get_stats()
        self.assertEqual(stats.total_tokens, 500)
        self.assertIsNotNone(stats.ttft_ms)
        self.assertGreaterEqual(stats.itl_p50_ms, 0.0)
        self.assertGreaterEqual(stats.itl_p95_ms, stats.itl_p50_ms)
        self.assertGreater(stats.throughput_tps, 0.0)

    def test_vram_probe_invariants(self):
        """Verify that VRAM probe metrics satisfy physical memory bounds."""
        probe = VRAMProbe(total_kv_blocks=1024)
        sample = probe.sample(active_tokens=2048)

        self.assertEqual(sample.total_kv_blocks, 1024)
        self.assertTrue(0.0 <= sample.utilization_pct <= 100.0)
        self.assertLessEqual(sample.allocated_mb, sample.total_mb)

        # Block partition invariant
        total_assigned = (
            sample.active_blocks
            + sample.prefix_cached_blocks
            + sample.fragmented_blocks
            + sample.free_blocks
        )
        self.assertEqual(total_assigned, sample.total_kv_blocks)

    def test_mock_inference_profiler_stream(self):
        """Verify mock streaming timing and token delivery."""
        async def _run():
            profiler = StreamInferenceProfiler()
            tokens = ["Hello", ",", " world", "!"]

            start = time.perf_counter()
            collected = []
            async for delta, stats in profiler.mock_stream(
                tokens=tokens, min_itl_ms=5.0, max_itl_ms=10.0, prefill_ms=15.0
            ):
                collected.append(delta.token)

            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self.assertEqual(collected, tokens)
            self.assertGreaterEqual(elapsed_ms, 25.0)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
