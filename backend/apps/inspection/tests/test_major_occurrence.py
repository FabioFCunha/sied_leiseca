from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.inspection.major_occurrence import report_major_occurrence_analysis


class OperationsStub:
    def __init__(self, operations=None):
        self.operations = operations or []

    def all(self):
        return self.operations


def report_with_text(text):
    return SimpleNamespace(
        changes_general=text,
        miscellaneous_changes="",
        change_ols="",
        change_support="",
        changes_material="",
        low_approach_reasons="",
        operations=OperationsStub(),
    )


class MajorOccurrenceAnalysisTests(SimpleTestCase):
    def test_detects_high_relevance_incident_from_synced_report_text(self):
        analysis = report_major_occurrence_analysis(
            report_with_text(
                "Motociclista tentou atropelar uma policial, que foi conduzida "
                "ao hospital e permaneceu internada. O fato foi registrado na delegacia."
            )
        )

        self.assertTrue(analysis["suspected"])
        self.assertGreaterEqual(analysis["score"], 5)
        self.assertIn(
            "Atropelamento ou tentativa de atropelamento",
            analysis["reasons"],
        )

    def test_does_not_flag_ordinary_operational_observation(self):
        analysis = report_major_occurrence_analysis(
            report_with_text(
                "Operação realizada em sistema de abre e fecha devido ao fluxo de veículos."
            )
        )

        self.assertFalse(analysis["suspected"])
        self.assertEqual(analysis["score"], 0)
