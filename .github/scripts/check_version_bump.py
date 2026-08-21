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


def read_json_at(ref, path):
    try:
        text = git("show", f"{ref}:{path}")
    except subprocess.CalledProcessError:
        return None
    return json.loads(text)


def parse_version(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except (ValueError, AttributeError):
        return None


def main():
    if len(sys.argv) < 2:
        print("usage: check_version_bump.py <base> [<head>]", file=sys.stderr)
        sys.exit(2)
    base = sys.argv[1]
    head = sys.argv[2] if len(sys.argv) > 2 else "HEAD"

    changed = changed_files(base, head)
    plugin_manifests = sorted(Path(".").glob("plugins/*/.claude-plugin/plugin.json"))
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
