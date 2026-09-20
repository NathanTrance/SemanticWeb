"""Re-serialize the RDF files into other syntaxes.

Demonstrates the key point that RDF/XML, Turtle, JSON-LD and N-Triples are
just different *serializations* of the same triples - converting between
them adds or removes nothing. The canonical files stay in RDF/XML
(ontology/drinkonto.owl, data/rdf/data.rdf, data/links/links.rdf); the
exports land in exports/ (git-ignored) and are handy for the report.

Run:
    python etl/export_formats.py          # export every graph
    python etl/export_formats.py ontology/drinkonto.owl
"""

from __future__ import annotations

import sys
from pathlib import Path

from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "exports"
SOURCES = [
    ROOT / "ontology" / "drinkonto.owl",
    ROOT / "data" / "rdf" / "data.rdf",
    ROOT / "data" / "links" / "links.rdf",
]
TARGETS = {"ttl": "turtle", "jsonld": "json-ld", "nt": "nt"}


def export(source: Path) -> None:
    graph = Graph()
    graph.parse(source)
    OUT.mkdir(parents=True, exist_ok=True)
    for extension, rdf_format in TARGETS.items():
        destination = OUT / f"{source.stem}.{extension}"
        graph.serialize(
            destination=str(destination), format=rdf_format, encoding="utf-8"
        )
        print(f"{len(graph):>6} triples -> {destination.relative_to(ROOT)}")


def main(argv: list[str]) -> int:
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
    sources = [Path(a) for a in argv[1:]] or SOURCES
    for source in sources:
        if source.exists():
            export(source)
        else:
            print(f"skip (missing): {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
