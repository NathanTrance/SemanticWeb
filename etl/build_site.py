"""Generate a static site so our IRIs dereference on GitHub Pages.

For every entity IRI (`.../id/<type>/<slug>`) we write a file at exactly that
path holding a concise RDF/XML description, plus a sibling `.html` page for
humans. The ontology is published at `.../onto`. Publishing this folder on
GitHub Pages makes the IRIs resolve on the public web.

Caveat: GitHub Pages is static and cannot do HTTP content negotiation, so it
serves the extensionless RDF as a download rather than as `text/turtle`. The
local `web/server.py` demonstrates proper negotiation; this export is the
"publicly resolvable" evidence.

Run:  python etl/build_site.py [--out site]
"""

from __future__ import annotations

import argparse
import html
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDFS
from rdflib.term import Node

ROOT = Path(__file__).resolve().parents[1]
GRAPHS = [
    ROOT / "ontology" / "drinkonto.owl",
    ROOT / "data" / "rdf" / "data.rdf",
    ROOT / "data" / "links" / "links.rdf",
]
BASE_IRI = "https://nathantrance.github.io/SemanticWeb/"
ID_PREFIX = BASE_IRI + "id/"

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{title}</title>
<style>
body{{font:15px/1.5 system-ui,sans-serif;margin:2rem;max-width:70rem;color:#1b1b1b}}
a{{color:#9a5b00}} table{{border-collapse:collapse;margin-top:1rem}}
td,th{{border:1px solid #ddd;padding:4px 8px;text-align:left;vertical-align:top}}
h1{{margin-bottom:.2rem}} .muted{{color:#777}}
</style></head>
<body>
{body}
</body></html>"""


def load() -> tuple[Graph, Graph]:
    ontology = Graph()
    ontology.parse(GRAPHS[0])
    merged = Graph()
    for prefix, namespace in ontology.namespaces():
        merged.bind(prefix, namespace)
    for path in GRAPHS:
        merged.parse(path)
    return ontology, merged


def label(graph: Graph, subject: Node) -> str:
    for value in graph.objects(subject, RDFS.label):
        return str(value)
    return str(subject).rsplit("/", 1)[-1]


def description(graph: Graph, subject: Node) -> Graph:
    subgraph = Graph()
    for prefix, namespace in graph.namespaces():
        subgraph.bind(prefix, namespace)
    for predicate, obj in graph.predicate_objects(subject):
        subgraph.add((subject, predicate, obj))
        if isinstance(obj, URIRef) and str(obj).startswith(ID_PREFIX):
            for nested_predicate, nested_obj in graph.predicate_objects(obj):
                subgraph.add((obj, nested_predicate, nested_obj))
    return subgraph


def render_table(graph: Graph, subgraph: Graph) -> str:
    rows = []
    for predicate, obj in sorted(subgraph.predicate_objects(), key=lambda t: str(t[0])):
        short = graph.namespace_manager.normalizeUri(str(predicate))
        value = f'<a href="{obj}">{html.escape(str(obj))}</a>' if isinstance(obj, URIRef) else html.escape(str(obj))
        rows.append(f"<tr><td>{html.escape(short)}</td><td>{value}</td></tr>")
    return "<table><tbody>" + "".join(rows) + "</tbody></table>"


def write_page(path: Path, title: str, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PAGE.format(title=html.escape(title), body=content), encoding="utf-8")


def build(out: Path) -> None:
    ontology, merged = load()
    out.mkdir(parents=True, exist_ok=True)
    (out / ".nojekyll").write_text("", encoding="utf-8")

    ontology.serialize(destination=str(out / "onto"), format="xml")
    ontology.serialize(destination=str(out / "onto.ttl"), format="turtle")
    ontology.serialize(destination=str(out / "onto.jsonld"), format="json-ld")

    index: dict[str, list[tuple[str, str]]] = defaultdict(list)
    subjects = sorted(
        {
            str(subject)
            for subject in merged.subjects()
            if isinstance(subject, URIRef)
            and str(subject).startswith(ID_PREFIX)
            and not str(subject).startswith(ID_PREFIX + "ingredient-amount/")
        }
    )

    for uri in subjects:
        subject = URIRef(uri)
        subgraph = description(merged, subject)
        relative = uri[len(ID_PREFIX):]
        kind = relative.split("/", 1)[0]
        name = label(merged, subject)

        resource = out / "id" / relative
        resource.parent.mkdir(parents=True, exist_ok=True)
        subgraph.serialize(destination=str(resource), format="xml")

        filename = relative.rsplit("/", 1)[-1]
        content = (
            f"<h1>{html.escape(name)}</h1>"
            f'<p class="muted">{html.escape(kind)} &middot; '
            f'<a href="{filename}">RDF/XML</a></p>'
            + render_table(merged, subgraph)
        )
        write_page(out / "id" / f"{relative}.html", name, content)
        index[kind].append((name, f"id/{relative}.html"))

    sections = []
    for kind in sorted(index):
        entries = sorted(index[kind])
        links = "\n".join(
            f'<li><a href="{href}">{html.escape(name)}</a></li>' for name, href in entries
        )
        sections.append(f"<h2>{html.escape(kind)} ({len(entries)})</h2><ul>{links}</ul>")

    landing = (
        "<h1>linked-drinks</h1>"
        "<p>5&#9733; Linked Open Data for cocktails, spirits &amp; distilleries. "
        f"<a href='onto.html'>Ontology</a> &middot; "
        f"<a href='onto.ttl'>ontology (Turtle)</a></p>"
        f"<p class='muted'>{len(subjects)} dereferenceable entity IRIs; "
        f"{len(merged)} triples.</p>" + "".join(sections)
    )
    write_page(out / "index.html", "linked-drinks", landing)
    write_page(
        out / "onto.html",
        "drinkonto",
        "<h1>drinkonto ontology</h1>"
        '<p class="muted"><a href="onto">RDF/XML</a> &middot; '
        '<a href="onto.ttl">Turtle</a> &middot; <a href="onto.jsonld">JSON-LD</a></p>'
        + render_table(merged, ontology),
    )
    try:
        shown = out.relative_to(ROOT)
    except ValueError:
        shown = out
    print(f"wrote {len(subjects)} entity IRIs + ontology to {shown}")


def main(argv: list[str]) -> int:
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "site"))
    args = parser.parse_args(argv[1:])
    build(Path(args.out).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
