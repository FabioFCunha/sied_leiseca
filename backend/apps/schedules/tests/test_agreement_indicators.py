from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.schedules.models import (
    Agenda,
    EducationReport,
    EducationAction,
    ActionType,
    Sector,
)
from apps.schedules.serializers import AgendaSerializer, EducationActionSerializer, EducationReportSerializer
from apps.schedules.agreement_indicators import (
    derive_education_agreement_indicator,
    derive_from_agenda,
    normalize_entity_type,
    normalize_age_range,
    EducationAgreementIndicator,
    EducationActionAgeRange,
    RequesterEntityKind,
    RequesterEntityNature,
)
from apps.statistics.models import ConsolidatedStatistic
from apps.statistics.services import generate_statistics_for_report

User = get_user_model()


class AgreementIndicatorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpassword",
            role=User.Role.ADMIN,
        )
        self.sector = Sector.objects.create(name="Operacional", is_active=True)

        self.action_palestra, _ = ActionType.objects.update_or_create(
            name="Palestra", defaults={"is_active": True, "category": ActionType.Category.LECTURE}
        )
        self.action_acao, _ = ActionType.objects.update_or_create(
            name="Ação", defaults={"is_active": True, "category": ActionType.Category.EDUCATIONAL_ACTION}
        )
        self.action_escola_nota_10, _ = ActionType.objects.update_or_create(
            name="Escola Nota 10", defaults={"is_active": True, "category": ActionType.Category.PROGRAM_INDICATOR}
        )
        self.action_escolinha_nota_10, _ = ActionType.objects.update_or_create(
            name="Escolinha Nota 10", defaults={"is_active": True, "category": ActionType.Category.PROGRAM_INDICATOR}
        )
        self.action_palestra_escola, _ = ActionType.objects.update_or_create(
            name="Palestra Escola", defaults={"is_active": False, "category": ActionType.Category.LECTURE}
        )
        self.action_palestra_escola_publica, _ = ActionType.objects.update_or_create(
            name="Palestra Escola Pública", defaults={"is_active": True, "category": ActionType.Category.LECTURE}
        )
        self.action_palestra_escola_privada, _ = ActionType.objects.update_or_create(
            name="Palestra Escola Privada", defaults={"is_active": True, "category": ActionType.Category.LECTURE}
        )

    def _make_agenda(self, **kwargs):
        defaults = dict(
            title="Ação Teste",
            description="Descrição Teste",
            location="Local Teste",
            responsible=self.user,
            created_by=self.user,
            date=date(2026, 8, 20),
            start_time="09:00",
            end_time="12:00",
            sector=self.sector,
            action_type_ref=self.action_palestra,
        )
        defaults.update(kwargs)
        return Agenda.objects.create(**defaults)

    # ==========================================================
    # 1. Agenda permanece sem age_range novo
    # ==========================================================
    def test_01_agenda_has_no_age_range_field(self):
        """Agenda model must NOT have an 'age_range' column (only age_ranges)."""
        field_names = [f.name for f in Agenda._meta.get_fields()]
        self.assertNotIn("age_range", field_names)
        self.assertIn("age_ranges", field_names)

    # ==========================================================
    # 2. Agenda.age_ranges histórico continua serializável
    # ==========================================================
    def test_02_agenda_age_ranges_serializable(self):
        agenda = self._make_agenda(
            requester_entity_type="Instituição de Ensino Público",
            age_ranges="05 - 10 anos (ensino fundamental - anos iniciais)",
        )
        serializer = AgendaSerializer(agenda)
        data = serializer.data
        self.assertEqual(data["age_ranges"], "05 - 10 anos (ensino fundamental - anos iniciais)")

    # ==========================================================
    # 3. Serializer calcula predicted_agreement_indicator
    # ==========================================================
    def test_03_serializer_computes_predicted_agreement_indicator(self):
        agenda = self._make_agenda(
            requester_entity_type="Instituição de Ensino Público",
            age_ranges="05 - 10 anos (ensino fundamental - anos iniciais)",
        )
        serializer = AgendaSerializer(agenda)
        data = serializer.data
        self.assertEqual(data["predicted_agreement_indicator"], EducationAgreementIndicator.ESCOLINHA_NOTA_10)
        self.assertEqual(data["predicted_agreement_indicator_label"], "Escolinha Nota 10")

    # ==========================================================
    # 4. predicted_agreement_indicator é read-only
    # ==========================================================
    def test_04_predicted_agreement_indicator_is_read_only(self):
        data = {
            "title": "Teste read-only",
            "description": "Descrição",
            "location": "Local",
            "responsible": self.user.id,
            "date": "2026-09-10",
            "start_time": "09:00",
            "end_time": "12:00",
            "sector": self.sector.id,
            "predicted_agreement_indicator": "ESCOLA_NOTA_10",
        }
        serializer = AgendaSerializer(data=data)
        if serializer.is_valid():
            self.assertNotIn("predicted_agreement_indicator", serializer.validated_data)

    # ==========================================================
    # 5. Primeira ação normaliza dados da Agenda
    # ==========================================================
    def test_05_first_action_normalizes_agenda_data(self):
        agenda = self._make_agenda(
            requester_entity_type="Instituição de Ensino Público",
            age_ranges="05 - 10 anos (ensino fundamental - anos iniciais)",
            action_type="Palestra Escola Pública",
            action_type_ref=self.action_palestra_escola_publica,
        )
        serializer = EducationReportSerializer(data={
            "agenda": agenda.id,
            "operation_date": "2026-08-20",
            "team": "ALFA",
            "actions": [
                {
                    "type_action": "Palestra Escola Pública",
                    "approached_lectures": 30,
                }
            ],
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        report = serializer.save(created_by=self.user)
        action = EducationAction.objects.get(report=report)
        self.assertEqual(action.requester_entity_kind, RequesterEntityKind.SCHOOL)
        self.assertEqual(action.requester_entity_nature, RequesterEntityNature.PUBLIC)
        self.assertEqual(action.age_range, EducationActionAgeRange.AGE_05_10)
        self.assertEqual(action.agreement_indicator, EducationAgreementIndicator.ESCOLINHA_NOTA_10)

    # ==========================================================
    # 6. Valor textual 05–10 vira AGE_05_10
    # ==========================================================
    def test_06_normalize_05_10(self):
        self.assertEqual(
            normalize_age_range("05 - 10 anos (ensino fundamental - anos iniciais)"),
            EducationActionAgeRange.AGE_05_10,
        )

    # ==========================================================
    # 7. Valor textual 11–14 vira AGE_11_14
    # ==========================================================
    def test_07_normalize_11_14(self):
        self.assertEqual(
            normalize_age_range("11 - 14 anos (ensino fundamental - anos finais)"),
            EducationActionAgeRange.AGE_11_14,
        )

    # ==========================================================
    # 8. Valor textual 15–17 vira AGE_15_17
    # ==========================================================
    def test_08_normalize_15_17(self):
        self.assertEqual(
            normalize_age_range("15 - 17 anos (ensino médio)"),
            EducationActionAgeRange.AGE_15_17,
        )

    # ==========================================================
    # 9. Valor textual Adultos vira AGE_ADULT
    # ==========================================================
    def test_09_normalize_adultos(self):
        self.assertEqual(
            normalize_age_range("acima de 18 anos - Adultos"),
            EducationActionAgeRange.AGE_ADULT,
        )
        self.assertIsNone(normalize_age_range("Adultos"))

    # ==========================================================
    # 10. AGE_ADULT gera ESCOLA_NOTA_10
    # ==========================================================
    def test_10_age_adult_generates_escola_nota_10(self):
        result = derive_education_agreement_indicator(
            kind=RequesterEntityKind.SCHOOL,
            nature=RequesterEntityNature.PUBLIC,
            age_range=EducationActionAgeRange.AGE_ADULT,
        )
        self.assertEqual(result, EducationAgreementIndicator.ESCOLA_NOTA_10)

    # ==========================================================
    # 11. Valor legado desconhecido não gera convênio
    # ==========================================================
    def test_11_unknown_legacy_value_no_agreement(self):
        result = derive_education_agreement_indicator(
            kind=RequesterEntityKind.SCHOOL,
            nature=RequesterEntityNature.PUBLIC,
            age_range="valor desconhecido legado",
        )
        self.assertIsNone(result)

    # ==========================================================
    # 12. Ação adicional inicia vazia
    # ==========================================================
    def test_12_additional_action_starts_empty(self):
        data = {
            "type_action": "",
            "approach": 0,
        }
        serializer = EducationActionSerializer(data=data)
        if serializer.is_valid():
            self.assertIsNone(serializer.validated_data.get("agreement_indicator"))

    # ==========================================================
    # 13. Spoofing é ignorado
    # ==========================================================
    def test_13_spoofing_ignored(self):
        data = {
            "type_action": "Palestra",
            "requester_entity_kind": RequesterEntityKind.SCHOOL,
            "requester_entity_nature": RequesterEntityNature.PUBLIC,
            "age_range": EducationActionAgeRange.AGE_05_10,
            "agreement_indicator": "ESCOLA_NOTA_10",  # Spoofed
            "approach": 50,
        }
        serializer = EducationActionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data.get("agreement_indicator"),
            EducationAgreementIndicator.ESCOLINHA_NOTA_10,
        )

    # ==========================================================
    # 14. Alteração incompatível limpa o indicador
    # ==========================================================
    def test_14_incompatible_change_clears_indicator(self):
        agenda = self._make_agenda(
            requester_entity_type="Instituição de Ensino Público",
            age_ranges="05 - 10 anos (ensino fundamental - anos iniciais)",
        )
        action = EducationAction.objects.create(
            report=EducationReport.objects.create(
                agenda=agenda,
                created_by=self.user,
                status=EducationReport.ReportStatus.DRAFT,
                operation_date=date(2026, 8, 20),
            ),
            agenda=agenda,
            type_action="Palestra Escola Pública",
            requester_entity_kind=RequesterEntityKind.SCHOOL,
            requester_entity_nature=RequesterEntityNature.PUBLIC,
            age_range=EducationActionAgeRange.AGE_05_10,
            agreement_indicator=EducationAgreementIndicator.ESCOLINHA_NOTA_10,
        )
        serializer = EducationActionSerializer(
            instance=action,
            data={
                "type_action": "Palestra Escola Privada",
                "requester_entity_kind": RequesterEntityKind.SCHOOL,
                "requester_entity_nature": RequesterEntityNature.PRIVATE,
                "age_range": EducationActionAgeRange.AGE_05_10,
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertIsNone(updated.agreement_indicator)

    # ==========================================================
    # 15. Não existem campos duplicados no model
    # ==========================================================
    def test_15_no_duplicate_fields_on_education_action(self):
        field_names = [f.name for f in EducationAction._meta.get_fields()]
        for field_name in ["requester_entity_kind", "requester_entity_nature", "age_range", "agreement_indicator"]:
            count = field_names.count(field_name)
            self.assertEqual(count, 1, f"Field '{field_name}' appears {count} times on EducationAction")

    # ==========================================================
    # 16. Migration 0076 não adiciona campos à Agenda
    # ==========================================================
    def test_16_migration_0076_no_agenda_fields(self):
        import importlib
        mod = importlib.import_module("apps.schedules.migrations.0076_actiontype_category_and_educationaction_fields")
        migration_cls = mod.Migration
        for op in migration_cls.operations:
            if hasattr(op, "model_name"):
                self.assertNotEqual(
                    op.model_name.lower(), "agenda",
                    f"Migration 0076 must not alter Agenda, but found operation on model '{op.model_name}'",
                )

    # ==========================================================
    # 17. Palestra Escola fica inativa
    # ==========================================================
    def test_17_palestra_escola_is_inactive(self):
        import importlib

        migration = importlib.import_module("apps.schedules.migrations.0077_deactivate_palestra_escola")
        ActionType.objects.filter(name="Palestra Escola").update(is_active=True, category=None)
        class FakeApps:
            @staticmethod
            def get_model(app_label, model_name):
                self.assertEqual(app_label, "schedules")
                self.assertEqual(model_name, "ActionType")
                return ActionType

        migration.categorize_and_deactivate_actions(apps=FakeApps(), schema_editor=None)
        pe = ActionType.objects.get(name="Palestra Escola")
        self.assertFalse(pe.is_active)
        self.assertEqual(pe.category, ActionType.Category.LECTURE)

    # ==========================================================
    # 18. Histórico com Palestra Escola permanece legível
    # ==========================================================
    def test_18_historical_palestra_escola_readable(self):
        agenda = self._make_agenda(action_type="Palestra Escola", action_type_ref=self.action_palestra_escola)
        serializer = AgendaSerializer(agenda)
        data = serializer.data
        self.assertEqual(data["action_type"], "Palestra Escola")

    # ==========================================================
    # 19. Snapshot adulto entra em Escola Nota 10
    # ==========================================================
    def test_19_adult_snapshot_escola_nota_10(self):
        agenda = self._make_agenda(
            requester_entity_type="Instituição de Ensino Público",
            age_ranges="acima de 18 anos - Adultos",
        )
        report = EducationReport.objects.create(
            agenda=agenda,
            created_by=self.user,
            status=EducationReport.ReportStatus.APPROVED,
            operation_date=date(2026, 8, 20),
            approximate_public=80,
        )
        EducationAction.objects.create(
            report=report,
            agenda=agenda,
            type_action="Palestra",
            requester_entity_kind=RequesterEntityKind.SCHOOL,
            requester_entity_nature=RequesterEntityNature.PUBLIC,
            age_range=EducationActionAgeRange.AGE_ADULT,
            agreement_indicator=EducationAgreementIndicator.ESCOLA_NOTA_10,
            approached_lectures=80,
        )

        generate_statistics_for_report(report, processed_by=self.user)

        stats = ConsolidatedStatistic.objects.filter(
            traceability_id=f"report_{report.id}",
            category_entity_type="EDUCATIONAL_AGREEMENT",
            status="ACTIVE",
        )
        action_stat = stats.filter(indicator_type="ACTION").first()
        self.assertIsNotNone(action_stat)
        self.assertEqual(action_stat.category_action_type.name, "Escola Nota 10")

    # ==========================================================
    # 20. Total geral não duplica
    # ==========================================================
    def test_20_total_does_not_duplicate(self):
        agenda = self._make_agenda(
            requester_entity_type="Instituição de Ensino Público",
            age_ranges="15 - 17 anos (ensino médio)",
        )
        report = EducationReport.objects.create(
            agenda=agenda,
            created_by=self.user,
            status=EducationReport.ReportStatus.APPROVED,
            operation_date=date(2026, 8, 20),
            approximate_public=100,
        )
        EducationAction.objects.create(
            report=report,
            agenda=agenda,
            type_action="Palestra",
            requester_entity_kind=RequesterEntityKind.SCHOOL,
            requester_entity_nature=RequesterEntityNature.PUBLIC,
            age_range=EducationActionAgeRange.AGE_15_17,
            agreement_indicator=EducationAgreementIndicator.ESCOLA_NOTA_10,
            approached_lectures=100,
        )

        generate_statistics_for_report(report, processed_by=self.user)
        stats = ConsolidatedStatistic.objects.filter(
            traceability_id=f"report_{report.id}",
            status="ACTIVE",
        )
        palestra_total = stats.get(
            indicator_type="ACTION",
            category_action_type__name="Palestra",
            category_entity_type="TOTAL",
        )
        self.assertEqual(float(palestra_total.value), 1.0)
        palestra_audience = stats.get(
            indicator_type="AUDIENCE",
            category_action_type__name="Palestra",
            category_entity_type="TOTAL",
        )
        self.assertEqual(float(palestra_audience.value), 100.0)
        agreement_action = stats.get(
            indicator_type="ACTION",
            category_action_type__name="Escola Nota 10",
            category_entity_type="EDUCATIONAL_AGREEMENT",
        )
        self.assertEqual(float(agreement_action.value), 1.0)

    def test_dashboard_exposes_educational_agreement(self):
        from django.core.cache import cache
        from apps.statistics.dashboard import dashboard_payload

        agenda = self._make_agenda(
            requester_entity_type="Instituição de Ensino Público",
            age_ranges="15 - 17 anos (ensino médio)",
        )
        report = EducationReport.objects.create(
            agenda=agenda,
            created_by=self.user,
            status=EducationReport.ReportStatus.APPROVED,
            operation_date=date(2026, 8, 20),
        )
        EducationAction.objects.create(
            report=report,
            agenda=agenda,
            type_action="Palestra",
            requester_entity_kind=RequesterEntityKind.SCHOOL,
            requester_entity_nature=RequesterEntityNature.PUBLIC,
            age_range=EducationActionAgeRange.AGE_15_17,
            agreement_indicator=EducationAgreementIndicator.ESCOLA_NOTA_10,
            approached_lectures=35,
        )
        generate_statistics_for_report(report, processed_by=self.user)
        cache.clear()

        payload = dashboard_payload(date(2026, 8, 1), date(2026, 8, 31), {})
        self.assertIn(
            {
                "code": "ESCOLA_NOTA_10",
                "label": "Escola Nota 10",
                "actions": 1,
                "audience": 35,
            },
            payload["educational_agreements"]["items"],
        )

    # ==========================================================
    # Additional: Serializer rejects Palestra Escola
    # ==========================================================
    def test_education_action_serializer_rejects_palestra_escola(self):
        data = {
            "type_action": "Palestra Escola",
            "approach": 30,
        }
        serializer = EducationActionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("type_action", serializer.errors)

    def test_historical_palestra_escola_report_can_be_updated(self):
        agenda = self._make_agenda(
            action_type="Palestra Escola",
            action_type_ref=self.action_palestra_escola,
        )
        report = EducationReport.objects.create(
            agenda=agenda,
            created_by=self.user,
            status=EducationReport.ReportStatus.DRAFT,
            operation_date=date(2026, 8, 20),
        )
        action = EducationAction.objects.create(
            report=report,
            agenda=agenda,
            type_action="Palestra Escola",
            institution_name="Escola histórica",
        )

        serializer = EducationReportSerializer(
            instance=report,
            data={
                "team": "ALFA",
                "actions": [{
                    "id": action.id,
                    "type_action": "Palestra Escola",
                    "institution_name": "Escola histórica atualizada",
                }],
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.actions.get().type_action, "Palestra Escola")
        self.assertEqual(updated.actions.get().institution_name, "Escola histórica atualizada")

    # ==========================================================
    # Additional: Serializer rejects program indicator type
    # ==========================================================
    def test_education_action_serializer_rejects_program_indicator(self):
        data = {
            "type_action": "Escola Nota 10",
            "approach": 30,
        }
        serializer = EducationActionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("type_action", serializer.errors)

    # ==========================================================
    # Additional: Agenda serializer rejects inactive action_type_ref
    # ==========================================================
    def test_agenda_serializer_rejects_inactive_action_type_ref(self):
        data = {
            "title": "Ação Teste",
            "description": "Descrição Teste",
            "location": "Local Teste",
            "responsible": self.user.id,
            "date": "2026-09-10",
            "start_time": "09:00",
            "end_time": "12:00",
            "action_type_ref": self.action_palestra_escola.id,
            "sector": self.sector.id,
        }
        serializer = AgendaSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("action_type_ref", serializer.errors)

    # ==========================================================
    # Additional: derive_from_agenda works correctly
    # ==========================================================
    def test_derive_from_agenda_helper(self):
        agenda = self._make_agenda(
            requester_entity_type="Instituição de Ensino Público",
            age_ranges="15 - 17 anos (ensino médio)",
        )
        result = derive_from_agenda(agenda)
        self.assertEqual(result, EducationAgreementIndicator.ESCOLA_NOTA_10)

    def test_derive_from_agenda_private(self):
        agenda = self._make_agenda(
            requester_entity_type="Instituição de Ensino Privado",
            age_ranges="05 - 10 anos (ensino fundamental - anos iniciais)",
        )
        result = derive_from_agenda(agenda)
        self.assertIsNone(result)

    def test_derive_from_agenda_no_data(self):
        agenda = self._make_agenda(requester_entity_type="", age_ranges="")
        result = derive_from_agenda(agenda)
        self.assertIsNone(result)

    def test_administrative_demand_normalizes_without_agreement_indicator(self):
        kind, nature = normalize_entity_type("Demanda Administrativa")
        self.assertEqual(kind, RequesterEntityKind.ADMINISTRATIVE)
        self.assertEqual(nature, RequesterEntityNature.NOT_APPLICABLE)
        self.assertIsNone(
            derive_education_agreement_indicator(
                kind,
                nature,
                EducationActionAgeRange.AGE_15_17,
            )
        )

    def test_administrative_demand_action_is_accepted_and_persisted(self):
        agenda = self._make_agenda(
            requester_entity_type="Demanda Administrativa",
            age_ranges="15 - 17 anos (ensino médio)",
        )
        serializer = EducationReportSerializer(data={
            "agenda": agenda.id,
            "operation_date": "2026-08-20",
            "team": "ALFA",
            "actions": [{
                "type_action": "Palestra",
                "requester_entity_kind": RequesterEntityKind.ADMINISTRATIVE,
                "requester_entity_nature": RequesterEntityNature.NOT_APPLICABLE,
                "age_range": EducationActionAgeRange.AGE_15_17,
            }],
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        report = serializer.save(created_by=self.user)
        action = report.actions.get()
        self.assertEqual(action.requester_entity_kind, RequesterEntityKind.ADMINISTRATIVE)
        self.assertEqual(action.requester_entity_nature, RequesterEntityNature.NOT_APPLICABLE)
        self.assertIsNone(action.agreement_indicator)

    def test_administrative_demand_first_action_inherits_persisted_values(self):
        agenda = self._make_agenda(
            requester_entity_type="Demanda Administrativa",
            age_ranges="15 - 17 anos (ensino médio)",
        )
        serializer = EducationReportSerializer(data={
            "agenda": agenda.id,
            "operation_date": "2026-08-20",
            "team": "ALFA",
            "actions": [{"type_action": "Palestra"}],
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        report = serializer.save(created_by=self.user)
        action = report.actions.get()
        self.assertEqual(action.requester_entity_kind, RequesterEntityKind.ADMINISTRATIVE)
        self.assertEqual(action.requester_entity_nature, RequesterEntityNature.NOT_APPLICABLE)
        self.assertIsNone(action.agreement_indicator)
