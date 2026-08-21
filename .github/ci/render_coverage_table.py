#!/usr/bin/env python3
"""
Render a coverage.py JSON report (`coverage json -o coverage.json`) as a
markdown table for the PR comment / job summary posted by the `coverage`
job in .github/workflows/test.yml.

Deliberately lives outside .github/scripts/, which is what that job's
`coverage run --source=.github/scripts` measures — this script is CI glue,
not the application code the 95% gate applies to.

Usage: render_coverage_table.py [coverage.json] [--threshold 95] [-o out.md]
"""
import argparse
import json
import sys


def render(data: dict, threshold: float) -> str:
    def row(name: str, s: dict) -> str:
        cover = f"{s['percent_covered']:.1f}%"
        branch_pct = s.get("percent_branches_covered")
        branch_cover = f"{branch_pct:.1f}%" if branch_pct is not None else "—"
        return (
            f"| {name} | {s['num_statements']} | {s['missing_lines']} | "
            f"{s.get('num_branches', 0)} | {s.get('num_partial_branches', 0)} | "
            f"{branch_cover} | {cover} |"
        )

    totals = data["totals"]
    percent = totals["percent_covered"]
    status = "✅ pass" if percent >= threshold else "❌ fail"

    lines = [
        "<!-- coverage-report -->",
        f"### Code coverage: {percent:.1f}% — gate is {threshold:.0f}% ({status})",
        "",
        "| File | Stmts | Miss | Branch | Partial | Branch % | Cover |",
        "|---|---|---|---|---|---|---|",
    ]
    for filename in sorted(data["files"]):
        lines.append(row(f"`{filename}`", data["files"][filename]["summary"]))
    lines.append(row("**TOTAL**", totals))
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage_json", nargs="?", default="coverage.json")
    parser.add_argument("--threshold", type=float, default=95.0)
    parser.add_argument("-o", "--output", default="coverage_comment.md")
    args = parser.parse_args()

    with open(args.coverage_json, encoding="utf-8") as f:
        data = json.load(f)

    table = render(data, args.threshold)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(table)
    sys.stdout.write(table)


if __name__ == "__main__":
    main()
