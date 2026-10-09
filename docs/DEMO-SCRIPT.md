# 5-minute video demo — script & actions

A shot-by-shot teleprompter for recording the project demo. Times are targets;
total **5:00**. Say the bold lines; do the on-screen actions in between.

- Project: **DrinkOnto** — a 5★ Linked Open Data app for cocktails, spirits & distilleries.
- UI / endpoint: <http://localhost:8000>
- Public site: <https://nathantrance.github.io/SemanticWeb/>
- Repo: <https://github.com/NathanTrance/SemanticWeb>

---

## 0. Pre-flight (do this BEFORE you press record)

Open four things and leave them ready:

1. **Terminal** at the repo root (large font, clear history: `clear`).
2. **Browser tab A** → <http://localhost:8000>  (the query UI).
3. **Browser tab B** → <https://nathantrance.github.io/SemanticWeb/>  (public site).
4. **Protégé** (optional) → open `ontology/drinkonto.owl`, expand the class tree.

Make sure the local server is running (leave this running for the whole video):

```bash
.venv/Scripts/python web/server.py
# -> loaded 25342 triples
# -> Query UI:        http://localhost:8000/
# -> SPARQL endpoint: http://localhost:8000/sparql
# -> Dereference:     http://localhost:8000/id/cocktail/negroni
```

Optional (only if you want to show the standard Jena engine):

```bash
docker compose up -d
.venv/Scripts/python etl/load_fuseki.py
```

> Tip: test each command once off-camera so package caching / ports are warm.

---

## 1. Intro  (0:00 – 0:30)

**On screen:** the repo open at the README, or the UI.

**Say:**
> "This is DrinkOnto, our 5-star Linked Open Data application for the domain of
> cocktails, spirits and distilleries. It covers all five course requirements:
> an OWL ontology, data collected from public sources, RDF transformation,
> links to Wikidata and DBpedia, and a SPARQL query interface. Our graph has
> 441 cocktails, 865 distilleries and about 25,000 triples."

---

## 2. The ontology  (0:30 – 1:15)

**On screen:** Protégé with `ontology/drinkonto.owl`, or scroll the `.owl` file.

**Action:** expand the class tree; click `Cocktail`, show `Spirit` subclasses.

**Say:**
> "The ontology is OWL 2, written in RDF/XML. We reuse schema.org, Dublin Core,
> FOAF and SKOS wherever possible and only mint our own `drink:` terms.
> The interesting part is measures: each use of an ingredient is a
> `drink:IngredientAmount` node, and we declare an OWL **property chain** so
> `hasIngredient` is *inferred* from `usesIngredient` composed with
> `ofIngredient`. That is real OWL reasoning, not just a class hierarchy."

**Action:** if in Protégé, open the `hasIngredient` property and show the
property chain; else point at the axiom in the file.

---

## 3. Data collection + provenance  (1:15 – 2:00)

**On screen:** terminal.

**Action:** run
```bash
.venv/Scripts/python etl/bootstrap.py
```
(cached, so it prints "cache hit" lines — that's fine, it proves idempotency.)

**Say:**
> "We pull from two free sources: TheCocktailDB for cocktails and the Wikidata
> SPARQL endpoint for distilleries and brands. Everything is cached and recorded
> in a provenance manifest with the URL, licence, timestamp and a SHA-256 hash.
> One real finding: the plan's distillery identifier was wrong — it pointed at a
> street in the Netherlands — so we verified the correct Wikidata class,
> Q1251750, via the search API."

**Action:** open `data/raw/manifest.json` briefly to show the SHA-256 + licences.

---

## 4. Transformation to RDF (4★)  (2:00 – 2:40)

**On screen:** terminal, then the RDF file.

**Action:** run
```bash
.venv/Scripts/python etl/map.py
.venv/Scripts/python etl/validate_rdf.py
```

**Say:**
> "The transform turns the raw JSON into one RDF/XML graph, `data/rdf/data.rdf`,
> under stable IRIs like `.../id/cocktail/negroni`. It detects the base spirit
> with a small heuristic and parses measures into numeric values plus units.
> The validator confirms every RDF file parses cleanly."

**Action:** scroll the top of `data/rdf/data.rdf` to show real triples.

---

## 5. Interlinking to reach 5★  (2:40 – 3:25)

**On screen:** terminal, then `data/links/sample.csv`.

**Action:** run
```bash
.venv/Scripts/python etl/reconcile.py
```

**Say:**
> "To earn the fifth star we link to other people's data. Distilleries and
> brands carry a verified Wikidata QID from collection. For cocktails and
> ingredients we search the MediaWiki API, accept only exact-label matches, and
> score the description to reject homonyms like 'Gin the village'. Each match
> also yields the DBpedia IRI via the enwiki sitelink. We measured precision on
> a random sample of fifty links."

**Action:** open `data/links/sample.csv` and point at the `verified_true_false`
column.

---

## 6. Live SPARQL queries  (3:25 – 4:30)

**On screen:** browser tab A (UI at <http://localhost:8000>).

**Action:** pick a preset from the dropdown, press **Run query** (Ctrl+Enter).
Do these four, narrating each briefly:

| Preset | Say (short) |
|---|---|
| `02-iba-gin-and-lemon` | "IBA cocktails that use both gin and lemon juice." |
| `03-distilleries-near-edinburgh` | "Geospatial query: distilleries within 250 km of Edinburgh." |
| `05-five-star-proof-wikidata-and-dbpedia` | "Star-five proof: cocktails linked to **both** Wikidata and DBpedia." |
| `08-cocktails-per-spirit-type` | "Aggregation: cocktails grouped by spirit type — rum, gin, vodka." |

**Say:**
> "The same queries run unchanged on our Python endpoint and on Apache Jena
> Fuseki; we verified all eleven pass on both."

---

## 7. Dereferencing + wrap  (4:30 – 5:00)

**On screen:** browser tab B (GitHub Pages), then back to the terminal.

**Action:** open <https://nathantrance.github.io/SemanticWeb/> and click a
couple of entity links.

**Say:**
> "Our IRIs are dereferenceable. On the public site every IRI resolves to RDF;
> locally, the server does HTTP content negotiation — the same IRI returns
> RDF to a machine and an HTML page to a browser."

**Action (optional, strong closer):** in the terminal:
```bash
curl -H "Accept: text/turtle" http://localhost:8000/id/cocktail/negroni
```
Show it returns Turtle with `owl:sameAs` to Wikidata and DBpedia.

**Say:**
> "That's DrinkOnto: an OWL ontology, reproducible data collection, 4-star RDF,
> 5-star links with measured precision, and a SPARQL interface. Thank you."

---

## Command cheat-sheet (copy-paste)

```bash
# run the app
.venv/Scripts/python web/server.py            # UI + /sparql + dereferencing

# full pipeline (cached, safe to re-run)
.venv/Scripts/python etl/bootstrap.py
.venv/Scripts/python etl/map.py
.venv/Scripts/python etl/reconcile.py
.venv/Scripts/python etl/validate_rdf.py
.venv/Scripts/python etl/run_queries.py

# dereferencing proof
curl -H "Accept: text/turtle" http://localhost:8000/id/cocktail/negroni

# optional standard endpoint
docker compose up -d
.venv/Scripts/python etl/load_fuseki.py
.venv/Scripts/python etl/run_queries.py --endpoint http://127.0.0.1:3030/ds/sparql
docker compose down
```

---

## Recovery if something breaks on camera

- **UI won't load** → the server isn't running: `.venv/Scripts/python web/server.py`.
- **Query returns nothing** → make sure you're on the Python endpoint
  (`/sparql`), or reload Fuseki with `etl/load_fuseki.py`.
- **Fuseki slow/errors** → use `127.0.0.1`, never `localhost` (IPv6 adds ~20 s).
- **Pages looks stale** → re-run the **Deploy** workflow in GitHub → Actions.

## After recording

```bash
# stop the local server: close its terminal, or Ctrl+C
docker compose down        # only if you started Fuseki
```

Keep it under 5 minutes: the timings leave ~10 s of slack. Speak the bold lines
in your own words — you only need to *hit the five requirements*.
