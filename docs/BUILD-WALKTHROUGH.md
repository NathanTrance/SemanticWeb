# Build walkthrough — from scratch to 5★ Linked Open Data

This document explains **how the project was built, step by step, and why each
decision was made**. Read it top to bottom once to grasp the ideas; then use it
as a script for the presentation / viva.

- Repo: `https://github.com/NathanTrance/SemanticWeb`
- Domain: cocktails, spirits & distilleries
- Base IRI: `https://nathantrance.github.io/SemanticWeb/`
- Ontology namespace (`drink:`): `https://nathantrance.github.io/SemanticWeb/onto#`
- Entity IRIs: `https://nathantrance.github.io/SemanticWeb/id/<type>/<slug>`

---

## 1. What we are building (and the 5-star model)

The course asks for a **Linked Open Data (LOD) application**: pick a domain,
define an ontology, collect data, publish it as RDF, link it to other datasets,
and expose it through SPARQL. The "5-star" scale (Tim Berners-Lee, 5stardata.info)
grades *how good* the published data is:

| Star | Meaning | How this project earns it |
|---|---|---|
| ★ | Available on the web under an open licence | Public GitHub repo + documented licences |
| ★★ | Machine-readable structured data | Raw JSON dumps + `manifest.json` |
| ★★★ | Non-proprietary format | RDF (RDF/XML `.owl`/`.rdf`) |
| ★★★★ | W3C open standards (RDF, SPARQL, IRIs) | OWL 2 ontology, SPARQL endpoint, global IRIs |
| ★★★★★ | Linked to other people's data | `owl:sameAs` to Wikidata + DBpedia |

The five course requirements map directly onto the pipeline:

| # | Requirement | Where it lives |
|---|---|---|
| 1 | Define an ontology | `ontology/drinkonto.owl` |
| 2 | Collect relevant data | `etl/bootstrap.py` → `data/raw/` |
| 3 | Transform to 4★ standard | `etl/map.py` → `data/rdf/data.rdf` |
| 4 | Link for 5★ | `etl/reconcile.py` → `data/links/links.rdf` |
| 5 | Query interface | `web/server.py` + `queries/demo.rq` |

---

## 2. Concept primer (read this first)

If you know these six ideas, the whole codebase makes sense.

**Triple.** RDF represents knowledge as subject–predicate–object statements,
e.g. *Negroni — has base spirit — Gin*. Everything is triples.

**IRI.** A global identifier for a "thing" — like a URL but it identifies an
entity, not necessarily a page. We mint our own (`.../id/cocktail/negroni`)
and reuse existing ones (`http://www.wikidata.org/entity/Q1401202`).

**Ontology.** The vocabulary/schema: which classes exist (Cocktail, Spirit,
Distillery) and which properties connect them (`hasIngredient`, `producedBy`).
It is the "database schema + dictionary" of the graph.

**Serialization (this is the `.owl` vs `.ttl` question).** RDF can be *written*
in several syntaxes — RDF/XML, Turtle, JSON-LD, N-Triples. They encode the
**same triples**; converting between them changes nothing semantically.

| File | Syntax | Notes |
|---|---|---|
| `.owl` (ours) | RDF/XML | Classic Protégé / "ontology file" extension |
| `.rdf` (ours) | RDF/XML | Same syntax, used for instance data |
| `.ttl` | Turtle | Compact, human-friendly; we can export it |
| `.jsonld` | JSON-LD | JSON-flavoured RDF |
| `.nt` | N-Triples | One triple per line |

> Key sentence for the lecturer: **"Turtle and RDF/XML are serializations, not
> different data models; the ontology is OWL 2 whichever syntax carries it."**

**OWL.** A W3C language for richer ontologies, built on RDF: class hierarchies
(`rdfs:subClassOf`), inverse properties (`owl:inverseOf`), and logical axioms
like property chains (`owl:propertyChainAxiom`), which a reasoner can use to
*infer* new triples.

**SPARQL.** The query language for RDF. `SELECT` returns rows (like SQL),
`CONSTRUCT` returns new RDF triples.

---

## 3. Repository layout

```
ontology/     drinkonto.owl        # the OWL 2 ontology (RDF/XML)
data/raw/     cached source dumps + manifest.json   # dumps git-ignored
data/rdf/     data.rdf             # generated instance graph (RDF/XML)
data/links/   links.rdf, sample.csv # owl:sameAs links + precision sample
etl/          Python pipeline: bootstrap / map / reconcile / validate /
              run_queries / export_formats / load_fuseki
queries/      demo.rq              # 11 curated SPARQL queries
web/          server.py, index.html, app.js, styles.css  # endpoint + UI
report/       query-result outputs, report/slides/video assets
docs/         data-licences.md, BUILD-WALKTHROUGH.md (this file)
```

---

## 4. Prerequisites

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # rdflib, requests
```

Only two Python dependencies. Java/Docker are optional (only for the Jena
endpoint). Everything else uses the standard library.

---

## 5. Step-by-step build

### Step 0 — Scaffold (`git` commit 1)

Create the folder skeleton, `.gitignore` (ignore the venv, raw dumps, `exports/`,
personal notes), `LICENSE` (MIT for code; data licences are separate), and
`requirements.txt`. **Why:** reproducibility and hygiene — a grader can clone
and run it.

---

### Step 1 — The ontology (`ontology/drinkonto.owl`)

This is the heart of the assignment, so we design it deliberately.

**Design principles**

1. **Reuse before inventing.** We import standard vocabularies:
   `schema.org` (Beverage, Brand, Organization, Place), `dcterms` (provenance),
   `foaf` (homepage, depiction), `geo` (lat/long), `skos` (flavour concepts).
   Only domain-specific terms get the `drink:` namespace.
2. **Separate types from instances.** `drink:Gin` is a *class*; the individual
   `id/spirit/gin` is its instance. Cocktails point at the individual, so we
   avoid OWL "punning" (using one IRI as both class and instance).
3. **Classes:** `drink:Cocktail`, `drink:Spirit` (+ 8 subclass spirit types),
   `drink:Ingredient`, `drink:IngredientAmount`, `drink:Brand`,
   `drink:Distillery`, `drink:GlassType`, `drink:FlavorProfile`.
4. **Properties:** `usesIngredient`, `ofIngredient`, `baseSpirit`, `servedIn`,
   `producedBy`/`produces`, `brandOf`/`hasBrand`, `locatedIn`,
   `countryOfOrigin`, plus datatype properties (`amountText`, `aboutABV`,
   `isIBA`, `preparation`, ...).

**The interesting modelling decision — measures.**
The hard question is *"how much lemon is in a Whiskey Sour?"*. A plain
`Cocktail → hasIngredient → Ingredient` edge cannot carry the measure. So each
ingredient use becomes a node:

```xml
<id/ingredient-amount/negroni/1> a drink:IngredientAmount ;
    drink:ofIngredient  id/ingredient/gin ;
    drink:amountText    "1 oz" ;
    drink:amountValue   1.0 ;
    drink:amountUnit    "oz" .
<id/cocktail/negroni> drink:usesIngredient <id/ingredient-amount/negroni/1> .
```

We then declare an **OWL 2 property chain** so that `hasIngredient` is *derived*
by a reasoner (or a SPARQL property path `usesIngredient/ofIngredient`):

```
drink:hasIngredient  owl:propertyChainAxiom ( drink:usesIngredient drink:ofIngredient )
```

**Why this is a good talking point:** it shows real OWL usage (not just
`rdfs:subClassOf`), it keeps measures queryable, and it answers the classic
"where does the amount live?" objection.

Open it in **Protégé**: File → Open → `ontology/drinkonto.owl`. You will see the
class tree and the property chain.

**Serialization note.** The file is RDF/XML (`.owl`) because that is the
conventional ontology format. `etl/export_formats.py` can emit the identical
triples as `.ttl`, `.jsonld` and `.nt` into `exports/` if you want to show the
"same data, different syntax" slide.

---

### Step 2 — Collect data (`etl/bootstrap.py`)

Two free sources:

- **TheCocktailDB** JSON API: we call the per-letter search endpoint
  (`search.php?f=a`…`z`,`0`…`9`) and deduplicate by `idDrink` → **441 cocktails**
  with ingredients and measures.
- **Wikidata SPARQL**: distilleries (`P31 wd:Q1251750`) with coordinates,
  country, inception, website, image, enwiki article → **865 distilleries**;
  and spirit brands (`P31/P279* wd:Q56139` with manufacturer a distillery) →
  **12 brands**.

**Design choices**

- **Cache everything** to `data/raw/` and skip on re-run unless `--force`.
  The pipeline is idempotent and reproducible.
- **Provenance manifest**: `data/raw/manifest.json` records URL, licence,
  timestamp, record count and a **SHA-256** per dump. This is direct ★1–★4
  evidence for the report.
- **A real bug we found:** the plan's "distillery" QID `Q18979992` is actually a
  *street in the Netherlands*. Querying the Wikidata search API showed the right
  class is **`Q1251750`**. Mentioning this shows you verified identifiers instead
  of trusting them.

```bash
.venv/Scripts/python etl/bootstrap.py
```

---

### Step 3 — Transform to RDF (`etl/map.py`, 4★)

Read the raw JSON and emit one instance graph `data/rdf/data.rdf` (RDF/XML).

Mapping rules:

- Cocktail → `id/cocktail/<slug>`, typed `drink:Cocktail`, labelled, given
  `dcterms:identifier`, `schema:image`, `drink:preparation`, `drink:isIBA`,
  `drink:servedIn` (glass), tags, and one `drink:IngredientAmount` node per
  ingredient.
- Ingredient → `id/ingredient/<slug>`, typed `drink:Ingredient`.
- We mint one **instance per spirit type** (`id/spirit/gin` a `drink:Gin`).
- **Base-spirit heuristic:** scan the ingredients in order and take the first
  whose tokens match a spirit keyword (`gin`, `whiskey`, `rum`, `cozumel`…).
  Simple, explainable, good enough (76 gin, 77 rum, …).
- **Slugify** makes deterministic IRIs and avoids collisions; the output is
  byte-stable (re-running produces the same file), so git diffs stay meaningful.
- **Measure parsing:** `parse_amount("1 1/2 oz") → (1.5, "oz")` using a small
  regex; prose measures like `"Juice of 1/2"` stay as `amountText` only.

```bash
.venv/Scripts/python etl/map.py
.venv/Scripts/python etl/validate_rdf.py        # parse-check (quality gate 1)
```

Result: ~22,300 triples.

---

### Step 4 — Interlink to Wikidata & DBpedia (`etl/reconcile.py`, 5★)

This is the "money-shot" for ★5.

- **Distilleries and brands link for free** — they already carry a Wikidata QID
  from collection (which we ourselves verified via `P31`).
- **Cocktails and ingredients** need reconciliation. For each label we call the
  **MediaWiki `wbsearchentities` API**, keep only candidates whose label matches
  ours **exactly**, and **score** the description:
  - reward type keywords (`cocktail`, `drink`, `juice`, `distilled`, …);
  - penalise homonyms (`family name`, `song`, `singer`, `number`, `http`, …);
  - cocktails must reach a higher threshold than ingredients (precision first).
- For each accepted QID we fetch the **enwiki sitelink** and mint the matching
  **DBpedia** IRI, so each entity gets two links:

```xml
<id/cocktail/negroni> owl:sameAs <http://www.wikidata.org/entity/Q1401202> ;
                      owl:sameAs <http://dbpedia.org/resource/Negroni> ;
                      dcterms:source <https://www.wikidata.org/wiki/Q1401202> .
```

- Output: `data/links/links.rdf` (~1,220 links) **plus `data/links/sample.csv`** —
  a seeded random sample of 50 links with a `verified_true_false` column.

**The precision number for your report.** Open `sample.csv`, check ~40 rows
against the QIDs in a browser, and compute *correct / checked*. This is the one
concrete, verifiable metric a grader can reproduce — aim for ≥90%.

```bash
.venv/Scripts/python etl/reconcile.py
```

---

### Step 5 — Query interface (`web/` + `queries/demo.rq`)

**Demo queries** (`queries/demo.rq`, 11 of them). Each block starts with
`# name:` so the runner can split them. They cover: multi-branch joins,
aggregation (`GROUP BY`), the ingredient-sharing graph, a `CONSTRUCT` round-trip,
the class hierarchy, a geospatial radius, measures, and the ★5 link proof.

Two practical gotchas we hit and fixed (good viva material):

- SPARQL **prefixed names cannot contain `/`**, so we added per-type prefixes
  (`c:negroni`, `ing:gin`) instead of `id:cocktail/negroni`.
- **Trigonometry is not portable.** Plain rdflib cannot parse `SIN`/`SQRT` at
  all, and Jena rejects the bare keywords too (it only exposes trig through the
  XPath `math:` namespace). So the Edinburgh radius query in `demo.rq` uses an
  equirectangular approximation with plain arithmetic and runs on both engines;
  the exact haversine lives in `queries/haversine-fuseki.rq` for Fuseki.

```bash
.venv/Scripts/python etl/run_queries.py     # writes report/query-results/*
```

**Endpoint + UI.** `web/server.py` is a zero-install SPARQL endpoint built on
`http.server` + rdflib:

- `POST /sparql` (or `GET /sparql?query=…`) with **content negotiation**:
  `application/sparql-results+json`, `…+xml`, or `text/turtle` for CONSTRUCT.
- Serves the static UI in `web/`, which loads `queries/demo.rq` as presets and
  renders results as a table (or raw response).

```bash
.venv/Scripts/python web/server.py
# open http://localhost:8000
```

**Standard endpoint (Apache Jena Fuseki).** `docker-compose.yml` starts Fuseki;
`etl/load_fuseki.py` loads the graphs (merged into the default graph by default,
or `--named-graphs` to keep onto/data/links separate). We verified the **same 11
demo queries pass on both engines** with `python etl/run_queries.py --endpoint
http://127.0.0.1:3030/ds/sparql`. Two practical notes: use `127.0.0.1` rather
than `localhost` (Windows resolves `localhost` to IPv6 first and Docker only
publishes IPv4, adding ~20 s per connection), and Jena evaluates trigonometry
via the XPath `math:` namespace (`queries/haversine-fuseki.rq`).

**IRI dereferencing (★4).** `web/server.py` also answers `GET /id/<type>/<slug>`
and `GET /onto` with **content negotiation**: the same IRI returns HTML to a
browser and RDF to a machine. `etl/build_site.py` generates a static twin for
GitHub Pages so the IRIs resolve publicly. Details and the honest caveat
(static Pages cannot negotiate) are in `docs/dereferencing.md`.

---

## 6. Run the whole pipeline from scratch

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python etl/bootstrap.py       # 1. collect (cached, manifest)
.venv/Scripts/python etl/map.py             # 2. JSON -> data.rdf
.venv/Scripts/python etl/reconcile.py       # 3. links.rdf + sample.csv
.venv/Scripts/python etl/validate_rdf.py    # 4. parse-check everything
.venv/Scripts/python etl/run_queries.py     # 5. verify the 11 queries
.venv/Scripts/python web/server.py          # 6. serve endpoint + UI
```

Expected numbers: **441 cocktails, 299 ingredients, 865 distilleries, 12 brands,
~1,220 `owl:sameAs`, ~25,300 triples** in the merged graph.

---

## 7. Demo script (5–6 minutes)

1. **Frame it (30s).** "Classic web = documents; semantic web = entities and
   relations. We built a 5★ knowledge graph of drinks."
2. **Ontology (60s).** Open `drinkonto.owl` in Protégé. Show the class tree, then
   the `IngredientAmount` + `owl:propertyChainAxiom` measure model.
3. **Pipeline (60s).** Run `map.py` and `reconcile.py`; show `manifest.json`
   and narrate the wrong-QID discovery.
4. **5★ proof (30s).** Run query 05 (entities linked to *both* Wikidata and
   DBpedia) and query 11 (all external links for the Negroni).
5. **Live SPARQL (90s).** In the UI: query 02 (IBA gin + lemon), query 03
   (distilleries near Edinburgh), query 08 (cocktails per spirit — `GROUP BY`),
   query 09 (measure in a Whiskey Sour).
6. **Wrap (30s).** Precision sample + limitations/future work.

---

## 8. Likely lecturer questions

- **"Why OWL and not just RDF?"** We use class hierarchies, inverse properties,
  and an OWL 2 property chain to *infer* `hasIngredient`; a plain RDF schema
  could not express that inference.
- **".owl or .ttl?"** Same triples, different serialization. Ours is RDF/XML;
  `export_formats.py` outputs Turtle/JSON-LD/N-Triples to prove it.
- **"How did you link?"** Exact-label matching + description scoring against the
  Wikimedia search API; distillery/brand links come from verified Wikidata
  `P31`; DBpedia IRIs via enwiki sitelinks. Precision measured on a 50-link
  sample.
- **"Is it really 5★?"** Map each star to an artifact (see §1 table); the
  manifest, the `.owl`, the SPARQL endpoint and `links.rdf` are the evidence.
- **"Why not federate live queries?"** Out of scope; we *publish* links
  (`owl:sameAs`) instead, which is what ★5 requires.
- **"Where's the XML link to the course?"** CocktailDB's native output is JSON;
  our transform is a syntactic/semantic mapping from structured source data to
  RDF — the same "syntax vs semantics" theme from the lectures.

---

## 9. Known limitations / future work

- **Link recall:** only ~90/441 cocktails found an exact Wikidata label match
  (precision chosen over recall). A fuzzy matcher (OpenRefine/Silk) would raise
  recall — good "future work" slide.
- **Dereferenceability (★4):** implemented. `web/server.py` negotiates
  (HTML/RDF) locally; `etl/build_site.py` + the Pages workflow publish the same
  descriptions publicly. Only remaining manual step is enabling Pages
  (Settings → Pages → Source = GitHub Actions). Note that static Pages cannot
  content-negotiate, so its extensionless RDF downloads rather than displaying as
  Turtle — the local server is the "correct" demonstration.
- **Base-spirit heuristic** can misfire on unusual recipes.
- **12 brands** is thin (Wikidata manufacturer coverage); brands could be
  enriched from another source.

---

## 10. Glossary

| Term | Meaning |
|---|---|
| RDF | Resource Description Framework; data as subject–predicate–object triples |
| IRI | Internationalized Resource Identifier; a global name for an entity |
| RDF/XML, Turtle, JSON-LD, N-Triples | Serializations of RDF (same triples) |
| Ontology | The vocabulary: classes + properties (here, OWL 2) |
| OWL 2 | W3C ontology language on top of RDF (hierarchies, inverses, property chains) |
| SPARQL | Query language for RDF (`SELECT`, `CONSTRUCT`, `ASK`) |
| Named graph | A graph identified by an IRI; we keep three (onto, data, links) |
| Reconciliation | Matching our entities to external identifiers (QIDs/DBpedia IRIs) |
| `owl:sameAs` | Asserts two IRIs denote the same real-world entity |
| Precision | Fraction of our links that are correct (measured on a sample) |
| Dereferenceable | An IRI that returns data when you fetch it |
