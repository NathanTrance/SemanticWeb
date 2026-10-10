#!/usr/bin/env bash
# demo-api.sh - prove the DrinkOnto API works over the web.
#
# Run from ANY machine that can reach the endpoint (e.g. another device on the
# same Tailscale network, or a teammate's laptop):
#
#   bash demo-api.sh                                   # ts.net URL (default)
#   bash demo-api.sh http://localhost:8000             # a local instance
#   bash demo-api.sh https://some-host.example/        # any deployment
#
# Only needs `curl`. It shows reachability, five SPARQL queries and IRI
# dereferencing - i.e. every course requirement, straight from the shell.

set -u
BASE="${1:-https://invidious.tailadee73.ts.net}"
BASE="${BASE%/}"

bold() { printf '\n\033[1m%s\033[0m\n' "$1"; }

# Pretty-print JSON if a Python is available, otherwise pass it through.
pretty() {
  if command -v python3 >/dev/null 2>&1; then python3 -m json.tool 2>/dev/null || cat
  elif command -v python  >/dev/null 2>&1; then python  -m json.tool 2>/dev/null || cat
  else cat; fi
}

# Run one SPARQL SELECT and return SPARQL-JSON (POST form-encoded).
sparql() {
  curl -s -X POST "$BASE/sparql" \
    -H "Accept: application/sparql-results+json" \
    --data-urlencode "query=$1"
}

printf 'DrinkOnto demo  ->  %s\n' "$BASE"

bold "0) Reachable? (expect HTTP 200)"
curl -s -o /dev/null -w "   HTTP %{http_code}  (%{time_total}s)\n" "$BASE/" \
  || { echo "   cannot reach $BASE"; exit 1; }

bold "1) SPARQL: total triples in the graph"
sparql 'SELECT (COUNT(*) AS ?triples) WHERE { ?s ?p ?o }' | pretty

bold "2) SPARQL: how many cocktails?"
sparql 'PREFIX drink: <https://nathantrance.github.io/SemanticWeb/onto#>
SELECT (COUNT(?c) AS ?cocktails) WHERE { ?c a drink:Cocktail }' | pretty

bold "3) SPARQL: cocktails per base spirit (GROUP BY)"
sparql 'PREFIX drink: <https://nathantrance.github.io/SemanticWeb/onto#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?spirit (COUNT(?c) AS ?n) WHERE {
  ?c drink:baseSpirit ?s . ?s rdfs:label ?spirit .
}
GROUP BY ?spirit ORDER BY DESC(?n)' | pretty

bold "4) SPARQL: 5-star proof - cocktails linked to Wikidata AND DBpedia"
sparql 'PREFIX drink: <https://nathantrance.github.io/SemanticWeb/onto#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?cocktail ?name ?wikidata ?dbpedia WHERE {
  ?cocktail a drink:Cocktail ; rdfs:label ?name ; owl:sameAs ?wikidata, ?dbpedia .
  FILTER(STRSTARTS(STR(?wikidata), "http://www.wikidata.org/entity/"))
  FILTER(STRSTARTS(STR(?dbpedia), "http://dbpedia.org/resource/"))
}
LIMIT 5' | pretty

bold "5) SPARQL: distilleries near Edinburgh (geospatial, plain arithmetic)"
sparql 'PREFIX drink: <https://nathantrance.github.io/SemanticWeb/onto#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
SELECT ?distillery ?label WHERE {
  ?distillery a drink:Distillery ; rdfs:label ?label ;
              geo:lat ?lat ; geo:long ?long .
  BIND((55.9533 - ?lat) * (55.9533 - ?lat)
       + 0.31 * (-3.1883 - ?long) * (-3.1883 - ?long) AS ?deg2)
  FILTER(?deg2 <= 5.04)
}
LIMIT 5' | pretty

bold "6) Dereference an IRI as a machine -> RDF (Turtle)"
curl -s -H "Accept: text/turtle" "$BASE/id/cocktail/negroni" | head -n 15

bold "7) Same IRI as a browser -> HTML"
curl -s -H "Accept: text/html" "$BASE/id/cocktail/negroni" | head -n 6

bold "8) The ontology document"
curl -s -H "Accept: text/turtle" "$BASE/onto" | head -n 10

bold "Done"
echo "   Covered: ontology (8), SPARQL querying (1-5), 5-star linkage (4), dereferencing (6-7)."
