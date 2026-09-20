"""Load the three RDF/XML graphs into a running Jena Fuseki dataset.

By default the graphs are merged into the dataset's **default graph** (a GSP
DELETE followed by one POST per file) so that the demo queries - which do not
use GRAPH - return the same results on Fuseki and on the local rdflib server.
Pass `--named-graphs` to instead keep onto/data/links separate for
provenance-style querying with GRAPH.

Companion to docker-compose.yml:

    docker compose up -d
    python etl/load_fuseki.py --endpoint http://127.0.0.1:3030/ds \
        --user admin --password admin

Use 127.0.0.1 rather than localhost: on Windows, localhost resolves to IPv6
(::1) first and Docker only publishes IPv4, costing ~20s per new connection.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://nathantrance.github.io/SemanticWeb/graph"
GRAPHS = {
    "onto": ROOT / "ontology" / "drinkonto.owl",
    "data": ROOT / "data" / "rdf" / "data.rdf",
    "links": ROOT / "data" / "links" / "links.rdf",
}
RDF_XML = {"Content-Type": "application/rdf+xml"}


def _report(action: str, target: str, response: requests.Response, path: Path) -> None:
    status = "OK " if response.ok else "FAIL"
    print(f"{status} {action:6} {target:55} ({response.status_code}) <- {path.name}")


def load_default(endpoint: str, auth: tuple[str, str]) -> None:
    response = requests.post(
        f"{endpoint}/update",
        data={"update": "CLEAR DEFAULT"},
        auth=auth,
        timeout=120,
    )
    print(f"{'OK ' if response.ok else 'FAIL'} clear  default graph"
          f" ({response.status_code})")
    for name, path in GRAPHS.items():
        response = requests.post(
            f"{endpoint}/data",
            data=path.read_bytes(),
            headers=RDF_XML,
            auth=auth,
            timeout=180,
        )
        _report("merge", "default graph", response, path)


def load_named(endpoint: str, auth: tuple[str, str]) -> None:
    for name, path in GRAPHS.items():
        response = requests.put(
            f"{endpoint}/data",
            params={"graph": f"{BASE}/{name}"},
            data=path.read_bytes(),
            headers=RDF_XML,
            auth=auth,
            timeout=180,
        )
        _report("put", f"graph {name}", response, path)


def main(argv: list[str]) -> int:
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://127.0.0.1:3030/ds")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="admin")
    parser.add_argument(
        "--named-graphs",
        action="store_true",
        help="keep onto/data/links as separate named graphs instead of merging",
    )
    args = parser.parse_args(argv[1:])

    auth = (args.user, args.password)
    if args.named_graphs:
        load_named(args.endpoint, auth)
    else:
        load_default(args.endpoint, auth)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
