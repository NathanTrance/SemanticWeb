"""Load the three RDF/XML graphs into a running Jena Fuseki dataset.

Uses the SPARQL 1.1 Graph Store Protocol (one PUT per named graph), so the
ontology, instance data and links land in separate graphs that can also be
queried together. Companion to docker-compose.yml:

    docker compose up -d
    python etl/load_fuseki.py --endpoint http://localhost:3030/ds \
        --user admin --password admin
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://nathantrance.github.io/SemanticWeb/graph"
GRAPHS = {
    f"{BASE}/onto": ROOT / "ontology" / "drinkonto.owl",
    f"{BASE}/data": ROOT / "data" / "rdf" / "data.rdf",
    f"{BASE}/links": ROOT / "data" / "links" / "links.rdf",
}


def main(argv: list[str]) -> int:
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://localhost:3030/ds")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="admin")
    args = parser.parse_args(argv[1:])

    for graph, path in GRAPHS.items():
        response = requests.put(
            f"{args.endpoint}/data",
            params={"graph": graph},
            data=path.read_bytes(),
            headers={"Content-Type": "application/rdf+xml"},
            auth=(args.user, args.password),
            timeout=180,
        )
        status = "OK " if response.ok else "FAIL"
        print(f"{status} {graph}  ({response.status_code})  <- {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
