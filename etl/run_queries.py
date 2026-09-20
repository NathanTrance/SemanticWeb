"""Run queries/demo.rq and save the results (quality gate #2 from AGENT.md).

By default the three graphs are merged into one in-memory rdflib store. Pass
`--endpoint` to run the exact same queries against a live SPARQL endpoint
(e.g. Fuseki) instead - this is how we prove the demo queries are portable.

Outputs go to report/query-results/<name>.csv (SELECT/ASK) or .rdf (CONSTRUCT),
so the report and slides can cite verified outputs.

    python etl/run_queries.py
    python etl/run_queries.py --endpoint http://127.0.0.1:3030/ds/sparql
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path
from typing import Any, cast

import requests
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
QUERIES = ROOT / "queries" / "demo.rq"
RESULTS = ROOT / "report" / "query-results"
GRAPHS = [
    ROOT / "ontology" / "drinkonto.owl",
    ROOT / "data" / "rdf" / "data.rdf",
    ROOT / "data" / "links" / "links.rdf",
]
NAME_RE = re.compile(r"^#\s*name:\s*(.+?)\s*$", re.MULTILINE)


def load_graph() -> Graph:
    graph = Graph()
    for path in GRAPHS:
        graph.parse(path)
    return graph


def split_queries(text: str) -> tuple[str, list[tuple[str, str]]]:
    parts = NAME_RE.split(text)
    prologue = parts[0].strip()
    blocks = [(parts[i], parts[i + 1].strip()) for i in range(1, len(parts), 2)]
    return prologue, blocks


def format_cell(value: object) -> str:
    return "" if value is None else str(value)


def run_local(blocks: list[tuple[str, str]], prologue: str, out: Path) -> int:
    graph = load_graph()
    print(f"loaded {len(graph)} triples; running {len(blocks)} queries\n")
    failures = 0
    for name, body in blocks:
        query = f"{prologue}\n\n{body}"
        started = time.perf_counter()
        try:
            result = graph.query(query)
        except Exception as exc:
            failures += 1
            print(f"FAIL {name}: {exc}\n")
            continue
        elapsed = (time.perf_counter() - started) * 1000

        if result.type in ("CONSTRUCT", "DESCRIBE"):
            output = out / f"{name}.rdf"
            result.serialize(destination=str(output), format="xml")
            print(f"OK   {name}  ({len(result)} triples, {elapsed:.0f} ms) -> {output.name}")
        elif result.type == "ASK":
            output = out / f"{name}.csv"
            output.write_text(f"askAnswer\n{result.askAnswer}\n", encoding="utf-8")
            print(f"OK   {name}  (ASK={result.askAnswer}, {elapsed:.0f} ms) -> {output.name}")
        else:
            rows = list(cast(Any, result))
            output = out / f"{name}.csv"
            with output.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow([str(var) for var in result.vars or []])
                for row in rows:
                    writer.writerow([format_cell(cell) for cell in row])
            print(f"OK   {name}  ({len(rows)} rows, {elapsed:.0f} ms) -> {output.name}")
            for row in rows[:3]:
                print("       " + " | ".join(format_cell(cell) for cell in row))
        print()
    return failures


def run_remote(blocks: list[tuple[str, str]], prologue: str, endpoint: str, out: Path) -> int:
    print(f"endpoint {endpoint}; running {len(blocks)} queries\n")
    failures = 0
    for name, body in blocks:
        query = f"{prologue}\n\n{body}"
        started = time.perf_counter()
        try:
            response = requests.post(
                endpoint,
                data={"query": query},
                headers={"Accept": "application/sparql-results+json, text/turtle"},
                timeout=120,
            )
            response.raise_for_status()
        except Exception as exc:
            failures += 1
            print(f"FAIL {name}: {exc}\n")
            continue
        elapsed = (time.perf_counter() - started) * 1000
        content_type = response.headers.get("content-type", "")

        if "json" in content_type:
            payload = response.json()
            if "boolean" in payload:
                output = out / f"{name}.csv"
                output.write_text(
                    f"askAnswer\n{payload['boolean']}\n", encoding="utf-8"
                )
                print(f"OK   {name}  (ASK={payload['boolean']}, {elapsed:.0f} ms) -> {output.name}")
            else:
                variables = payload["head"]["vars"]
                bindings = payload["results"]["bindings"]
                output = out / f"{name}.csv"
                with output.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(variables)
                    for binding in bindings:
                        writer.writerow(
                            [binding.get(var, {}).get("value", "") for var in variables]
                        )
                print(f"OK   {name}  ({len(bindings)} rows, {elapsed:.0f} ms) -> {output.name}")
                for binding in bindings[:3]:
                    print("       " + " | ".join(
                        binding.get(var, {}).get("value", "") for var in variables
                    ))
        else:
            output = out / f"{name}.ttl"
            output.write_text(response.text, encoding="utf-8")
            print(f"OK   {name}  (RDF result, {elapsed:.0f} ms) -> {output.name}")
        print()
    return failures


def main(argv: list[str]) -> int:
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="", help="SPARQL endpoint to query")
    parser.add_argument("--out", default=str(RESULTS))
    args = parser.parse_args(argv[1:])

    prologue, blocks = split_queries(QUERIES.read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.endpoint:
        failures = run_remote(blocks, prologue, args.endpoint, out)
    else:
        failures = run_local(blocks, prologue, out)
    print(f"{len(blocks) - failures}/{len(blocks)} queries succeeded")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
