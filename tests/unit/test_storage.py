from pathlib import Path

from bookvoice.io.storage import ArtifactStore


def test_artifact_store_roundtrip_text_json_audio(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")

    text_path = store.save_text(Path("text/raw.txt"), "hello")
    json_path = store.save_json(Path("meta/run.json"), {"run_id": "run-1"})
    audio_path = store.save_audio(Path("audio/chunk.wav"), b"RIFFDATA")

    assert text_path.exists()
    assert json_path.exists()
    assert audio_path.exists()
    assert store.load_text(Path("text/raw.txt")) == "hello"
    assert store.exists(Path("meta/run.json"))
    assert not store.exists(Path("missing.txt"))
