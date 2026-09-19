# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Exercise registry trust and input preservation at the executable boundary."""

import json

from test_finite_suites_v1 import profile, request, task

from anibench.cli import main
from anibench.finite_suites_v1 import suite_sha256


def inputs(tmp_path):
    p = profile(task(prior=100))
    r = request(p, {("a", "neural"): 0})
    source, registry = tmp_path / "request.json", tmp_path / "registry.json"
    source.write_text(json.dumps(r))
    registry.write_text(json.dumps({suite_sha256(p): p}))
    return source, registry


def test_cli_prior_only_is_not_acquired_precision(tmp_path, capsys):
    source, registry = inputs(tmp_path)
    output = tmp_path / "private-design-label.json"
    assert (
        main(["finite-suite", str(source), "--registry", str(registry), "--out", str(output)]) == 0
    )
    receipt = json.loads(output.read_text())
    assert receipt["attainment"] == "not_attained"
    assert receipt["scenarios"][0]["targets"][0]["task_receipt"]["attainment"] == "attained"
    summary = capsys.readouterr().out
    assert str(tmp_path) not in summary and "private-design-label" not in summary
    assert json.loads(summary)["request_sha256"] == receipt["request_sha256"]


def test_cli_cannot_overwrite_input_registry_or_their_hardlinks(tmp_path):
    source, registry = inputs(tmp_path)
    before = {p: p.read_bytes() for p in (source, registry)}
    alias = tmp_path / "alias.json"
    alias.hardlink_to(registry)
    for output in (source, registry, alias):
        assert (
            main(["finite-suite", str(source), "--registry", str(registry), "--out", str(output)])
            == 2
        )
    assert all(p.read_bytes() == raw for p, raw in before.items())


def test_cli_untrusted_profile_never_writes_output(tmp_path):
    source, registry = inputs(tmp_path)
    registry.write_text("{}")
    output = tmp_path / "result.json"
    assert (
        main(["finite-suite", str(source), "--registry", str(registry), "--out", str(output)]) == 2
    )
    assert not output.exists()
