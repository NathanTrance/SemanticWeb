# Data sources and licences

This project publishes a knowledge graph assembled from the sources below.
Each source keeps its own licence; the surrounding **code** is MIT (see
`LICENSE`) and the **ontology** is offered under CC BY 4.0.

| Source | What we use | Access | Licence |
|---|---|---|---|
| [TheCocktailDB](https://www.thecocktaildb.com/) | Cocktail names, categories, IBA flag, glass, instructions, images, ingredient list and measures (441 drinks) | Public JSON API (test key `1`) | Free for non-commercial use; attribution required |
| [Wikidata](https://query.wikidata.org/) | Distilleries (P31 `Q1251750`) with coordinates, country, inception, website, image, enwiki sitelink; spirit brands (P31/P279* `Q56139` with manufacturer `P176` a distillery) | SPARQL endpoint / MediaWiki API | CC0 1.0 (public domain dedication) |
| [DBpedia](https://www.dbpedia.org/) | Resource IRIs derived from Wikidata enwiki sitelinks, used for `owl:sameAs` | Resource IRIs (no bulk download) | CC BY-SA 4.0 |
| [Wikipedia](https://www.wikipedia.org/) | Indirectly, via Wikidata sitelinks | — | CC BY-SA 4.0 |

## Provenance

Every fetched dump is recorded in [`data/raw/manifest.json`](../data/raw/manifest.json)
with its URL, licence, retrieval timestamp, record count and a SHA-256 hash.
The linking step additionally records `dcterms:source` pointing at the matched
Wikidata item for each `owl:sameAs`. Raw dumps are cached but not committed;
re-run `etl/bootstrap.py` to reproduce them.

## Reuse in the report

If you quote or reproduce source data, cite the source and its licence above
and keep the IBA/non-commercial note for TheCocktailDB visible. No content from
review sites (ratebeer, untappd, ...) is used, in line with the project scope.
