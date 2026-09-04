import re
import unicodedata


def _value(action, field, default=None):
    if isinstance(action, dict):
        return action.get(field, default)
    return getattr(action, field, default)


def _normalized(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _minutes(value):
    match = re.fullmatch(r"\s*(\d{1,2})\s*(?::|h)\s*(\d{2})\s*", str(value or ""), re.IGNORECASE)
    if not match:
        return None
    hour, minute = map(int, match.groups())
    if hour > 23 or minute > 59:
        return None
    return hour * 60 + minute


def _material_rows(value):
    rows = []
    for line in str(value or "").splitlines():
        text = line.strip()
        if not text:
            continue
        text = re.sub(r"\[\s*\]", "| 0", text)
        if "|" in text:
            name, quantity = [part.strip() for part in text.rsplit("|", 1)]
        else:
            match = re.match(r"^(.*?)\s+-\s*(\d+)\s*$", text)
            if not match:
                continue
            name, quantity = match.groups()
        number = re.search(r"\d+", quantity)
        if name and number:
            rows.append((name, int(number.group(0))))
    return rows


def _is_kit(name):
    return "kit" in _normalized(name).split()


def _numeric_value(action, field):
    try:
        return max(0, int(_value(action, field, 0) or 0))
    except (TypeError, ValueError):
        return 0


def _action_audience(action, index):
    """Use the same audience rule applied by official education statistics."""
    lectures = _numeric_value(action, "approached_lectures")
    if index == 0 and lectures > 0:
        return lectures
    return _numeric_value(action, "approached_actions")


def education_action_consistency_errors(actions):
    """Return per-action errors for material/audience and overlapping times."""
    actions = list(actions or [])
    errors = {}

    def add(index, field, message):
        errors.setdefault(str(index), {}).setdefault(field, []).append(message)

    intervals = []
    for index, action in enumerate(actions):
        audience = _action_audience(action, index)
        for material_name, quantity in _material_rows(_value(action, "distribution_materials_distributed", "")):
            if _is_kit(material_name) and quantity > audience:
                add(
                    index,
                    "distribution_materials_distributed",
                    f"Ação {index + 1}: a quantidade de '{material_name}' distribuída ({quantity}) "
                    f"não pode ser maior que o público alcançado ({audience}).",
                )

        start = _minutes(_value(action, "start_time"))
        end = _minutes(_value(action, "final_hour"))
        if start is None or end is None:
            continue
        if end <= start:
            end += 24 * 60
        intervals.append((start, end, index))

    for position, (start, end, index) in enumerate(intervals):
        for other_start, other_end, other_index in intervals[position + 1:]:
            overlaps = any(
                start < other_end + shift and other_start + shift < end
                for shift in (-24 * 60, 0, 24 * 60)
            )
            if overlaps:
                message = (
                    f"Ação {other_index + 1}: o horário informado conflita com a Ação {index + 1}. "
                    "As atividades do mesmo relatório não podem ocorrer em horários sobrepostos."
                )
                add(other_index, "start_time", message)

    return errors
