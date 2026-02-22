"""Deterministic audio postprocessing for merged WAV outputs.

Responsibilities:
- Define explicit silence trimming and peak normalization defaults.
- Apply in-place, idempotent WAV transformations without transcoding.
"""

from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path
import wave


@dataclass(frozen=True, slots=True)
class PostprocessPolicy:
    """Deterministic WAV postprocessing policy.

    Attributes:
        target_peak_ratio: Desired absolute peak ratio in the normalized output.
        silence_threshold_ratio: Absolute per-frame threshold ratio used by trim policy.
    """

    target_peak_ratio: float = 0.95
    silence_threshold_ratio: float = 0.01


class AudioPostProcessor:
    """Deterministic WAV postprocessing service."""

    def __init__(self, policy: PostprocessPolicy | None = None) -> None:
        """Initialize postprocessor with explicit deterministic defaults."""

        self._policy = policy if policy is not None else PostprocessPolicy()

    def process_merged(self, audio_path: Path) -> Path:
        """Apply trim+normalize policy in deterministic order to a merged file."""

        trimmed = self.trim_silence(audio_path)
        return self.normalize(trimmed)

    def normalize(self, audio_path: Path) -> Path:
        """Normalize WAV peak amplitude to policy target and return output path."""

        if audio_path.suffix.lower() != ".wav":
            return audio_path

        params, frames = self._read_wav_frames(audio_path)
        if params.nframes == 0:
            return audio_path

        peak = self._peak_abs(frames, params.sampwidth)
        if peak <= 0:
            return audio_path

        max_amplitude = (1 << (params.sampwidth * 8 - 1)) - 1
        target_peak = int(round(max_amplitude * self._policy.target_peak_ratio))
        if abs(peak - target_peak) <= 1:
            return audio_path

        gain = target_peak / float(peak)
        normalized = self._scale_pcm(frames, params.sampwidth, gain)
        if normalized == frames:
            return audio_path
        self._write_wav_frames(audio_path, params, normalized)
        return audio_path

    def trim_silence(self, audio_path: Path) -> Path:
        """Trim deterministic leading/trailing silence and return output path."""

        if audio_path.suffix.lower() != ".wav":
            return audio_path

        params, frames = self._read_wav_frames(audio_path)
        if params.nframes == 0:
            return audio_path

        frame_width = params.nchannels * params.sampwidth
        max_amplitude = (1 << (params.sampwidth * 8 - 1)) - 1
        threshold = max(
            1,
            int(round(max_amplitude * self._policy.silence_threshold_ratio)),
        )

        start_index = 0
        end_index = params.nframes

        for index in range(params.nframes):
            frame = frames[index * frame_width : (index + 1) * frame_width]
            if self._peak_abs(frame, params.sampwidth) > threshold:
                start_index = index
                break
        else:
            if frames != b"":
                self._write_wav_frames(audio_path, params, b"")
            return audio_path

        for index in range(params.nframes - 1, -1, -1):
            frame = frames[index * frame_width : (index + 1) * frame_width]
            if self._peak_abs(frame, params.sampwidth) > threshold:
                end_index = index + 1
                break

        trimmed = frames[start_index * frame_width : end_index * frame_width]
        if trimmed == frames:
            return audio_path
        self._write_wav_frames(audio_path, params, trimmed)
        return audio_path

    def _read_wav_frames(self, audio_path: Path) -> tuple[wave._wave_params, bytes]:
        """Read WAV headers and PCM frame bytes from disk."""

        with wave.open(str(audio_path), "rb") as wav_file:
            params = wav_file.getparams()
            frames = wav_file.readframes(params.nframes)
        return params, frames

    def _write_wav_frames(
        self,
        audio_path: Path,
        params: wave._wave_params,
        frames: bytes,
    ) -> None:
        """Write WAV headers and PCM frame bytes atomically to disk."""

        with io.BytesIO() as buffer:
            with wave.open(buffer, "wb") as wav_file:
                wav_file.setnchannels(params.nchannels)
                wav_file.setsampwidth(params.sampwidth)
                wav_file.setframerate(params.framerate)
                wav_file.writeframes(frames)
            audio_path.write_bytes(buffer.getvalue())

    def _peak_abs(self, frames: bytes, sample_width: int) -> int:
        """Return absolute peak sample amplitude for PCM payload."""

        if sample_width not in (1, 2, 3, 4) or not frames:
            return 0
        peak = 0
        for sample in self._iter_samples(frames, sample_width):
            absolute = abs(sample)
            if absolute > peak:
                peak = absolute
        return peak

    def _scale_pcm(self, frames: bytes, sample_width: int, gain: float) -> bytes:
        """Scale PCM payload with clamping and return scaled bytes."""

        if sample_width not in (1, 2, 3, 4) or not frames:
            return frames

        if sample_width == 1:
            min_value = -128
            max_value = 127
        else:
            min_value = -(1 << (sample_width * 8 - 1))
            max_value = (1 << (sample_width * 8 - 1)) - 1

        scaled_chunks: list[bytes] = []
        for sample in self._iter_samples(frames, sample_width):
            scaled = int(round(sample * gain))
            clamped = min(max_value, max(min_value, scaled))
            scaled_chunks.append(self._sample_to_bytes(clamped, sample_width))
        return b"".join(scaled_chunks)

    def _iter_samples(self, frames: bytes, sample_width: int) -> list[int]:
        """Decode PCM frame bytes into signed integer samples."""

        if sample_width not in (1, 2, 3, 4):
            return []

        samples: list[int] = []
        for offset in range(0, len(frames), sample_width):
            chunk = frames[offset : offset + sample_width]
            if len(chunk) != sample_width:
                continue
            if sample_width == 1:
                samples.append(chunk[0] - 128)
            else:
                samples.append(int.from_bytes(chunk, "little", signed=True))
        return samples

    def _sample_to_bytes(self, sample: int, sample_width: int) -> bytes:
        """Encode signed integer sample to PCM bytes."""

        if sample_width == 1:
            return bytes([sample + 128])
        return int(sample).to_bytes(sample_width, "little", signed=True)
