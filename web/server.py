"""A tiny, dependency-free Linked Data server + SPARQL endpoint.

Three jobs, all from one process:

  * GET /sparql            - SPARQL 1.1 endpoint (JSON/XML/Turtle, CORS)
  * GET /onto              - the ontology document
  * GET /id/<type>/<slug>  - dereference an entity IRI

The two Linked Data routes do HTTP **content negotiation**: send
`Accept: text/html` and you get a readable page; send `Accept: text/turtle`
(or application/rdf+xml, application/ld+json) and you get RDF. That is what
makes our IRIs dereferenceable (star-4) instead of inert identifiers. It is
a stand-in for Apache Jena Fuseki (see docker-compose.yml).

Run:  python web/server.py            # http://localhost:8000
      curl -H "Accept: text/turtle" http://localhost:8000/id/cocktail/negroni
"""

from __future__ import annotations

import argparse
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from rdflib import Graph, URIRef
from rdflib.term import Node

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GRAPHS = [
    ROOT / "ontology" / "drinkonto.owl",
    ROOT / "data" / "rdf" / "data.rdf",
    ROOT / "data" / "links" / "links.rdf",
]

BASE_IRI = "https://nathantrance.github.io/SemanticWeb/"
ONTO_PATH = BASE_IRI + "onto"
ID_PREFIX = BASE_IRI + "id/"

# Accept substring -> (rdflib format, media type)
RDF_FORMATS = {
    "text/turtle": ("turtle", "text/turtle; charset=utf-8"),
    "application/ld+json": ("json-ld", "application/ld+json; charset=utf-8"),
    "application/rdf+xml": ("xml", "application/rdf+xml; charset=utf-8"),
}
DEFAULT_RDF = ("xml", "application/rdf+xml; charset=utf-8")

STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".rq": "text/plain; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


def load_graphs() -> tuple[Graph, Graph]:
    """Return (merged onto+data+links for SPARQL, ontology-only document)."""
    ontology = Graph()
    ontology.parse(GRAPHS[0])
    merged = Graph()
    for prefix, namespace in ontology.namespaces():
        merged.bind(prefix, namespace)
    for path in GRAPHS:
        merged.parse(path)
    return merged, ontology


def concise_description(graph: Graph, subject: Node) -> Graph:
    """A subject's triples plus one hop into our own IRIs.

    The extra hop pulls in the ingredient-amount nodes and their labels, so a
    single IRI fetch returns a self-contained description (Linked Data style).
    """
    subgraph = Graph()
    for prefix, namespace in graph.namespaces():
        subgraph.bind(prefix, namespace)
    for predicate, obj in graph.predicate_objects(subject):
        subgraph.add((subject, predicate, obj))
        if isinstance(obj, URIRef) and str(obj).startswith(ID_PREFIX):
            for nested_predicate, nested_obj in graph.predicate_objects(obj):
                subgraph.add((obj, nested_predicate, nested_obj))
    return subgraph


class Handler(BaseHTTPRequestHandler):
    graph: Graph
    ontology: Graph
    server_version = "linked-drinks/0.2"

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write("  " + (format % args) + "\n")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send(204, b"", "text/plain")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/sparql":
            self._run(parse_qs(parsed.query).get("query", [""])[0])
        elif parsed.path == "/onto" or parsed.path.startswith("/id/"):
            self._dereference(parsed)
        else:
            self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/sparql":
            self._send(404, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        content_type = self.headers.get("Content-Type", "")
        if "application/sparql-query" in content_type:
            query = body
        else:
            query = parse_qs(body).get("query", [""])[0]
        self._run(query)

    # -- Linked Data ------------------------------------------------------

    def _dereference(self, parsed) -> None:
        override = parse_qs(parsed.query).get("format", [""])[0].lower()
        if parsed.path == "/onto":
            subgraph = self.ontology
            title = "drinkonto ontology"
        else:
            subject = URIRef(BASE_IRI + parsed.path.lstrip("/"))
            subgraph = concise_description(self.graph, subject)
            if not len(subgraph):
                message = f"No description found for {subject}"
                self._send(404, message.encode("utf-8"), "text/plain; charset=utf-8")
                return
            title = self._label(subgraph, subject)

        if override in ("html",) or (
            not override and "text/html" in self.headers.get("Accept", "")
        ):
            body = self._render_html(title, subgraph)
            self._send(200, body.encode("utf-8"), "text/html; charset=utf-8")
            return

        fmt, media = self._negotiate(
            self.headers.get("Accept", "*/*"), override
        )
        body = subgraph.serialize(format=fmt)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self._send(200, body or b"", media)

    def _negotiate(self, accept: str, override: str) -> tuple[str, str]:
        if override in ("ttl", "turtle"):
            return RDF_FORMATS["text/turtle"]
        if override in ("rdf", "xml"):
            return DEFAULT_RDF
        if override in ("jsonld", "json-ld"):
            return RDF_FORMATS["application/ld+json"]
        for token, target in RDF_FORMATS.items():
            if token in accept:
                return target
        return DEFAULT_RDF

    def _label(self, graph: Graph, subject: Node) -> str:
        from rdflib.namespace import RDFS

        for label in graph.objects(subject, RDFS.label):
            return str(label)
        return str(subject)

    def _render_html(self, title: str, subgraph: Graph) -> str:
        rows = []
        for predicate, obj in sorted(subgraph.predicate_objects(), key=lambda t: str(t[0])):
            short = self.graph.namespace_manager.normalizeUri(str(predicate))
            if isinstance(obj, URIRef):
                value = f'<a href="{obj}">{obj}</a>'
            else:
                value = str(obj)
            rows.append(f"<tr><td>{short}</td><td>{value}</td></tr>")
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{title}</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;margin:2rem;max-width:60rem}}
table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:4px 8px;text-align:left;vertical-align:top}}
code{{background:#f3f3f3;padding:1px 4px}}</style></head>
<body><h1>{title}</h1>
<p>Dereferenced Linked Data. Machine-readable formats:
<a href="?format=turtle">Turtle</a> ·
<a href="?format=rdf">RDF/XML</a> ·
<a href="?format=jsonld">JSON-LD</a></p>
<table><tbody>{''.join(rows)}</tbody></table>
</body></html>"""

    # -- static + SPARQL --------------------------------------------------

    def _serve_static(self, path: str) -> None:
        relative = "index.html" if path in ("/", "") else path.lstrip("/")
        for base in (HERE, ROOT):
            target = (base / relative).resolve()
            if base != target and base not in target.parents:
                continue
            if target.is_file():
                kind = STATIC_TYPES.get(target.suffix, "application/octet-stream")
                self._send(200, target.read_bytes(), kind)
                return
        self._send(404, b"not found", "text/plain")

    def _run(self, query: str) -> None:
        if not query.strip():
            self._send(400, b"missing query parameter", "text/plain")
            return
        accept = self.headers.get("Accept", "application/sparql-results+json")
        try:
            result = self.graph.query(query)
        except Exception as exc:
            self._send(400, str(exc).encode("utf-8"), "text/plain; charset=utf-8")
            return

        if result.type in ("CONSTRUCT", "DESCRIBE"):
            if "text/turtle" in accept:
                fmt, media = "turtle", "text/turtle; charset=utf-8"
            elif "ld+json" in accept:
                fmt, media = "json-ld", "application/ld+json"
            else:
                fmt, media = "xml", "application/rdf+xml; charset=utf-8"
        else:
            if "sparql-results+xml" in accept or "application/xml" in accept:
                fmt, media = "xml", "application/sparql-results+xml; charset=utf-8"
            else:
                fmt, media = "json", "application/sparql-results+json; charset=utf-8"

        body = result.serialize(format=fmt)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self._send(200, body or b"", media)


def main(argv: list[str]) -> int:
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv[1:])

    merged, ontology = load_graphs()
    Handler.graph = merged
    Handler.ontology = ontology
    print(f"loaded {len(merged)} triples")
    print(f"Query UI:        http://{args.host}:{args.port}/")
    print(f"SPARQL endpoint: http://{args.host}:{args.port}/sparql")
    print(f"Dereference:     http://{args.host}:{args.port}/id/cocktail/negroni")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
