from django.test import TestCase

from apps.inspection.models import (
    InspectionMunicipality,
    InspectionRegion,
)
from apps.inspection.territorial import (
    normalize_municipality_name,
    resolve_municipality,
    resolve_region,
    resolve_territory,
)


class InspectionTerritorialTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.metropolitana = InspectionRegion.objects.get(
            code="METROPOLITANA",
        )
        cls.norte_fluminense = InspectionRegion.objects.get(
            code="NORTE_FLUMINENSE",
        )
        cls.costa_verde = InspectionRegion.objects.get(
            code="COSTA_VERDE",
        )

        cls.niteroi = InspectionMunicipality.objects.get(
            normalized_name="NITEROI",
        )
        cls.sao_goncalo = InspectionMunicipality.objects.get(
            normalized_name="SAO GONCALO",
        )
        cls.macae = InspectionMunicipality.objects.get(
            normalized_name="MACAE",
        )
        cls.paraty = InspectionMunicipality.objects.get(
            normalized_name="PARATY",
        )

    def test_database_has_8_regions(self):
        self.assertEqual(
            InspectionRegion.objects.count(),
            8,
        )

    def test_database_has_92_municipalities(self):
        self.assertEqual(
            InspectionMunicipality.objects.count(),
            92,
        )

    def test_every_municipality_has_region(self):
        self.assertEqual(
            InspectionMunicipality.objects.filter(
                region__isnull=True,
            ).count(),
            0,
        )

    def test_normalize_municipality_name_removes_accents(self):
        self.assertEqual(
            normalize_municipality_name("São Gonçalo"),
            "SAO GONCALO",
        )

    def test_normalize_municipality_name_converts_to_uppercase(self):
        self.assertEqual(
            normalize_municipality_name("niterói"),
            "NITEROI",
        )

    def test_normalize_municipality_name_removes_extra_spaces(self):
        self.assertEqual(
            normalize_municipality_name(
                "  Rio   de   Janeiro  "
            ),
            "RIO DE JANEIRO",
        )

    def test_normalize_municipality_name_removes_punctuation(self):
        self.assertEqual(
            normalize_municipality_name(
                "São-Pedro da aldeia"
            ),
            "SAO PEDRO DA ALDEIA",
        )

    def test_normalize_municipality_name_empty_value(self):
        self.assertEqual(
            normalize_municipality_name(""),
            "",
        )

        self.assertEqual(
            normalize_municipality_name(None),
            "",
        )

    def test_resolve_municipality_with_accent(self):
        municipality = resolve_municipality("Niterói")

        self.assertIsNotNone(municipality)
        self.assertEqual(
            municipality.name,
            "Niterói",
        )
        self.assertEqual(
            municipality.region.name,
            "Metropolitana",
        )

    def test_resolve_municipality_without_accent(self):
        municipality = resolve_municipality("NITEROI")

        self.assertIsNotNone(municipality)
        self.assertEqual(
            municipality.name,
            "Niterói",
        )

    def test_resolve_municipality_lowercase(self):
        municipality = resolve_municipality("são gonçalo")

        self.assertIsNotNone(municipality)
        self.assertEqual(
            municipality.name,
            "São Gonçalo",
        )

    def test_resolve_region_metropolitana(self):
        region = resolve_region("São Gonçalo")

        self.assertIsNotNone(region)
        self.assertEqual(
            region.code,
            "METROPOLITANA",
        )
        self.assertEqual(
            region.name,
            "Metropolitana",
        )

    def test_resolve_region_norte_fluminense(self):
        region = resolve_region("Macaé")

        self.assertIsNotNone(region)
        self.assertEqual(
            region.code,
            "NORTE_FLUMINENSE",
        )
        self.assertEqual(
            region.name,
            "Norte Fluminense",
        )

    def test_resolve_region_costa_verde(self):
        region = resolve_region("Paraty")

        self.assertIsNotNone(region)
        self.assertEqual(
            region.code,
            "COSTA_VERDE",
        )
        self.assertEqual(
            region.name,
            "Costa Verde",
        )

    def test_unknown_municipality_returns_none(self):
        municipality = resolve_municipality(
            "Municipio Inexistente"
        )

        self.assertIsNone(municipality)

    def test_unknown_region_returns_none(self):
        region = resolve_region(
            "Municipio Inexistente"
        )

        self.assertIsNone(region)

    def test_resolve_territory_returns_complete_structure(self):
        result = resolve_territory("Niterói")

        self.assertTrue(
            result["matched"],
        )
        self.assertEqual(
            result["source_city"],
            "Niterói",
        )
        self.assertEqual(
            result["normalized_city"],
            "NITEROI",
        )
        self.assertEqual(
            result["municipality"],
            "Niterói",
        )
        self.assertEqual(
            result["municipality_id"],
            self.niteroi.id,
        )
        self.assertEqual(
            result["region"],
            "Metropolitana",
        )
        self.assertEqual(
            result["region_code"],
            "METROPOLITANA",
        )
        self.assertEqual(
            result["region_id"],
            self.metropolitana.id,
        )

    def test_resolve_territory_unknown_municipality(self):
        result = resolve_territory(
            "Municipio Inexistente"
        )

        self.assertFalse(
            result["matched"],
        )
        self.assertEqual(
            result["normalized_city"],
            "MUNICIPIO INEXISTENTE",
        )
        self.assertIsNone(
            result["municipality_id"],
        )
        self.assertIsNone(
            result["municipality"],
        )
        self.assertIsNone(
            result["region_id"],
        )
        self.assertIsNone(
            result["region_code"],
        )
        self.assertIsNone(
            result["region"],
        )

    def test_resolve_territory_empty_city(self):
        result = resolve_territory("")

        self.assertFalse(
            result["matched"],
        )
        self.assertEqual(
            result["source_city"],
            "",
        )
        self.assertEqual(
            result["normalized_city"],
            "",
        )
        self.assertIsNone(
            result["municipality"],
        )
        self.assertIsNone(
            result["region"],
        )

    def test_inactive_municipality_is_not_resolved(self):
        self.niteroi.is_active = False
        self.niteroi.save(
            update_fields=["is_active"],
        )

        municipality = resolve_municipality(
            "Niterói"
        )

        self.assertIsNone(
            municipality,
        )

    def test_municipality_from_inactive_region_is_not_resolved(self):
        self.metropolitana.is_active = False
        self.metropolitana.save(
            update_fields=["is_active"],
        )

        municipality = resolve_municipality(
            "São Gonçalo"
        )

        self.assertIsNone(
            municipality,
        )

    def test_known_typo_ruo_de_janeiro_resolves_to_rio_de_janeiro(self):
        result = resolve_territory(
            "Ruo de janeiro"
        )

        self.assertTrue(
            result["matched"]
        )

        self.assertEqual(
            result["municipality"],
            "Rio de Janeiro",
        )

        self.assertEqual(
            result["region_code"],
            "METROPOLITANA",
        )

    def test_alias_rj_resolves_to_rio_de_janeiro(self):
        result = resolve_territory("RJ")

        self.assertTrue(result["matched"])
        self.assertEqual(
            result["municipality"],
            "Rio de Janeiro",
        )

    def test_alias_imbarie_resolves_to_duque_de_caxias(self):
        result = resolve_territory("Imbariê")

        self.assertTrue(result["matched"])
        self.assertEqual(
            result["municipality"],
            "Duque de Caxias",
        )

    def test_alias_com_levy_gasparian_resolves_to_official_name(self):
        result = resolve_territory(
            "Com.Levy Gasparian"
        )

        self.assertTrue(result["matched"])
        self.assertEqual(
            result["municipality"],
            "Comendador Levy Gasparian",
        )

    def test_case_and_accent_variations_resolve_to_official_name(self):
        result = resolve_territory(
            "Casimiro de abreu"
        )

        self.assertTrue(result["matched"])
        self.assertEqual(
            result["municipality"],
            "Casimiro de Abreu",
        )

        result = resolve_territory(
            "São Pedro da aldeia"
        )

        self.assertTrue(result["matched"])
        self.assertEqual(
            result["municipality"],
            "São Pedro da Aldeia",
        )

        result = resolve_territory(
            "Três rios"
        )

        self.assertTrue(result["matched"])
        self.assertEqual(
            result["municipality"],
            "Três Rios",
        )

    def test_all_92_registered_municipalities_can_be_resolved(self):
        municipalities = (
            InspectionMunicipality.objects
            .select_related("region")
            .filter(
                is_active=True,
                region__is_active=True,
            )
        )

        self.assertEqual(
            municipalities.count(),
            92,
        )

        for municipality in municipalities:
            with self.subTest(
                municipality=municipality.name,
            ):
                result = resolve_territory(
                    municipality.name
                )

                self.assertTrue(
                    result["matched"],
                )
                self.assertEqual(
                    result["municipality_id"],
                    municipality.id,
                )
                self.assertEqual(
                    result["municipality"],
                    municipality.name,
                )
                self.assertEqual(
                    result["region_id"],
                    municipality.region_id,
                )
                self.assertEqual(
                    result["region"],
                    municipality.region.name,
                )

    def test_all_92_normalized_names_are_unique(self):
        total = InspectionMunicipality.objects.count()

        unique_total = (
            InspectionMunicipality.objects
            .values("normalized_name")
            .distinct()
            .count()
        )

        self.assertEqual(
            total,
            92,
        )
        self.assertEqual(
            unique_total,
            92,
        )
