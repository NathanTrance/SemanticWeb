# Study guide — understanding the linked-drinks project from zero

This guide teaches the project **step by step**, assuming no prior Semantic Web
experience. It is a companion to the other docs:

| Document | Purpose |
|---|---|
| `docs/BUILD-WALKTHROUGH.md` | 5-minute viva script + design rationale |
| `PLANNING.md` | the original plan, written *before* building |
| `docs/STUDY-GUIDE.md` (this file) | learn the concepts, the code, and the evidence |
| `session-ses_f41c.md` | raw transcript of the AI-assisted build session |
| `AGENT.md` | repo conventions + quality gates |

**How to use it:** read in order; do the "Run it" boxes; answer the self-check
questions *before* looking at the answer key in §14. Total reading time is about
2–3 hours; each step alone is 20–30 minutes.

Numbers labelled **verified** were counted directly from the files in this repo;
numbers labelled **doc** come from `BUILD-WALKTHROUGH.md` / `README.md` and are
approximate.

---

## 1. The big picture

### 1.1 What problem are we solving?

The classic web links **documents** (a page about the Negroni links to a page
about gin). The Semantic Web links **entities**: it publishes facts about
*things* — cocktails, spirits, distilleries — in a machine-readable form, so
that data from different websites can be joined automatically.

Our project publishes a small knowledge graph of cocktails, then **bridges** it
to Wikidata and DBpedia with `owl:sameAs`. After that, a query can combine our
facts with theirs even though the three datasets were built independently. That
bridge is what "Linked Open Data" means, and it is what the ★★★★★ grade is
about.

### 1.2 The unit of data: the triple

RDF stores knowledge as **subject – predicate – object** statements, called
**triples**. One fact from this repo, in Turtle syntax (a compact RDF
serialization):

```ttl
<https://nathantrance.github.io/SemanticWeb/id/cocktail/negroni>
    <https://nathantrance.github.io/SemanticWeb/onto#baseSpirit>
    <https://nathantrance.github.io/SemanticWeb/id/spirit/gin> .
```

In words: *the Negroni — has base spirit — Gin*. A whole graph is just a big
set of these. There are no tables, no columns, no foreign keys — only triples.
When you query, you are searching for patterns of triples.

### 1.3 IRI: the global name of a thing

An **IRI** (Internationalized Resource Identifier) is a globally unique name.
It looks like a URL, but it identifies a *thing*, not necessarily a web page.
This project mints its own IRIs under one base:

| IRI | Identifies |
|---|---|
| `.../onto#Cocktail` | the *class* Cocktail (in the schema) |
| `.../id/cocktail/negroni` | the *individual* Negroni |
| `.../id/ingredient/gin` | the individual ingredient gin |
| `http://www.wikidata.org/entity/Q1401202` | the same Negroni in Wikidata (we did not mint it) |

Because IRIs are global, two datasets can refer to the same thing — or *assert*
they are the same thing with `owl:sameAs`.

### 1.4 Ontology: the schema + dictionary

An **ontology** declares which classes exist (`Cocktail`, `Distillery`) and
which predicates may connect them (`baseSpirit`, `producedBy`). It plays the
role of "database schema + controlled vocabulary". We use **OWL 2**, a W3C
language layered on RDF that can express richer axioms: class hierarchies
(`rdfs:subClassOf`), inverse properties (`owl:inverseOf`), and logical rules
like `owl:propertyChainAxiom`. See `ontology/drinkonto.owl` and §3 below.

### 1.5 Serialization: same triples, different spelling

RDF can be written in several syntaxes. They encode **identical triples**;
converting changes nothing semantically.

| Extension | Syntax | In this repo |
|---|---|---|
| `.owl`, `.rdf` | RDF/XML | canonical files |
| `.ttl` | Turtle | generated demo via `etl/export_formats.py` |
| `.jsonld` | JSON-LD | generated demo |
| `.nt` | N-Triples | generated demo |

> The one-sentence exam answer: **"Turtle and RDF/XML are serializations, not
> different data models; the ontology is OWL 2 whichever syntax carries it."**

### 1.6 The five stars and where they live

| Star | Meaning | Evidence in this repo |
|---|---|---|
| ★ | open licence, on the web | public GitHub repo, `LICENSE`, `docs/data-licences.md` |
| ★★ | machine-readable structured data | cached JSON in `data/raw/` + `manifest.json` |
| ★★★ | non-proprietary format | RDF (`ontology/drinkonto.owl`, `data/rdf/data.rdf`, `data/links/links.rdf`) |
| ★★★★ | W3C standards: RDF, OWL 2, SPARQL, IRIs | ontology axioms, 11 SPARQL queries, dereferenceable IRIs (`web/server.py`, `docs/dereferencing.md`) |
| ★★★★★ | linked to other people's data | `owl:sameAs` to Wikidata + DBpedia in `data/links/links.rdf` |

### 1.7 Architecture: three graphs, four tools

```
  TheCocktailDB API                Wikidata SPARQL endpoint
  (cocktails, JSON)                (distilleries, brands)
        \                              /
         \   etl/bootstrap.py (collect, cache, manifest)
          v                            v
         data/raw/*.json  (git-ignored dumps + manifest.json)
                |
                |  etl/map.py  (JSON -> RDF)
                v
  ontology/drinkonto.owl ---> data/rdf/data.rdf  (schema + instances, 3 graphs total)
                |
                |  etl/reconcile.py  (entity matching -> owl:sameAs)
                v
         data/links/links.rdf + data/links/sample.csv
                |
                |  queries/demo.rq -> etl/run_queries.py -> report/query-results/
                v
         web/server.py  (SPARQL endpoint + query UI + IRI dereferencing)
         or Apache Jena Fuseki via docker-compose.yml + etl/load_fuseki.py
```

The pipeline pattern is **collect → transform → link → serve**, which is the
classic ETL (extract/transform/load) idea applied to RDF.

### 1.8 Course requirements → where they are satisfied

| # | Requirement | Where |
|---|---|---|
| 1 | Define an ontology | `ontology/drinkonto.owl` |
| 2 | Collect relevant data | `etl/bootstrap.py`, `data/raw/manifest.json` |
| 3 | Transform to 4★ standard | `etl/map.py` → `data/rdf/data.rdf` |
| 4 | Link for 5★ | `etl/reconcile.py` → `data/links/links.rdf` |
| 5 | Query interface | `web/server.py` + `queries/demo.rq` |

### 1.9 Numbers you can quote

| Quantity | Value | Source / how to verify |
|---|---|---|
| Cocktails collected | 441 | `data/raw/manifest.json` (records) |
| Distillery rows collected | 998 | manifest |
| Distilleries in the graph | 865 | after dedup by QID in `map.py` |
| Brands | 12 | manifest |
| Instance graph size | ~22,300 triples (doc) | `python etl/validate_rdf.py` |
| Ontology size | ~190 triples (doc) | same |
| Links total `owl:sameAs` | **1,610 (verified)** | grep/python count, §10 |
| — of which Wikidata | **1,220 (verified)** | one per linked entity |
| — of which DBpedia | **390 (verified)** | only where an enwiki sitelink existed |
| Merged graph | ~25,300 triples (doc) | 190 + 22,300 + ~2,830 ≈ 25,320 |

> **Trap:** `README.md` says "1,220 `owl:sameAs` links". That is the number of
> *entities* linked to Wikidata; the file actually contains 1,610 `owl:sameAs`
> statements (1,220 Wikidata + 390 DBpedia). Quoting 1,610 with this
> explanation sounds precise in a viva; repeating 1,220 without it can be
> challenged.

### Self-check — big picture

- **Q1.1** In one sentence: what is a triple? Give an example from this repo.
- **Q1.2** What is the difference between the ontology, the instance graph, and the links graph?
- **Q1.3** Why keep them as three files instead of one merged blob?
- **Q1.4** Which file defines `drink:baseSpirit`, and which file contains the Negroni's base spirit?

---

## 2. Step 0 — scaffold (commits `a09df50`, `d652200`)

**Goal:** create a repo skeleton that a grader can clone and run.

**What the commits added**

| Commit | Message | Contents |
|---|---|---|
| `a09df50` | `scaffold: LOD capstone plan...` | `PLANNING.md` (the design doc), `AGENT.md`, `.gitignore`, `README.md` |
| `d652200` | `scaffold: repo layout, venv deps, LICENSE and ignore rules` | folders `ontology/ data/rdf data/links data/raw etl queries web report docs`, each with `.gitkeep`; `LICENSE`; `requirements.txt` |

**Why each piece exists**

- `requirements.txt` contains exactly two packages: `rdflib` (RDF parsing,
  querying, serializing) and `requests` (HTTP). Fewer dependencies = easier for
  a grader to install and less to explain.
- `.gitkeep` files are a git trick: git cannot track empty directories, so a
  placeholder file keeps the empty folder structure in the repo.
- `.gitignore` excludes `.venv/`, `__pycache__/`, downloaded raw dumps,
  `exports/`, and Fuseki runtime files. Rule of thumb: **generated or huge
  things are not committed; small deterministic outputs are** — that is why
  `data/rdf/data.rdf` and `data/links/links.rdf` *are* committed but the raw
  JSON dumps are not.
- `LICENSE`: MIT for code. Data lives under separate licences documented in
  `docs/data-licences.md` (CocktailDB: free non-commercial; Wikidata: CC0;
  DBpedia/Wikipedia: CC BY-SA).

**Concept box — reproducibility.** A pipeline is *idempotent* when re-running
it produces the same result. `bootstrap.py` caches downloads, `map.py` uses
deterministic slugs, `reconcile.py` samples with a fixed random seed. A grader
can therefore re-run everything and get the same numbers.

**Run it**

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

### Self-check — step 0

- **Q2.1** Why are there only two Python dependencies?
- **Q2.2** What is `.gitkeep` for?
- **Q2.3** `data/raw/manifest.json` is committed but the raw dumps are not. Why?
- **Q2.4** What must you run after a fresh clone before `etl/map.py` can work?

---

## 3. Step 1 — the ontology (`ontology/drinkonto.owl`, commits `605c9b1`, `3971bd9`)

**Goal:** define the vocabulary: 17 classes and 21 properties, reusing standard
vocabularies wherever possible.

### 3.1 Reading RDF/XML

One block = one subject and its facts:

```xml
<rdf:Description rdf:about=".../onto#baseSpirit">
  <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#ObjectProperty"/>
  <rdfs:domain rdf:resource=".../onto#Cocktail"/>
  <rdfs:range  rdf:resource=".../onto#Spirit"/>
  <rdfs:label  xml:lang="en">base spirit</rdfs:label>
</rdf:Description>
```

Read it as triples: *baseSpirit — rdf:type — owl:ObjectProperty*,
*baseSpirit — rdfs:domain — Cocktail*, etc. `rdfs:domain`/`rdfs:range` are the
schema's way of saying "this property starts at a Cocktail and points at a
Spirit".

### 3.2 Classes (verified from the file)

| Class | Superclass | Meaning |
|---|---|---|
| `drink:Beverage` | `schema:Beverage` | local umbrella class for cocktails + spirits |
| `drink:Cocktail` | `drink:Beverage` | a recipe: base spirit, ingredients, glass |
| `drink:Spirit` | `drink:Beverage` | a spirit *type* (gin, rum…) |
| `drink:Gin` … `drink:Absinthe` | `drink:Spirit` | 8 spirit subclasses: Gin, Whisky, Rum, Vodka, Tequila, Brandy, Liqueur, Absinthe |
| `drink:Ingredient` | `schema:Product` | juice, syrup, a specific brand used in a recipe… |
| `drink:IngredientAmount` | (none) | one ingredient's use in one cocktail, with the measure |
| `drink:Brand` | `schema:Brand` | Bombay Sapphire, Glenfiddich |
| `drink:Distillery` | `schema:Organization` | a production site |
| `drink:GlassType` | `schema:Product` | coupe, highball… |
| `drink:FlavorProfile` | `skos:Concept` | dry, sweet, herbal… |

**Design principle — reuse before inventing.** `schema.org` gives `Beverage`,
`Brand`, `Organization`, `Product`, `Place`; `dcterms` gives provenance
(`source`, `identifier`); `foaf` gives `homepage`/`depiction`; `geo` gives
`lat`/`long`; `skos` gives concepts. Only domain-specific terms get the `drink:`
namespace. A lecturer loves this: fewer invented terms = more interoperable
graph.

### 3.3 Object vs datatype properties

- **Object property** = points at another entity:
  `baseSpirit` (`:15`), `usesIngredient` (`:81`), `ofIngredient` (`:178`),
  `servedIn` (`:125`), `producedBy`/`produces` (`:22`/`:34`),
  `hasBrand`/`brandOf` (`:95`/`:241`), `locatedIn` (`:169`),
  `countryOfOrigin` (`:234`), `hasIngredient` (`:226`),
  `hasFlavorProfile` (`:156`).
- **Datatype property** = points at a literal value:
  `isIBA` boolean (`:8`), `hasTag` string (`:47`), `amountText` string (`:54`),
  `foundedYear` gYear (`:61`), `preparation` string (`:74`),
  `amountValue` decimal (`:256`), `amountUnit` string (`:249`), plus
  `garnish` (`:88`) and `aboutABV` decimal (`:191`).

### 3.4 Three OWL axioms to know

1. **Inverse properties.** `producedBy` and `produces` are declared inverses
   (`:22–39`); same for `brandOf`/`hasBrand` (`:95–101`, `:241–248`). A
   reasoner could infer one direction from the other.
2. **Sub-property.** `locatedIn` is declared a sub-property of both
   `dcterms:spatial` and `schema:location` (`:169–177`), so generic spatial
   queries written against the standard vocabularies still match our data.
3. **Property chain (the interesting one).** See below.

### 3.5 The measure model — the project's best talking point

*Problem:* a plain `Cocktail → Ingredient` edge cannot carry a measure. How much
gin is in a Negroni? The amount must live *on the relationship*, but RDF
relationships are bare predicates.

*Solution:* reify each ingredient use as a node of type `drink:IngredientAmount`
(designed at `:263–267`):

```ttl
id:ingredient-amount/negroni/1  a drink:IngredientAmount ;
    drink:ofIngredient id:ingredient/gin ;
    drink:amountText   "1 oz" ;
    drink:amountValue  1.0 ;
    drink:amountUnit   "oz" .

id:cocktail/negroni  drink:usesIngredient id:ingredient-amount/negroni/1 .
```

This pattern is sometimes called "reification-lite": not the heavy RDF
reification vocabulary, just an explicit intermediate node.

*Bonus:* now define a **property chain** (`:226–233`), read as "usesIngredient
followed by ofIngredient *is* hasIngredient":

```
drink:hasIngredient  owl:propertyChainAxiom  ( drink:usesIngredient drink:ofIngredient )
```

So a reasoner can *infer* `negroni hasIngredient gin` without anyone asserting
it. In this repo no reasoner is actually run — the same inference is
demonstrated by SPARQL property paths (`drink:usesIngredient/drink:ofIngredient`,
see queries 04 and 10). That is a defensible design: the axiom documents intent,
the query executes it.

**RDF list syntax decoded (why you see `rdf:first`/`rdf:rest`).** OWL property
chains are written as an ordered list, and RDF has no native lists, so the file
contains two helper blank nodes (`:30–33` and `:204–207`): one says "the list
starts with `ofIngredient` and the rest is nil"; the other says "the list starts
with `usesIngredient` and the rest is the first node". Read them backwards:
the chain is `(usesIngredient, ofIngredient)`.

### 3.6 Class vs instance (and "punning")

`drink:Gin` (class, in the ontology) and `id/spirit/gin` (individual, in the
data, generated by `map.py:218–224`) are **different IRIs**. If cocktails
pointed directly at the class `drink:Gin`, we would be using one IRI as both a
class and an instance — OWL "punning", a classic design smell. The lecturer can
ask about this; the answer is at `ontology/drinkonto.owl:119–124` and
`map.py:218–224`.

### 3.7 Serialization history (a real repo story)

The first ontology commit `605c9b1` created `ontology/drinkonto.ttl` (Turtle).
Commit `3971bd9` converted everything to RDF/XML (`.owl`/`.rdf`). Two stale
traces remain — harmless, but good to know:

- `ontology/drinkonto.owl:110` — `owl:versionIRI` still points to
  `.../drinkonto.ttl`.
- `etl/map.py:3` — docstring still says "terms defined in
  `ontology/drinkonto.ttl`".

`etl/export_formats.py` regenerates Turtle/JSON-LD/N-Triples from the canonical
RDF/XML, proving the conversion is lossless.

**Run it**

```bash
.venv/Scripts/python etl/validate_rdf.py            # parse-check (quality gate 1)
.venv/Scripts/python etl/export_formats.py          # Turtle/JSON-LD/N-Triples into exports/
# optional: open ontology/drinkonto.owl in Protege to see the class tree
```

### Self-check — step 1

- **Q3.1** What is the difference between `drink:Gin` and `id/spirit/gin`?
- **Q3.2** Why is `drink:IngredientAmount` needed instead of a direct
  `Cocktail → Ingredient` edge?
- **Q3.3** What does the property chain let you do, and why are there no
  `drink:hasIngredient` triples in `data.rdf`?
- **Q3.4** Is `.owl` a different data model from `.ttl`? Explain.
- **Q3.5** Which class do `Cocktail` and `Spirit` share as a superclass, and
  which standard vocabulary does it reuse?

---

## 4. Step 2 — collect the data (`etl/bootstrap.py`, commits `2505b50`, `126d1b1`)

**Goal:** download the two source datasets, cache them, and record provenance.

### 4.1 The two sources

| Source | What | How |
|---|---|---|
| TheCocktailDB | 441 cocktails with ingredients, measures, glass, IBA flag, image | JSON API, one request per character `a–z0–9` (`:115–125`) |
| Wikidata | 998 distillery rows + 12 brands | SPARQL queries (`:47–72`) |

Why 36 requests for cocktails? The free API only offers search endpoints; there
is no single "dump all" endpoint. The code loops and **deduplicates by
`idDrink`** (`:120–121`), which makes the result independent of duplicates
across letters.

### 4.2 Reading the Wikidata SPARQL queries

```sparql
SELECT ?d ?dLabel ?coord ?country ... WHERE {
  ?d wdt:P31 wd:Q1251750 .                # "?d is an instance of distillery"
  OPTIONAL { ?d wdt:P625 ?coord . }       # coordinates, if any
  OPTIONAL { ?d wdt:P17  ?country . }     # country, if any
  ...
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,de,fr,es". }
}
```

- `P31` = "instance of". `Q1251750` is the Wikidata item for *distillery*. The
  optional blocks mean items without coordinates still come back.
- `SERVICE wikibase:label` is a Wikidata convenience that adds `?dLabel` in the
  requested languages.
- The brand query (`:47–59`) uses a property *path*
  `wdt:P31/wdt:P279* wd:Q56139`: "is an instance of, or a subclass* of, spirit
  (Q56139)", and requires the manufacturer (`P176`) to be a distillery. That is
  why only 12 brands come back — Wikidata's manufacturer coverage is thin.

**The wrong-QID story (tell it in the viva).** `PLANNING.md` (written earlier)
said distilleries were `P31 Q18979992`. Before building, the QID was checked —
`Q18979992` turned out to be *a street in the Netherlands*. The correct class is
**`Q1251750`**. Lesson: verify external identifiers instead of trusting a plan
document. Evidence: `PLANNING.md:116` vs `bootstrap.py:35` and the manifest
source string in `data/raw/manifest.json`.

### 4.3 Caching and the provenance manifest

- **Caching** (`:110–112`, `:140–142`): if the output file exists, return a
  manifest entry rebuilt from the file and skip the network. `--force`
  re-downloads. This is what makes repeated runs fast and deterministic.
- **Manifest** (`_write`, `:92–104`): for each dump it records file path,
  source URL, licence, UTC fetch time, record count, and a **SHA-256** hash of
  the file. SHA-256 is a fingerprint: if a later run produces a different hash,
  the source changed. This single JSON file is ★1–★4 evidence (open licence,
  structured data, provenance, reproducible IRIs).

**Where the 998 vs 865 gap goes.** The SPARQL result is one row *per binding* —
a distillery with several coordinates, websites or sitelinks can produce
multiple rows. `map.py` groups rows by QID (`:239–247`) before minting one IRI
per distillery, giving 865 unique entities. Verified manifest: 998 rows.

**Run it**

```bash
.venv/Scripts/python etl/bootstrap.py            # first run downloads, later runs are cache hits
.venv/Scripts/python etl/bootstrap.py --force    # re-download
```

The raw dumps are git-ignored; on a fresh clone `data/raw/` contains only
`manifest.json`, so run this **before** `map.py`.

### Self-check — step 2

- **Q4.1** Why does the collector make 36 API calls for cocktails?
- **Q4.2** What does the manifest record, and which star does it support?
- **Q4.3** How was the wrong distillery QID discovered, and what is the correct one?
- **Q4.4** Why is re-running `bootstrap.py` cheap?
- **Q4.5** The manifest says 998 distillery rows; the graph has 865 distilleries. Explain.

---

## 5. Step 3 — transform to RDF (`etl/map.py`, commit `126d1b1`)

**Goal:** convert cached JSON into one RDF graph using the ontology's terms,
with deterministic IRIs.

### 5.1 The IRI scheme

- Entity: `https://nathantrance.github.io/SemanticWeb/id/<type>/<slug>`
- Types used: `cocktail`, `ingredient`, `ingredient-amount`, `spirit`,
  `glass`, `distillery`, `brand`, `place`.

`slugify()` (`:89–93`) lowercases, strips accents, and hyphenates:
`"Old Fashioned" → "old-fashioned"`. `unique_slug()` (`:133–142`) resolves
collisions by appending `-2`, `-3`… Because everything is deterministic, a
re-run produces the same bytes and `git diff` only shows real changes.

### 5.2 Mapping a cocktail (annotated)

For each drink (`_add_cocktails`, `:150–215`):

```python
node = ID[f"cocktail/{cocktail_slug}"]          # the IRI we mint
graph.add((node, RDF.type, DRINK.Cocktail))     # rdf:type
graph.add((node, RDFS.label, Literal(name)))    # human label
graph.add((node, SCHEMA.name, Literal(name)))   # schema.org name (same value!)
graph.add((node, DCTERMS.identifier, Literal(drink["idDrink"])))  # source id -> provenance
graph.add((node, DCTERMS.source, URIRef(...lookup.php?i=...)))    # where it came from
```

Note `rdfs:label` *and* `schema:name` carry the same string. This duplication
is deliberate: different consumers look for different predicates, so publishing
both maximises interoperability (same for `schema:image` + `foaf:depiction`
at `:167–169`).

Then, for each non-empty ingredient slot 1–15 (`:185–211`):

```python
amount_node = ID[f"ingredient-amount/{cocktail_slug}/{index}"]
graph.add((amount_node, RDF.type, DRINK.IngredientAmount))
graph.add((amount_node, DRINK.ofIngredient, ingredient_node))
graph.add((node, DRINK.usesIngredient, amount_node))
```

— exactly the measure pattern from §3.5, one node per ingredient use.

### 5.3 Measure parsing

`parse_amount()` (`:96–120`) turns source text into a number and a unit:

| Input | Result |
|---|---|
| `"1 1/2 oz"` | `(1.5, "oz")` |
| `"1/2 slice"` | `(0.5, "slice")` |
| `"1 oz"` | `(1.0, "oz")` |
| `"Juice of 1/2"` | `(None, None)` — prose; kept only as `amountText` |

Unicode fractions are normalised first (`½ → 1/2`, `:74–84`). The tooling
consequence is visible in query 09's real output: the Whiskey Sour has *two*
lemon entries — `"Juice of 1/2"` (text only) and `"1/2 slice"` (numeric 0.5),
because the source itself lists lemon twice. This is honest data messiness; a
great answer to "how clean was your source data?".

### 5.4 Spirit instances and the base-spirit heuristic

- `_add_spirit_types()` (`:218–224`) mints exactly one individual per spirit
  type (`id/spirit/gin`) typed both `drink:Spirit` and `drink:Gin`.
- `detect_spirit()` (`:123–130`) scans the ingredient list **in order** and
  returns the first slug whose keyword table (`:49–72`) matches a word.
  `whiskey`, `scotch`, `bourbon`, `rye` all map to `whisky`; `Cointreau`,
  `Campari`, `triple sec`… map to `liqueur`.
- Verified outcomes (from query 08): Rum 77, Gin 76, Vodka 62, Liqueur 45,
  Whisky 40. It is a heuristic — unusual recipes can misfire. Say that openly;
  it is listed as a known limitation in the walkthrough.

### 5.5 Distilleries, brands, places

- `_add_distilleries()` (`:238–271`): groups rows by QID, mints one IRI per
  distillery, copies `dcterms:identifier` = QID (this QID is what makes ★5
  linking "free" later), parses `Point(lon lat)` from Wikidata into separate
  `geo:long`/`geo:lat` literals (`:255–259`), and adds `foundedYear`,
  `foaf:homepage`, `foaf:depiction`.
- `_add_places()` (`:227–235`): country becomes a `schema:Place` node; the
  distillery points to it with `drink:countryOfOrigin`.
- `_add_brands()` (`:274–316`): same pattern plus
  `drink:producedBy` → the distillery node (looking it up by QID, falling back
  to a slug-based node if the distillery was not in the result set).

**Run it**

```bash
.venv/Scripts/python etl/bootstrap.py     # first, if data/raw is empty
.venv/Scripts/python etl/map.py           # writes data/rdf/data.rdf
.venv/Scripts/python etl/validate_rdf.py  # parse-check
```

### Self-check — step 3

- **Q5.1** What is the IRI of the Negroni's second ingredient-amount node?
- **Q5.2** How does `parse_amount` treat `"1 1/2 oz"` versus `"Juice of 1/2"`?
- **Q5.3** Why does the data point at `id/spirit/gin` instead of the class `drink:Gin`?
- **Q5.4** Why does deterministic slugging matter for git?
- **Q5.5** Describe the base-spirit heuristic in one sentence and give one way it can fail.

---

## 6. Step 4 — link to the world (`etl/reconcile.py`, commit `28d2d3f`)

**Goal:** add `owl:sameAs` statements connecting our entities to Wikidata and
DBpedia — the ★★★★★ evidence.

**Concept box — reconciliation** means matching entities in your dataset to
identifiers in someone else's ("our *Negroni* = Wikidata *Q1401202*"). It is
the heart of Linked Data: without it, your graph is just an island.

### 6.1 Two kinds of links

1. **Free links — distilleries and brands.** They already carry a Wikidata QID
   from collection, which we verified via `P31`. `collect_links()` just copies
   it (`:288–303`). No guessing needed, so confidence is always `high`.
2. **Reconciled links — cocktails and ingredients.** For each label we call the
   Wikimedia `wbsearchentities` API and apply a rule.

### 6.2 The matching rule (precision first)

```python
def score(candidate, kind):
    value = 1.0
    if any(word in description for word in KIND_KEYWORDS[kind]): value += 1.0
    if any(word in description for word in BLACKLIST):           value -= 2.0
    return value
```

- **Exact label match required** after normalisation (`normalize()`, `:150–154`):
  accents stripped, lowercase, punctuation collapsed. `"Goldschläger"` matches
  `"Goldschlager"`.
- **Reward keywords** (`KIND_KEYWORDS`, `:54–80`): a cocktail whose Wikidata
  description mentions `cocktail`/`drink`/`beverage` scores 2.0; an ingredient
  mentioning `juice`, `syrup`, `bitters`, `distilled`… scores 2.0.
- **Blacklist** (`:82–139`): `family name`, `song`, `street`, `number`,
  `programming language`, `singer`… subtract 2.0.
- **Thresholds** (`MIN_SCORE`, `:141`): cocktails need ≥ 2.0, ingredients ≥ 1.0.
  Cocktails are held to a higher bar because a wrong cocktail link is more
  visible; score 2.0 is labelled `confidence: high`.
- Best acceptable candidate wins (`best_match`, `:197–215`); if none, the entity
  stays unlinked. That is why recall is low (~90/441 cocktails linked) and
  precision is the priority.

**Worked examples** (real rows in `data/links/sample.csv`):

| Our label | QID | Wikidata description | Score | Outcome |
|---|---|---|---|---|
| Negroni | Q1401202 | cocktail | 2.0 | accepted, high confidence |
| Goldschlager | Q3110126 | Swiss cinnamon schnapps | 1.0 | accepted, **low** confidence (ingredient threshold is 1.0) |
| Martini | Q1068671 | Brand of Italian drinks | 2.0 | accepted as high because "drink" is a reward word — but it is the vermouth *brand*, not the cocktail. **This is why you hand-verify the sample.** |

That third row is a genuine, reproducible precision error sitting in the repo.
Reporting it honestly ("we found one false positive in the sample; the scoring
prefers recall of the reward word over disambiguating brand vs cocktail") is
exactly the kind of evaluation a grader wants.

### 6.3 From QID to DBpedia IRI

For each accepted QID, `fetch_entities()` (`:218–246`) batch-fetches 50 items
per call asking only for `sitelinks` filtered to `enwiki`. If the item has an
English Wikipedia article, the article title becomes a DBpedia IRI:
`http://dbpedia.org/resource/<title with underscores>` (`dbpedia_iri`, `:249–254`),
percent-encoded with `quote()`.

So each accepted match can yield **two** `owl:sameAs` statements plus
provenance (`build_links_graph`, `:307–328`):

```xml
<rdf:Description rdf:about=".../id/cocktail/negroni">
  <owl:sameAs rdf:resource="http://www.wikidata.org/entity/Q1401202"/>
  <owl:sameAs rdf:resource="http://dbpedia.org/resource/Negroni"/>
  <dcterms:source rdf:resource="https://www.wikidata.org/wiki/Q1401202"/>
</rdf:Description>
```

**Verified counts:** 1,220 entities linked to Wikidata, 390 of them also to
DBpedia (1,610 `owl:sameAs` total). The DBpedia gap exists because not every
Wikidata item has an English Wikipedia article.

### 6.4 Measuring quality: `sample.csv`

`write_sample()` (`:331–362`) draws a fixed random sample of 50 links with
`random.seed(42)` (same 50 every time — reproducible), writes the columns you
need to check, and leaves a blank `verified_true_false` column. The workflow:

1. Open `data/links/sample.csv`.
2. For each row, open `https://www.wikidata.org/wiki/<QID>` and decide: does
   that item really denote our entity?
3. Write `true`/`false`.
4. **Precision = correct / checked.** The project target is ≥ 90% (AGENT.md
   quality gate 3). This single number is the most concrete, verifiable
   evaluation in the whole assignment.

**Run it**

```bash
.venv/Scripts/python etl/reconcile.py          # writes links.rdf + sample.csv (cached searches)
.venv/Scripts/python etl/reconcile.py --limit 5  # quick smoke test
```

### Self-check — step 4

- **Q6.1** What does "reconciliation" mean in this project?
- **Q6.2** A candidate description is `"family name"`. What score does it get, and what happens?
- **Q6.3** Where does the DBpedia IRI come from?
- **Q6.4** How do you compute link precision, and why is the seed fixed at 42?
- **Q6.5** Why do distilleries not need the search/scoring step?

---

## 7. Step 5 — query and serve (`queries/demo.rq`, `etl/run_queries.py`, `web/`, commit `bfaa062`)

**Goal:** prove the graph is queryable, and give a human a way to query it.

### 7.1 How `demo.rq` is organised

The file starts with a **prologue** of `PREFIX` declarations, then 11 blocks,
each headed by a marker comment:

```sparql
# name: 05-five-star-proof-wikidata-and-dbpedia
SELECT ?cocktail ?name ?wikidata ?dbpedia WHERE { ... }
```

`run_queries.py` splits the file with a regex on `# name:` (`:45–49`),
prepends the prologue to each block, runs it, and writes
`report/query-results/<name>.csv` (SELECT/ASK) or `.rdf` (CONSTRUCT) (`:56–91`).
That output folder is the evidence that all 11 queries actually ran.

**Concept box — SPARQL.** Like SQL for triples: `SELECT` returns rows,
`CONSTRUCT` returns new RDF triples, `ASK` returns true/false. Graph patterns
are written as triples with variables (`?cocktail a drink:Cocktail ;
rdfs:label ?name`), and `OPTIONAL`, `FILTER`, `GROUP BY`, `ORDER BY` behave as
you would expect from SQL.

### 7.2 The 11 queries at a glance

| # | Name | Demonstrates | Verified output |
|---|---|---|---|
| 01 | cocktails-with-glass-and-spirit | multi-branch join + OPTIONAL + LIMIT | 30 rows |
| 02 | iba-gin-and-lemon | two required ingredient joins (`?a1, ?a2`) | 6 rows: Aviation, Bramble, Casino, French 75, Rose, White Lady |
| 03 | distilleries-near-edinburgh | geospatial FILTER with arithmetic approximation | 30 rows |
| 04 | shares-2-ingredients-with-negroni | subquery + property path + GROUP BY/HAVING | 8 rows (Americano, Artillery, Bijou…) |
| 05 | five-star-proof-… | requires same entity linked to both Wikidata *and* DBpedia | 25 rows |
| 06 | construct-negroni-subgraph | CONSTRUCT round-trip (rows → new RDF graph) | 21 triples in `.rdf` |
| 07 | spirit-taxonomy | walks `rdfs:subClassOf` to the spirit class | 30 rows |
| 08 | cocktails-per-spirit-type | aggregation GROUP BY | Rum 77, Gin 76, Vodka 62… |
| 09 | ingredient-measures-whiskey-sour | measures live on `IngredientAmount` nodes | 5 rows incl. two lemons |
| 10 | most-used-ingredients | aggregation over the chain join | gin 85, vodka 67, lemon juice 50… |
| 11 | negroni-external-links | ★5 proof for a single entity | Wikidata + DBpedia IRIs |

### 7.3 Three queries worth deep understanding

**Query 03 — geospatial, portable.** rdflib cannot evaluate `SIN`/`SQRT` at
all, and Jena only exposes trigonometry through the XPath `math:` namespace.
So the shipped query uses a **pure-arithmetic equirectangular approximation**
(`demo.rq:39–56`): `dlat² + 0.31·dlon² ≤ 5.04`, where 0.31 ≈ cos²(56°N) and
5.04 ≈ (250 km / 111.3 km-per-degree)². It is accurate enough near Edinburgh
and runs on both engines. The exact haversine formula lives in
`queries/haversine-fuseki.rq` for Fuseki only.

**Query 04 — property path as reasoning.** The inner subquery collects the
Negroni's ingredients via `drink:usesIngredient/drink:ofIngredient`
(`demo.rq:62–64`); the sequence path `/` is exactly the property chain from the
ontology, executed without a reasoner. The outer query replays the path for
every cocktail, counts shared ingredients, and keeps those with ≥ 2
(`demo.rq:66–73`). Verified: Americano, Artillery, Bijou, English Highball,
French Negroni… each share 2.

**Query 06 — CONSTRUCT.** `CONSTRUCT { ?cocktail ?p ?o } WHERE { ... }` returns
a new RDF graph containing every triple of the Negroni — an "export this
subgraph" operation. The runner saves it as `.rdf`, which is a nice
demonstration that SPARQL can *produce* RDF, not only table rows.

### 7.4 The zero-install server

`web/server.py` does three jobs from one stdlib process (no web framework):

| Route | Job | Code |
|---|---|---|
| `GET/POST /sparql` | SPARQL endpoint with content negotiation (JSON/XML results, Turtle/RDF/JSON-LD for CONSTRUCT) and CORS | `:118–130`, `:219–246` |
| `GET /onto`, `GET /id/<type>/<slug>` | IRI dereferencing: browser gets HTML, machine gets RDF | `:134–203` |
| everything else | serves the static UI (`web/index.html`, `app.js`, `styles.css`) | `:207–217` |

The graphs are loaded once at startup (`load_graphs`, `:59–68`), query running
is just `graph.query(...)` (`:225`). The dereferencing route builds a **concise
bounded description** (`concise_description`, `:71–85`): the subject's own
triples plus one hop into our own IRIs, so fetching
`/id/cocktail/negroni` also returns its three ingredient-amount nodes with
their measures. Unknown IRIs return 404, and the HTML page links to
`?format=turtle|rdf|jsonld` for machines.

The UI (`web/app.js`) fetches `queries/demo.rq`, splits it with the same
`# name:` convention (`:12–15`), fills a presets dropdown (`:17–38`), POSTs the
query to whatever endpoint is in the Endpoint field (`:92–99`), and renders
`application/sparql-results+json` as a table (`:47–77`), with a "raw" checkbox
for the unformatted response.

**Cross-check with the frontend:** `app.js:12–15` duplicates the splitting
logic of `run_queries.py:45–49`. Two implementations of one convention — if
you ever changed the marker syntax you would have to change both. A classic
small technical-debt note for "future work".

### 7.5 The "standard" endpoint (Apache Jena Fuseki)

`docker-compose.yml` starts `stain/jena-fuseki`; `etl/load_fuseki.py` loads the
three files. Two modes:

- **default:** `CLEAR DEFAULT` then one POST per file → all triples in the
  default graph, so the demo queries (which never use `GRAPH`) return the same
  rows as on rdflib (`load_fuseki.py:42–59`).
- **`--named-graphs`:** each file goes into its own named graph
  (`.../graph/onto`, `.../graph/data`, `.../graph/links`), which is how you
  would do provenance-style queries with `GRAPH` (`:62–72`).

The same 11 queries were verified against both engines; outputs are kept in
`report/query-results-fuseki/`. Three practical gotchas:

1. **Prefixes cannot contain `/`** (`demo.rq:8–9`): you cannot write
   `id:cocktail/negroni`, so per-type prefixes `c:` and `ing:` were added.
2. **Trigonometry portability** (see query 03 above).
3. **`127.0.0.1`, not `localhost`** on Windows: `localhost` resolves to IPv6
   first, Docker publishes IPv4, costing ~20 s per connection
   (`docker-compose.yml:8–11`, `load_fuseki.py:15–16`).

**Run it**

```bash
.venv/Scripts/python etl/run_queries.py       # 11/11, writes report/query-results/
.venv/Scripts/python web/server.py            # http://localhost:8000
# optional standard endpoint:
docker compose up -d
.venv/Scripts/python etl/load_fuseki.py
.venv/Scripts/python etl/run_queries.py --endpoint http://127.0.0.1:3030/ds/sparql
docker compose down
```

### Self-check — step 5

- **Q7.1** What does a `# name:` line do, and which two programs depend on it?
- **Q7.2** Which query proves ★5, and what exactly must an entity have to appear?
- **Q7.3** How does the project "run" the property chain without a reasoner?
- **Q7.4** Why can't a SPARQL prefixed name contain `/`, and what is the workaround?
- **Q7.5** What does content negotiation mean for `GET /id/cocktail/negroni`?
- **Q7.6** When would you load Fuseki with `--named-graphs`?

---

## 8. After step 5 — the polish commits

These commits turn a working pipeline into a presentable 5★ deliverable.

| Commit | What | Why it matters |
|---|---|---|
| `19cd706` | deleted query-result files left over from renames | hygiene; results match query names |
| `3971bd9` | Turtle → RDF/XML everywhere, added `export_formats.py` and `BUILD-WALKTHROUGH.md` | canonical ontology format; proves serialization equivalence |
| `d286999` | dereferencing in `server.py` + `build_site.py` + Pages workflow + `docs/dereferencing.md` | makes IRIs actually resolve — the strongest ★4 evidence |
| `65f8b5d` | fixed `--out` path in `build_site.py` for CI | the workflow passes a relative `site` path |
| `eeed490` | Fuseki verification, portable geo query, `haversine-fuseki.rq` | proves the queries are not rdflib-specific |
| `de98011` | added the session transcript | full audit trail of the AI-assisted build |

### 8.1 Dereferenceable IRIs (the ★4 idea)

An IRI is a *name*; it is **dereferenceable** when fetching it returns a
description — RDF for machines, HTML for humans. `docs/dereferencing.md`
explains both routes:

1. **Local dynamic server (correct):** `web/server.py` reads the `Accept`
   header: `text/html` → page, `text/turtle` → Turtle,
   `application/rdf+xml` → RDF/XML, `application/ld+json` → JSON-LD
   (`_negotiate`, `server.py:163–173`). Demo:

   ```bash
   curl -H "Accept: text/turtle" http://localhost:8000/id/cocktail/negroni
   ```

2. **Static GitHub Pages (public):** `build_site.py` writes a file at the
   *exact* path of every IRI — RDF/XML at `site/id/cocktail/negroni`, plus a
   sibling `negroni.html` for humans (`build_site.py:114–133`). It skips
   `ingredient-amount` internals (`:110`) so the site lists real entities only.
   The workflow `.github/workflows/pages.yml` builds and deploys it on every
   push to `main`.

**The honest caveat:** GitHub Pages is static and cannot negotiate content; it
serves the extensionless RDF file as a download rather than as `text/turtle`.
So the *public* route demonstrates resolvability, and the *local* server
demonstrates correct negotiation. State this before the lecturer finds it.

**Why the ontology collapses to `/onto`:** the namespace uses a **hash**
(`.../onto#Cocktail`). Browsers never send the `#fragment` to a server, so the
class dereferences through the document `.../onto`, which returns the whole
ontology. That is standard practice, not a bug (`dereferencing.md:85–89`).

### 8.2 Two quality gates, automated

- **Gate 1 — parse check:** `etl/validate_rdf.py` parses every RDF file and
  prints `OK <path> (N triples)` or `FAIL` (`:21–33`); non-zero exit on
  failure, so it can be a CI/pre-commit hook.
- **Gate 2 — queries:** `etl/run_queries.py` exits non-zero unless all 11
  queries succeed. Both gates were run before commits, per `AGENT.md:25–29`.

### Self-check — step 6

- **Q8.1** Why did the project switch from Turtle to RDF/XML, and what proves nothing was lost?
- **Q8.2** What is a dereferenceable IRI, and how does `build_site.py` make one?
- **Q8.3** What is the honest caveat about the public GitHub Pages route?
- **Q8.4** Why does query 03 use an approximation instead of the exact haversine formula?

---

## 9. One data journey — the Negroni, end to end

This is the best way to convince yourself the whole pipeline works.

### 9.1 Source (TheCocktailDB)

The Negroni is record `idDrink = 11003`: 3 ingredients (Gin, Campari, Sweet
Vermouth, each 1 oz), glass "Old Fashioned glass", IBA flag "Unforgettables",
tags `IBA, Classic`, instructions "Stir into glass over ice, garnish and
serve." Raw dumps are not committed, so run `bootstrap.py` to see the JSON; the
mapped facts are quoted below.

### 9.2 Instance triples (`data/rdf/data.rdf`, verified)

```xml
<rdf:Description rdf:about=".../id/cocktail/negroni">
  <rdf:type rdf:resource=".../onto#Cocktail"/>
  <rdfs:label>Negroni</rdfs:label>
  <dcterms:identifier>11003</dcterms:identifier>
  <drink:preparation>Stir into glass over ice, garnish and serve.</drink:preparation>
  <drink:servedIn rdf:resource=".../id/glass/old-fashioned-glass"/>
  <drink:isIBA rdf:datatype=".../XMLSchema#boolean">true</drink:isIBA>
  <drink:hasTag>Unforgettables</drink:hasTag>
  <drink:usesIngredient rdf:resource=".../id/ingredient-amount/negroni/1"/>
  <drink:usesIngredient rdf:resource=".../id/ingredient-amount/negroni/2"/>
  <drink:usesIngredient rdf:resource=".../id/ingredient-amount/negroni/3"/>
  <drink:baseSpirit rdf:resource=".../id/spirit/gin"/>
</rdf:Description>

<rdf:Description rdf:about=".../id/ingredient-amount/negroni/1">
  <rdf:type rdf:resource=".../onto#IngredientAmount"/>
  <drink:ofIngredient rdf:resource=".../id/ingredient/gin"/>
  <drink:amountText>1 oz</drink:amountText>
  <drink:amountValue rdf:datatype=".../XMLSchema#double">1.0</drink:amountValue>
  <drink:amountUnit>oz</drink:amountUnit>
</rdf:Description>
```

Note what is **absent**: no `drink:hasIngredient` triple. It is derivable via
the property chain, and queries 04/10 navigate the path instead.

### 9.3 Link triples (`data/links/links.rdf`, verified)

```xml
<rdf:Description rdf:about=".../id/cocktail/negroni">
  <owl:sameAs rdf:resource="http://www.wikidata.org/entity/Q1401202"/>
  <owl:sameAs rdf:resource="http://dbpedia.org/resource/Negroni"/>
  <dcterms:source rdf:resource="https://www.wikidata.org/wiki/Q1401202"/>
</rdf:Description>
```

### 9.4 Query 11 result (`report/query-results/11-negroni-external-links.csv`, verified)

```
link
http://www.wikidata.org/entity/Q1401202
http://dbpedia.org/resource/Negroni
```

### 9.5 Follow-ups to try yourself

- `SELECT ?ingredient WHERE { c:negroni drink:usesIngredient/drink:ofIngredient ?ingredient }` → gin, campari, sweet-vermouth.
- Fetch `http://localhost:8000/id/cocktail/negroni` with `Accept: text/turtle`
  and find the same six triples plus the measure nodes in the response.
- Open `https://www.wikidata.org/wiki/Q1401202` and confirm it is the Negroni
  cocktail — that is the manual check every sample row gets.

---

## 10. Reproducing the numbers (evidence commands)

After `pip install -r requirements.txt`:

```bash
# triple counts per file (quality gate 1)
.venv/Scripts/python etl/validate_rdf.py
# OK ontology/drinkonto.owl   (~190 triples)
# OK data/rdf/data.rdf        (~22,300 triples)
# OK data/links/links.rdf     (~2,830 triples)

# exact link counts (Git Bash; works without rdflib)
grep -o '<owl:sameAs' data/links/links.rdf | wc -l                                   # 1610
grep -o '<owl:sameAs rdf:resource="http://www.wikidata.org/entity/' data/links/links.rdf | wc -l   # 1220
grep -o '<owl:sameAs rdf:resource="http://dbpedia.org/resource/'    data/links/links.rdf | wc -l   # 390
```

Cross-check with the docs:

- `manifest.json`: cocktails 441, distillery rows 998, brands 12.
- Doc triple counts: ontology ~190 + data ~22,300 + links ~2,830 = ~25,320
  merged — matching the walkthrough's "~25,300".
- The `README.md` "1,220 `owl:sameAs`" figure is the count of *entities linked
  to Wikidata*; the total `owl:sameAs` statements in the file is 1,610.

---

## 11. Viva preparation

### 11.1 Six storylines to have ready

1. **Measures via `IngredientAmount` + OWL 2 property chain** (§3.5).
2. **The wrong QID** (`Q18979992` street → `Q1251750` distillery) — verification
   mindset (§4.2).
3. **Precision-first reconciliation** with exact labels + description scoring
   + blacklist, and the honest false-positive example (§6.2–6.4).
4. **Serialization vs data model** — Turtle/JSON-LD exports prove the point
   (§1.5, §3.7).
5. **Portability gotchas** — prefixes can't contain `/`; trig via `math:`; the
   approximation; `127.0.0.1` vs `localhost` (§7.3, §7.5).
6. **Dereferenceable IRIs** — same IRI, HTML vs RDF; static Pages caveat (§8.1).

### 11.2 Likely questions with model answers

**"Why OWL and not just RDF/RDFS?"** We declare inverse properties, a
sub-property, and an OWL 2 property chain so `hasIngredient` is *derivable*;
plain RDFS cannot express the chain. We then demonstrate the inference with a
SPARQL property path.

**".owl or .ttl?"** Same triples, different serialization. Ours is RDF/XML as
the canonical format; `etl/export_formats.py` emits Turtle, JSON-LD and
N-Triples to show it changes nothing.

**"How did you link your data?"** Distilleries/brands copy their verified
Wikidata QID; cocktails/ingredients require exact label match plus description
scoring against the MediaWiki search API. Accepted QIDs are resolved to DBpedia
through the enwiki sitelink.

**"Is it really 5-star?"** Map each star to an artifact: licence docs (★1),
cached JSON + manifest (★2), RDF files (★3), OWL/SPARQL/dereferenceable IRIs
(★4), `owl:sameAs` + precision sample (★5).

**"Why not federate live queries?"** Out of scope; ★5 requires *publishing*
links (`owl:sameAs`), not querying other endpoints. Federation is future work.

**"How good is the linking?"** Precision measured on a 50-link seeded sample;
target ≥ 90%. Report the number you actually measured, and mention the
Martini-brand false positive as a known failure mode. Recall is deliberately
low (~90/441 cocktails) because we required exact labels and high thresholds.

**"Where is the XML in this project?"** TheCocktailDB's native output is JSON;
our transform maps structured source data to RDF/XML. The XML syntax lesson is
in the *serialization* choice (RDF/XML) and in the syntactic-vs-semantic
mapping from source records to triples.

**"What would you do differently?"** Fuzzy matching (OpenRefine/Silk) for
recall; merge the duplicated prefix-splitting logic between `run_queries.py`
and `app.js`; enrich the 12 brands from another source; materialise inferred
`hasIngredient` triples with an OWL reasoner (e.g. Apache Jena) instead of
property paths.

### 11.3 Traps to avoid

- Saying "RDF/XML and Turtle are different data models" — they are not.
- Quoting "1,220 links" without explaining it is the Wikidata-link count; the
  total is 1,610 with DBpedia.
- Claiming a reasoner runs in the pipeline — it does not; property paths do the
  job. Say "the axiom makes the inference possible; we demonstrate it with
  property paths".
- Claiming the base-spirit heuristic is always right — it is a heuristic.
- Forgetting the Pages negotation caveat when showing public IRIs.

---

## 12. Common beginner confusions (cleared up)

1. **"A triple looks like a sentence, so is RDF just text?"** The text is only
   the serialization. The graph is a set of triples; you can reserialize it
   without changing the meaning.
2. **"`drink:` — is that part of the data?"** No. Prefixes are shorthand
   defined at the top of a file. `drink:Cocktail` expands to the full IRI
   `https://nathantrance.github.io/SemanticWeb/onto#Cocktail`. The prefix name
   itself is never stored.
3. **"Why are `rdfs:label` and `schema:name` both present with the same value?"**
   Interoperability: different toolkits look for different properties. The data
   says one fact twice in two vocabularies.
4. **"Why does the Negroni have ingredient-amount nodes instead of ingredients?"**
   Measures. The edge needed a body, so it became a node (§3.5).
5. **"Why is `hasIngredient` defined but never used in the data?"** It is an
   inferred (derived) property. The chain axiom documents the rule; queries use
   the path `usesIngredient/ofIngredient`.
6. **"What are those `rdf:first`/`rdf:rest` blank nodes?"** RDF's way of
   encoding an ordered list — here, the two properties of the property chain
   (§3.5).
7. **"Why two namespaces, `onto#` and `id/`?"** `onto#` (hash namespace) holds
   the schema and dereferences through the document `/onto`; `id/` (slash
   namespace) gives every individual its own resolvable IRI.
8. **"Is `owl:sameAs` the same as `dcterms:source`?"** No. `owl:sameAs` asserts
   identity of the real-world thing; `dcterms:source` records provenance (where
   we found the match). We publish both, with different purposes.
9. **"Why does `sample.csv` label some distilleries by slug (`dyfi-distillery`)?**
   For distilled/brand links the label column is filled from the IRI's last
   segment (`reconcile.py:297`), not from `rdfs:label`. Cosmetic; a nice thing
   to fix or mention.
10. **"Do I need Docker?"** No. The zero-install server is the default; Fuseki
    is an optional "standard endpoint" proof of portability.

---

## 13. Cheat sheet

**Pipeline (from a fresh clone)**

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python etl/bootstrap.py       # 1. collect (cache + manifest)
.venv/Scripts/python etl/map.py             # 2. JSON -> data/rdf/data.rdf
.venv/Scripts/python etl/reconcile.py       # 3. -> data/links/links.rdf + sample.csv
.venv/Scripts/python etl/validate_rdf.py    # 4. parse check
.venv/Scripts/python etl/run_queries.py     # 5. 11/11 queries -> report/query-results/
.venv/Scripts/python web/server.py          # 6. http://localhost:8000
```

**Optional**

```bash
.venv/Scripts/python etl/export_formats.py   # Turtle/JSON-LD/N-Triples into exports/
.venv/Scripts/python etl/build_site.py       # static dereferenceable site into site/
docker compose up -d && .venv/Scripts/python etl/load_fuseki.py
.venv/Scripts/python etl/run_queries.py --endpoint http://127.0.0.1:3030/ds/sparql
```

**File map**

| Path | What it is |
|---|---|
| `ontology/drinkonto.owl` | OWL 2 ontology, RDF/XML, Protégé-compatible |
| `data/raw/manifest.json` | provenance: URL, licence, time, count, SHA-256 |
| `data/rdf/data.rdf` | instance graph (cocktails, ingredients, distilleries, brands) |
| `data/links/links.rdf` | `owl:sameAs` + `dcterms:source` |
| `data/links/sample.csv` | 50-link seeded precision sample (fill `verified_true_false`!) |
| `etl/bootstrap.py` | collect + cache + manifest |
| `etl/map.py` | JSON → RDF |
| `etl/reconcile.py` | entity matching → links |
| `etl/validate_rdf.py` | quality gate 1 |
| `etl/run_queries.py` | quality gate 2 + report outputs |
| `etl/export_formats.py` | serialization demos |
| `etl/build_site.py` | static dereferenceable Pages site |
| `etl/load_fuseki.py` | load graphs into Jena Fuseki |
| `queries/demo.rq` | 11 demo queries |
| `queries/haversine-fuseki.rq` | exact-distance query (Fuseki only) |
| `web/server.py` | SPARQL endpoint + dereferencing |
| `web/app.js` | preset loading, query execution, table rendering |
| `docs/dereferencing.md` | ★4 details and caveats |
| `docs/data-licences.md` | source licences |
| `docs/BUILD-WALKTHROUGH.md` | design narrative + demo script |

**External references**

- 5-star open data: https://5stardata.info/en/
- RDF 1.1 primer: https://www.w3.org/TR/rdf11-primer/
- OWL 2 primer: https://www.w3.org/TR/owl2-primer/
- SPARQL 1.1: https://www.w3.org/TR/sparql11-query/
- Wikidata Query Service: https://query.wikidata.org/
- TheCocktailDB: https://www.thecocktaildb.com/
- Negroni in Wikidata: https://www.wikidata.org/wiki/Q1401202
- Distillery class Q1251750: https://www.wikidata.org/wiki/Q1251750

---

## 14. Self-check answer key

**Big picture**

- **A1.1** A subject–predicate–object statement; e.g. Negroni `drink:baseSpirit` gin (§1.2).
- **A1.2** Ontology = schema/classes/properties; instance graph = actual entities
  and facts; links graph = `owl:sameAs` bridges to Wikidata/DBpedia.
- **A1.3** Separate graphs let you reload/replace one layer without touching the
  others, are the conventional way to model provenance, and make ★4/★5 evidence
  files self-contained. (Fuseki can also keep them as named graphs.)
- **A1.4** Defined in `ontology/drinkonto.owl:15–21`; the Negroni's base spirit
  is asserted in `data/rdf/data.rdf`.

**Step 0**

- **A2.1** rdflib handles all RDF work and requests handles HTTP; the rest uses
  the standard library, so installation is trivial and reproducible.
- **A2.2** Git cannot track empty directories; `.gitkeep` keeps the intended
  folder structure in the repo.
- **A2.3** The manifest is small, deterministic and is provenance evidence
  (★2–★4). The dumps are large and re-downloadable, so they are ignored to keep
  the repo lean and avoid stale data.
- **A2.4** `etl/bootstrap.py` (to fetch the raw dumps into `data/raw/`).

**Step 1**

- **A3.1** `drink:Gin` is a class in the schema; `id/spirit/gin` is an
  individual instance of that class (plus `drink:Spirit`). Data points at the
  individual to avoid OWL punning.
- **A3.2** RDF predicates cannot carry attributes; the intermediate node makes
  the measure addressable (`amountText`, `amountValue`, `amountUnit`) and
  supports the ingredient-sharing queries.
- **A3.3** It defines `hasIngredient` as the composition of `usesIngredient`
  and `ofIngredient`, so it can be inferred. The data does not assert it; SPARQL
  property paths traverse the same chain.
- **A3.4** No — both are serializations of RDF; the triples are identical.
- **A3.5** `drink:Beverage`, which is a sub-class of `schema:Beverage`.

**Step 2**

- **A4.1** The free API only supports per-letter search; the loop covers
  `a–z0–9` and deduplicates by `idDrink`, so duplicates are harmless.
- **A4.2** File path, source URL, licence, fetch timestamp, record count and
  SHA-256; it is provenance evidence for ★1–★4 and proves reproducibility.
- **A4.3** The planned QID was checked against Wikidata: `Q18979992` is a
  street in the Netherlands; the distillery class is `Q1251750`.
- **A4.4** Dumps are cached; `bootstrap.py` returns manifest entries from disk
  unless `--force` is passed.
- **A4.5** The SPARQL result has multiple rows per distillery (e.g. several
  coordinates/sitelinks); `map.py` groups by QID first, yielding 865 unique
  entities.

**Step 3**

- **A5.1** `https://nathantrance.github.io/SemanticWeb/id/ingredient-amount/negroni/2`.
- **A5.2** `"1 1/2 oz"` → `(1.5, "oz")` (mixed-number regex, then unit);
  `"Juice of 1/2"` → `(None, None)` because the regex requires the quantity at
  the start; the original text survives as `amountText`.
- **A5.3** To avoid using one IRI as both class and instance (punning).
- **A5.4** Same input → same IRIs → same file bytes, so `git diff` shows only
  real changes and re-runs are verifiable.
- **A5.5** It returns the first ingredient whose name matches a keyword table
  (`gin`, `whisky/scotch/bourbon/rye`, `campari→liqueur`…). It can misfire when
  a recipe lists an unusual base, e.g. a cocktail whose first match is a
  liqueur while the real base is something else.

**Step 4**

- **A6.1** Matching our entities to external identifiers (Wikidata QIDs, then
  DBpedia IRIs) and publishing the equivalences as `owl:sameAs`.
- **A6.2** Base 1.0 − 2.0 = −1.0, below every threshold, so the candidate is
  rejected; the entity stays unlinked.
- **A6.3** From the Wikidata item's English Wikipedia sitelink:
  `http://dbpedia.org/resource/<article title>` with underscores and percent
  encoding.
- **A6.4** Draw the seeded 50-link sample, check each QID manually, and divide
  the number correct by the number checked. Seed 42 makes the sample identical
  on every run, so the measurement is reproducible.
- **A6.5** Their QIDs came directly from the Wikidata SPARQL collection and were
  verified through `P31`, so no label matching is needed.

**Step 5**

- **A7.1** It names a query block. `etl/run_queries.py:45–49` and
  `web/app.js:12–15` both split on it — two implementations of one convention.
- **A7.2** Query 05: the entity must be a `drink:Cocktail` with an
  `owl:sameAs` to a `wikidata.org/entity/` IRI *and* one to a
  `dbpedia.org/resource/` IRI.
- **A7.3** With a SPARQL property path (`drink:usesIngredient/drink:ofIngredient`),
  used by queries 04 and 10.
- **A7.4** The SPARQL grammar reserves `/` for property paths, so it cannot
  appear in a prefixed name; the project defines `c:` and `ing:` prefixes.
- **A7.5** The server inspects the client's `Accept` header: `text/html` gets a
  human page, `text/turtle`/`application/rdf+xml`/`application/ld+json` get RDF;
  the response body is a concise description including one hop to the
  ingredient-amount nodes.
- **A7.6** When you want ontology/data/links as separate named graphs for
  `GRAPH`-based provenance queries, instead of the merged default graph.

**Step 6**

- **A8.1** RDF/XML is the conventional `.owl` ontology format; `export_formats.py`
  re-serializes the same graphs as Turtle, JSON-LD and N-Triples, proving the
  triples are unchanged. (Stale `.ttl` references remain in
  `drinkonto.owl:110` and `map.py:3`.)
- **A8.2** An IRI that returns a description when fetched. `build_site.py`
  writes an RDF/XML file at the exact IRI path plus an HTML twin, so the public
  Pages URL resolves.
- **A8.3** Static hosting cannot perform content negotiation, so the public RDF
  downloads instead of being served as `text/turtle`; the local server is the
  correct negotiation demo.
- **A8.4** Portability: plain rdflib cannot evaluate trigonometric functions,
  and Jena rejects the bare SPARQL `SIN`/`COS`/`SQRT` keywords. The
  equirectangular approximation needs only arithmetic and runs on both engines;
  the exact haversine is kept for Fuseki in `queries/haversine-fuseki.rq`.

---

*End of study guide. If something is still unclear, it is a documentation bug —
ask and this file can grow an explanation.*
