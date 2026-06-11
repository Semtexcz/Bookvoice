"""Bounded ordered concurrency helpers for provider stages.

Responsibilities:
- Execute independent per-item work with a fixed worker limit.
- Preserve input ordering in returned results regardless of completion order.
- Wrap worker failures with stage and item context.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypeVar

from ..errors import PipelineStageError

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


def run_ordered_bounded(
    *,
    stage_name: str,
    items: Sequence[InputT],
    max_workers: int,
    worker: Callable[[int, InputT], OutputT],
) -> list[OutputT]:
    """Run per-item work with bounded concurrency and deterministic output order."""

    if max_workers <= 0:
        raise PipelineStageError(
            stage="config",
            detail="`max_provider_workers` must be a positive integer.",
            hint="Set `--max-provider-workers` or `BOOKVOICE_MAX_PROVIDER_WORKERS` to 1 or higher.",
        )

    if not items:
        return []

    if max_workers == 1 or len(items) == 1:
        return [worker(index, item) for index, item in enumerate(items)]

    results: list[OutputT | None] = [None] * len(items)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(worker, index, item): index
            for index, item in enumerate(items)
        }
        try:
            for future in as_completed(futures):
                index = futures[future]
                try:
                    results[index] = future.result()
                except PipelineStageError:
                    for pending in futures:
                        if pending is not future:
                            pending.cancel()
                    raise
                except Exception as exc:
                    for pending in futures:
                        if pending is not future:
                            pending.cancel()
                    raise PipelineStageError(
                        stage=stage_name,
                        detail=(
                            f"Provider item {index + 1}/{len(items)} failed during "
                            f"`{stage_name}`: {exc}"
                        ),
                        hint=(
                            "Reduce `max_provider_workers` if this is caused by provider "
                            "rate limits, then rerun or resume the build."
                        ),
                    ) from exc
        finally:
            for pending in futures:
                pending.cancel()

    return [item for item in results if item is not None]
