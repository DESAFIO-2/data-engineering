from pathlib import Path

from scripts.eval.package_delivery import safe_files


def test_delivery_includes_guide_but_excludes_paused_corpus_archive(tmp_path: Path) -> None:
    guide = tmp_path / "guia"
    guide.mkdir()
    (guide / "entrega.md").write_text("Guia de entrega", encoding="utf-8")
    active = tmp_path / "data/corpus/experimental"
    active.mkdir(parents=True)
    (active / "manifest.json").write_text("{}", encoding="utf-8")
    paused = tmp_path / "data/corpus/experimental-corrected-paused-2026-11-08"
    paused.mkdir(parents=True)
    (paused / "chunks.jsonl").write_text("{}\n", encoding="utf-8")

    included = {path.relative_to(tmp_path).as_posix() for path in safe_files(tmp_path)}

    assert "guia/entrega.md" in included
    assert "data/corpus/experimental/manifest.json" in included
    assert "data/corpus/experimental-corrected-paused-2026-11-08/chunks.jsonl" not in included
