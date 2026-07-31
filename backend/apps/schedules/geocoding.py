import json
import os
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_USER_AGENT = "SIED-Agenda-Geocoder/1.0"


class GeocodingError(Exception):
    pass


def _clean_component(value):
    text = re.sub(r"\s+", " ", str(value or "").strip())
    return re.sub(r"\s*,\s*", ", ", text).strip(" ,")


def _comparable(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _contains_component(address, component):
    address_key = _comparable(address)
    component_key = _comparable(component)
    if not address_key or not component_key:
        return False
    return re.search(rf"(?:^|\s){re.escape(component_key)}(?:$|\s)", address_key) is not None


def normalize_agenda_address(agenda):
    address = _clean_component(getattr(agenda, "address", ""))
    if not address:
        return ""

    neighborhood_ref = getattr(agenda, "neighborhood_ref", None)
    municipality_ref = getattr(agenda, "municipality_ref", None)
    components = [
        address,
        _clean_component(getattr(agenda, "neighborhood", "") or getattr(neighborhood_ref, "name", "")),
        _clean_component(getattr(agenda, "city", "") or getattr(municipality_ref, "name", "")),
        _clean_component(getattr(agenda, "state", "")),
        "Brasil",
    ]
    normalized = []
    for component in components:
        if component and not _contains_component(", ".join(normalized), component):
            normalized.append(component)
    return ", ".join(normalized)


def geocode_address(address, *, base_url=None, user_agent=None, timeout=None, opener=urlopen):
    if not address:
        return None
    service_url = base_url or os.getenv("NOMINATIM_BASE_URL", DEFAULT_NOMINATIM_URL)
    identifying_agent = user_agent or os.getenv("NOMINATIM_USER_AGENT", DEFAULT_USER_AGENT)
    request_timeout = float(timeout or os.getenv("NOMINATIM_TIMEOUT", "10"))
    query = urlencode({"format": "jsonv2", "limit": 1, "countrycodes": "br", "q": address})
    request = Request(
        f"{service_url.rstrip('?')}?{query}",
        headers={"Accept": "application/json", "User-Agent": identifying_agent},
    )
    try:
        with opener(request, timeout=request_timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise GeocodingError("Falha ao consultar o serviço de geocodificação.") from exc
    if not payload:
        return None
    try:
        latitude = Decimal(str(payload[0]["lat"]))
        longitude = Decimal(str(payload[0]["lon"]))
    except (KeyError, TypeError, InvalidOperation) as exc:
        raise GeocodingError("O serviço de geocodificação retornou coordenadas inválidas.") from exc
    if not (Decimal("-90") <= latitude <= Decimal("90") and Decimal("-180") <= longitude <= Decimal("180")):
        raise GeocodingError("O serviço de geocodificação retornou coordenadas fora dos limites válidos.")
    return latitude, longitude
