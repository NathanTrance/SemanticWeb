"""Parse-check every RDF file in the given paths.

Quality gate #1 from AGENT.md. Usage:
    python etl/validate_rdf.py [path ...]
Accepts the common RDF serializations (.owl, .rdf, .ttl, .nt, .jsonld) and
guesses the parser from the file extension. Defaults to the ontology,
generated RDF and link graphs. Exits non-zero if any file fails to parse,
so it can be wired into a pre-commit hook or CI.
"""

from __future__ import annotations

import sys
from pathlib import Path

from rdflib import Graph

SUFFIXES = {".owl", ".rdf", ".ttl", ".nt", ".jsonld", ".n3"}


def validate(paths: list[Path]) -> int:
    """Try to parse each file; return the number that failed."""
    failed = 0
    for path in paths:
        graph = Graph()
        try:
            graph.parse(path)
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
            files.extend(
                sorted(p for p in path.rglob("*") if p.suffix in SUFFIXES)
            )
        elif path.exists():
            files.append(path)
    if not files:
        print("no RDF files found")
        return 1
    failed = validate(files)
    print(f"\n{len(files) - failed}/{len(files)} file(s) parsed cleanly")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
