# IRI dereferencing (the ★4 star)

An IRI is a **name** for a thing. It is **dereferenceable** when fetching it
returns a description of that thing (RDF), not a 404. That is what separates a
Linked Data IRI from a plain database key, and it is the strongest evidence for
the ★4 ("use W3C open standards") star.

Our IRIs:

```
https://nathantrance.github.io/SemanticWeb/onto                     # the ontology
https://nathantrance.github.io/SemanticWeb/id/cocktail/negroni      # an entity
```

There are two ways this project makes them resolve.

## 1. Local server with HTTP content negotiation (correct)

`web/server.py` returns the **same IRI** in the format the client asks for:

| Client `Accept` header | Response |
|---|---|
| `text/html` | a human-readable page |
| `text/turtle` | Turtle RDF |
| `application/rdf+xml` | RDF/XML (default) |
| `application/ld+json` | JSON-LD |

```bash
.venv/Scripts/python web/server.py

# machine view -> RDF
curl -H "Accept: text/turtle" http://localhost:8000/id/cocktail/negroni
curl -H "Accept: application/rdf+xml" http://localhost:8000/onto

# human view -> HTML
open http://localhost:8000/id/cocktail/negroni      # or paste in a browser
```

Each response is a **concise bounded description**: the entity's own triples
plus one hop into our own IRIs, so a single fetch returns the cocktail *and* its
ingredient measures. Unknown IRIs return **404** rather than a misleading page.

Screenshot one of the `curl` commands for the report — it is direct ★4 proof.

## 2. Public static site on GitHub Pages (resolvable on the web)

`etl/build_site.py` writes a `site/` tree where every IRI has a file at exactly
that path (RDF/XML) plus an `.html` twin for humans:

```
site/index.html
site/onto, site/onto.ttl, site/onto.jsonld
site/id/cocktail/negroni          <- RDF/XML at the exact IRI
site/id/cocktail/negroni.html     <- human page
...
```

```bash
.venv/Scripts/python etl/build_site.py --out site
```

A GitHub Actions workflow (`.github/workflows/pages.yml`) builds and deploys
this to Pages on every push to `main`.

**Enable it once:** repo **Settings → Pages → Build and deployment → Source =
GitHub Actions** (the workflow also attempts to enable it automatically). Then
push, and after the action finishes visit:

```
https://nathantrance.github.io/SemanticWeb/id/cocktail/negroni
```

### Caveat (state it honestly in the viva)

GitHub Pages is **static and cannot do content negotiation**, and it serves
extensionless files as a download (`application/octet-stream`) rather than
`text/turtle`. So:

- **browser + public web** → use the `.html` twin pages;
- **correct machine negotiation** → use the local server (route 1) or a dynamic
  host / Fuseki with a negotiation layer.

Both routes publish the *same* RDF; only the HTTP plumbing differs.

## Why the content collapses to `/onto`

The ontology namespace uses a **hash** (`.../onto#Cocktail`). Fragments are not
sent to the server, so `.../onto#Cocktail` dereferences via the document
`.../onto`, which returns the whole ontology. That is the standard convention.
