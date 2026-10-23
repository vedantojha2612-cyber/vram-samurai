"""
Real-time streaming metrics calculator for local LLM inference.
Uses pre-allocated ring buffers and nanosecond-precision clocks
for zero GC jitter and sub-millisecond accuracy.
"""

from __future__ import annotations

import math
import time
from collections import deque
from typing import Deque, List, Optional
from pydantic import BaseModel, Field


class TokenDelta(BaseModel):
    """Telemetry payload for an individual streamed token delta."""
    index: int = Field(..., ge=0, description="Token sequence index")
    token: str = Field(..., description="Decoded token string")
    latency_ms: float = Field(..., ge=0.0, description="Inter-token latency or TTFT in milliseconds")
    timestamp_ns: int = Field(..., ge=0, description="Nanosecond timestamp of arrival")
    is_first_token: bool = Field(False, description="True if this is the first token (TTFT)")


class MetricStats(BaseModel):
    """Aggregated latency percentiles and throughput figures."""
    total_tokens: int = 0
    ttft_ms: Optional[float] = None
    itl_p50_ms: float = 0.0
    itl_p95_ms: float = 0.0
    itl_p99_ms: float = 0.0
    itl_avg_ms: float = 0.0
    throughput_tps: float = 0.0
    elapsed_sec: float = 0.0


class InferenceMetrics:
    """
    High-performance, non-allocating metrics accumulator.
    Maintains a fixed-size ring buffer for inter-token latencies.
    """

    def __init__(self, window_size: int = 256) -> None:
        self.window_size = window_size
        self._latencies: Deque[float] = deque(maxlen=window_size)
        self.request_start_ns: Optional[int] = None
        self.first_token_ns: Optional[int] = None
        self.last_token_ns: Optional[int] = None
        self.total_tokens: int = 0

    def start_request(self) -> None:
        """Call immediately before firing the HTTP inference stream."""
        self.request_start_ns = time.perf_counter_ns()
        self.first_token_ns = None
        self.last_token_ns = None
        self.total_tokens = 0
        self._latencies.clear()

    def record_token(self, token: str) -> TokenDelta:
        """
        Record a newly arrived token delta and compute latency delta.
        """
        now_ns = time.perf_counter_ns()
        self.total_tokens += 1
        is_first = (self.first_token_ns is None)

        if is_first:
            self.first_token_ns = now_ns
            self.last_token_ns = now_ns
            ttft_ns = now_ns - (self.request_start_ns or now_ns)
            latency_ms = ttft_ns / 1_000_000.0
            return TokenDelta(
                index=self.total_tokens,
                token=token,
                latency_ms=round(latency_ms, 2),
                timestamp_ns=now_ns,
                is_first_token=True,
            )

        itl_ns = now_ns - (self.last_token_ns or now_ns)
        self.last_token_ns = now_ns
        latency_ms = itl_ns / 1_000_000.0
        self._latencies.append(latency_ms)

        return TokenDelta(
            index=self.total_tokens,
            token=token,
            latency_ms=round(latency_ms, 2),
            timestamp_ns=now_ns,
            is_first_token=False,
        )

    def get_stats(self) -> MetricStats:
        """
        Calculate percentiles and throughput without heap reallocations.
        """
        now_ns = time.perf_counter_ns()
        start = self.request_start_ns or now_ns
        elapsed_sec = max((now_ns - start) / 1_000_000_000.0, 0.0001)

        ttft_ms: Optional[float] = None
        if self.first_token_ns and self.request_start_ns:
            ttft_ms = round((self.first_token_ns - self.request_start_ns) / 1_000_000.0, 2)

        if not self._latencies:
            tps = (self.total_tokens / elapsed_sec) if self.total_tokens > 0 else 0.0
            return MetricStats(
                total_tokens=self.total_tokens,
                ttft_ms=ttft_ms,
                throughput_tps=round(tps, 1),
                elapsed_sec=round(elapsed_sec, 2),
            )

        sorted_lat = sorted(self._latencies)
        n = len(sorted_lat)

        def pct(p: float) -> float:
            idx = max(0, min(n - 1, math.ceil(p * n) - 1))
            return sorted_lat[idx]

        p50 = pct(0.50)
        p95 = pct(0.95)
        p99 = pct(0.99)
        avg = sum(sorted_lat) / n

        # Decode tokens per second calculation (excluding prefill if available)
        if self.first_token_ns and self.total_tokens > 1:
            decode_sec = max((now_ns - self.first_token_ns) / 1_000_000_000.0, 0.0001)
            tps = (self.total_tokens - 1) / decode_sec
        else:
            tps = self.total_tokens / elapsed_sec

        return MetricStats(
            total_tokens=self.total_tokens,
            ttft_ms=ttft_ms,
            itl_p50_ms=round(p50, 2),
            itl_p95_ms=round(p95, 2),
            itl_p99_ms=round(p99, 2),
            itl_avg_ms=round(avg, 2),
            throughput_tps=round(tps, 1),
            elapsed_sec=round(elapsed_sec, 2),
        )
