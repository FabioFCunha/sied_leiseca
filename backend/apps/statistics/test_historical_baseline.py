from django.test import SimpleTestCase

from apps.statistics.historical_baseline import HISTORICAL_BASELINE


class HistoricalEducationBaselineTests(SimpleTestCase):
    def test_2020_audience_total_matches_lectures_and_actions(self):
        values = HISTORICAL_BASELINE[2020]

        self.assertEqual(values["AUDIENCE - PALESTRAS"], 3674)
        self.assertEqual(values["AUDIENCE - ACOES"], 51751)
        self.assertEqual(
            values["AUDIENCE - PALESTRAS"] + values["AUDIENCE - ACOES"],
            55425,
        )
        self.assertEqual(values["AUDIENCE - Geral"], 55425)

    def test_2025_action_categories_match_official_total(self):
        values = HISTORICAL_BASELINE[2025]
        keys = (
            "ACTION - Bares",
            "ACTION - Pedágio",
            "ACTION - Praças Esportivas",
            "ACTION - Praia",
            "ACTION - Eventos",
            "ACTION - Shopping",
            "ACTION - Praças/Parques Públicos",
            "ACTION - Pontos turísticos",
            "ACTION - Ação Social",
            "ACTION - Outros",
            "ACTION - Ação conjunta com a fiscalização",
        )

        self.assertEqual([values[key] for key in keys], [207, 4, 10, 68, 195, 40, 0, 0, 3, 1014, 0])
        self.assertEqual(sum(values[key] for key in keys), 1541)
        self.assertEqual(values["ACTION - Geral"], 1541)

    def test_2018_historical_action_compatibility_is_preserved(self):
        values = HISTORICAL_BASELINE[2018]

        self.assertEqual(values["ACTION - Geral"], 726)
        self.assertEqual(values["LECTURES - Geral"], 310)
        self.assertEqual(values["ACTION - Geral"] - values["LECTURES - Geral"], 416)
