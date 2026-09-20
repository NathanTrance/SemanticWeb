"""Run queries/demo.rq against the merged graph and save the results.

Quality gate #2 from AGENT.md. Merges the ontology, data and links graphs
(the three named graphs) into one in-memory store, executes every query in
the demo file, prints a preview and writes the result to
report/query-results/<name>.csv (SELECT/ASK) or .rdf (CONSTRUCT/DESCRIBE),
so the report and slides can cite verified outputs.
"""

from __future__ import annotations

import csv
import re
import sys
import time
from pathlib import Path
from typing import Any, cast

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


def main() -> int:
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
    graph = load_graph()
    prologue, blocks = split_queries(QUERIES.read_text(encoding="utf-8"))
    RESULTS.mkdir(parents=True, exist_ok=True)
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
            output = RESULTS / f"{name}.rdf"
            result.serialize(destination=str(output), format="xml")
            print(f"OK   {name}  ({len(result)} triples, {elapsed:.0f} ms) -> {output.name}")
        elif result.type == "ASK":
            output = RESULTS / f"{name}.csv"
            output.write_text(f"askAnswer\n{result.askAnswer}\n", encoding="utf-8")
            print(f"OK   {name}  (ASK={result.askAnswer}, {elapsed:.0f} ms) -> {output.name}")
        else:
            rows = list(cast(Any, result))
            output = RESULTS / f"{name}.csv"
            with output.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow([str(var) for var in result.vars or []])
                for row in rows:
                    writer.writerow([format_cell(cell) for cell in row])
            print(f"OK   {name}  ({len(rows)} rows, {elapsed:.0f} ms) -> {output.name}")
            for row in rows[:3]:
                print("       " + " | ".join(format_cell(cell) for cell in row))
        print()

    print(f"{len(blocks) - failures}/{len(blocks)} queries succeeded")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
