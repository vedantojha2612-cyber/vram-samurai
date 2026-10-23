"""
Asynchronous streaming inference client & latency profiler.
Connects to local endpoints (Ollama, vLLM, llama.cpp) via OpenAI SSE format,
capturing prefill TTFT and decode ITL down to the nanosecond.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncGenerator, Callable, Dict, List, Optional, Tuple
import httpx

from .metrics import InferenceMetrics, MetricStats, TokenDelta


class StreamInferenceProfiler:
    """
    Hooks into local inference streaming endpoints to capture real-time
    token deltas, TTFT, and ITL metrics.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        timeout_sec: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.metrics = InferenceMetrics(window_size=512)

    async def profile_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
        on_token: Optional[Callable[[TokenDelta, MetricStats], None]] = None,
    ) -> AsyncGenerator[Tuple[TokenDelta, MetricStats], None]:
        """
        Stream completions from a live OpenAI-compatible endpoint.
        Yields (TokenDelta, MetricStats) for every received chunk.
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        self.metrics.start_request()

        timeout = httpx.Timeout(self.timeout_sec, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if not content:
                                continue

                            token_delta = self.metrics.record_token(content)
                            current_stats = self.metrics.get_stats()

                            if on_token:
                                on_token(token_delta, current_stats)

                            yield token_delta, current_stats

                        except json.JSONDecodeError:
                            continue

    async def mock_stream(
        self,
        tokens: Optional[List[str]] = None,
        min_itl_ms: float = 12.0,
        max_itl_ms: float = 18.0,
        prefill_ms: float = 38.0,
    ) -> AsyncGenerator[Tuple[TokenDelta, MetricStats], None]:
        """
        Deterministic mock streaming generator for CI tests, benchmark audits,
        and offline GUI/TUI preview.
        """
        if tokens is None:
            tokens = [
                "VRAM", "-Samurai", " detects", " KV", "-cache", " paging",
                " fragmentation", " in", " real", "-time", " using", " high",
                "-frequency", " nanosecond", " timestamps", " across", " local",
                " inference", " runs", "."
            ]

        self.metrics.start_request()
        # Emulate prompt prefill phase
        await asyncio.sleep(prefill_ms / 1000.0)

        for tok in tokens:
            token_delta = self.metrics.record_token(tok)
            stats = self.metrics.get_stats()
            yield token_delta, stats

            # Emulate inter-token decode latency
            itl = min_itl_ms + (max_itl_ms - min_itl_ms) * 0.5
            await asyncio.sleep(itl / 1000.0)
