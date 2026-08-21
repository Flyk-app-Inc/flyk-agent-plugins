"""
Unit tests for the Flyk plugin marketplace's static files.

No network access, no `claude` CLI, no API key required — these only check that
the JSON manifests and Markdown frontmatter are well-formed and internally
consistent. Run with:

    python3 -m unittest discover -s tests/unit -v
"""
import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKETPLACE_PATH = REPO_ROOT / ".claude-plugin" / "marketplace.json"

KEBAB_CASE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_frontmatter(md_path: Path):
    """Minimal YAML-frontmatter parser for the flat key: value / key: [a, b]
    frontmatter used by command and skill files in this repo. Not a general
    YAML parser."""
    text = md_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    fm_text, body = m.group(1), m.group(2)
    fm = {}
    for line in fm_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key, value = key.strip(), value.strip()
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]
        elif value.startswith("[") and value.endswith("]"):
            value = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",") if v.strip()]
        fm[key] = value
    return fm, body


class MarketplaceManifestTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MARKETPLACE_PATH.is_file(), f"missing {MARKETPLACE_PATH}")
        self.marketplace = load_json(MARKETPLACE_PATH)

    def test_required_top_level_fields(self):
        for field in ("name", "owner", "plugins"):
            self.assertIn(field, self.marketplace)
        self.assertTrue(KEBAB_CASE.match(self.marketplace["name"]), self.marketplace["name"])
        self.assertIsInstance(self.marketplace["plugins"], list)
        self.assertGreater(len(self.marketplace["plugins"]), 0, "marketplace lists no plugins")

    def test_owner_has_contact_info(self):
        owner = self.marketplace["owner"]
        self.assertIn("name", owner)

    def test_every_plugin_entry_resolves_to_a_local_plugin_dir(self):
        for entry in self.marketplace["plugins"]:
            self.assertIn("name", entry)
            self.assertTrue(KEBAB_CASE.match(entry["name"]), entry["name"])
            source = entry["source"]
            # This repo only uses local path sources today; git/npm/archive
            # sources are documented but not exercised by these tests.
            self.assertIsInstance(source, str, "expected a local path source")
            self.assertTrue(source.startswith("./"), source)
            plugin_dir = (MARKETPLACE_PATH.parent.parent / source).resolve()
            self.assertTrue(plugin_dir.is_dir(), f"{source} does not exist")
            self.assertTrue(
                (plugin_dir / ".claude-plugin" / "plugin.json").is_file(),
                f"{source} has no .claude-plugin/plugin.json",
            )


class PluginManifestTests(unittest.TestCase):
    """Parameterized-by-hand over every plugin listed in marketplace.json."""

    @classmethod
    def setUpClass(cls):
        marketplace = load_json(MARKETPLACE_PATH)
        # Only local path sources have a plugin.json in this checkout to
        # test against; a git/npm/archive source (a dict, not a str) is a
        # valid marketplace.json shape but isn't present on disk here, so
        # skip it rather than crashing setUpClass (and every test in this
        # class) on a Path / dict TypeError.
        cls.plugin_dirs = [
            (MARKETPLACE_PATH.parent.parent / e["source"]).resolve()
            for e in marketplace["plugins"]
            if isinstance(e.get("source"), str)
        ]
        cls.marketplace_names = {e["name"] for e in marketplace["plugins"]}
        cls.marketplace_entries_by_source = {
            e["name"]: e for e in marketplace["plugins"] if isinstance(e.get("source"), str)
        }

    def test_plugin_json_required_fields_and_name_match(self):
        for plugin_dir in self.plugin_dirs:
            with self.subTest(plugin=plugin_dir.name):
                manifest = load_json(plugin_dir / ".claude-plugin" / "plugin.json")
                self.assertIn("name", manifest)
                self.assertTrue(KEBAB_CASE.match(manifest["name"]), manifest["name"])
                self.assertIn(
                    manifest["name"],
                    self.marketplace_names,
                    "plugin.json name must match its marketplace.json entry",
                )
                self.assertIn("description", manifest)
                self.assertTrue(manifest["description"].strip())

    def test_plugin_json_version_matches_marketplace_entry(self):
        """Companion to the name-match check above: marketplace.json's
        per-plugin `version` is a convenience copy of plugin.json's real
        version, and nothing else enforces they agree — a stale marketplace
        entry would otherwise pass CI silently (check_version_bump.py only
        reads plugin.json). A marketplace entry is allowed to omit
        `version` entirely (it isn't a required field); but if present, it
        must match plugin.json exactly rather than silently drifting."""
        for plugin_dir in self.plugin_dirs:
            with self.subTest(plugin=plugin_dir.name):
                manifest = load_json(plugin_dir / ".claude-plugin" / "plugin.json")
                entry = self.marketplace_entries_by_source[manifest["name"]]
                if "version" not in entry:
                    continue
                self.assertEqual(
                    entry["version"],
                    manifest.get("version"),
                    f"marketplace.json's version for {manifest['name']} "
                    f"({entry['version']!r}) does not match its plugin.json "
                    f"version ({manifest.get('version')!r})",
                )

    def test_plugin_is_open_access_no_user_config(self):
        """Regression test: this plugin was deliberately made open / no API
        key. If someone reintroduces a required userConfig field, this
        should fail loudly rather than silently reintroducing a setup step."""
        for plugin_dir in self.plugin_dirs:
            with self.subTest(plugin=plugin_dir.name):
                manifest = load_json(plugin_dir / ".claude-plugin" / "plugin.json")
                self.assertNotIn(
                    "userConfig",
                    manifest,
                    "plugin.json declares userConfig — this plugin is meant to be open access",
                )

    def test_mcp_server_declares_no_auth(self):
        """Companion to the userConfig check above: open access also means
        .mcp.json itself carries no auth material (a header, a bearer
        token, an API-key-shaped field) — the mechanism this plugin
        actually had removed earlier in its history."""
        auth_like = re.compile(r"auth|api[_-]?key|token|secret|bearer", re.IGNORECASE)
        for plugin_dir in self.plugin_dirs:
            mcp_path = plugin_dir / ".mcp.json"
            if not mcp_path.is_file():
                continue
            with self.subTest(plugin=plugin_dir.name):
                servers = load_json(mcp_path)
                for server_name, config in servers.items():
                    self.assertNotIn(
                        "headers", config, f"{server_name} declares headers — not open access"
                    )
                    for key in config:
                        self.assertNotRegex(
                            key,
                            auth_like,
                            f"{server_name}.{key} looks auth-related — not open access",
                        )

    def test_declared_component_paths_exist(self):
        for plugin_dir in self.plugin_dirs:
            manifest = load_json(plugin_dir / ".claude-plugin" / "plugin.json")
            for field in ("commands", "skills", "mcpServers"):
                if field not in manifest:
                    continue
                value = manifest[field]
                paths = value if isinstance(value, list) else [value]
                for rel_path in paths:
                    with self.subTest(plugin=plugin_dir.name, field=field, path=rel_path):
                        resolved = (plugin_dir / rel_path).resolve()
                        self.assertTrue(
                            resolved.exists(), f"{field} path {rel_path} does not exist"
                        )

    def test_mcp_server_config_shape(self):
        for plugin_dir in self.plugin_dirs:
            mcp_path = plugin_dir / ".mcp.json"
            if not mcp_path.is_file():
                continue
            with self.subTest(plugin=plugin_dir.name):
                servers = load_json(mcp_path)
                self.assertIsInstance(servers, dict)
                self.assertGreater(len(servers), 0, ".mcp.json declares no servers")
                for server_name, config in servers.items():
                    self.assertTrue(KEBAB_CASE.match(server_name) or server_name.isalnum(), server_name)
                    if config.get("type") in ("http", "sse"):
                        self.assertIn("url", config)
                        self.assertTrue(config["url"].startswith("https://"), config["url"])
                    else:
                        # stdio server (type omitted or "stdio")
                        self.assertIn("command", config)

    def test_command_files_have_description_frontmatter(self):
        for plugin_dir in self.plugin_dirs:
            commands_dir = plugin_dir / "commands"
            if not commands_dir.is_dir():
                continue
            md_files = sorted(commands_dir.glob("*.md"))
            self.assertGreater(len(md_files), 0, f"{commands_dir} has no command files")
            for md_file in md_files:
                with self.subTest(command=md_file.name):
                    fm, body = parse_frontmatter(md_file)
                    self.assertIn("description", fm, f"{md_file} missing description frontmatter")
                    self.assertTrue(fm["description"].strip())
                    self.assertTrue(body.strip(), f"{md_file} has an empty body")

    def test_skill_files_have_matching_name_and_description(self):
        for plugin_dir in self.plugin_dirs:
            skills_dir = plugin_dir / "skills"
            if not skills_dir.is_dir():
                continue
            skill_files = sorted(skills_dir.glob("*/SKILL.md"))
            self.assertGreater(len(skill_files), 0, f"{skills_dir} has no SKILL.md files")
            for skill_file in skill_files:
                with self.subTest(skill=skill_file.parent.name):
                    fm, body = parse_frontmatter(skill_file)
                    self.assertIn("name", fm)
                    self.assertEqual(fm["name"], skill_file.parent.name)
                    self.assertIn("description", fm)
                    self.assertTrue(fm["description"].strip())
                    self.assertTrue(body.strip())


if __name__ == "__main__":
    unittest.main()
