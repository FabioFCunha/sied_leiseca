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


def _remove_zero_house_number(value):
    return re.sub(
        r"(?i)(?:,\s*0|(?:,\s*|\s+)n(?:[º°]|o|[úu]mero)\.?\s*0)$",
        "",
        value,
    ).rstrip(" ,")


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
    address = _remove_zero_house_number(_clean_component(getattr(agenda, "address", "")))
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


def _emit_diagnostic(diagnostic, message):
    if diagnostic is not None:
        diagnostic(f"[geocoding] {message}")


def geocode_address(
    address,
    *,
    base_url=None,
    user_agent=None,
    timeout=None,
    opener=urlopen,
    diagnostic=None,
):
    if not address:
        _emit_diagnostic(diagnostic, "Não encontrado: endereço normalizado vazio.")
        return None
    service_url = base_url or os.getenv("NOMINATIM_BASE_URL", DEFAULT_NOMINATIM_URL)
    identifying_agent = user_agent or os.getenv("NOMINATIM_USER_AGENT", DEFAULT_USER_AGENT)
    request_timeout = float(timeout or os.getenv("NOMINATIM_TIMEOUT", "10"))
    query = urlencode({"format": "jsonv2", "limit": 1, "countrycodes": "br", "q": address})
    request = Request(
        f"{service_url.rstrip('?')}?{query}",
        headers={"Accept": "application/json", "User-Agent": identifying_agent},
    )
    _emit_diagnostic(diagnostic, f"URL final: {request.full_url}")
    try:
        with opener(request, timeout=request_timeout) as response:
            status = getattr(response, "status", None)
            if status is None:
                getcode = getattr(response, "getcode", None)
                status = getcode() if callable(getcode) else "indisponível"
            response_body = response.read().decode("utf-8")
            body_preview = re.sub(r"\s+", " ", response_body).strip()[:240]
            _emit_diagnostic(diagnostic, f"Status HTTP: {status}")
            _emit_diagnostic(diagnostic, f"Corpo da resposta (até 240 caracteres): {body_preview}")
            payload = json.loads(response_body)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, HTTPError):
            _emit_diagnostic(diagnostic, f"Status HTTP: {exc.code}")
        _emit_diagnostic(
            diagnostic,
            f"Exceção/timeout: {type(exc).__name__}: {str(exc)[:240]}",
        )
        raise GeocodingError("Falha ao consultar o serviço de geocodificação.") from exc
    result_count = len(payload) if isinstance(payload, list) else 0
    _emit_diagnostic(diagnostic, f"Quantidade de resultados: {result_count}")
    if not payload:
        _emit_diagnostic(diagnostic, "Não encontrado: o serviço retornou zero resultados.")
        return None
    try:
        latitude = Decimal(str(payload[0]["lat"]))
        longitude = Decimal(str(payload[0]["lon"]))
    except (KeyError, TypeError, InvalidOperation) as exc:
        _emit_diagnostic(
            diagnostic,
            f"Exceção: coordenadas inválidas ({type(exc).__name__}: {str(exc)[:240]}).",
        )
        raise GeocodingError("O serviço de geocodificação retornou coordenadas inválidas.") from exc
    if not (Decimal("-90") <= latitude <= Decimal("90") and Decimal("-180") <= longitude <= Decimal("180")):
        _emit_diagnostic(diagnostic, "Exceção: coordenadas retornadas estão fora dos limites válidos.")
        raise GeocodingError("O serviço de geocodificação retornou coordenadas fora dos limites válidos.")
    return latitude, longitude
