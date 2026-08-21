#!/usr/bin/env python3
"""
Fail if a plugin's files changed in this PR but its
.claude-plugin/plugin.json "version" field was not bumped.

Enforces the release-discipline note in the repo README's publishing
checklist: customers can pin a plugin version, so an unbumped version means
they never see the fix.

Usage: check_version_bump.py <base-sha-or-ref> [<head-sha-or-ref>]
"""
import json
import subprocess
import sys
from pathlib import Path


def git(*args):
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout


def changed_files(base, head):
    out = git("diff", "--name-only", f"{base}...{head}")
    return [line for line in out.splitlines() if line]


def _ref_exists(ref):
    return subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        capture_output=True,
    ).returncode == 0


def _path_exists_at(ref, path):
    return subprocess.run(
        ["git", "cat-file", "-e", f"{ref}:{path}"], capture_output=True
    ).returncode == 0


def read_json_at(ref, path):
    if not _ref_exists(ref):
        # A bad/unresolvable ref is a real error, not "file doesn't exist at
        # this ref" — let it raise instead of silently treating the plugin
        # as new/deleted (which would skip the version-bump check).
        raise RuntimeError(f"not a valid ref: {ref!r}")
    if not _path_exists_at(ref, path):
        return None
    text = git("show", f"{ref}:{path}")
    return json.loads(text)


def local_plugin_manifests():
    """Plugin manifest paths, driven by marketplace.json (the same source
    of truth tests/unit/test_manifests.py uses) rather than a filesystem
    glob, so the two can't drift apart as plugins are added/moved. Only
    local path sources are covered — see marketplace.json's own comment on
    that; git/npm/archive-sourced plugins aren't present in this checkout to
    version-check anyway."""
    with open(".claude-plugin/marketplace.json", encoding="utf-8") as f:
        marketplace = json.load(f)
    paths = []
    for entry in marketplace.get("plugins", []):
        source = entry.get("source")
        if isinstance(source, str) and source.startswith("./"):
            paths.append((Path(source) / ".claude-plugin" / "plugin.json"))
    return sorted(p.resolve().relative_to(Path.cwd()) for p in paths)


def parse_version(v):
    # Compare only the numeric dotted-prefix, stripping any prerelease/build
    # metadata (e.g. "1.2.3-beta.1" -> (1, 2, 3), "1.2.3+build5" -> (1, 2, 3)).
    # Without this, a version like "1.0.0-beta" fails int() parsing, returns
    # None, and silently skips the increase check below — letting a real
    # downgrade like "2.0.0" -> "1.0.0-beta" pass.
    numeric_prefix = str(v).split("+", 1)[0].split("-", 1)[0]
    try:
        return tuple(int(x) for x in numeric_prefix.split("."))
    except (ValueError, AttributeError):
        return None


def main():
    if len(sys.argv) < 2:
        print("usage: check_version_bump.py <base> [<head>]", file=sys.stderr)
        sys.exit(2)
    base = sys.argv[1]
    head = sys.argv[2] if len(sys.argv) > 2 else "HEAD"

    changed = changed_files(base, head)
    plugin_manifests = local_plugin_manifests()
    failures = []

    for manifest_path in plugin_manifests:
        plugin_dir = manifest_path.parent.parent
        rel_manifest = manifest_path.as_posix()
        plugin_prefix = plugin_dir.as_posix() + "/"
        touched = [f for f in changed if f.startswith(plugin_prefix)]
        if not touched:
            continue

        old = read_json_at(base, rel_manifest)
        new = read_json_at(head, rel_manifest)
        if old is None or new is None:
            # New or deleted plugin — nothing to compare a version against.
            continue

        old_version, new_version = old.get("version"), new.get("version")
        if old_version == new_version:
            failures.append(
                f'{rel_manifest}: {plugin_dir.name} changed ({len(touched)} file(s): '
                f'{", ".join(touched[:5])}{"..." if len(touched) > 5 else ""}) but '
                f'"version" is still {old_version!r}. Bump it in plugin.json.'
            )
            continue

        old_parsed, new_parsed = parse_version(old_version), parse_version(new_version)
        if old_parsed is not None and new_parsed is not None and new_parsed <= old_parsed:
            failures.append(
                f"{rel_manifest}: version went {old_version!r} -> {new_version!r}, "
                "which is not an increase."
            )

    if failures:
        print("::error::Version bump check failed")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)

    print("OK: every changed plugin bumped its version (or is new/deleted).")


if __name__ == "__main__":
    main()
