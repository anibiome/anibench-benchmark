from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pypdf import PdfReader

pytest.importorskip("reportlab", reason="Install the paper extra to reproduce the PDF")
from scripts.build_manuscript import build


def test_paper_replays_numbers_builds_deterministically_and_preserves_outputs(tmp_path):
    first = tmp_path / "first" / "paper.pdf"
    second = tmp_path / "second" / "paper.pdf"
    one, two = build(first), build(second)
    assert one["pdf_sha256"] == two["pdf_sha256"]
    audit = json.loads(Path(one["replay"]).read_text())
    assert audit["geometry_values"]["intensive_rank"] == [2, 1]
    assert audit["geometry_values"]["median_span"] == [90, 360]
    assert audit["gaussian_model"]["information_bits"]["different_coordinates"][-1] == 8
    assert audit["gaussian_model"]["information_bits"]["copied_observation"] == [0.5] * 16
    assert audit["collection_profile"]["population"]["roster_participants"] == 3
    text = "\n".join(p.extract_text() for p in PdfReader(first).pages)
    for title in ("Abstract", "References", "Comparison and benchmark evolution", "Validation and limitations"):
        assert title in text
    for number in ("0.301030", "0.150515", "2.645141", "1.322571"):
        assert number in text
    assert "Figure 1." in text and "Figure 2." in text
    assert all(f"Figure {i}." in text for i in range(3, 9))
    assert "13,687" in text and "10,325" in text
    assert "synthetic" in text and "conditional witnesses" in text
    assert len(audit["publication_plates"]) == 6
    assert "web/source-architecture.json" in audit["publication_bindings"]
    original = hashlib.sha256(first.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="new paths"):
        build(first)
    assert hashlib.sha256(first.read_bytes()).hexdigest() == original
