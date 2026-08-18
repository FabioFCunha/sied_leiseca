import re
import unicodedata

from apps.inspection.models import InspectionMunicipality


def normalize_municipality_name(value):
    """
    Normaliza nomes de município para comparação.

    Exemplos:
    "São Gonçalo"   -> "SAO GONCALO"
    "  niterói  "   -> "NITEROI"
    "Rio   Claro"   -> "RIO CLARO"
    """
    if not value:
        return ""

    value = str(value).strip()

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )

    value = value.upper()
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def resolve_municipality(city):
    """
    Localiza o município cadastrado a partir do texto recebido da operação.

    Não altera o valor original da operação.
    Retorna None quando não houver correspondência segura.
    """
    normalized_name = normalize_municipality_name(city)

    if not normalized_name:
        return None

    return (
        InspectionMunicipality.objects
        .select_related("region")
        .filter(
            normalized_name=normalized_name,
            is_active=True,
            region__is_active=True,
        )
        .first()
    )


def resolve_region(city):
    """
    Retorna a região correspondente ao município informado.
    """
    municipality = resolve_municipality(city)

    if municipality is None:
        return None

    return municipality.region


def resolve_territory(city):
    """
    Retorna uma estrutura pronta para uso na estatística territorial.
    """
    normalized_name = normalize_municipality_name(city)
    municipality = resolve_municipality(city)

    if municipality is None:
        return {
            "source_city": city or "",
            "normalized_city": normalized_name,
            "matched": False,
            "municipality_id": None,
            "municipality": None,
            "region_id": None,
            "region_code": None,
            "region": None,
        }

    return {
        "source_city": city or "",
        "normalized_city": normalized_name,
        "matched": True,
        "municipality_id": municipality.id,
        "municipality": municipality.name,
        "region_id": municipality.region_id,
        "region_code": municipality.region.code,
        "region": municipality.region.name,
    }