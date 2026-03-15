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
from typing import Annotated

import typer

from .cli_rendering import (
    echo_chapter_list,
    echo_chapter_source,
    echo_chapter_summary,
    echo_cost_summary,
    exit_with_command_error,
)
from .config import BookvoiceConfig, ConfigLoader, RuntimeConfigSources
from .credentials import create_credential_store
from .cli_runtime import resolve_provider_runtime_sources
from .errors import PipelineStageError
from .parsing import normalize_optional_string, parse_permissive_boolean
from .pipeline import BookvoicePipeline
from .pipeline.reader_exports import (
    reader_export_formats_csv,
    resolve_reader_export_formats,
)
from .telemetry.logger import RunLogger

app = typer.Typer(
    name="bookvoice",
    no_args_is_help=True,
    help="Bookvoice CLI.",
)


class BuildProgressIndicator:
    """Render deterministic per-stage progress lines for long-running commands."""

    _SPINNER_FRAMES = "|/-\\"

    def __init__(self, command_name: str) -> None:
        """Initialize progress indicator metadata for a command invocation."""

        self._command_name = command_name

    def on_stage_start(self, stage_name: str, stage_index: int, stage_total: int) -> None:
        """Print one progress line for a stage start transition."""

        spinner = self._SPINNER_FRAMES[(stage_index - 1) % len(self._SPINNER_FRAMES)]
        typer.echo(
            f"[progress] command={self._command_name} "
            f"{spinner} {stage_index}/{stage_total} stage={stage_name}"
        )


def _load_yaml_config(config_path: Path | None) -> BookvoiceConfig | None:
    """Load a YAML config file when requested and map failures to stage errors."""

    if config_path is None:
        return None

    try:
        return ConfigLoader.from_yaml(config_path)
    except FileNotFoundError as exc:
        raise PipelineStageError(
            stage="config",
            detail=f"Config file not found: `{config_path}`.",
            hint="Provide an existing path via `--config <path.yaml>`.",
        ) from exc
    except ValueError as exc:
        raise PipelineStageError(
            stage="config",
            detail=f"Invalid config file `{config_path}`: {exc}",
            hint="Fix config schema/values and rerun.",
        ) from exc
    except Exception as exc:
        raise PipelineStageError(
            stage="config",
            detail=f"Failed to load config file `{config_path}`: {exc}",
            hint="Verify YAML syntax and file permissions.",
        ) from exc


def _resolve_command_base_config(
    config_file: Path | None,
    input_path: Path | None,
    out: Path | None,
    chapters: str | None,
    language: str | None,
    rewrite_bypass: bool | None,
    output_format: str | None = None,
    package_mode: str | None = None,
    package_chapters: bool | None = None,
    package_chapter_numbering: str | None = None,
    package_naming: str | None = None,
    package_encoding_bitrate: str | None = None,
    package_encoding_profile: str | None = None,
    package_keep_merged: bool | None = None,
    reader_output_format: str | None = None,
) -> BookvoiceConfig:
    """Resolve effective command config from YAML defaults and explicit CLI overrides."""

    loaded_config = _load_yaml_config(config_file)
    env_values = os.environ

    def _resolve_value(cli_value: str | None, env_key: str, file_value: str | None) -> str | None:
        """Resolve optional string value with CLI > env > config-file precedence."""

        cli_normalized = normalize_optional_string(cli_value)
        if cli_normalized is not None:
            return cli_normalized
        env_normalized = normalize_optional_string(env_values.get(env_key))
        if env_normalized is not None:
            return env_normalized
        return normalize_optional_string(file_value)

    def _resolve_bool(
        cli_value: bool | None,
        env_key: str,
        file_value: bool | None,
        default: bool,
    ) -> bool:
        """Resolve bool value with CLI > env > config-file > default precedence."""

        if cli_value is not None:
            return cli_value
        env_raw = env_values.get(env_key)
        if env_raw is not None:
            env_parsed = parse_permissive_boolean(env_raw)
            if env_parsed is None:
                raise PipelineStageError(
                    stage="config",
                    detail=(
                        f"Environment variable `{env_key}` must be a boolean value "
                        "(`true`/`false`, `1`/`0`, `yes`/`no`)."
                    ),
                    hint=f"Set `{env_key}` to a valid boolean token and rerun.",
                )
            return env_parsed
        if file_value is not None:
            return file_value
        return default

    file_language = loaded_config.language if loaded_config is not None else None
    resolved_language = _resolve_value(language, "BOOKVOICE_LANGUAGE", file_language) or "cs"

    loaded_extra = dict(loaded_config.extra) if loaded_config is not None else {}
    resolved_extra = dict(loaded_extra)
    resolved_output_format = _resolve_value(
        output_format,
        "BOOKVOICE_OUTPUT_FORMAT",
        normalize_optional_string(loaded_extra.get("packaging_output_format")),
    )
    if resolved_output_format is None:
        resolved_output_format = _resolve_value(
            package_mode,
            "BOOKVOICE_PACKAGE_MODE",
            normalize_optional_string(loaded_extra.get("packaging_mode")),
        )
    if resolved_output_format is not None:
        resolved_extra["packaging_output_format"] = resolved_output_format
    if package_mode is not None:
        resolved_extra["packaging_mode"] = package_mode

    resolved_package_chapters = _resolve_bool(
        package_chapters,
        "BOOKVOICE_PACKAGE_CHAPTERS",
        parse_permissive_boolean(loaded_extra.get("packaging_chapter_outputs")),
        default=True,
    )
    resolved_extra["packaging_chapter_outputs"] = (
        "true" if resolved_package_chapters else "false"
    )

    resolved_chapter_numbering = _resolve_value(
        package_chapter_numbering,
        "BOOKVOICE_PACKAGE_CHAPTER_NUMBERING",
        normalize_optional_string(loaded_extra.get("packaging_chapter_numbering")),
    )
    if resolved_chapter_numbering is not None:
        resolved_extra["packaging_chapter_numbering"] = resolved_chapter_numbering

    resolved_naming_mode = _resolve_value(
        package_naming,
        "BOOKVOICE_PACKAGE_NAMING_MODE",
        normalize_optional_string(loaded_extra.get("packaging_naming_mode")),
    )
    if resolved_naming_mode is not None:
        resolved_extra["packaging_naming_mode"] = resolved_naming_mode

    resolved_encoding_bitrate = _resolve_value(
        package_encoding_bitrate,
        "BOOKVOICE_PACKAGE_ENCODING_BITRATE",
        normalize_optional_string(loaded_extra.get("packaging_encoding_bitrate")),
    )
    if resolved_encoding_bitrate is not None:
        resolved_extra["packaging_encoding_bitrate"] = resolved_encoding_bitrate

    resolved_encoding_profile = _resolve_value(
        package_encoding_profile,
        "BOOKVOICE_PACKAGE_ENCODING_PROFILE",
        normalize_optional_string(loaded_extra.get("packaging_encoding_profile")),
    )
    if resolved_encoding_profile is not None:
        resolved_extra["packaging_encoding_profile"] = resolved_encoding_profile

    resolved_keep_merged = _resolve_bool(
        package_keep_merged,
        "BOOKVOICE_PACKAGE_KEEP_MERGED",
        parse_permissive_boolean(loaded_extra.get("packaging_keep_merged")),
        default=True,
    )
    resolved_extra["packaging_keep_merged"] = "true" if resolved_keep_merged else "false"

    resolved_reader_output_format = _resolve_value(
        reader_output_format,
        "BOOKVOICE_READER_OUTPUT_FORMAT",
        normalize_optional_string(loaded_extra.get("reader_output_format")),
    )
    if resolved_reader_output_format is not None:
        try:
            formats = resolve_reader_export_formats(resolved_reader_output_format)
        except ValueError as exc:
            raise PipelineStageError(
                stage="config",
                detail=str(exc),
                hint="Use `--reader-output-format` with `epub`, `pdf`, or `epub,pdf`.",
            ) from exc
        resolved_extra["reader_output_format"] = reader_export_formats_csv(formats)

    if loaded_config is None:
        if input_path is None:
            raise PipelineStageError(
                stage="config",
                detail="Input source path is required when `--config` is not provided.",
                hint=(
                    "Pass `<source-document>` or use `--config <path.yaml>` with "
                    "`input_path` (or backward-compatible `input_pdf`)."
                ),
            )
        resolved_output_dir = out if out is not None else Path("out")
        resolved_rewrite_bypass = rewrite_bypass if rewrite_bypass is not None else False
        return BookvoiceConfig(
            input_pdf=input_path,
            output_dir=resolved_output_dir,
            language=resolved_language,
            chapter_selection=chapters,
            rewrite_bypass=resolved_rewrite_bypass,
            extra=resolved_extra,
        )

    resolved_input_path = input_path if input_path is not None else loaded_config.input_path
    resolved_output_dir = out if out is not None else loaded_config.output_dir
    resolved_chapters = chapters if chapters is not None else loaded_config.chapter_selection
    resolved_rewrite_bypass = (
        rewrite_bypass if rewrite_bypass is not None else loaded_config.rewrite_bypass
    )

    return BookvoiceConfig(
        input_pdf=resolved_input_path,
        output_dir=resolved_output_dir,
        language=resolved_language,
        provider_translator=loaded_config.provider_translator,
        provider_rewriter=loaded_config.provider_rewriter,
        provider_tts=loaded_config.provider_tts,
        model_translate=loaded_config.model_translate,
        model_rewrite=loaded_config.model_rewrite,
        model_tts=loaded_config.model_tts,
        tts_voice=loaded_config.tts_voice,
        rewrite_bypass=resolved_rewrite_bypass,
        api_key=loaded_config.api_key,
        chunk_size_chars=loaded_config.chunk_size_chars,
        chapter_selection=resolved_chapters,
        resume=loaded_config.resume,
        extra=resolved_extra,
    )


def _apply_runtime_sources(
    base_config: BookvoiceConfig,
    runtime_cli_values: dict[str, str],
    runtime_secure_values: dict[str, str],
) -> BookvoiceConfig:
    """Attach runtime source mappings while keeping base config defaults intact."""

    return BookvoiceConfig(
        input_pdf=base_config.input_path,
        output_dir=base_config.output_dir,
        language=base_config.language,
        provider_translator=base_config.provider_translator,
        provider_rewriter=base_config.provider_rewriter,
        provider_tts=base_config.provider_tts,
        model_translate=base_config.model_translate,
        model_rewrite=base_config.model_rewrite,
        model_tts=base_config.model_tts,
        tts_voice=base_config.tts_voice,
        rewrite_bypass=base_config.rewrite_bypass,
        api_key=base_config.api_key,
        chunk_size_chars=base_config.chunk_size_chars,
        chapter_selection=base_config.chapter_selection,
        resume=base_config.resume,
        runtime_sources=RuntimeConfigSources(
            cli=runtime_cli_values,
            secure=runtime_secure_values,
            env=os.environ,
        ),
        extra=dict(base_config.extra),
    )


@app.command("build")
def build_command(
    input_path: Annotated[
        Path | None,
        typer.Argument(
            help="Path to source document (`.pdf` or `.epub`). Required unless provided by `--config`.",
        ),
    ] = None,
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Output directory (overrides config file value)."),
    ] = None,
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Path to YAML config file with command defaults.",
        ),
    ] = None,
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
        bool | None,
        typer.Option(
            "--rewrite-bypass/--no-rewrite-bypass",
            help=(
                "Bypass rewrite provider call and keep translated text unchanged "
                "using deterministic pass-through mode."
            ),
        ),
    ] = None,
    language: Annotated[
        str | None,
        typer.Option("--language", help="Output language code override (for example `cs`)."),
    ] = None,
    output_format: Annotated[
        str | None,
        typer.Option(
            "--output-format",
            help="Output format intent: `wav`, `m4a`, `mp3`, or multi-target `m4a,mp3`.",
        ),
    ] = None,
    package_mode: Annotated[
        str | None,
        typer.Option(
            "--package-mode",
            help="Packaged output mode: `none`, `aac`, `mp3`, or `both`.",
        ),
    ] = None,
    package_chapters: Annotated[
        bool | None,
        typer.Option(
            "--package-chapters/--no-package-chapters",
            help="Enable or disable chapter-split packaged outputs.",
        ),
    ] = None,
    package_chapter_numbering: Annotated[
        str | None,
        typer.Option(
            "--package-chapter-numbering",
            help="Number packaged chapter files by source index or sequential order.",
        ),
    ] = None,
    package_naming: Annotated[
        str | None,
        typer.Option(
            "--package-naming",
            help="Packaged naming mode: `deterministic` or `reader_friendly`.",
        ),
    ] = None,
    package_encoding_bitrate: Annotated[
        str | None,
        typer.Option(
            "--package-encoding-bitrate",
            help="Packaged encoding bitrate (for example `128k`).",
        ),
    ] = None,
    package_encoding_profile: Annotated[
        str | None,
        typer.Option(
            "--package-encoding-profile",
            help="Packaged encoding profile (`balanced`, `voice`, or `music`).",
        ),
    ] = None,
    package_keep_merged: Annotated[
        bool | None,
        typer.Option(
            "--package-keep-merged/--no-package-keep-merged",
            help="Keep full merged WAV deliverable inside packaged output folder.",
        ),
    ] = None,
) -> None:
    """Run the full pipeline."""

    try:
        runtime_cli_values, runtime_secure_values = resolve_provider_runtime_sources(
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
            credential_store_factory=create_credential_store,
        )
        base_config = _resolve_command_base_config(
            config_file=config_file,
            input_path=input_path,
            out=out,
            chapters=chapters,
            language=language,
            rewrite_bypass=rewrite_bypass,
            output_format=output_format,
            package_mode=package_mode,
            package_chapters=package_chapters,
            package_chapter_numbering=package_chapter_numbering,
            package_naming=package_naming,
            package_encoding_bitrate=package_encoding_bitrate,
            package_encoding_profile=package_encoding_profile,
            package_keep_merged=package_keep_merged,
        )
        config = _apply_runtime_sources(
            base_config=base_config,
            runtime_cli_values=runtime_cli_values,
            runtime_secure_values=runtime_secure_values,
        )
        progress = BuildProgressIndicator(command_name="build")
        pipeline = BookvoicePipeline(
            run_logger=RunLogger(),
            stage_progress_callback=progress.on_stage_start,
        )
        manifest = pipeline.run(config)
    except Exception as exc:
        exit_with_command_error("build", exc)

    typer.echo(f"Run id: {manifest.run_id}")
    typer.echo(f"Merged audio: {manifest.merged_audio_path}")
    typer.echo(f"Packaged audio artifact: {manifest.extra.get('packaged_audio', '(not written)')}")
    typer.echo(f"Manifest: {manifest.extra.get('manifest_path', '(not written)')}")
    echo_chapter_summary(manifest)
    echo_cost_summary(manifest)


@app.command("chapters-only")
def chapters_only_command(
    input_path: Annotated[Path, typer.Argument(help="Path to source document (`.pdf` or `.epub`).")],
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
            input_pdf=input_path,
            output_dir=out,
            chapter_selection=chapters,
        )
        manifest = pipeline.run_chapters_only(config)
    except Exception as exc:
        exit_with_command_error("chapters-only", exc)

    typer.echo(f"Run id: {manifest.run_id}")
    typer.echo(f"Chapters artifact: {manifest.extra.get('chapters', '(not written)')}")
    typer.echo(f"Manifest: {manifest.extra.get('manifest_path', '(not written)')}")
    echo_chapter_summary(manifest)


@app.command("list-chapters")
def list_chapters_command(
    input_path: Annotated[
        Path | None,
        typer.Argument(help="Path to source document (`.pdf` or `.epub`)."),
    ] = None,
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

    if (input_path is None and chapters_artifact is None) or (
        input_path is not None and chapters_artifact is not None
    ):
        exit_with_command_error(
            "list-chapters",
            PipelineStageError(
                stage="list-chapters-input",
                detail=(
                    "Provide exactly one input source: `<source-document>` or "
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
            if input_path is None:
                raise PipelineStageError(
                    stage="list-chapters-input",
                    detail="Input source path is required when artifact path is not provided.",
                    hint="Provide `<source-document>` or use `--chapters-artifact <path>`.",
                )
            config = BookvoiceConfig(input_pdf=input_path, output_dir=out)
            chapters, source, fallback_reason = pipeline.list_chapters_from_source(config)
    except Exception as exc:
        exit_with_command_error("list-chapters", exc)

    echo_chapter_source(source, fallback_reason)
    echo_chapter_list(chapters)


@app.command("translate-only")
def translate_only_command(
    input_path: Annotated[
        Path | None,
        typer.Argument(
            help="Path to source document (`.pdf` or `.epub`). Required unless provided by `--config`.",
        ),
    ] = None,
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Output directory (overrides config file value)."),
    ] = None,
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Path to YAML config file with command defaults.",
        ),
    ] = None,
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
        bool | None,
        typer.Option(
            "--rewrite-bypass/--no-rewrite-bypass",
            help=(
                "Set rewrite bypass preference metadata using deterministic pass-through mode "
                "for downstream commands."
            ),
        ),
    ] = None,
    language: Annotated[
        str | None,
        typer.Option("--language", help="Output language code override (for example `cs`)."),
    ] = None,
    reader_output_format: Annotated[
        str | None,
        typer.Option(
            "--reader-output-format",
            help="Reader export request: `none`, `epub`, `pdf`, or `epub,pdf`.",
        ),
    ] = None,
) -> None:
    """Run pipeline stages through translation and persist text artifacts."""

    try:
        runtime_cli_values, runtime_secure_values = resolve_provider_runtime_sources(
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
            credential_store_factory=create_credential_store,
        )
        base_config = _resolve_command_base_config(
            config_file=config_file,
            input_path=input_path,
            out=out,
            chapters=chapters,
            language=language,
            rewrite_bypass=rewrite_bypass,
            reader_output_format=reader_output_format,
        )
        config = _apply_runtime_sources(
            base_config=base_config,
            runtime_cli_values=runtime_cli_values,
            runtime_secure_values=runtime_secure_values,
        )
        progress = BuildProgressIndicator(command_name="translate-only")
        pipeline = BookvoicePipeline(
            run_logger=RunLogger(),
            stage_progress_callback=progress.on_stage_start,
        )
        manifest = pipeline.run_translate_only(config)
    except Exception as exc:
        exit_with_command_error("translate-only", exc)

    typer.echo(f"Run id: {manifest.run_id}")
    typer.echo(f"Translations artifact: {manifest.extra.get('translations', '(not written)')}")
    typer.echo(
        "Reader export request: "
        f"{manifest.extra.get('reader_export_formats_csv', 'none')} "
        f"[{manifest.extra.get('reader_export_status', 'not_requested')}]"
    )
    typer.echo(f"Manifest: {manifest.extra.get('manifest_path', '(not written)')}")
    echo_chapter_summary(manifest)
    echo_cost_summary(manifest)


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
        exit_with_command_error(
            "credentials",
            PipelineStageError(
                stage="credentials",
                detail="`--set-api-key` and `--clear-api-key` cannot be used together.",
                hint="Run one credentials action per command invocation.",
            ),
        )

    credential_store = create_credential_store()
    if set_api_key:
        prompted_api_key = normalize_optional_string(
            typer.prompt(
                "OpenAI API key (hidden input)",
                default="",
                hide_input=True,
                show_default=False,
            )
        )
        if prompted_api_key is None:
            exit_with_command_error(
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
            exit_with_command_error(
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
    """Run only TTS/merge stages from an existing manifest and text artifacts."""

    try:
        progress = BuildProgressIndicator(command_name="tts-only")
        pipeline = BookvoicePipeline(
            run_logger=RunLogger(),
            stage_progress_callback=progress.on_stage_start,
        )
        replayed_manifest = pipeline.run_tts_only_from_manifest(manifest)
    except Exception as exc:
        exit_with_command_error("tts-only", exc)

    typer.echo(f"Run id: {replayed_manifest.run_id}")
    typer.echo(f"Merged audio: {replayed_manifest.merged_audio_path}")
    typer.echo(f"Audio parts artifact: {replayed_manifest.extra.get('audio_parts', '(not written)')}")
    typer.echo(
        f"Packaged audio artifact: {replayed_manifest.extra.get('packaged_audio', '(not written)')}"
    )
    typer.echo(f"Manifest: {replayed_manifest.extra.get('manifest_path', '(not written)')}")
    echo_chapter_summary(replayed_manifest)
    echo_cost_summary(replayed_manifest)


@app.command("resume")
def resume_command(
    manifest: Annotated[Path, typer.Argument(help="Path to run manifest JSON.")],
) -> None:
    """Resume pipeline from an existing manifest."""

    try:
        progress = BuildProgressIndicator(command_name="resume")
        pipeline = BookvoicePipeline(
            run_logger=RunLogger(),
            stage_progress_callback=progress.on_stage_start,
        )
        resumed_manifest = pipeline.resume(manifest)
    except Exception as exc:
        exit_with_command_error("resume", exc)

    typer.echo(f"Run id: {resumed_manifest.run_id}")
    typer.echo(
        f"Resumed from stage: {resumed_manifest.extra.get('resume_next_stage', 'unknown')}"
    )
    typer.echo(f"Merged audio: {resumed_manifest.merged_audio_path}")
    typer.echo(
        f"Packaged audio artifact: {resumed_manifest.extra.get('packaged_audio', '(not written)')}"
    )
    typer.echo(f"Manifest: {resumed_manifest.extra.get('manifest_path', '(not written)')}")
    echo_chapter_summary(resumed_manifest)
    echo_cost_summary(resumed_manifest)


def main() -> None:
    """CLI entrypoint for console scripts."""
    app()


if __name__ == "__main__":
    main()
