from datetime import date

from django.test import TestCase

from apps.inspection.horus_historical_push import (
    HorusHistorical2022PushService,
    HorusHistoricalPushConflict,
    HorusHistoricalPushError,
    HorusHistoricalRainUpdateService,
)
from apps.inspection.models import (
    HistoricalSourceType,
    HistoricalTaxonomyEra,
    InspectionHistoricalStatistic,
)


class HorusHistoricalMaintenanceTests(
    TestCase
):
    def setUp(self):
        self.sha256 = "a" * 64

    def payload_2022(
        self,
        **overrides,
    ):
        payload = {
            "source_type": (
                HistoricalSourceType.DAILY
            ),
            "taxonomy_era": (
                HistoricalTaxonomyEra.ERA_C
            ),
            "reference_date": (
                date(2022, 10, 3)
            ),
            "team": "BRAVO",
            "source_row": 1,
            "reports_count": 1,
            "operations_count": 1,
            "rain": 1,
            "approach": 100,
            "reconductor": 5,
            "refusal": 7,
            "fined": 20,
            "towed": 2,
            "cnh_collected": 3,
            "four_ml": 88,
            "thirtythree_ml": 1,
            "thirtyfour_ml": 0,
            "passive_tests_performed": 50,
            "removal_resolutions": 10,
            "arrests_means_evidence": 0,
            "art307": 1,
            "criminal_occurrences": 0,
            "driving_canceled_license": 0,
        }

        payload.update(
            overrides
        )

        return payload

    def test_import_2022_creates_record_with_rain(
        self,
    ):
        result = (
            HorusHistorical2022PushService()
            .push_single(
                self.payload_2022(),
                file_sha256=self.sha256,
            )
        )

        self.assertEqual(
            result["result"],
            "created",
        )

        stat = (
            InspectionHistoricalStatistic
            .objects
            .get(
                reference_date=date(
                    2022,
                    10,
                    3,
                ),
                team="BRAVO",
                source_type=(
                    HistoricalSourceType.DAILY
                ),
                taxonomy_era=(
                    HistoricalTaxonomyEra.ERA_C
                ),
            )
        )

        self.assertEqual(
            stat.rain,
            1,
        )
        self.assertEqual(
            stat.historical_approached,
            100,
        )
        self.assertEqual(
            stat.refusal,
            7,
        )

    def test_import_2022_is_idempotent(
        self,
    ):
        service = (
            HorusHistorical2022PushService()
        )

        first = service.push_single(
            self.payload_2022(),
            file_sha256=self.sha256,
        )

        second = service.push_single(
            self.payload_2022(),
            file_sha256=self.sha256,
        )

        self.assertEqual(
            first["result"],
            "created",
        )
        self.assertEqual(
            second["result"],
            "already_exists",
        )
        self.assertEqual(
            InspectionHistoricalStatistic
            .objects
            .count(),
            1,
        )

    def test_import_2022_conflict_does_not_overwrite(
        self,
    ):
        service = (
            HorusHistorical2022PushService()
        )

        service.push_single(
            self.payload_2022(),
            file_sha256=self.sha256,
        )

        with self.assertRaises(
            HorusHistoricalPushConflict
        ):
            service.push_single(
                self.payload_2022(
                    approach=999,
                ),
                file_sha256=self.sha256,
            )

        stat = (
            InspectionHistoricalStatistic
            .objects
            .get(
                reference_date=date(
                    2022,
                    10,
                    3,
                ),
                team="BRAVO",
            )
        )

        self.assertEqual(
            stat.historical_approached,
            100,
        )

    def test_import_2022_rejects_date_outside_extension(
        self,
    ):
        with self.assertRaises(
            HorusHistoricalPushError
        ):
            (
                HorusHistorical2022PushService()
                .push_single(
                    self.payload_2022(
                        reference_date=date(
                            2023,
                            1,
                            1,
                        )
                    ),
                    file_sha256=self.sha256,
                )
            )

    def test_update_rain_changes_only_rain(
        self,
    ):
        (
            HorusHistorical2022PushService()
            .push_single(
                self.payload_2022(
                    rain=0,
                ),
                file_sha256=self.sha256,
            )
        )

        stat = (
            InspectionHistoricalStatistic
            .objects
            .get(
                reference_date=date(
                    2022,
                    10,
                    3,
                ),
                team="BRAVO",
            )
        )

        original_approach = (
            stat.historical_approached
        )
        original_refusal = (
            stat.refusal
        )
        original_fined = (
            stat.fined
        )

        result = (
            HorusHistoricalRainUpdateService()
            .update_single(
                {
                    "source_type": (
                        HistoricalSourceType.DAILY
                    ),
                    "taxonomy_era": (
                        HistoricalTaxonomyEra.ERA_C
                    ),
                    "reference_date": date(
                        2022,
                        10,
                        3,
                    ),
                    "team": "BRAVO",
                    "rain": 2,
                }
            )
        )

        self.assertEqual(
            result["result"],
            "updated",
        )

        stat.refresh_from_db()

        self.assertEqual(
            stat.rain,
            2,
        )
        self.assertEqual(
            stat.historical_approached,
            original_approach,
        )
        self.assertEqual(
            stat.refusal,
            original_refusal,
        )
        self.assertEqual(
            stat.fined,
            original_fined,
        )

    def test_update_rain_missing_record_is_rejected(
        self,
    ):
        with self.assertRaises(
            HorusHistoricalPushError
        ):
            (
                HorusHistoricalRainUpdateService()
                .update_single(
                    {
                        "source_type": (
                            HistoricalSourceType.DAILY
                        ),
                        "taxonomy_era": (
                            HistoricalTaxonomyEra.ERA_C
                        ),
                        "reference_date": date(
                            2023,
                            1,
                            1,
                        ),
                        "team": "BRAVO",
                        "rain": 1,
                    }
                )
            )
