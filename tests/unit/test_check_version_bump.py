"""
Unit tests for .github/scripts/check_version_bump.py — the CI gate that
fails a PR when a plugin's files changed but its plugin.json "version"
field wasn't bumped (or was lowered).

These build real, throwaway git repositories under a tempdir and run real
`git` commands against them (no mocking of subprocess or the filesystem) —
matching this repo's stated preference for exercising real behavior over
mocks (see tests/integration/test_mcp_server.py). Everything here is local:
no network access needed.

Run with:

    python3 -m unittest discover -s tests/unit -v
"""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "check_version_bump.py"


def _load_module():
    """.github/scripts isn't an importable package (dotted dir name), so
    load the script directly from its file path."""
    spec = importlib.util.spec_from_file_location("check_version_bump", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cvb = _load_module()


def _git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout


def _init_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    return path


def _commit(path, message="commit"):
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", message)
    return _git(path, "rev-parse", "HEAD").strip()


def _write_plugin(repo, name, version):
    plugin_dir = repo / "plugins" / name
    (plugin_dir / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": name, "version": version}), encoding="utf-8"
    )


def _touch_plugin_file(repo, name, rel="commands/foo.md", content="x"):
    path = repo / "plugins" / name / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_marketplace(repo, entries):
    """entries: list of (plugin_name, source) pairs; source can be a
    "./plugins/<name>" string or a non-local dict (git/npm source shape)."""
    (repo / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    marketplace = {
        "name": "test-marketplace",
        "owner": {"name": "Test"},
        "plugins": [{"name": n, "source": s} for n, s in entries],
    }
    (repo / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps(marketplace), encoding="utf-8"
    )


class GitHelperFunctionTests(unittest.TestCase):
    """Direct tests of the module's small git-wrapping helpers, exercised
    against a real local repo rather than main()'s end-to-end flow — some
    branches (like an unresolvable ref) never happen inside main() because
    `git diff` itself already fails first on a bad ref."""

    def setUp(self):
        self._orig_cwd = os.getcwd()
        self.addCleanup(lambda: os.chdir(self._orig_cwd))
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.repo = Path(self.tmpdir.name)
        _init_repo(self.repo)
        _write_marketplace(self.repo, [("acme", "./plugins/acme")])
        _write_plugin(self.repo, "acme", "1.0.0")
        self.base_sha = _commit(self.repo, "initial")
        _write_plugin(self.repo, "acme", "1.1.0")
        _touch_plugin_file(self.repo, "acme")
        self.head_sha = _commit(self.repo, "bump")
        os.chdir(self.repo)

    def test_git_runs_and_returns_stdout(self):
        out = cvb.git("rev-parse", "HEAD")
        self.assertEqual(out.strip(), self.head_sha)

    def test_changed_files_lists_diff_between_refs(self):
        changed = cvb.changed_files(self.base_sha, self.head_sha)
        self.assertIn("plugins/acme/.claude-plugin/plugin.json", changed)
        self.assertIn("plugins/acme/commands/foo.md", changed)

    def test_ref_exists_true_for_real_ref(self):
        self.assertTrue(cvb._ref_exists(self.head_sha))
        self.assertTrue(cvb._ref_exists("HEAD"))

    def test_ref_exists_false_for_bogus_ref(self):
        self.assertFalse(cvb._ref_exists("not-a-real-ref-xyz"))

    def test_path_exists_at_true_and_false(self):
        self.assertTrue(
            cvb._path_exists_at(self.head_sha, "plugins/acme/.claude-plugin/plugin.json")
        )
        self.assertFalse(cvb._path_exists_at(self.head_sha, "does/not/exist.json"))

    def test_read_json_at_returns_parsed_json(self):
        data = cvb.read_json_at(self.head_sha, "plugins/acme/.claude-plugin/plugin.json")
        self.assertEqual(data, {"name": "acme", "version": "1.1.0"})

    def test_read_json_at_returns_none_when_path_missing(self):
        self.assertIsNone(cvb.read_json_at(self.head_sha, "plugins/acme/nope.json"))

    def test_read_json_at_raises_on_bad_ref(self):
        with self.assertRaises(RuntimeError):
            cvb.read_json_at("not-a-real-ref-xyz", "plugins/acme/.claude-plugin/plugin.json")

    def test_local_plugin_manifests_lists_local_sources_only(self):
        _write_marketplace(
            self.repo,
            [
                ("acme", "./plugins/acme"),
                ("remote-git-plugin", {"type": "git", "url": "https://example.com/x.git"}),
                ("outside-repo-plugin", "../not-local"),
            ],
        )
        manifests = cvb.local_plugin_manifests()
        self.assertEqual(
            manifests, [Path("plugins/acme/.claude-plugin/plugin.json")]
        )


class ParseVersionTests(unittest.TestCase):
    def test_plain_version(self):
        self.assertEqual(cvb.parse_version("1.2.3"), (1, 2, 3))

    def test_prerelease_suffix_stripped(self):
        self.assertEqual(cvb.parse_version("1.2.3-beta.1"), (1, 2, 3))

    def test_build_metadata_stripped(self):
        self.assertEqual(cvb.parse_version("1.2.3+build5"), (1, 2, 3))

    def test_both_suffixes_stripped(self):
        self.assertEqual(cvb.parse_version("2.0.0-rc.1+build9"), (2, 0, 0))

    def test_unparseable_version_returns_none(self):
        self.assertIsNone(cvb.parse_version("not-a-version"))

    def test_two_part_version(self):
        self.assertEqual(cvb.parse_version("1.0"), (1, 0))


class MainScenarioTests(unittest.TestCase):
    """End-to-end tests of main(), invoked in-process against real repos
    built per test (chdir + patched argv), checking both stdout/stderr
    messaging and the process exit code main() would produce."""

    def setUp(self):
        self._orig_cwd = os.getcwd()
        self.addCleanup(lambda: os.chdir(self._orig_cwd))
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.repo = Path(self.tmpdir.name)
        _init_repo(self.repo)

    def _run_main(self, *argv):
        os.chdir(self.repo)
        stdout, stderr = io.StringIO(), io.StringIO()
        code = None
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with unittest.mock.patch.object(sys, "argv", ["check_version_bump.py", *argv]):
                try:
                    cvb.main()
                except SystemExit as exc:
                    code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def test_usage_error_when_no_base_given(self):
        code, out, err = self._run_main()
        self.assertEqual(code, 2)
        self.assertIn("usage:", err)

    def test_defaults_head_to_HEAD_when_omitted(self):
        _write_marketplace(self.repo, [("acme", "./plugins/acme")])
        _write_plugin(self.repo, "acme", "1.0.0")
        base = _commit(self.repo, "initial")
        _write_plugin(self.repo, "acme", "1.1.0")
        _commit(self.repo, "bump")

        code, out, err = self._run_main(base)  # no head arg -> defaults to HEAD
        self.assertIsNone(code)
        self.assertIn("OK", out)

    def test_ok_when_version_bumped(self):
        _write_marketplace(self.repo, [("acme", "./plugins/acme")])
        _write_plugin(self.repo, "acme", "1.0.0")
        base = _commit(self.repo, "initial")
        _write_plugin(self.repo, "acme", "1.1.0")
        _touch_plugin_file(self.repo, "acme")
        head = _commit(self.repo, "bump")

        code, out, err = self._run_main(base, head)
        self.assertIsNone(code)
        self.assertIn("OK: every changed plugin bumped its version", out)

    def test_ok_when_no_plugin_files_touched(self):
        _write_marketplace(self.repo, [("acme", "./plugins/acme")])
        _write_plugin(self.repo, "acme", "1.0.0")
        base = _commit(self.repo, "initial")
        (self.repo / "README.md").write_text("unrelated change", encoding="utf-8")
        head = _commit(self.repo, "unrelated")

        code, out, err = self._run_main(base, head)
        self.assertIsNone(code)
        self.assertIn("OK", out)

    def test_fails_when_version_unchanged(self):
        _write_marketplace(self.repo, [("acme", "./plugins/acme")])
        _write_plugin(self.repo, "acme", "1.0.0")
        base = _commit(self.repo, "initial")
        _touch_plugin_file(self.repo, "acme")
        head = _commit(self.repo, "touch without bump")

        code, out, err = self._run_main(base, head)
        self.assertEqual(code, 1)
        self.assertIn("::error::Version bump check failed", out)
        self.assertIn("still '1.0.0'", out)
        self.assertIn("Bump it in plugin.json", out)

    def test_fails_when_version_decreased(self):
        _write_marketplace(self.repo, [("acme", "./plugins/acme")])
        _write_plugin(self.repo, "acme", "2.0.0")
        base = _commit(self.repo, "initial")
        _write_plugin(self.repo, "acme", "1.0.0")
        _touch_plugin_file(self.repo, "acme")
        head = _commit(self.repo, "downgrade")

        code, out, err = self._run_main(base, head)
        self.assertEqual(code, 1)
        self.assertIn("which is not an increase", out)

    def test_fails_when_prerelease_suffix_does_not_count_as_increase(self):
        """"1.0.0-beta" -> "1.0.0" is a different string (passes the equality
        check) but parses to an equal numeric tuple, so it must still fail."""
        _write_marketplace(self.repo, [("acme", "./plugins/acme")])
        _write_plugin(self.repo, "acme", "1.0.0-beta")
        base = _commit(self.repo, "initial")
        _write_plugin(self.repo, "acme", "1.0.0")
        _touch_plugin_file(self.repo, "acme")
        head = _commit(self.repo, "drop prerelease tag")

        code, out, err = self._run_main(base, head)
        self.assertEqual(code, 1)
        self.assertIn("which is not an increase", out)

    def test_passes_when_build_metadata_versions_actually_increase(self):
        _write_marketplace(self.repo, [("acme", "./plugins/acme")])
        _write_plugin(self.repo, "acme", "1.0.0+build1")
        base = _commit(self.repo, "initial")
        _write_plugin(self.repo, "acme", "1.0.1+build2")
        _touch_plugin_file(self.repo, "acme")
        head = _commit(self.repo, "bump with build metadata")

        code, out, err = self._run_main(base, head)
        self.assertIsNone(code)
        self.assertIn("OK", out)

    def test_unparseable_versions_skip_the_increase_check(self):
        """Two different, non-numeric version strings can't be compared
        numerically — parse_version returns None for both, so main() can't
        run the <= check and must not treat this as a failure."""
        _write_marketplace(self.repo, [("acme", "./plugins/acme")])
        _write_plugin(self.repo, "acme", "unstable")
        base = _commit(self.repo, "initial")
        _write_plugin(self.repo, "acme", "unstable-2")
        _touch_plugin_file(self.repo, "acme")
        head = _commit(self.repo, "bump non-numeric version")

        code, out, err = self._run_main(base, head)
        self.assertIsNone(code)
        self.assertIn("OK", out)

    def test_new_plugin_is_skipped(self):
        _write_marketplace(self.repo, [])
        base = _commit(self.repo, "initial (no plugins)")

        _write_marketplace(self.repo, [("acme", "./plugins/acme")])
        _write_plugin(self.repo, "acme", "1.0.0")
        head = _commit(self.repo, "add new plugin")

        code, out, err = self._run_main(base, head)
        self.assertIsNone(code)
        self.assertIn("OK", out)

    def test_deleted_plugin_is_skipped(self):
        _write_marketplace(self.repo, [("acme", "./plugins/acme")])
        _write_plugin(self.repo, "acme", "1.0.0")
        base = _commit(self.repo, "initial")

        _write_marketplace(self.repo, [])
        _git(self.repo, "rm", "-r", "-q", "plugins/acme")
        head = _commit(self.repo, "remove plugin")

        code, out, err = self._run_main(base, head)
        self.assertIsNone(code)
        self.assertIn("OK", out)

    def test_only_touched_plugin_is_checked_among_several(self):
        _write_marketplace(
            self.repo, [("acme", "./plugins/acme"), ("globex", "./plugins/globex")]
        )
        _write_plugin(self.repo, "acme", "1.0.0")
        _write_plugin(self.repo, "globex", "1.0.0")
        base = _commit(self.repo, "initial")

        # Only globex changes, and forgets to bump its version — acme is
        # untouched and must not show up in the failure output.
        _touch_plugin_file(self.repo, "globex")
        head = _commit(self.repo, "touch globex only")

        code, out, err = self._run_main(base, head)
        self.assertEqual(code, 1)
        self.assertIn("globex", out)
        self.assertNotIn("acme changed", out)

    def test_failure_message_truncates_long_file_list(self):
        _write_marketplace(self.repo, [("acme", "./plugins/acme")])
        _write_plugin(self.repo, "acme", "1.0.0")
        base = _commit(self.repo, "initial")
        for i in range(6):
            _touch_plugin_file(self.repo, "acme", rel=f"commands/f{i}.md")
        head = _commit(self.repo, "touch six files without bumping")

        code, out, err = self._run_main(base, head)
        self.assertEqual(code, 1)
        self.assertIn("6 file(s)", out)
        self.assertIn("...", out)


if __name__ == "__main__":
    unittest.main()
