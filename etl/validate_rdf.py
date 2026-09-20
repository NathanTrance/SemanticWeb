"""Parse-check every Turtle file in the given paths.

Quality gate #1 from AGENT.md. Usage:
    python etl/validate_rdf.py [path ...]
Defaults to the ontology, generated RDF and link graphs. Exits non-zero if
any file fails to parse, so it can be wired into a pre-commit hook or CI.
"""

from __future__ import annotations

import sys
from pathlib import Path

from rdflib import Graph


def validate(paths: list[Path]) -> int:
    """Try to parse each file; return the number that failed."""
    failed = 0
    for path in paths:
        graph = Graph()
        try:
            graph.parse(path, format="turtle")
        except Exception as exc:
            print(f"FAIL {path}: {exc}")
            failed += 1
        else:
            print(f"OK   {path}  ({len(graph)} triples)")
    return failed


def main(argv: list[str]) -> int:
    targets = argv[1:] or ["ontology", "data/rdf", "data/links"]
    files: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.ttl")))
        elif path.exists():
            files.append(path)
    if not files:
        print("no .ttl files found")
        return 1
    failed = validate(files)
    print(f"\n{len(files) - failed}/{len(files)} file(s) parsed cleanly")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
