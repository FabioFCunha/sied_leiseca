from datetime import date
from types import SimpleNamespace
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.schedules.models import ActionType
from apps.statistics.models import ConsolidatedStatistic
from apps.statistics.services import _parse_materials, aggregate_official_statistics, generate_statistics_for_report
from apps.statistics.views import StatisticsComparisonView, get_hybrid_queryset


class OfficialStatisticsTests(TestCase):
    def setUp(self):
        self.action = ActionType.objects.get(name='A\u00e7\u00e3o')
        self.lecture = ActionType.objects.get(name='Palestra')

        self.user = get_user_model().objects.create_user(email='statistics-test@example.com', password='test')
    def stat(self, indicator, value, *, action=None, entity=None, methodology='SIED_OPERATIONAL', reference_date=date(2026, 7, 10), status='ACTIVE', trace='test'):
        return ConsolidatedStatistic.objects.create(
            reference_date=reference_date if methodology == 'SIED_OPERATIONAL' else None,
            reference_year=(reference_date or date(2026, 1, 1)).year,
            reference_month=reference_date.month if reference_date and methodology == 'SIED_OPERATIONAL' else None,
            indicator_type=indicator, category_action_type=action,
            category_entity_type=entity, value=value, methodology=methodology,
            traceability_id=f'{trace}_{ConsolidatedStatistic.objects.count()}', status=status,
        )

    def test_audience_general_does_not_sum_subtotals(self):
        self.stat('AUDIENCE', 100)
        self.stat('AUDIENCE', 60, action=self.lecture, entity='TOTAL')
        self.stat('AUDIENCE', 40, action=self.action, entity='TOTAL')
        totals = aggregate_official_statistics(ConsolidatedStatistic.objects.all())
        self.assertEqual(totals['AUDIENCE - Geral'], 100)
        self.assertEqual(totals['AUDIENCE - PALESTRAS'], 60)
        self.assertEqual(totals['AUDIENCE - ACOES'], 40)

    def test_action_total_does_not_sum_operational_details(self):
        self.stat('ACTION', 3, action=self.action, entity='TOTAL')
        self.stat('ACTION', 2, action=self.action, entity='BARES')
        self.stat('ACTION', 1, action=self.action, entity='PEDAGIO')
        totals = aggregate_official_statistics(ConsolidatedStatistic.objects.all())
        self.assertEqual(totals['ACTION - Geral'], 3)
        self.assertEqual(totals['ACTION - Bares'], 2)
        self.assertEqual(totals['ACTION - Ped\u00e1gio'], 1)

    def test_legacy_action_total_is_rebuilt_from_details_once(self):
        self.stat('ACTION', 2, entity='Escola', methodology='HISTORICAL_LEGACY')
        self.stat('ACTION', 3, entity='Bares', methodology='HISTORICAL_LEGACY')
        totals = aggregate_official_statistics(ConsolidatedStatistic.objects.all())
        self.assertEqual(totals['ACTION - Geral'], 5)

    def test_material_parser_supports_text_and_json(self):
        self.assertEqual(_parse_materials('Certificado | 3\nRevistinha - 2\nFolder | 4'), (9, 3, 2))
        self.assertEqual(_parse_materials('[{"name":"Certificados","quantity":2},{"material":"Gibi Soprinho","count":5}]'), (7, 2, 5))

    @override_settings(STATISTICS_CUTOFF_DATE='2026-07-09')
    def test_hybrid_queryset_respects_period_methodology_and_status(self):
        self.stat('AUDIENCE', 10, methodology='HISTORICAL_LEGACY', trace='legacy')
        self.stat('AUDIENCE', 20, reference_date=date(2026, 7, 10), trace='inside')
        self.stat('AUDIENCE', 30, reference_date=date(2026, 7, 25), trace='outside')
        self.stat('AUDIENCE', 40, reference_date=date(2026, 7, 12), status='SUSPENDED', trace='suspended')
        qs = get_hybrid_queryset(date(2026, 1, 1), date(2026, 7, 24))
        self.assertEqual(aggregate_official_statistics(qs)['AUDIENCE - Geral'], 30)

    @override_settings(STATISTICS_CUTOFF_DATE='2026-07-09')
    def test_comparison_cards_use_official_totals(self):
        self.stat('AUDIENCE', 100)
        self.stat('AUDIENCE', 60, action=self.lecture, entity='TOTAL')
        self.stat('ACTION', 3, action=self.action, entity='TOTAL')
        self.stat('ACTION', 3, action=self.action, entity='BARES')
        request = APIRequestFactory().get('/statistics/comparison/', {'date_from': '2026-07-09', 'date_to': '2026-07-24', 'prev_date_from': '2025-01-01', 'prev_date_to': '2025-12-31'})
        force_authenticate(request, user=self.user)
        response = StatisticsComparisonView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['macro_current']['AUDIENCE'], 100)
        self.assertEqual(response.data['macro_current']['ACTION'], 3)
        self.assertEqual(response.data['current_period']['ACTION - Bares'], 3)

    def test_generate_is_idempotent_and_uses_action_materials(self):
        agenda = SimpleNamespace(action_type_ref=self.action, action_type='', requester_entity_type='7')
        action = SimpleNamespace(agenda=agenda, type_action='A\u00e7\u00e3o', distribution_materials_distributed='Certificados | 2\nRevistinha | 3')
        report = SimpleNamespace(id=999, status='APPROVED', operation_date=date(2026, 7, 10), created_at=None, approximate_public=25, distribution_materials_distributed='', actions=SimpleNamespace(all=lambda: [action]), statistics_processed=False, statistics_processed_at=None, statistics_processed_by=None, save=lambda **kwargs: None)
        generate_statistics_for_report(report)
        first_count = ConsolidatedStatistic.objects.filter(traceability_id='report_999').count()
        generate_statistics_for_report(report)
        second_count = ConsolidatedStatistic.objects.filter(traceability_id='report_999').count()
        self.assertEqual(first_count, second_count)
        materials = ConsolidatedStatistic.objects.get(traceability_id='report_999', indicator_type='MATERIAL', category_action_type__isnull=True, category_entity_type__isnull=True)
        self.assertEqual(materials.value, 5)

    def test_missing_canonical_action_type_has_clear_error(self):
        self.action.delete()
        agenda = SimpleNamespace(action_type_ref=SimpleNamespace(name='A\u00e7\u00e3o'), action_type='', requester_entity_type='7')
        action = SimpleNamespace(agenda=agenda, type_action='A\u00e7\u00e3o', distribution_materials_distributed='')
        report = SimpleNamespace(id=1000, status='APPROVED', operation_date=date(2026, 7, 10), created_at=None, approximate_public=1, distribution_materials_distributed='', actions=SimpleNamespace(all=lambda: [action]), statistics_processed=False, statistics_processed_at=None, statistics_processed_by=None, save=lambda **kwargs: None)
        with self.assertRaisesMessage(ValueError, 'nao cadastrado'):
            generate_statistics_for_report(report)
