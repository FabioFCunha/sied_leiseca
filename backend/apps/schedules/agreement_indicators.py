from django.db import models


class EducationAgreementIndicator(models.TextChoices):
    ESCOLINHA_NOTA_10 = "ESCOLINHA_NOTA_10", "Escolinha Nota 10"
    ESCOLA_NOTA_10 = "ESCOLA_NOTA_10", "Escola Nota 10"


class EducationActionAgeRange(models.TextChoices):
    AGE_05_10 = "AGE_05_10", "05 - 10 anos (ensino fundamental - anos iniciais)"
    AGE_11_14 = "AGE_11_14", "11 - 14 anos (ensino fundamental - anos finais)"
    AGE_15_17 = "AGE_15_17", "15 - 17 anos (ensino médio)"
    AGE_ADULT = "AGE_ADULT", "acima de 18 anos - Adultos"


class RequesterEntityKind(models.TextChoices):
    SCHOOL = "SCHOOL", "Instituição de Ensino"
    BUSINESS = "BUSINESS", "Empresa"
    EVENT_ORGANIZATION = "EVENT_ORGANIZATION", "Organização de Evento"
    MILITARY = "MILITARY", "Órgão Militar"
    PUBLIC = "PUBLIC", "Órgão Público"
    OTHER = "OTHER", "Outros"
    ADMINISTRATIVE = "ADMINISTRATIVE", "Demanda Administrativa"


class RequesterEntityNature(models.TextChoices):
    PUBLIC = "PUBLIC", "Pública"
    PRIVATE = "PRIVATE", "Privada"
    NOT_APPLICABLE = "NOT_APPLICABLE", "Não se aplica"


_SCHOOL_MARKERS = ("instituição de ensino", "instituicao de ensino", "escola", "colégio", "colegio")
_PUBLIC_MARKERS = (" público", " pública", "publico", "publica")
_PRIVATE_MARKERS = (" privado", " privada", "privado", "privada", "particular")

_AGENDA_AGE_RANGE_MAP = {
    "05 - 10 anos (ensino fundamental - anos iniciais)": EducationActionAgeRange.AGE_05_10,
    "11 - 14 anos (ensino fundamental - anos finais)": EducationActionAgeRange.AGE_11_14,
    "15 - 17 anos (ensino médio)": EducationActionAgeRange.AGE_15_17,
    "acima de 18 anos - Adultos": EducationActionAgeRange.AGE_ADULT,
}


def normalize_entity_type(requester_entity_type_str):
    text = str(requester_entity_type_str or "").strip()
    if not text:
        return None, None

    if text == "Demanda Administrativa" or text == RequesterEntityKind.ADMINISTRATIVE:
        return RequesterEntityKind.ADMINISTRATIVE, RequesterEntityNature.NOT_APPLICABLE

    if text == RequesterEntityKind.SCHOOL:
        return RequesterEntityKind.SCHOOL, None
    if text == RequesterEntityKind.BUSINESS:
        return RequesterEntityKind.BUSINESS, None
    if text == RequesterEntityKind.EVENT_ORGANIZATION:
        return RequesterEntityKind.EVENT_ORGANIZATION, None
    if text == RequesterEntityKind.MILITARY:
        return RequesterEntityKind.MILITARY, None
    if text == RequesterEntityKind.PUBLIC:
        return RequesterEntityKind.PUBLIC, None
    if text == RequesterEntityKind.OTHER:
        return RequesterEntityKind.OTHER, None

    if text == "2":
        return RequesterEntityKind.SCHOOL, None
    if text == "4":
        return RequesterEntityKind.BUSINESS, None
    if text == "1":
        return RequesterEntityKind.PUBLIC, None

    text_lower = text.lower()
    nature = None
    if any(marker in text_lower for marker in _PUBLIC_MARKERS):
        nature = RequesterEntityNature.PUBLIC
    elif any(marker in text_lower for marker in _PRIVATE_MARKERS):
        nature = RequesterEntityNature.PRIVATE

    if any(marker in text_lower for marker in _SCHOOL_MARKERS):
        return RequesterEntityKind.SCHOOL, nature

    if "empresa" in text_lower:
        return RequesterEntityKind.BUSINESS, nature

    if "organização de evento" in text_lower or "organizacao de evento" in text_lower:
        return RequesterEntityKind.EVENT_ORGANIZATION, nature

    if "militar" in text_lower:
        return RequesterEntityKind.MILITARY, nature

    if "órgão" in text_lower or "orgao" in text_lower:
        return RequesterEntityKind.PUBLIC, nature

    return None, None


def normalize_age_range(age_text):
    text = str(age_text or "").strip()
    if not text:
        return None

    if text in EducationActionAgeRange.values:
        return text

    return _AGENDA_AGE_RANGE_MAP.get(text)


def derive_education_agreement_indicator(kind, nature, age_range):
    internal_age = normalize_age_range(age_range)
    if (
        kind != RequesterEntityKind.SCHOOL
        or nature != RequesterEntityNature.PUBLIC
        or not internal_age
    ):
        return None

    if internal_age in (EducationActionAgeRange.AGE_05_10, EducationActionAgeRange.AGE_11_14):
        return EducationAgreementIndicator.ESCOLINHA_NOTA_10

    if internal_age in (EducationActionAgeRange.AGE_15_17, EducationActionAgeRange.AGE_ADULT):
        return EducationAgreementIndicator.ESCOLA_NOTA_10

    return None


def derive_from_agenda(agenda):
    if not agenda:
        return None
    req_type = getattr(agenda, "requester_entity_type", "") if hasattr(agenda, "requester_entity_type") else agenda.get("requester_entity_type", "")
    age_ranges = getattr(agenda, "age_ranges", "") if hasattr(agenda, "age_ranges") else agenda.get("age_ranges", "")
    kind, nature = normalize_entity_type(req_type)
    return derive_education_agreement_indicator(kind, nature, age_ranges)
