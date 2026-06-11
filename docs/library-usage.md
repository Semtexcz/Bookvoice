# Library Usage

Bookvoice is still primarily a Python CLI for local users, but backend workers
and other Python applications can run the full audiobook pipeline directly
without invoking the CLI through a subprocess.

Use `bookvoice.api.build_audiobook` for full programmatic execution:

```python
from pathlib import Path

from bookvoice.api import build_audiobook
from bookvoice.config import BookvoiceConfig

config = BookvoiceConfig(
    input_pdf=Path("input.pdf"),
    output_dir=Path("out"),
    language="cs",
    rewrite_bypass=False,
    max_provider_workers=1,
)

manifest = build_audiobook(config)
print(manifest.run_id)
```

The public API also exposes the main non-interactive CLI workflows as library
functions:

```python
from pathlib import Path

from bookvoice.api import (
    list_chapters,
    list_chapters_from_artifact,
    resume_audiobook,
    run_chapters_only,
    run_translate_only,
    run_tts_only,
)

chapters, source, fallback_reason = list_chapters(config)
chapters_manifest = run_chapters_only(config)
translate_manifest = run_translate_only(config)
tts_manifest = run_tts_only(Path("out/run-id/run_manifest.json"))
resumed_manifest = resume_audiobook(Path("out/run-id/run_manifest.json"))
artifact_chapters, artifact_source, artifact_fallback = list_chapters_from_artifact(
    Path("out/run-id/text/chapters.json")
)
```

These functions delegate to the same pipeline implementation as the CLI while
leaving command parsing, credential prompts, and terminal rendering outside the
library API.

For new library integrations, `create_build_config` provides format-neutral
input naming while returning the same `BookvoiceConfig` used by the pipeline:

```python
from pathlib import Path

from bookvoice.api import build_audiobook, create_build_config

config = create_build_config(
    input_path=Path("input.epub"),
    output_dir=Path("out"),
    language="cs",
)

manifest = build_audiobook(config)
```

Backend workers should construct `BookvoiceConfig` non-interactively and provide
credentials through `BookvoiceConfig.api_key`, environment variables such as
`OPENAI_API_KEY`, or the existing runtime configuration mechanisms. The public
API does not prompt for terminal input and does not use Typer.

Progress reporting can be integrated with a job system by passing a callback:

```python
from bookvoice.api import build_audiobook


def record_progress(stage_name: str, stage_index: int, stage_total: int) -> None:
    update_job_progress(stage=stage_name, current=stage_index, total=stage_total)


manifest = build_audiobook(config, progress_callback=record_progress)
```

The same callback shape is accepted by `run_chapters_only`,
`run_translate_only`, `run_tts_only`, and `resume_audiobook`.

Web routing, authentication, payment, database persistence, and job
orchestration belong in the calling application. This repository remains the
reusable Bookvoice Python CLI/library engine.
