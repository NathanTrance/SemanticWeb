"""Transform the cached raw sources into one Turtle instance graph.

Step 3 of the pipeline: raw JSON (data/raw) -> RDF (data/rdf/data.ttl),
using the terms defined in ontology/drinkonto.ttl and the IRI scheme
    https://nathantrance.github.io/SemanticWeb/id/<type>/<slug>

Design notes (defensible in the report):
  * Every ingredient use is a named drink:IngredientAmount node, so a
    measure is addressable and the property chain infers hasIngredient.
  * Spirit *types* are ontology classes; we mint one instance per type so
    cocktails point at an individual, not a class (avoids OWL punning).
  * Slugs are deterministic, so re-running produces a byte-stable file.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, OWL, RDF, RDFS, SKOS, XSD

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "rdf" / "data.ttl"

DRINK = Namespace("https://nathantrance.github.io/SemanticWeb/onto#")
ID = Namespace("https://nathantrance.github.io/SemanticWeb/id/")
SCHEMA = Namespace("https://schema.org/")
GEO = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")
WD = Namespace("http://www.wikidata.org/entity/")
COCKTAILDB = "https://www.thecocktaildb.com/api/json/v1/1"

SPIRITS: dict[str, tuple[str, str]] = {
    "gin": ("Gin", "Gin"),
    "whisky": ("Whisky", "Whisky"),
    "rum": ("Rum", "Rum"),
    "vodka": ("Vodka", "Vodka"),
    "tequila": ("Tequila", "Tequila"),
    "brandy": ("Brandy", "Brandy"),
    "liqueur": ("Liqueur", "Liqueur"),
    "absinthe": ("Absinthe", "Absinthe"),
}

SPIRIT_KEYWORDS: dict[str, str] = {
    "gin": "gin",
    "whisky": "whisky",
    "whiskey": "whisky",
    "scotch": "whisky",
    "bourbon": "whisky",
    "rye": "whisky",
    "rum": "rum",
    "vodka": "vodka",
    "tequila": "tequila",
    "brandy": "brandy",
    "cognac": "brandy",
    "armagnac": "brandy",
    "absinthe": "absinthe",
    "cointreau": "liqueur",
    "amaretto": "liqueur",
    "kahlua": "liqueur",
    "sambuca": "liqueur",
    "chartreuse": "liqueur",
    "drambuie": "liqueur",
    "baileys": "liqueur",
    "campari": "liqueur",
    "triple sec": "liqueur",
}

UNICODE_FRACTIONS = {
    "½": "1/2",
    "¼": "1/4",
    "¾": "3/4",
    "⅓": "1/3",
    "⅔": "2/3",
    "⅛": "1/8",
    "⅜": "3/8",
    "⅝": "5/8",
    "⅞": "7/8",
}

COORD_RE = re.compile(r"Point\(([-\d.]+)\s+([-\d.]+)\)")


def slugify(text: str) -> str:
    """ASCII, lowercase, hyphenated slug: 'Old Fashioned' -> 'old-fashioned'."""
    normalised = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalised).strip("-").lower()
    return slug or "unnamed"


def parse_amount(text: str | None) -> tuple[float | None, str | None]:
    """Split '1 1/2 oz' into (1.5, 'oz'); return (None, None) if unparseable."""
    if not text:
        return None, None
    value = text.strip().lower()
    for glyph, fraction in UNICODE_FRACTIONS.items():
        value = value.replace(glyph, f" {fraction} ")
    value = re.sub(r"\s+", " ", value).strip()

    match = re.match(r"^(\d+)\s+(\d+)\s*/\s*(\d+)", value)
    if match:
        amount = int(match.group(1)) + int(match.group(2)) / int(match.group(3))
    else:
        match = re.match(r"^(\d+)\s*/\s*(\d+)", value)
        if match:
            amount = int(match.group(1)) / int(match.group(2))
        else:
            match = re.match(r"^(\d+(?:\.\d+)?)", value)
            if not match:
                return None, None
            amount = float(match.group(1))

    rest = value[match.end() :].strip(" .,-")
    unit = rest.split()[0] if rest else None
    return amount, unit


def detect_spirit(names: list[str]) -> str | None:
    """First ingredient whose tokens mention a known spirit wins."""
    for name in names:
        lowered = name.lower()
        for keyword, slug in SPIRIT_KEYWORDS.items():
            if re.search(rf"\b{re.escape(keyword)}\b", lowered):
                return slug
    return None


def unique_slug(used: set[tuple[str, str]], kind: str, name: str) -> str:
    """Deterministic unique slug within a kind, disambiguating collisions."""
    base = slugify(name)
    slug = base
    counter = 2
    while (kind, slug) in used:
        slug = f"{base}-{counter}"
        counter += 1
    used.add((kind, slug))
    return slug


def load(name: str) -> list[dict]:
    path = RAW / name
    return json.loads(path.read_text(encoding="utf-8"))


def _add_cocktails(graph: Graph, drinks: list[dict], used: set[tuple[str, str]]) -> None:
    for drink in drinks:
        name = drink["strDrink"].strip()
        cocktail_slug = unique_slug(used, "cocktail", name)
        node = ID[f"cocktail/{cocktail_slug}"]
        graph.add((node, RDF.type, DRINK.Cocktail))
        graph.add((node, RDFS.label, Literal(name)))
        graph.add((node, SCHEMA.name, Literal(name)))
        graph.add((node, DCTERMS.identifier, Literal(drink["idDrink"])))
        graph.add((node, DCTERMS.source, URIRef(f"{COCKTAILDB}/lookup.php?i={drink['idDrink']}")))

        if drink.get("strDrinkAlternate"):
            graph.add((node, SKOS.altLabel, Literal(drink["strDrinkAlternate"])))
        if drink.get("strInstructions"):
            graph.add((node, DRINK.preparation, Literal(drink["strInstructions"])))
            graph.add((node, SCHEMA.description, Literal(drink["strInstructions"])))
        if drink.get("strDrinkThumb"):
            graph.add((node, SCHEMA.image, URIRef(drink["strDrinkThumb"])))
            graph.add((node, FOAF.depiction, URIRef(drink["strDrinkThumb"])))
        if drink.get("strGlass"):
            glass = ID[f"glass/{slugify(drink['strGlass'])}"]
            graph.add((glass, RDF.type, DRINK.GlassType))
            graph.add((glass, RDFS.label, Literal(drink["strGlass"])))
            graph.add((node, DRINK.servedIn, glass))
        if drink.get("strIBA"):
            graph.add((node, DRINK.isIBA, Literal(True, datatype=XSD.boolean)))
            graph.add((node, DRINK.hasTag, Literal(drink["strIBA"])))
        for tag in (drink.get("strTags") or "").split(","):
            tag = tag.strip()
            if tag:
                graph.add((node, DRINK.hasTag, Literal(tag)))

        ingredient_names: list[str] = []
        measures: list[str | None] = []
        for index in range(1, 16):
            ingredient = (drink.get(f"strIngredient{index}") or "").strip()
            if not ingredient:
                continue
            ingredient_names.append(ingredient)
            measures.append(drink.get(f"strMeasure{index}"))

            ingredient_node = ID[f"ingredient/{slugify(ingredient)}"]
            graph.add((ingredient_node, RDF.type, DRINK.Ingredient))
            graph.add((ingredient_node, RDFS.label, Literal(ingredient)))
            graph.add((ingredient_node, SCHEMA.name, Literal(ingredient)))

            amount_node = ID[f"ingredient-amount/{cocktail_slug}/{index}"]
            graph.add((amount_node, RDF.type, DRINK.IngredientAmount))
            graph.add((amount_node, DRINK.ofIngredient, ingredient_node))
            graph.add((node, DRINK.usesIngredient, amount_node))
            measure = measures[-1]
            if measure and measure.strip():
                graph.add((amount_node, DRINK.amountText, Literal(measure.strip())))
                value, unit = parse_amount(measure)
                if value is not None:
                    graph.add((amount_node, DRINK.amountValue, Literal(value)))
                if unit:
                    graph.add((amount_node, DRINK.amountUnit, Literal(unit)))

        slug = detect_spirit(ingredient_names)
        if slug:
            graph.add((node, DRINK.baseSpirit, ID[f"spirit/{slug}"]))


def _add_spirit_types(graph: Graph) -> None:
    for slug, (label, class_name) in SPIRITS.items():
        node = ID[f"spirit/{slug}"]
        graph.add((node, RDF.type, DRINK.Spirit))
        graph.add((node, RDF.type, DRINK[class_name]))
        graph.add((node, RDFS.label, Literal(label)))
        graph.add((node, SCHEMA.name, Literal(label)))


def _add_places(graph: Graph, country_uri: str | None, country_label: str | None) -> URIRef | None:
    if not country_label:
        return None
    node = ID[f"place/{slugify(country_label)}"]
    graph.add((node, RDF.type, SCHEMA.Place))
    graph.add((node, RDFS.label, Literal(country_label)))
    if country_uri:
        graph.add((node, DCTERMS.identifier, Literal(country_uri.rsplit("/", 1)[-1])))
    return node


def _add_distilleries(graph: Graph, rows: list[dict], used: set[tuple[str, str]]) -> dict[str, URIRef]:
    by_qid: dict[str, dict] = {}
    for row in rows:
        qid = row["d"]["value"].rsplit("/", 1)[-1]
        entry = by_qid.setdefault(qid, {"label": row.get("dLabel", {}).get("value", qid)})
        for key in ("coord", "country", "countryLabel", "inception", "website", "image", "article"):
            if key in row:
                entry[key] = row[key]["value"]
    lookup: dict[str, URIRef] = {}
    for qid, entry in by_qid.items():
        label = entry["label"]
        node = ID[f"distillery/{unique_slug(used, 'distillery', label)}"]
        lookup[qid] = node
        graph.add((node, RDF.type, DRINK.Distillery))
        graph.add((node, RDFS.label, Literal(label)))
        graph.add((node, SCHEMA.name, Literal(label)))
        graph.add((node, DCTERMS.identifier, Literal(qid)))
        if "coord" in entry:
            match = COORD_RE.search(entry["coord"])
            if match:
                graph.add((node, GEO.long, Literal(float(match.group(1)))))
                graph.add((node, GEO.lat, Literal(float(match.group(2)))))
        if "inception" in entry:
            year = entry["inception"][:4]
            if year.isdigit():
                graph.add((node, DRINK.foundedYear, Literal(year, datatype=XSD.gYear)))
        if "website" in entry:
            graph.add((node, FOAF.homepage, URIRef(entry["website"])))
        if "image" in entry:
            graph.add((node, FOAF.depiction, URIRef(entry["image"])))
        place = _add_places(graph, entry.get("country"), entry.get("countryLabel"))
        if place:
            graph.add((node, DRINK.countryOfOrigin, place))
    return lookup


def _add_brands(
    graph: Graph,
    rows: list[dict],
    distilleries: dict[str, URIRef],
    used: set[tuple[str, str]],
) -> None:
    by_qid: dict[str, dict] = {}
    for row in rows:
        qid = row["b"]["value"].rsplit("/", 1)[-1]
        entry = by_qid.setdefault(
            qid,
            {
                "label": row.get("bLabel", {}).get("value", qid),
                "distillery": row.get("d", {}).get("value"),
                "distilleryLabel": row.get("dLabel", {}).get("value"),
            },
        )
        for key in ("country", "countryLabel", "inception", "website", "image"):
            if key in row:
                entry[key] = row[key]["value"]
    for qid, entry in by_qid.items():
        label = entry["label"]
        node = ID[f"brand/{unique_slug(used, 'brand', label)}"]
        graph.add((node, RDF.type, DRINK.Brand))
        graph.add((node, RDFS.label, Literal(label)))
        graph.add((node, SCHEMA.name, Literal(label)))
        graph.add((node, DCTERMS.identifier, Literal(qid)))
        if entry.get("website"):
            graph.add((node, FOAF.homepage, URIRef(entry["website"])))
        if entry.get("image"):
            graph.add((node, FOAF.depiction, URIRef(entry["image"])))
        place = _add_places(graph, entry.get("country"), entry.get("countryLabel"))
        if place:
            graph.add((node, DRINK.countryOfOrigin, place))

        distillery_qid = entry.get("distillery", "").rsplit("/", 1)[-1]
        distillery = distilleries.get(distillery_qid)
        if distillery is None and entry.get("distilleryLabel"):
            distillery = ID[f"distillery/{slugify(entry['distilleryLabel'])}"]
            graph.add((distillery, RDF.type, DRINK.Distillery))
            graph.add((distillery, RDFS.label, Literal(entry["distilleryLabel"])))
        if distillery is not None:
            graph.add((node, DRINK.producedBy, distillery))


def bind_prefixes(graph: Graph) -> None:
    for prefix, namespace in {
        "drink": DRINK,
        "id": ID,
        "schema": SCHEMA,
        "geo": GEO,
        "foaf": FOAF,
        "dcterms": DCTERMS,
        "skos": SKOS,
        "owl": OWL,
        "rdf": RDF,
        "rdfs": RDFS,
        "xsd": XSD,
        "wd": WD,
    }.items():
        graph.bind(prefix, namespace)


def build() -> Graph:
    graph = Graph()
    bind_prefixes(graph)
    used: set[tuple[str, str]] = set()
    _add_cocktails(graph, load("cocktaildb/drinks.json"), used)
    _add_spirit_types(graph)
    distilleries = _add_distilleries(graph, load("wikidata/distilleries.json"), used)
    _add_brands(graph, load("wikidata/brands.json"), distilleries, used)
    return graph


def main() -> int:
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
    graph = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=OUT, format="turtle")
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(graph)} triples, {generated})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
