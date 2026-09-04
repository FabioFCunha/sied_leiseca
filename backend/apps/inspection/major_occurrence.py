import re
import unicodedata


MAJOR_OCCURRENCE_RULES = (
    ("Atropelamento ou tentativa de atropelamento", 5, ("atropel",)),
    ("Ferimento envolvendo integrante", 5, ("policial ferid", "agente ferid", "integrante ferid")),
    ("Atendimento hospitalar ou internação", 4, ("hospital", "internad", "ambulancia", "atendimento medico")),
    ("Arma ou munição", 4, ("arma de fogo", "pistola", "revolver", "municao")),
    ("Morte", 5, ("obito", "falecimento", "morte")),
    ("Agressão ou ameaça", 4, ("agress", "ameaca")),
    ("Perseguição ou evasão relevante", 2, ("persegu", "evadiu", "evasao")),
    ("Registro policial", 2, ("delegacia", "registro policial", "boletim de ocorrencia", "b.a.m", "bam n")),
    ("Apoio policial emergencial", 2, ("apoio do", "apoio policial", "socorro")),
)


def _normalize(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip().lower()


def report_major_occurrence_analysis(report):
    parts = [
        report.changes_general,
        report.miscellaneous_changes,
        report.change_ols,
        report.change_support,
        report.changes_material,
        report.low_approach_reasons,
    ]
    for operation in report.operations.all():
        parts.extend(
            [
                operation.changes_material,
                operation.vehicle_resolutions,
                operation.administrative_tests,
            ]
        )

    text = _normalize(" ".join(str(part or "") for part in parts))
    score = 0
    reasons = []
    for label, points, terms in MAJOR_OCCURRENCE_RULES:
        if any(term in text for term in terms):
            score += points
            reasons.append(label)

    return {
        "suspected": score >= 5,
        "score": score,
        "reasons": reasons,
    }
