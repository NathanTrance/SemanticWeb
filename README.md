# linked-drinks

5-star Linked Open Data for **cocktails, spirits & distilleries** — a Semantic
Web / LOD capstone (Masters, Hanoi University of Science and Technology,
Project 1). The graph is modelled in OWL 2, generated with Python + RDFlib,
linked to Wikidata and DBpedia, and served over a SPARQL endpoint with a small
query UI.

See [`PLANNING.md`](PLANNING.md) for the full plan and [`AGENT.md`](AGENT.md)
for the repo working agreements.

## What it contains

| Graph | File | Triples |
|---|---|---|
| Ontology (`drinkonto`) | `ontology/drinkonto.ttl` | ~190 |
| Instances | `data/rdf/data.ttl` | ~22,300 |
| Links (`owl:sameAs`) | `data/links/links.ttl` | ~2,800 |

Entities: **441 cocktails**, **299 ingredients**, **865 distilleries**, **12
brands**, **1,220 `owl:sameAs` links** (Wikidata + DBpedia).

## The five stars

1. **Open licence** — public repo; licences documented in [`docs/data-licences.md`](docs/data-licences.md).
2. **Structured data** — cached JSON dumps in `data/raw/` with a provenance manifest.
3. **Non-proprietary** — RDF Turtle in `data/rdf/` and `data/links/`.
4. **W3C standards** — RDF, RDF-S, OWL 2, SPARQL, IRIs (no local identifiers).
5. **Linked** — `owl:sameAs` to Wikidata (`CC0`) and DBpedia, with a precision-check sample.

## Pipeline

```
data/raw/  ->  etl/bootstrap.py  -> fetch CocktailDB + Wikidata (cached, manifest)
           ->  etl/map.py        -> data/rdf/data.ttl
           ->  etl/reconcile.py  -> data/links/links.ttl + sample.csv
           ->  web/server.py     -> SPARQL endpoint + query UI
```

## Quickstart

```bash
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt

python etl/bootstrap.py          # download sources (idempotent)
python etl/map.py                # raw JSON -> Turtle
python etl/reconcile.py          # owl:sameAs to Wikidata/DBpedia
python etl/validate_rdf.py       # parse-check every .ttl
python etl/run_queries.py        # run demo queries, save report outputs

python web/server.py             # http://localhost:8000  (UI + /sparql)
```

Optional "standard" endpoint (Apache Jena Fuseki via Docker):

```bash
docker compose up -d
python etl/load_fuseki.py        # loads onto/data/links as named graphs
# UI at web/ -> set Endpoint to http://localhost:3030/ds/sparql
```

## Repo layout

```
ontology/     drinkonto.ttl (Protégé-compatible)
data/raw/     cached source dumps + manifest.json (dumps git-ignored)
data/rdf/     generated instance graph
data/links/   owl:sameAs links + precision sample
etl/          bootstrap / map / reconcile / validate / run_queries / load_fuseki
queries/      demo.rq (11 curated SPARQL queries)
web/          zero-install SPARQL endpoint + UI
report/       query-result outputs, report/slides/video assets
docs/         provenance and licence notes
```

## Delivery

Slide deck, report (≤15 pages) and video (3–5 min) live under `report/`.
