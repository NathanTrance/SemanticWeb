"""Reconcile our entities with Wikidata and DBpedia to reach 5-star LOD.

Step 4 of the pipeline: for every cocktail and ingredient we search the
MediaWiki API, keep only candidates whose label matches ours exactly and
score them on their Wikidata description (rewarding "cocktail", "juice",
"distilled", ... and penalising "family name", "song", ...). Distilleries
and brands already carry their QID from collection, so they are linked for
free. For every accepted QID we pull the enwiki sitelink to mint the
matching DBpedia IRI.

Outputs:
  data/links/links.ttl  -> owl:sameAs + provenance, in the links graph
  data/links/sample.csv -> seeded random sample for the report's precision
                           check (fill the `verified` column by hand)
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

import requests

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA_TTL = ROOT / "data" / "rdf" / "data.ttl"
LINKS_TTL = ROOT / "data" / "links" / "links.ttl"
SAMPLE_CSV = ROOT / "data" / "links" / "sample.csv"
CACHE = RAW / "reconcile"

DRINK = Namespace("https://nathantrance.github.io/SemanticWeb/onto#")
ID = Namespace("https://nathantrance.github.io/SemanticWeb/id/")
WD_ENTITY = "http://www.wikidata.org/entity/"
WD_PAGE = "https://www.wikidata.org/wiki/"
DBPEDIA = "http://dbpedia.org/resource/"

API = "https://www.wikidata.org/w/api.php"
USER_AGENT = (
    "linked-drinks-coursework/0.1 "
    "(https://github.com/NathanTrance/SemanticWeb; educational)"
)

KIND_KEYWORDS: dict[str, set[str]] = {
    "cocktail": {"cocktail", "drink", "beverage"},
    "ingredient": {
        "juice",
        "syrup",
        "bitters",
        "ingredient",
        "water",
        "sugar",
        "cream",
        "milk",
        "egg",
        "wine",
        "soda",
        "fruit",
        "herb",
        "spice",
        "food",
        "sauce",
        "extract",
        "liqueur",
        "spirit",
        "distilled",
        "drink",
        "brand",
    },
}

BLACKLIST = {
    "family name",
    "given name",
    "surname",
    "song",
    "single",
    "album",
    "film",
    "television",
    "episode",
    "video game",
    "character",
    "village",
    "municipality",
    "district",
    "species",
    "genus",
    "language",
    "company",
    "brewer",
    "racehorse",
    "painting",
    "sculpture",
    "novel",
    "band",
    "software",
    "framework",
    "asteroid",
    "crater",
    "street",
    "highway",
    "list article",
    "wikimedia",
}


def session() -> requests.Session:
    http = requests.Session()
    http.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return http


def normalize(text: str) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def search(http: "requests.Session", term: str) -> list[dict]:
    """Cached wbsearchentities lookup for one term."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE / "search" / f"{normalize(term).replace(' ', '_')}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    response = http.get(
        API,
        params={
            "action": "wbsearchentities",
            "search": term,
            "language": "en",
            "uselang": "en",
            "type": "item",
            "limit": "10",
            "format": "json",
        },
        timeout=30,
    )
    response.raise_for_status()
    candidates = response.json().get("search", [])
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    time.sleep(0.1)
    return candidates


def score(candidate: dict, kind: str) -> float:
    """Score an exact-label candidate on its description; <0 means reject."""
    description = (candidate.get("description") or "").lower()
    value = 1.0
    if any(word in description for word in KIND_KEYWORDS.get(kind, set())):
        value += 1.0
    if any(word in description for word in BLACKLIST):
        value -= 2.0
    return value


def best_match(http: "requests.Session", term: str, kind: str) -> dict | None:
    wanted = normalize(term)
    best: dict | None = None
    best_score = 0.0
    for candidate in search(http, term):
        if normalize(candidate.get("label", "")) != wanted:
            continue
        value = score(candidate, kind)
        if value > best_score:
            best, best_score = candidate, value
    if best is None:
        return None
    return {
        "qid": best["id"],
        "wd_label": best.get("label", ""),
        "description": best.get("description", ""),
        "confidence": "high" if best_score >= 2.0 else "low",
    }


def fetch_entities(http: "requests.Session", qids: list[str]) -> dict[str, dict]:
    """Batch-fetch enwiki sitelinks for a set of QIDs (50 per call)."""
    result: dict[str, dict] = {}
    for start in range(0, len(qids), 50):
        chunk = qids[start : start + 50]
        cache_file = CACHE / "entities" / f"{chunk[0]}_{chunk[-1]}.json"
        if cache_file.exists():
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
        else:
            response = http.get(
                API,
                params={
                    "action": "wbgetentities",
                    "ids": "|".join(chunk),
                    "props": "sitelinks",
                    "sitefilter": "enwiki",
                    "format": "json",
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json().get("entities", {})
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
            )
            time.sleep(0.1)
        result.update(payload)
    return result


def dbpedia_iri(entities: dict[str, dict], qid: str) -> URIRef | None:
    sitelinks = entities.get(qid, {}).get("sitelinks", {})
    title = sitelinks.get("enwiki", {}).get("title")
    if not title:
        return None
    return URIRef(DBPEDIA + quote(title.replace(" ", "_")))


def subjects(graph: Graph, rdf_type: URIRef, label_property: URIRef) -> list[tuple[str, str]]:
    return [
        (str(subject), str(label))
        for subject, label in graph.subject_objects(label_property)
        if (subject, RDF.type, rdf_type) in graph
    ]


def reconciled_subjects(graph: Graph, rdf_type: URIRef) -> list[tuple[str, str]]:
    return [
        (str(subject), str(qid))
        for subject, qid in graph.subject_objects(DCTERMS.identifier)
        if (subject, RDF.type, rdf_type) in graph
    ]


def collect_links(http: "requests.Session", graph: Graph) -> list[dict]:
    links: list[dict] = []

    for rdf_type, label_property, kind in [
        (DRINK.Cocktail, RDFS.label, "cocktail"),
        (DRINK.Ingredient, RDFS.label, "ingredient"),
    ]:
        targets = subjects(graph, rdf_type, label_property)
        for index, (subject, label) in enumerate(targets, 1):
            match = best_match(http, label, kind)
            if match:
                links.append({"subject": subject, "kind": kind, "label": label, **match})
            if index % 50 == 0:
                print(f"  {kind}: {index}/{len(targets)}")

    for rdf_type, kind in [
        (DRINK.Distillery, "distillery"),
        (DRINK.Brand, "brand"),
    ]:
        for subject, qid in reconciled_subjects(graph, rdf_type):
            links.append(
                {
                    "subject": subject,
                    "kind": kind,
                    "label": subject.rsplit("/", 1)[-1],
                    "qid": qid,
                    "label_wd": "",
                    "description": "from Wikidata collection (P31 verified)",
                    "confidence": "high",
                }
            )
    return links


def build_links_graph(graph: Graph, links: list[dict]) -> Graph:
    qids = [link["qid"] for link in links]
    http = session()
    entities = fetch_entities(http, qids)

    out = Graph()
    out.bind("owl", OWL)
    out.bind("dcterms", DCTERMS)
    out.bind("rdfs", RDFS)

    for link in links:
        subject = URIRef(link["subject"])
        wd = URIRef(WD_ENTITY + link["qid"])
        out.add((subject, OWL.sameAs, wd))
        out.add((subject, DCTERMS.source, URIRef(WD_PAGE + link["qid"])))
        dbpedia = dbpedia_iri(entities, link["qid"])
        if dbpedia is not None:
            out.add((subject, OWL.sameAs, dbpedia))
            link["dbpedia"] = str(dbpedia)
        else:
            link["dbpedia"] = ""
    return out


def write_sample(links: list[dict]) -> None:
    random.seed(42)
    sample = random.sample(links, min(50, len(links)))
    SAMPLE_CSV.parent.mkdir(parents=True, exist_ok=True)
    with SAMPLE_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "subject",
                "kind",
                "our_label",
                "wikidata_qid",
                "wikidata_description",
                "dbpedia",
                "confidence",
                "verified_true_false",
            ]
        )
        for link in sample:
            writer.writerow(
                [
                    link["subject"],
                    link["kind"],
                    link["label"],
                    link["qid"],
                    link.get("description", ""),
                    link.get("dbpedia", ""),
                    link["confidence"],
                    "",
                ]
            )
    print(f"saved {SAMPLE_CSV.relative_to(ROOT)}  ({len(sample)} links to verify)")


def main(argv: list[str]) -> int:
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=0, help="reconcile only the first N of each kind"
    )
    args = parser.parse_args(argv[1:])

    graph = Graph()
    graph.parse(DATA_TTL, format="turtle")
    http = session()
    links = collect_links(http, graph)
    if args.limit:
        links = links[: args.limit]

    out = build_links_graph(graph, links)
    LINKS_TTL.parent.mkdir(parents=True, exist_ok=True)
    out.serialize(destination=LINKS_TTL, format="turtle")
    write_sample(links)

    by_kind: dict[str, int] = {}
    dbpedia_hits = sum(1 for link in links if link.get("dbpedia"))
    for link in links:
        by_kind[link["kind"]] = by_kind.get(link["kind"], 0) + 1
    print(f"wrote {LINKS_TTL.relative_to(ROOT)}  ({len(out)} triples)")
    print(f"links by kind: {by_kind}")
    print(f"DBpedia coverage: {dbpedia_hits}/{len(links)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
