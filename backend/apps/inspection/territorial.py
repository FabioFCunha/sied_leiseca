import re
import unicodedata

from apps.inspection.models import (
    InspectionMunicipality,
    InspectionRegion,
)


MUNICIPALITY_ALIASES = {
    "RUO DE JANEIRO": "RIO DE JANEIRO",
    "RJ": "RIO DE JANEIRO",
    "IMBARIE": "DUQUE DE CAXIAS",
    "COM LEVY GASPARIAN": (
        "COMENDADOR LEVY GASPARIAN"
    ),
}


def _canonicalize_text(value):
    text = unicodedata.normalize(
        "NFKD",
        value,
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(
            character
        )
    )

    text = text.upper()

    text = re.sub(
        r"[^A-Z0-9]+",
        " ",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def normalize_municipality_name(value):
    if value is None:
        return ""

    text = str(value).strip()

    if not text:
        return ""

    text = _canonicalize_text(text)

    return MUNICIPALITY_ALIASES.get(
        text,
        text,
    )


def resolve_municipality(city):
    normalized_city = (
        normalize_municipality_name(
            city
        )
    )

    if not normalized_city:
        return None

    municipalities = list(
        InspectionMunicipality.objects
        .select_related("region")
        .filter(
            is_active=True,
            region__is_active=True,
        )
    )

    for municipality in municipalities:
        if (
            municipality.normalized_name
            == normalized_city
        ):
            return municipality

    canonical_matches = [
        municipality
        for municipality in municipalities
        if _canonicalize_text(
            municipality.normalized_name
        )
        == normalized_city
    ]

    if len(canonical_matches) == 1:
        return canonical_matches[0]

    return None


def resolve_region(city):
    municipality = (
        resolve_municipality(city)
    )

    if municipality is None:
        return None

    return municipality.region


def resolve_territory(city):
    source_city = (
        ""
        if city is None
        else str(city)
    )

    normalized_city = (
        normalize_municipality_name(
            source_city
        )
    )

    municipality = (
        resolve_municipality(
            source_city
        )
    )

    if municipality is None:
        return {
            "source_city": source_city,
            "normalized_city": (
                normalized_city
            ),
            "matched": False,
            "municipality_id": None,
            "municipality": None,
            "region_id": None,
            "region_code": None,
            "region": None,
        }

    region = municipality.region

    return {
        "source_city": source_city,
        "normalized_city": (
            normalized_city
        ),
        "matched": True,
        "municipality_id": (
            municipality.id
        ),
        "municipality": (
            municipality.name
        ),
        "region_id": region.id,
        "region_code": region.code,
        "region": region.name,
    }
