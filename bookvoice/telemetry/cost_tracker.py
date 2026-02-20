"""Cost accounting scaffolds for LLM/TTS usage.

Responsibilities:
- Track provider usage costs per stage.
- Provide summary output for run manifests and reporting.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CostTracker:
    """Collect and summarize run-level cost counters."""

    llm_cost_usd: float = 0.0
    tts_cost_usd: float = 0.0

    def add_llm_usage(self, cost_usd: float) -> None:
        """Add LLM usage cost in USD."""

        self.llm_cost_usd += max(0.0, cost_usd)

    def add_tts_usage(self, cost_usd: float) -> None:
        """Add TTS usage cost in USD."""

        self.tts_cost_usd += max(0.0, cost_usd)

    def summary(self) -> dict[str, float]:
        """Return a summary dictionary for manifest/reporting."""

        return {
            "llm_cost_usd": self.llm_cost_usd,
            "tts_cost_usd": self.tts_cost_usd,
            "total_cost_usd": self.llm_cost_usd + self.tts_cost_usd,
        }
