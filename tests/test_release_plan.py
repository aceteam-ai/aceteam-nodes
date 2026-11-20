"""Offline checks for the CI release planner and version-bump command."""

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "release_plan.py"
SPEC = importlib.util.spec_from_file_location("release_plan", SCRIPT)
assert SPEC and SPEC.loader
release_plan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_plan)


@pytest.fixture
def release_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "aceteam-nodes"\nversion = "0.8.0"\n'
    )
    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname = "aceteam-nodes"\nversion = "0.8.0"\n'
    )
    init = tmp_path / "src" / "aceteam_nodes" / "__init__.py"
    init.parent.mkdir(parents=True)
    init.write_text('__version__ = "0.8.0"\n')
    (tmp_path / "CHANGELOG.md").write_text(
        "## [Unreleased]\n\n## [0.8.1rc1] - 2026-11-19\n\nRelease note.\n"
        "\n## [0.8.0] - 2026-10-26\n\nPrevious release.\n"
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_sites_and_changelog_fail_closed(release_tree: Path) -> None:
    assert release_plan.version_sites() == "0.8.0"
    init = release_tree / "src" / "aceteam_nodes" / "__init__.py"
    init.write_text('__version__ = "0.7.9"\n')
    with pytest.raises(SystemExit, match="Version sites disagree"):
        release_plan.version_sites()
    init.write_text('__version__ = "0.8.0"\n')
    (release_tree / "uv.lock").write_text(
        '[[package]]\nname = "aceteam-nodes"\nversion = "0.7.9"\n'
    )
    with pytest.raises(SystemExit, match="Version sites disagree"):
        release_plan.version_sites()
    with pytest.raises(SystemExit, match="lacks"):
        release_plan.changelog_section("0.8.1rc2")


def test_main_push_without_version_bump_is_noop(
    release_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        release_plan.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, (release_tree / "pyproject.toml").read_text(), ""
        ),
    )
    assert release_plan.plan(
        "push", "a" * 40, "b" * 40, "aceteam-ai/aceteam-nodes", "test"
    ) == {
        "run": "false",
        "published": "false",
        "version": "",
    }


def test_main_push_with_older_version_fails_closed(
    release_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        release_plan.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, '[project]\nname = "aceteam-nodes"\nversion = "0.8.1"\n', ""
        ),
    )
    with pytest.raises(SystemExit, match="greater than"):
        release_plan.plan(
            "push", "a" * 40, "b" * 40, "aceteam-ai/aceteam-nodes", "test"
        )


def test_complete_release_is_noop(
    release_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(release_plan, "checked_tag", lambda version, sha: True)
    monkeypatch.setattr(release_plan, "pypi_metadata", lambda version: {"urls": []})
    monkeypatch.setattr(release_plan, "request_json", lambda url, token: {"id": 1})
    assert release_plan.plan(
        "workflow_dispatch", "", "b" * 40, "aceteam-ai/aceteam-nodes", "test"
    ) == {"run": "false", "published": "true", "version": "0.8.0"}


def test_published_version_recovers_metadata_without_republishing(
    release_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(release_plan, "checked_tag", lambda version, sha: False)
    monkeypatch.setattr(release_plan, "pypi_metadata", lambda version: {"urls": []})
    monkeypatch.setattr(release_plan, "request_json", lambda url, token: None)
    assert release_plan.plan(
        "workflow_dispatch", "", "b" * 40, "aceteam-ai/aceteam-nodes", "test"
    ) == {"run": "true", "published": "true", "version": "0.8.0"}


def test_conflicting_tag_fails_closed(
    release_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def conflicting_tag(version: str, sha: str) -> bool:
        raise SystemExit("Existing tag points to another commit")

    monkeypatch.setattr(release_plan, "checked_tag", conflicting_tag)
    with pytest.raises(SystemExit, match="another commit"):
        release_plan.plan(
            "workflow_dispatch", "", "b" * 40, "aceteam-ai/aceteam-nodes", "test"
        )


def test_bump_requires_changelog_and_changes_version_sites(release_tree: Path) -> None:
    with pytest.raises(SystemExit, match="lacks"):
        release_plan.bump("0.8.1rc2")
    assert release_plan.bump("--rc") == "0.8.1rc1"
    assert 'version = "0.8.1rc1"' in (release_tree / "pyproject.toml").read_text()
    assert (
        '__version__ = "0.8.1rc1"'
        in (release_tree / "src/aceteam_nodes/__init__.py").read_text()
    )
    assert 'version = "0.8.0"' in (release_tree / "uv.lock").read_text()
    assert release_plan.version_order("0.8.1") > release_plan.version_order("0.8.1rc1")


def test_bump_script_cli_accepts_rc_flag(
    release_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    scripts = release_tree / "scripts"
    scripts.mkdir()
    shutil.copy2(SCRIPT, scripts / SCRIPT.name)
    shutil.copy2(SCRIPT.parent / "bump-version.sh", scripts / "bump-version.sh")
    bin_dir = release_tree / "bin"
    bin_dir.mkdir()
    uv = bin_dir / "uv"
    uv.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "p=Path('uv.lock')\n"
        "p.write_text(p.read_text().replace('0.8.0', '0.8.1rc1'))\n"
    )
    uv.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    result = subprocess.run(
        ["bash", str(scripts / "bump-version.sh"), "--rc"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert release_plan.version_sites() == "0.8.1rc1"
