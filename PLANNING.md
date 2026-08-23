# PLANNING — LOD Capstone: Cocktails, Spirits & Distilleries

Status: DRAFT 0.1 (approve before building) · Course: Semantic Web / Linked Open Data (Masters, HUST) · Type: LOD application (Project 1)

## 0. TL;DR

Build a 5-star **Linked Open Data** knowledge graph about the world of drinks:

- **Cocktails** (IBA classics + modern), their **ingredients**, **glassware**, and **measures**
- **Spirits** (gin, whisky, rum, vodka, tequila, …) and their **flavor/style categories**
- **Brands** and the **distilleries** that make them, with **locations** (geospatial)

Everything exposed via a SPARQL endpoint + a small web query UI. Deliverables: slide deck, ≤15-page report, 3–5 min video.

**Why this domain (duplication-proof):**
With 30–40 class groups, football/Vietnamese-football/education/health are crowded. Drinks is niche, fun, and **visually great for demos** (images, maps, recipes). Crucially, the data is unusually clean:

| Aspect | Why it's easy here |
|---|---|
| Cocktail data | TheCocktailDB gives a free, structured JSON API (IBAs flagged) |
| Spirit/distillery data | Wikidata SPARQL query returns thousands of items, many with lat/long |
| 5★ linking | Almost every cocktail/spirit/brand/distillery already exists in Wikidata/DBpedia → `owl:sameAs` is nearly free |
| Course tie-in | The course covers XML — CocktailDB's raw data maps naturally onto XML you then transform to RDF |

---

## 1. Course requirements → how we satisfy them

| # | Requirement | Our answer |
|---|---|---|
| 1 | Define an ontology | `drinkonto:` in `ontology/drinkonto.ttl` — build in Protégé, reuse schema.org/FOAF/dcterms/GeoSPARQL |
| 2 | Collect relevant data | CocktailDB API + Wikidata SPARQL + Wikipedia/DBpedia |
| 3 | Transform to **4★** | pipelined RDF transformation (Python/RDFlib) → dereferenceable HTTP URIs, valid parseable RDF |
| 4 | Link for **5★** | reconciliation to Wikidata/DBpedia → `owl:sameAs` + provenance; measure quality |
| 5 | Query interface | Apache Jena Fuseki SPARQL endpoint + tiny web app |

**5★ cheat-sheet (https://5stardata.info):**
- ★1: make stuff available on the Web (open licence) — our GitHub repo + static site
- ★2: machine-readable structured data — JSON/CSV dumps in `data/raw/`
- ★3: non-proprietary format — `data/rdf/*.ttl` (Turtle/RDF)
- ★4: use open standards from W3C — RDF, RDF-S, OWL, SPARQL (IRIs, no local identifiers)
- ★5: link to other people's data — `owl:sameAs` to Wikidata/DBpedia, proved reachable in the report

---

## 2. Scope (agreed in/out)

**IN**
- ~200 cocktails (IBA classics + popular modern) with ingredients, measures, glass, prep instructions, images, tags
- ~30–60 spirits (brands) across 8 spirit types
- ~80–150 distilleries (whisky/gin/rum focus) with coordinates + country
- Ingredient/vocabulary nodes (e.g. Angostura bitters) to support graph queries
- Links to Wikidata (QIDs) and DBpedia (resource IRIs)
- SPARQL endpoint + read-only query UI

**OUT (defer / explicitly cut)**
- No bars/restaurants, no reviews/ratings
- No live crawl of ratebeer/untappd/BGG-like review sites (ToS risk) — we do NOT scrape them
- No federated queries (we just publish links)
- No auth/multi-user — demo tool only

---

## 3. Ontology plan (`ontology/drinkonto.ttl`)

Build in Protégé. **Prefer reuse, add minimally.**

**Reused vocabularies**
| Prefix | Namespace | Used for |
|---|---|---|
| schema | http://schema.org/ | `schema:Beverage`, `schema:name`, `schema:image`, `schema:description`, `schema:alcoholContent` |
| dcterms | http://purl.org/dc/terms/ | `dcterms:title`, `dcterms:source`, `dcterms:license`, `dcterms:creator` |
| foaf | http://xmlns.com/foaf/0.1/ | `foaf:name`, `foaf:homepage`, `foaf:depiction` |
| geo | http://www.w3.org/2003/01/geo/wgs84_pos# | `geo:lat`, `geo:long` |
| owl | http://www.w3.org/2002/07/owl# | `owl:sameAs`, `owl:Class`, `owl:equivalentClass` |
| rdf/rdfs | http://www.w3.org/1999/02/22-rdf-syntax-ns# ... | `rdf:type`, `rdfs:label`, `rdfs:subClassOf`, `rdfs:comment` |

**Custom namespace (proposed):** `https://fizzology.example.org/onto#` → prefix `drink:`
> Note: pick your own base IRI. A real, resolvable domain is a nice-to-have for ★4 dereferenceability (see §12 – cost ~$10/yr).

**Classes**
| Class | Superclass | Notes |
|---|---|---|
| `drink:Cocktail` | schema:Beverage | IBA flag + glass + prep |
| `drink:Spirit` | schema:Beverage | e.g. Gin, Whisky, Rum … |
| `drink:Ingredient` | owl:Class | e.g. Angostura bitters, lemon juice |
| `drink:Brand` | owl:Class | e.g. Bombay Sapphire, Glenfiddich |
| `drink:Distillery` | owl:Class | geo data + country + founded year |
| `drink:GlassType` | owl:Class | Coupe, Highball, … |
| `drink:FlavorProfile` | owl:Class | dry, sweet, herbal, citrusy |

**Key object/data properties**
| Property | Domain → Range |
|---|---|
| `drink:hasIngredient` | Cocktail → Ingredient |
| `drink:baseSpirit` | Cocktail → Spirit |
| `drink:servedIn` | Cocktail → GlassType |
| `drink:producedBy` | Brand → Distillery |
| `drink:locatedIn` (≡ dcterms:spatial) | Distillery → place |
| `drink:producedBy` / `drink:brandOf` | Spirit ↔ Brand |
| `drink:countryOfOrigin` | owl:Class (or reuse schema:countryOfOrigin) |
| `drink:aboutABV` (xsd:decimal) | spirit strength % |
| `drink:measure` (e.g. "30 ml", "1 dash") | Cocktail → xsd:string, *attribute of the ingredient edge* |

**Design decision — measures:** attach `drink:measure` on the Cocktail→Ingredient **edge** (blank node or reification-lite via a `drink:Measure` node), so we can answer "how much lemon in a Whiskey Sour?" in SPARQL. Simpler alternative: `drink:hasIngredient` + `drink:hasMeasure` data property on Cocktail with ordinal — decide in Step 2b.

---

## 4. Data sources & acquisition

| Source | What we take | Access | Licence note |
|---|---|---|---|
| **TheCocktailDB API** | Cocktails: id, name, IBA flag, glass, instructions, ingredients 1–15, measures 1–15, image, tags | Free tier (`strDrink` filter endpoints; no heavy scraping) | Personal/non-commercial free; fine for coursework — *document licence in report* |
| **Wikidata SPARQL** (`query.wikidata.org`) | Distilleries (P31 Q18979992) with coords P625, brands, spirit items, article links | Public SPARQL endpoint | CC0 |
| **Wikipedia / DBpedia** | Classic cocktail articles (Old Fashioned, Negroni …), short descriptions, images | DBpedia SPARQL endpoint | CC BY-SA (cite) |
| **Reconciliation** | Match our labels → Wikidata QIDs / DBpedia resources | Wikidata Reconcile Service / MediaWiki API | free |

**Golden rule:** cache everything we fetch under `data/raw/` with a small manifest (`sources.ttl` / CSV), so the pipeline is reproducible and the report can show provenance (★4/5 evidence).

---

## 5. Build pipeline (steps you will implement, in order)

```
data/raw/   (fetched dumps/JSON/CSV)
    ↓  1. bootstrap.py  — pull CocktailDB + Wikidata SPARQL results, write to data/raw
    ↓  2. clean/validate (dedupe, normalize names, map ingredient synonyms, add WB/DB IRIs)
    ↓  3. transform → RDF  (map.py  → data/rdf/*.ttl, our IRI scheme, triples to ontology)
    ↓  4. reconcile + link  (reconcile.csv / OpenRefine → owl:sameAs to WD/DBpedia; optional Silk/LIMES)
    ↓  5. load into Fuseki (data/drinkonto.ttl + data/rdf/*.ttl) → SPARQL endpoint
    ↓  6. query UI (web app → endpoint) + screenshot/verified demo queries
```

Tooling: **Python 3 + RDFlib** (bootstrap/map), **OpenRefine + Wikidata Reconcile Service** for linking (low-code, looks good in report), **Apache Jena Fuseki** as SPARQL server, **Protégé** for ontology editing, optional **Docker** to containerize the endpoint.

---

## 6. Interlinking strategy (the ★5 money-shot)

Two layers:

1. **Explicit alignment (bulk of the work):**
   - Run label/alias matching against Wikidata via the **Reconcile Service** (or MediaWiki API) to get QIDs; map Wikipedia title ↔ DBpedia resource IRI for the same entity.
   - Emit `owl:sameAs <https://www.wikidata.org/wiki/Q…>`, `owl:sameAs <http://dbpedia.org/resource/…>` triples with provenance (`dcterms:source`, `prov:wasDerivedFrom`).
2. **Optional fuzzy layer (bonus mark):**
   - Use **Silk (LODES)** or **LIMES** on a subset (distilleries via name+country+coords similarity) to demonstrate tool-based linking; report precision/recall on a hand-checked gold sample.

**Quality metric for the report:** take a random sample of 50 links, manually verify 40 via *lookup*. Report precision (>=90% target). This one number proves ★5.

---

## 7. Storage & SPARQL endpoint

- **Apache Jena Fuseki** (works on Windows, just add Java + run `fuseki server`; or Docker `stainless/jena-fuseki`).
- Load graphs: `onto:` (ontology), `data:` (instances), `links:` (sameAs).
- Configure **dereferencing** demo: Fuseki + a tiny content-negotiation wrapper (or TDB2 + a static `.htaccess`/server rule) so IRIs resolve — screenshot in report as ★4 evidence.

**Demo queries ready in `queries/demo.rq`** (aim for 8–12 that showcase RDF-S/OWL/GeoSPARQL):
1. All cocktails with their glass + base spirit (basic 3-branch join)
2. "Give me every IBA cocktail containing lemon juice + gin, sorted by name"
3. "Find all distilleries within 250 km of Edinburgh" (geospatial via Wikidata coords)
4. "Show me the ingredient sharing graph — which cocktails share ≥3 ingredients with a Negroni"
5. "Which whiskies link (`owl:sameAs`) to a DBpedia resource?" (proves 5★)
6. A `CONSTRUCT` extracting a mini-graph of one cocktail (RDF round-trip demo)
7. One that uses the custom ontology class hierarchy (`rdfs:subClassOf` inference, needs OWL reasoner / `owl:sameAs` closure)
8. Aggregation: count cocktails per spirit type (proves GROUP BY/aggregates)

---

## 8. Interface (reachable deliverable)

Minimal but presentable:
- **Backend:** Fuseki SPARQL endpoint (HTTPS optional).
- **Frontend:** single-page app (static HTML/JS) with a query box, preset demo queries, and simple result table/json viewer. Optional: leaflet map of distilleries using coords.
- Host for free/demo: GitHub Pages for UI + a free-tier VM (or localhost during demo) for Fuseki.

---

## 9. Tools & install (Windows dev machine — you)

| Tool | Purpose | Install |
|---|---|---|
| Python 3.11+ | ETL (RDFlib, requests, pandas) | python.org or winget |
| OpenRefine | reconciliation → QIDs | openrefine.org (zip) |
| Apache Jena Fuseki | SPARQL server | fuseki.apache.org (zip, needs Java 17) |
| Protégé | ontology editor | protege.stanford.edu (needs Java) |
| Docker (optional) | containerize endpoint | Docker Desktop |
| silk/limes (optional) | fuzzy linking bonus | jar via repo |

Verify with: `python --version`, `java -version`, then prototype step 2b.

---

## 10. Compute & external resources (cost/needs — your question)

**Essentially $0.** This is a laptop-scale project; even a modest machine (8 GB RAM) is overkill for the dataset size.

| Resource | Need it? | Cost |
|---|---|---|
| Local laptop + Java 17 + Python | yes | free (you have it) |
| Wikidata SPARQL endpoint | read-only access | free, public, rate-limited |
| DBpedia SPARQL endpoint | read-only access | free, public |
| TheCocktailDB API | free tier | free (register), ~respect rate limits |
| Protégé / Fuseki / OpenRefine / RDFlib | all open source | free |
| GitHub (code + UI via Pages) | yes | free (public repo) |
| Always-on SPARQL endpoint | only for final demo | **free-tier options:** Oracle Cloud Always Free VM / AWS/CSP free tier / Fly.io — or demo on `localhost` and record the video. A cheap VPS is ~$5/mo, optional |
| Custom domain for pretty IRIs (★4 deref) | optional, only if you want IRIs to resolve to a domain | ~$10/yr (e.g. Namecheap) — can also use free `github.io`/`vercel.app` subdomain |

> "Funding" is not a concern — the real investment is **time**, not money.

---

## 11. Timeline (evenings + weekends, ~10–12 h/wk → ~4 weeks)

| Week | Milestone | Definition of done |
|---|---|---|
| **W1** | Foundation | W1: ONTOLOGY v1 in Protégé (classes/props) saved to `ontology/`; `data/raw` populated; bootstrap.py fetches CocktailDB + Wikidata; decide measure-model (2b). |
| **W2** | 4★ | map.py outputs valid Turtle for all entities; `riot --validate` passes; IRIs unique + use our scheme; raw dumps + provenance manifest committed. |
| **W3** | 5★ | reconciliation done (QIDs+DBpedia IRIs); `owl:sameAs` triples loaded; precision sample measured (≥90%); optional Silk/LIMES subset. |
| **W4** | Deliver | Fuseki endpoint + web UI live; 8 demo queries verified with screenshots; draft report, slides, video script; GitHub repo polished (README, LICENSE, diagrams); internal review. |

**Checkpoint gates:** after each week, run the demo queries; if `riot --validate` or queries fail, fix before advancing.

---

## 12. Report outline (≤15 pages)

1. Introduction & motivation (2–3) … 2. Background: 5★ open data, RDF/RDF-S/OWL/SPARQL/RIF/XML as used (3–4) … 3. Ontology design + reuse decisions (2–3) … 4. Data collection & ETL (2) … 5. Interlinking & quality evaluation (2–3) … 6. SPARQL endpoint + UI + demo queries (1–2) … 7. Lessons learned + future work (1) … References (licensed sources).

## 13. Slide deck outline (10–12 slides)

Title · Problem & 5★ recap · Domain choice · Ontology diagram (screenshot) · Data sources · Pipeline diagram · Linking results (numbers) · Endpoint demo (screencap) · Demo query video burst · Evaluation · Future work · Q&A.

## 14. Video script outline (3–5 min)

Hook (why linked data for drinks) → 30s ontology → 60s pipeline → 60s live SPARQL demos (3 queries incl. a map) → 30s linking/★5 proof → 30s UI → 30s wrap.

---

## 15. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| CocktailDB rate limits / API shape change | medium | cache everything to `data/raw` early; single bootstrap pass |
| Field duplication (another group also picks drinks) | low | niche; grab repo name + one-paragraph scope doc early |
| Reconcile precision (label clashes) | medium | validate sample; keep gold sample in repo |
| Time overrun (job pressure) | medium | freeze scope (see §2); everything after W2 is optional polish |
| OWL reasoning quirks in queries | low | keep reasoner demos optional; plain SPARQL always works |

---

## 16. Grading / marks strategy

1. **Finish every requirement** — a working 5★ endpoint + UI guarantees the base.
2. **Visible artifacts:** runnable repo, LICENSE with data licences, README with screenshots, the 8 demo queries with outputs.
3. **One strong number:** aim ≥90% link precision on a hand-checked sample (this is what a grader can *verify*).
4. **Polish, not volume:** a smaller graph that is clean/valid beats a huge messy one; graders weight correctness.
5. **De-risked domain choice** is itself a talking point in the intro (why not football → why drinks).

---

## 17. Repo hygiene & GitHub

- Public repo (free, portfolio value). Create with a good name, e.g. `linked-drinks` / `spirit-graph` / `cocktail-lod`.
- `AGENTS.md` documents conventions for agent-assisted development (this project already uses one).
- Structure: `ontology/`, `data/raw|rdf|links`, `etl/`, `queries/`, `web/`, `docs/`, `report/`.
- `.gitignore`: `data/raw/*.json` dumps (or commit a sample + manifest), `venv/`, `.venv/`, `__pycache__/`, Fuseki `run/`, `node_modules/`.

### Create & push (one time)
```bash
# 1. create repo once (title your language — use your own account name)
gh repo create linked-drinks --public --source=. --remote=origin --description "5-star Linked Open Data for cocktails, spirits & distilleries"

# 2. or WITHOUT gh CLI: create the repo in the GitHub web UI (empty, no README), then:
git remote add origin https://github.com/<yourname>/linked-drinks.git
git branch -M main
git push -u origin main
```

---

## References
- 5-star open data: https://5stardata.info/en/
- Silk (LODES): https://silkframework.org
- LOD cloud: https://lod-cloud.net
- DBpedia SPARQL: https://www.dbpedia.org/resources/sparql/
- Wikidata SPARQL: https://query.wikidata.org · Reconcile service: https://www.wikidata.org/wiki/Wikidata:Reconcile
- TheCocktailDB: https://www.thecocktaildb.com/docs.php
- FOAF: http://xmlns.com/foaf/0.1/ · schema.org · dcterms · GeoSPARQL: https://www.ogc.org/standard/geosparql/