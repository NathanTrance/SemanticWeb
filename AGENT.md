# AGENTS — working agreements for this repository

This is a Linked Open Data (LOD) capstone for a Masters "Semantic Web" course (HUST) — Project 1 (LOD application) for the domain **cocktails, spirits & distilleries**. Goal: a 5-star knowledge graph (RDF/OWL/SPARQL) with a SPARQL endpoint and a small query UI.

Read `PLANNING.md` first — it is the source of truth for scope, ontology, pipeline, and grading strategy.

## Current status
- W1–W3 done. Ontology (`ontology/drinkonto.owl`), instance data (`data/rdf/data.rdf`),
  links (`data/links/links.rdf`) and the SPARQL endpoint + UI (`web/`) are in place.
- 441 cocktails, 299 ingredients, 865 distilleries, 12 brands, ~1,220 `owl:sameAs`.
- Stack in use: Python 3 + RDFlib, `web/server.py` (rdflib endpoint + IRI
  dereferencing), Docker + Jena Fuseki as the standard endpoint (verified: the
  same 11 demo queries pass on both engines). IRIs dereference locally and on
  GitHub Pages.
- Todo: report/slides/video, fill `data/links/sample.csv` for the precision metric.

## Conventions
- **Directories:** `ontology/` (RDF/XML ontology + Protégé), `data/raw/` (fetched dumps, git-ignored), `data/rdf/` (generated RDF), `data/links/` (sameAs), `etl/` (Python), `queries/` (`.rq` demo queries), `web/` (query UI), `report/` (report/slides/video assets), `docs/` (provenance manifest, licence notes).
- **Vocabularies:** always reuse schema.org / dcterms / foaf / geo / owl; project-specific terms use the `drink:` namespace defined in `ontology/drinkonto.owl`. Do not mint IRIs that duplicate existing vocabularies.
- **RDF output format:** RDF/XML (`.owl` for the ontology, `.rdf` for data/links). Keep one file per named graph: `onto`, `data`, `links`. Other serializations (Turtle/JSON-LD/N-Triples) are generated on demand into `exports/`.
- **IRIs:** use the project base IRI from `PLANNING.md`; never put spaces/local IDs in IRIs; encode with percent-encoding where needed.
- **Code style:** Python 3.11+, minimal deps, type annotations on public functions, no comments unless they explain *why*. Keep scripts idempotent + rerunnable (cache fetches to `data/raw/`).
- **No scraping of review sites** (ratebeer/untappd etc.) — ToS risk. Only the documented sources in PLANNING §4.

## Quality gates (run before each commit/PR-size change)
1. Validate generated RDF: `python etl/validate_rdf.py` (rdflib parse check), or `riot --validate` if Jena is installed.
2. Run the demo queries from `queries/demo.rq`: `python etl/run_queries.py`; capture outputs if demo-critical.
3. Check links: a random sample of 50 `owl:sameAs` should resolve (≥90% precision target).
4. `git status` clean of secrets, dumps, venv, `__pycache__/`, Fuseki `run/`.

## Common commands
```bash
python -m venv .venv && .venv/Scripts/activate     # Windows venv
pip install -r requirements.txt
# zero-install endpoint + UI
.venv/Scripts/python web/server.py
# or the standard endpoint (Apache Jena Fuseki via Docker)
docker compose up -d && .venv/Scripts/python etl/load_fuseki.py
.venv/Scripts/python etl/run_queries.py --endpoint http://127.0.0.1:3030/ds/sparql
docker compose down
```

## Do / don't
- DO commit small, well-labeled RDF samples + provenance manifest; DON'T commit huge raw dumps (git-ignore, or commit a representative subset).
- DO cite data licences (CocktailDB non-commercial free, Wikidata CC0, Wikipedia/DBpedia CC BY-SA) in the report and README.
- DON'T edit `PLANNING.md` scope silently — scope freezes are decisions; call them out.

## GitHub workflow
- Branch per milestone (W1/W2/W3/W4), merge to `main` only at gates. Commit messages: `<what>: <why>`.
- Push decisions (repo name, public/private) belong to the repo owner (the student).