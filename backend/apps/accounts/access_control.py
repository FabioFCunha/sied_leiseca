from rest_framework.permissions import SAFE_METHODS


EDUCATION = "EDUCATION"
INSPECTION = "INSPECTION"
VALID_ACCESS_AREAS = {EDUCATION, INSPECTION}


def normalized_access_areas(user):
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    if getattr(user, "is_superuser", False):
        return set(VALID_ACCESS_AREAS)
    areas = getattr(user, "access_areas", None)
    if areas is None:
        return set(VALID_ACCESS_AREAS)
    return {str(area).upper() for area in areas if str(area).upper() in VALID_ACCESS_AREAS}


def has_access_area(user, area):
    return str(area).upper() in normalized_access_areas(user)


def is_creator(user):
    return bool(user and getattr(user, "is_superuser", False))


def is_read_only_user(user):
    return bool(user and not is_creator(user) and getattr(user, "is_read_only", False))


def can_write_request(user, method):
    return method in SAFE_METHODS or not is_read_only_user(user)
