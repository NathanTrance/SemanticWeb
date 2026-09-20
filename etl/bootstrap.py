"""Fetch the two raw sources into data/raw/ and record provenance.

Step 1 of the build pipeline in PLANNING.md (the "star 1/2/3" material):
  - TheCocktailDB public API  -> all cocktails with ingredients + measures
  - Wikidata SPARQL           -> distilleries (Q1251750) with coords, country,
                                 founding year, website, image and article

Everything is cached: re-running is a no-op unless --force is given, so the
pipeline is reproducible and the report can cite exactly what was fetched.
A manifest (data/raw/manifest.json) records URL, fetch time, licence, record
count and a sha256 of each dump.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "manifest.json"

COCKTAILDB_API = "https://www.thecocktaildb.com/api/json/v1/1"
COCKTAILDB_SOURCE = f"{COCKTAILDB_API}/search.php?f=<a-z0-9>"
COCKTAILDB_LICENCE = "TheCocktailDB - free for non-commercial use (test key 1)"
WIKIDATA_SOURCE = "Wikidata Query Service - items with P31 wd:Q1251750 (distillery)"
WIKIDATA_LICENCE = "Wikidata - CC0 1.0"
WIKIDATA_BRAND_SOURCE = (
    "Wikidata Query Service - spirits (P31/P279* wd:Q56139) with "
    "manufacturer (P176) a distillery (P31 wd:Q1251750)"
)
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
USER_AGENT = (
    "linked-drinks-coursework/0.1 "
    "(https://github.com/NathanTrance/SemanticWeb; educational)"
)

WIKIDATA_BRAND_QUERY = """
SELECT ?b ?bLabel ?d ?dLabel ?country ?countryLabel ?inception ?website ?image ?article WHERE {
  ?b wdt:P31/wdt:P279* wd:Q56139 .
  ?b wdt:P176 ?d .
  ?d wdt:P31 wd:Q1251750 .
  OPTIONAL { ?b wdt:P495 ?country . }
  OPTIONAL { ?b wdt:P571 ?inception . }
  OPTIONAL { ?b wdt:P856 ?website . }
  OPTIONAL { ?b wdt:P18 ?image . }
  OPTIONAL { ?article schema:about ?b ; schema:isPartOf <https://en.wikipedia.org/> . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""

WIKIDATA_DISTILLERY_QUERY = """
SELECT ?d ?dLabel ?coord ?country ?countryLabel ?inception ?website ?image ?article WHERE {
  ?d wdt:P31 wd:Q1251750 .
  OPTIONAL { ?d wdt:P625 ?coord . }
  OPTIONAL { ?d wdt:P17 ?country . }
  OPTIONAL { ?d wdt:P571 ?inception . }
  OPTIONAL { ?d wdt:P856 ?website . }
  OPTIONAL { ?d wdt:P18 ?image . }
  OPTIONAL { ?article schema:about ?d ; schema:isPartOf <https://en.wikipedia.org/> . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,de,fr,es". }
}
"""


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    retry = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, payload: object, count: int, source: str, licence: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "source": source,
        "licence": licence,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "records": count,
        "sha256": _sha256(path),
    }


def fetch_cocktaildb(session: requests.Session, force: bool = False) -> dict:
    """Fetch every cocktail via the per-letter search endpoint, dedup by id."""
    out = RAW / "cocktaildb" / "drinks.json"
    if out.exists() and not force:
        print(f"cache hit  {out.relative_to(ROOT)}")
        return _entry_from(out, COCKTAILDB_SOURCE, COCKTAILDB_LICENCE)

    drinks: dict[str, dict] = {}
    for letter in "abcdefghijklmnopqrstuvwxyz0123456789":
        url = f"{COCKTAILDB_API}/search.php"
        response = session.get(url, params={"f": letter}, timeout=30)
        response.raise_for_status()
        batch = response.json().get("drinks") or []
        for drink in batch:
            drinks[drink["idDrink"]] = drink
        print(f"CocktailDB  '{letter}': +{len(batch):3d}   total {len(drinks)}")
        time.sleep(0.2)

    payload = sorted(drinks.values(), key=lambda d: d["strDrink"])
    return _write(
        out, payload, len(payload), COCKTAILDB_SOURCE, COCKTAILDB_LICENCE
    )


def _fetch_sparql(
    session: requests.Session,
    query: str,
    out: Path,
    source: str,
    licence: str,
    force: bool = False,
) -> dict:
    """Run a Wikidata SPARQL query, caching the JSON bindings on disk."""
    if out.exists() and not force:
        print(f"cache hit  {out.relative_to(ROOT)}")
        return _entry_from(out, source, licence)

    response = session.get(
        WIKIDATA_SPARQL, params={"query": query, "format": "json"}, timeout=180
    )
    response.raise_for_status()
    bindings = response.json()["results"]["bindings"]
    return _write(out, bindings, len(bindings), source, licence)


def fetch_wikidata_distilleries(session: requests.Session, force: bool = False) -> dict:
    """Run the distillery SPARQL query and store the bindings."""
    return _fetch_sparql(
        session,
        WIKIDATA_DISTILLERY_QUERY,
        RAW / "wikidata" / "distilleries.json",
        WIKIDATA_SOURCE,
        WIKIDATA_LICENCE,
        force,
    )


def fetch_wikidata_brands(session: requests.Session, force: bool = False) -> dict:
    """Run the spirit-brand SPARQL query and store the bindings."""
    return _fetch_sparql(
        session,
        WIKIDATA_BRAND_QUERY,
        RAW / "wikidata" / "brands.json",
        WIKIDATA_BRAND_SOURCE,
        WIKIDATA_LICENCE,
        force,
    )


def _entry_from(path: Path, source: str, licence: str) -> dict:
    """Rebuild a manifest entry for a file already on disk."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "source": source,
        "licence": licence,
        "fetched_at": datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        ).isoformat(timespec="seconds"),
        "records": len(payload),
        "sha256": _sha256(path),
    }


def write_manifest(entries: list[dict]) -> None:
    MANIFEST.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"manifest   {MANIFEST.relative_to(ROOT)} ({len(entries)} source(s))")


def main(argv: list[str]) -> int:
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="ignore cache and re-download"
    )
    args = parser.parse_args(argv[1:])

    session = _session()
    entries = [
        fetch_cocktaildb(session, args.force),
        fetch_wikidata_distilleries(session, args.force),
        fetch_wikidata_brands(session, args.force),
    ]
    write_manifest(entries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
