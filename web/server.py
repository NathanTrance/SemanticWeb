"""A tiny, dependency-free SPARQL endpoint for the linked-drinks graph.

Serves the static UI in this folder and a SPARQL 1.1 query endpoint at
/sparql over the merged onto + data + links graphs, using rdflib. It is a
stand-in for Apache Jena Fuseki (see docker-compose.yml) so the project can
be demoed without a Java install; both speak the SPARQL protocol, so the
same UI works against either.

Run:  python web/server.py            # http://localhost:8000
      python web/server.py --port 3030
"""

from __future__ import annotations

import argparse
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from rdflib import Graph

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GRAPHS = [
    ROOT / "ontology" / "drinkonto.owl",
    ROOT / "data" / "rdf" / "data.rdf",
    ROOT / "data" / "links" / "links.rdf",
]

STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".rq": "text/plain; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


def load_graph() -> Graph:
    graph = Graph()
    for path in GRAPHS:
        graph.parse(path)
    return graph


class Handler(BaseHTTPRequestHandler):
    graph: Graph
    server_version = "linked-drinks/0.1"

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
            query = parse_qs(parsed.query).get("query", [""])[0]
            self._run(query)
            return
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

    Handler.graph = load_graph()
    print(f"loaded {len(Handler.graph)} triples")
    print(f"SPARQL endpoint: http://{args.host}:{args.port}/sparql")
    print(f"Query UI:        http://{args.host}:{args.port}/")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
