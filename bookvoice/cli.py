"""Command-line interface for Bookvoice.

Responsibilities:
- Expose user-facing commands for pipeline operations.
- Convert CLI arguments into `BookvoiceConfig` and execute stubs.

Key public functions:
- `app`: Typer application instance.
- `main`: invoke the Typer application.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from .config import BookvoiceConfig, RuntimeConfigSources
from .credentials import create_credential_store
from .errors import PipelineStageError
from .models.datatypes import Chapter, RunManifest
from .pipeline import BookvoicePipeline

app = typer.Typer(
    name="bookvoice",
    no_args_is_help=True,
    help="Bookvoice CLI.",
)


def _normalize_optional_text(value: str | None) -> str | None:
    """Normalize user-provided optional text values to stripped non-empty strings."""

    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _set_runtime_cli_value(
    runtime_cli_values: dict[str, str], key: str, value: str | None
) -> None:
    """Set a normalized runtime CLI value when user input is present."""

    normalized = _normalize_optional_text(value)
    if normalized is not None:
        runtime_cli_values[key] = normalized


def _prompt_for_provider_runtime_values(
    runtime_cli_values: dict[str, str],
    prompt_api_key: bool,
) -> bool:
    """Prompt user for provider/model settings and optionally API key.

    Returns:
        `True` when an API key was entered via prompt in this run.
    """

    runtime_cli_values["provider_translator"] = typer.prompt(
        "Translator provider",
        default=runtime_cli_values.get("provider_translator", "openai"),
    ).strip()
    runtime_cli_values["provider_rewriter"] = typer.prompt(
        "Rewriter provider",
        default=runtime_cli_values.get("provider_rewriter", "openai"),
    ).strip()
    runtime_cli_values["provider_tts"] = typer.prompt(
        "TTS provider",
        default=runtime_cli_values.get("provider_tts", "openai"),
    ).strip()
    runtime_cli_values["model_translate"] = typer.prompt(
        "Translate model",
        default=runtime_cli_values.get("model_translate", "gpt-4.1-mini"),
    ).strip()
    runtime_cli_values["model_rewrite"] = typer.prompt(
        "Rewrite model",
        default=runtime_cli_values.get("model_rewrite", "gpt-4.1-mini"),
    ).strip()
    runtime_cli_values["model_tts"] = typer.prompt(
        "TTS model",
        default=runtime_cli_values.get("model_tts", "gpt-4o-mini-tts"),
    ).strip()
    runtime_cli_values["tts_voice"] = typer.prompt(
        "TTS voice",
        default=runtime_cli_values.get("tts_voice", "echo"),
    ).strip()
    if not prompt_api_key:
        return False
    prompted_api_key = _normalize_optional_text(
        typer.prompt(
            "OpenAI API key (hidden; leave blank to skip)",
            default="",
            hide_input=True,
            show_default=False,
        )
    )
    if prompted_api_key is None:
        return False
    runtime_cli_values["api_key"] = prompted_api_key
    return True


def _runtime_sources_for_provider_config(
    provider_translator: str | None,
    provider_rewriter: str | None,
    provider_tts: str | None,
    model_translate: str | None,
    model_rewrite: str | None,
    model_tts: str | None,
    tts_voice: str | None,
    api_key: str | None,
    interactive_provider_setup: bool,
    prompt_api_key: bool,
    store_api_key: bool,
) -> tuple[dict[str, str], dict[str, str]]:
    """Resolve CLI and secure runtime source mappings for provider configuration."""

    runtime_cli_values: dict[str, str] = {}
    _set_runtime_cli_value(runtime_cli_values, "provider_translator", provider_translator)
    _set_runtime_cli_value(runtime_cli_values, "provider_rewriter", provider_rewriter)
    _set_runtime_cli_value(runtime_cli_values, "provider_tts", provider_tts)
    _set_runtime_cli_value(runtime_cli_values, "model_translate", model_translate)
    _set_runtime_cli_value(runtime_cli_values, "model_rewrite", model_rewrite)
    _set_runtime_cli_value(runtime_cli_values, "model_tts", model_tts)
    _set_runtime_cli_value(runtime_cli_values, "tts_voice", tts_voice)
    _set_runtime_cli_value(runtime_cli_values, "api_key", api_key)

    api_key_entered_in_run = "api_key" in runtime_cli_values
    if interactive_provider_setup:
        prompted_key_entered = _prompt_for_provider_runtime_values(
            runtime_cli_values=runtime_cli_values,
            prompt_api_key=prompt_api_key or "api_key" not in runtime_cli_values,
        )
        api_key_entered_in_run = api_key_entered_in_run or prompted_key_entered
    elif prompt_api_key and "api_key" not in runtime_cli_values:
        prompted_api_key = _normalize_optional_text(
            typer.prompt(
                "OpenAI API key (hidden; leave blank to skip)",
                default="",
                hide_input=True,
                show_default=False,
            )
        )
        if prompted_api_key is not None:
            runtime_cli_values["api_key"] = prompted_api_key
            api_key_entered_in_run = True

    credential_store = create_credential_store()
    runtime_secure_values: dict[str, str] = {}
    stored_api_key = credential_store.get_api_key()
    if stored_api_key is not None:
        runtime_secure_values["api_key"] = stored_api_key

    if api_key_entered_in_run and "api_key" in runtime_cli_values and store_api_key:
        try:
            credential_store.set_api_key(runtime_cli_values["api_key"])
            typer.echo("Stored API key in secure credential storage.")
        except Exception as exc:
            raise PipelineStageError(
                stage="credentials",
                detail=f"Failed to store API key securely: {exc}",
                hint=(
                    "Install and configure a keyring backend, or rerun with "
                    "`--no-store-api-key` for one-off usage."
                ),
            ) from exc

    return runtime_cli_values, runtime_secure_values


def _exit_with_command_error(command_name: str, exc: Exception) -> NoReturn:
    """Print concise diagnostics for command failures and exit with code 1."""

    if isinstance(exc, PipelineStageError):
        typer.secho(
            f"{command_name} failed at stage `{exc.stage}`: {exc.detail}",
            fg=typer.colors.RED,
            err=True,
        )
        if exc.hint:
            typer.secho(f"Hint: {exc.hint}", fg=typer.colors.YELLOW, err=True)
    else:
        typer.secho(f"{command_name} failed: {exc}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc


def _echo_cost_summary(manifest: RunManifest) -> None:
    """Print run-level cost summary in USD."""

    typer.echo(f"Cost LLM (USD): {manifest.total_llm_cost_usd:.6f}")
    typer.echo(f"Cost TTS (USD): {manifest.total_tts_cost_usd:.6f}")
    typer.echo(f"Cost Total (USD): {manifest.total_cost_usd:.6f}")


def _echo_chapter_summary(manifest: RunManifest) -> None:
    """Print chapter extraction source and fallback reason when available."""

    source = manifest.extra.get("chapter_source", "unknown")
    fallback_reason = manifest.extra.get("chapter_fallback_reason", "")
    typer.echo(f"Chapter source: {source}")
    if fallback_reason:
        typer.echo(f"Chapter fallback reason: {fallback_reason}")
    selection_label = manifest.extra.get("chapter_scope_label", "all")
    selection_mode = manifest.extra.get("chapter_scope_mode", "all")
    typer.echo(f"Chapter scope: {selection_mode} ({selection_label})")


def _echo_chapter_list(chapters: list[Chapter]) -> None:
    """Print compact deterministic chapter index/title rows."""

    sorted_rows = sorted(
        ((chapter.index, chapter.title) for chapter in chapters),
        key=lambda item: item[0],
    )
    for index, title in sorted_rows:
        typer.echo(f"{index}. {title}")


@app.command("build")
def build_command(
    input_pdf: Annotated[Path, typer.Argument(help="Path to source PDF.")],
    out: Annotated[Path, typer.Option("--out", help="Output directory.")] = Path("out"),
    chapters: Annotated[
        str | None,
        typer.Option(
            "--chapters",
            help=(
                "1-based chapter selection: `5`, `1,3,7`, `2-4`, or mixed `1,3-5`."
            ),
        ),
    ] = None,
    provider_translator: Annotated[
        str | None, typer.Option("--provider-translator", help="Translator provider id.")
    ] = None,
    provider_rewriter: Annotated[
        str | None, typer.Option("--provider-rewriter", help="Rewriter provider id.")
    ] = None,
    provider_tts: Annotated[
        str | None, typer.Option("--provider-tts", help="TTS provider id.")
    ] = None,
    model_translate: Annotated[
        str | None,
        typer.Option("--model-translate", help="Translation model id override."),
    ] = None,
    model_rewrite: Annotated[
        str | None,
        typer.Option("--model-rewrite", help="Rewrite model id override."),
    ] = None,
    model_tts: Annotated[
        str | None,
        typer.Option("--model-tts", help="TTS model id override."),
    ] = None,
    tts_voice: Annotated[
        str | None,
        typer.Option("--tts-voice", help="TTS voice id override."),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key",
            help="Provider API key override. Prefer `--prompt-api-key` to avoid shell history.",
        ),
    ] = None,
    prompt_api_key: Annotated[
        bool,
        typer.Option(
            "--prompt-api-key",
            help="Prompt for API key with hidden input (never echoed).",
        ),
    ] = False,
    interactive_provider_setup: Annotated[
        bool,
        typer.Option(
            "--interactive-provider-setup",
            help="Prompt interactively for provider/model values and optional API key.",
        ),
    ] = False,
    store_api_key: Annotated[
        bool,
        typer.Option(
            "--store-api-key/--no-store-api-key",
            help="Persist CLI-entered API key to secure credential storage.",
        ),
    ] = True,
    rewrite_bypass: Annotated[
        bool,
        typer.Option(
            "--rewrite-bypass/--no-rewrite-bypass",
            help=(
                "Bypass rewrite provider call and keep translated text unchanged "
                "using deterministic pass-through mode."
            ),
        ),
    ] = False,
) -> None:
    """Run the full pipeline."""

    try:
        runtime_cli_values, runtime_secure_values = _runtime_sources_for_provider_config(
            provider_translator=provider_translator,
            provider_rewriter=provider_rewriter,
            provider_tts=provider_tts,
            model_translate=model_translate,
            model_rewrite=model_rewrite,
            model_tts=model_tts,
            tts_voice=tts_voice,
            api_key=api_key,
            interactive_provider_setup=interactive_provider_setup,
            prompt_api_key=prompt_api_key,
            store_api_key=store_api_key,
        )
        pipeline = BookvoicePipeline()
        config = BookvoiceConfig(
            input_pdf=input_pdf,
            output_dir=out,
            chapter_selection=chapters,
            rewrite_bypass=rewrite_bypass,
            runtime_sources=RuntimeConfigSources(
                cli=runtime_cli_values,
                secure=runtime_secure_values,
                env=os.environ,
            ),
        )
        manifest = pipeline.run(config)
    except Exception as exc:
        _exit_with_command_error("build", exc)

    typer.echo(f"Run id: {manifest.run_id}")
    typer.echo(f"Merged audio: {manifest.merged_audio_path}")
    typer.echo(f"Manifest: {manifest.extra.get('manifest_path', '(not written)')}")
    _echo_chapter_summary(manifest)
    _echo_cost_summary(manifest)


@app.command("chapters-only")
def chapters_only_command(
    input_pdf: Annotated[Path, typer.Argument(help="Path to source PDF.")],
    out: Annotated[Path, typer.Option("--out", help="Output directory.")] = Path("out"),
    chapters: Annotated[
        str | None,
        typer.Option(
            "--chapters",
            help=(
                "1-based chapter selection: `5`, `1,3,7`, `2-4`, or mixed `1,3-5`."
            ),
        ),
    ] = None,
) -> None:
    """Run only extract, clean, and chapter split stages."""

    try:
        pipeline = BookvoicePipeline()
        config = BookvoiceConfig(
            input_pdf=input_pdf,
            output_dir=out,
            chapter_selection=chapters,
        )
        manifest = pipeline.run_chapters_only(config)
    except Exception as exc:
        _exit_with_command_error("chapters-only", exc)

    typer.echo(f"Run id: {manifest.run_id}")
    typer.echo(f"Chapters artifact: {manifest.extra.get('chapters', '(not written)')}")
    typer.echo(f"Manifest: {manifest.extra.get('manifest_path', '(not written)')}")
    _echo_chapter_summary(manifest)


@app.command("list-chapters")
def list_chapters_command(
    input_pdf: Annotated[Path | None, typer.Argument(help="Path to source PDF.")] = None,
    chapters_artifact: Annotated[
        Path | None,
        typer.Option(
            "--chapters-artifact",
            help="Path to `text/chapters.json` chapter artifact.",
        ),
    ] = None,
    out: Annotated[
        Path,
        typer.Option("--out", help="Output directory used for extract/clean/split flow."),
    ] = Path("out"),
) -> None:
    """List extracted chapter indices and titles for a PDF or chapters artifact."""

    if (input_pdf is None and chapters_artifact is None) or (
        input_pdf is not None and chapters_artifact is not None
    ):
        _exit_with_command_error(
            "list-chapters",
            PipelineStageError(
                stage="list-chapters-input",
                detail=(
                    "Provide exactly one input source: `<input.pdf>` or "
                    "`--chapters-artifact <path>`."
                ),
                hint="Use `bookvoice list-chapters --help` for usage examples.",
            ),
        )
    try:
        pipeline = BookvoicePipeline()
        if chapters_artifact is not None:
            chapters, source, fallback_reason = pipeline.list_chapters_from_artifact(
                chapters_artifact
            )
        else:
            if input_pdf is None:
                raise PipelineStageError(
                    stage="list-chapters-input",
                    detail="Input PDF path is required when artifact path is not provided.",
                    hint="Provide `<input.pdf>` or use `--chapters-artifact <path>`.",
                )
            config = BookvoiceConfig(input_pdf=input_pdf, output_dir=out)
            chapters, source, fallback_reason = pipeline.list_chapters_from_pdf(config)
    except Exception as exc:
        _exit_with_command_error("list-chapters", exc)

    typer.echo(f"Chapter source: {source or 'unknown'}")
    if fallback_reason:
        typer.echo(f"Chapter fallback reason: {fallback_reason}")
    _echo_chapter_list(chapters)


@app.command("translate-only")
def translate_only_command(
    input_pdf: Annotated[Path, typer.Argument(help="Path to source PDF.")],
    out: Annotated[Path, typer.Option("--out", help="Output directory.")] = Path("out"),
) -> None:
    """Run translation stages only (stub currently runs full pipeline)."""

    try:
        pipeline = BookvoicePipeline()
        config = BookvoiceConfig(input_pdf=input_pdf, output_dir=out)
        manifest = pipeline.run(config)
    except Exception as exc:
        _exit_with_command_error("translate-only", exc)

    typer.echo(f"[translate-only] Would process: {config.input_pdf}")
    typer.echo(f"[translate-only] Output dir: {config.output_dir}")
    typer.echo(f"[translate-only] Stub run id: {manifest.run_id}")


@app.command("credentials")
def credentials_command(
    set_api_key: Annotated[
        bool,
        typer.Option(
            "--set-api-key",
            help="Prompt for API key with hidden input and store it securely.",
        ),
    ] = False,
    clear_api_key: Annotated[
        bool,
        typer.Option(
            "--clear-api-key",
            help="Clear stored API key from secure credential storage.",
        ),
    ] = False,
) -> None:
    """Manage securely stored CLI credentials."""

    if set_api_key and clear_api_key:
        _exit_with_command_error(
            "credentials",
            PipelineStageError(
                stage="credentials",
                detail="`--set-api-key` and `--clear-api-key` cannot be used together.",
                hint="Run one credentials action per command invocation.",
            ),
        )

    credential_store = create_credential_store()
    if set_api_key:
        prompted_api_key = _normalize_optional_text(
            typer.prompt(
                "OpenAI API key (hidden input)",
                default="",
                hide_input=True,
                show_default=False,
            )
        )
        if prompted_api_key is None:
            _exit_with_command_error(
                "credentials",
                PipelineStageError(
                    stage="credentials",
                    detail="No API key entered.",
                    hint="Provide a non-empty API key when using `--set-api-key`.",
                ),
            )
        try:
            credential_store.set_api_key(prompted_api_key)
        except Exception as exc:
            _exit_with_command_error(
                "credentials",
                PipelineStageError(
                    stage="credentials",
                    detail=f"Failed to store API key securely: {exc}",
                    hint="Install and configure a keyring backend and retry.",
                ),
            )
        typer.echo("API key stored in secure credential storage.")
        return

    if clear_api_key:
        removed = credential_store.clear_api_key()
        if removed:
            typer.echo("Stored API key cleared from secure credential storage.")
        else:
            typer.echo("No stored API key found in secure credential storage.")
        return

    availability = "available" if credential_store.is_available() else "unavailable"
    has_stored_key = credential_store.get_api_key() is not None
    status = "present" if has_stored_key else "not set"
    typer.echo(f"Secure credential storage: {availability}")
    typer.echo(f"Stored OpenAI API key: {status}")


@app.command("tts-only")
def tts_only_command(
    manifest: Annotated[Path, typer.Argument(help="Path to run manifest JSON.")],
) -> None:
    """Run TTS stage from prior artifacts."""
    typer.echo(f"[tts-only] Would synthesize audio from manifest: {manifest}")


@app.command("resume")
def resume_command(
    manifest: Annotated[Path, typer.Argument(help="Path to run manifest JSON.")],
) -> None:
    """Resume pipeline from an existing manifest."""

    try:
        pipeline = BookvoicePipeline()
        resumed_manifest = pipeline.resume(manifest)
    except Exception as exc:
        _exit_with_command_error("resume", exc)

    typer.echo(f"Run id: {resumed_manifest.run_id}")
    typer.echo(
        f"Resumed from stage: {resumed_manifest.extra.get('resume_next_stage', 'unknown')}"
    )
    typer.echo(f"Merged audio: {resumed_manifest.merged_audio_path}")
    typer.echo(f"Manifest: {resumed_manifest.extra.get('manifest_path', '(not written)')}")
    _echo_chapter_summary(resumed_manifest)
    _echo_cost_summary(resumed_manifest)


def main() -> None:
    """CLI entrypoint for console scripts."""
    app()


if __name__ == "__main__":
    main()
