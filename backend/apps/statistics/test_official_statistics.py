from datetime import date
from types import SimpleNamespace
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.schedules.models import ActionType, Agenda, EducationAction, EducationReport, Sector
from apps.statistics.models import ConsolidatedStatistic
from apps.statistics.services import _parse_materials, aggregate_official_statistics, generate_statistics_for_report
from apps.statistics.dashboard import _category_audience
from apps.statistics.views import StatisticsComparisonView, StatisticsDashboardFiltersView, StatisticsDashboardView, get_hybrid_queryset


class OfficialStatisticsTests(TestCase):
    def setUp(self):
        cache.clear()
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

    def test_new_street_action_categories_are_exposed(self):
        self.stat('ACTION', 2, action=self.action, entity='PRACAS')
        self.stat('ACTION', 3, action=self.action, entity='PONTOS TURISTICOS')
        self.stat('ACTION', 4, action=self.action, entity='FISCALIZACAO')
        totals = aggregate_official_statistics(ConsolidatedStatistic.objects.all())
        self.assertEqual(totals['ACTION - Pra\u00e7as/Parques P\u00fablicos'], 2)
        self.assertEqual(totals['ACTION - Pontos tur\u00edsticos'], 3)
        self.assertEqual(totals['ACTION - A\u00e7\u00e3o conjunta com a fiscaliza\u00e7\u00e3o'], 4)
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

    @override_settings(STATISTICS_CUTOFF_DATE='2026-07-09')
    def test_dashboard_uses_official_aggregation_for_all_sections(self):
        self.stat('AUDIENCE', 100)
        self.stat('ACTION', 2, action=self.lecture, entity='TOTAL')
        self.stat('ACTION', 2, action=self.lecture, entity='ESCOLA')
        self.stat('ACTION', 3, action=self.action, entity='TOTAL')
        self.stat('ACTION', 3, action=self.action, entity='BARES')
        request = APIRequestFactory().get('/statistics/dashboard/', {
            'date_from': '2026-07-09', 'date_to': '2026-07-24',
        })
        force_authenticate(request, user=self.user)
        response = StatisticsDashboardView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['summary']['AUDIENCE - Geral'], 100)
        self.assertEqual(response.data['summary']['LECTURES - Geral'], 2)
        self.assertEqual(response.data['summary']['STREET_ACTIONS - Geral'], 3)
        self.assertIn('annual', response.data)
        self.assertIn('monthly', response.data)
        self.assertIn('categories', response.data)
        self.assertIn('heatmap', response.data)

    @override_settings(STATISTICS_CUTOFF_DATE='2026-07-09')
    def test_dashboard_annual_series_includes_spreadsheet_history(self):
        self.stat('AUDIENCE', 100, reference_date=date(2026, 7, 10), trace='sied')
        request = APIRequestFactory().get('/statistics/dashboard/', {
            'date_from': '2026-07-09', 'date_to': '2026-07-24',
        })
        force_authenticate(request, user=self.user)
        response = StatisticsDashboardView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        annual = {row['year']: row['values'] for row in response.data['annual']}
        self.assertEqual(annual[2011]['AUDIENCE - Geral'], 766996)
        self.assertEqual(annual[2025]['ACTION - Geral'], 1541)
        self.assertEqual(annual[2026]['AUDIENCE - Geral'], 84803)

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

    def street_report(self, report_id, label, public=80):
        agenda = SimpleNamespace(
            action_type_ref=SimpleNamespace(name='Acao de Rua'),
            action_type='',
            requester_entity_type='Acao de Rua',
            institution_location='Acao externa',
            street_action_details=[label],
        )
        action = SimpleNamespace(
            agenda=agenda,
            type_action='Acao de Rua',
            institution_name='Acao externa',
            distribution_materials_distributed='',
        )
        return SimpleNamespace(
            id=report_id,
            status='APPROVED',
            operation_date=date(2026, 7, 24),
            created_at=None,
            approximate_public=public,
            street_action_details=[label],
            distribution_materials_distributed='',
            actions=SimpleNamespace(all=lambda: [action]),
            statistics_processed=False,
            statistics_processed_at=None,
            statistics_processed_by=None,
            save=lambda **kwargs: None,
        )

    def test_all_current_street_action_details_feed_official_categories(self):
        cases = [
            ('Bares', 'BARES'),
            ('Pedagio', 'PEDAGIO'),
            ('Pracas Esportivas', 'ESPORTES'),
            ('Praia', 'PRAIA'),
            ('Eventos', 'EVENTOS'),
            ('Shopping/Centro Comerciais', 'SHOPPING'),
            ('Pracas/Parques Publicos', 'PRACAS'),
            ('Pontos turisticos', 'PONTOS TURISTICOS'),
            ('Acao conjunta com a fiscalizacao', 'FISCALIZACAO'),
        ]
        for index, (label, expected_entity) in enumerate(cases, start=1002):
            with self.subTest(label=label):
                report = self.street_report(index, label)
                generate_statistics_for_report(report)
                stats = ConsolidatedStatistic.objects.filter(traceability_id=f'report_{index}', status='ACTIVE')
                category = stats.get(indicator_type='ACTION', category_action_type=self.action, category_entity_type=expected_entity)
                totals = aggregate_official_statistics(stats)
                self.assertEqual(category.value, 1)
                self.assertEqual(totals['ACTION - Outros'], 0)
                self.assertEqual(totals['AUDIENCE - ACOES'], 80)

    def create_processed_street_report(self, *, team, label='Bares', public=200):
        sector, _ = Sector.objects.get_or_create(name='Educacao')
        agenda = Agenda.objects.create(
            title=f'Acao de Rua - {label}',
            description='Acao externa',
            date=date(2026, 7, 24),
            start_time='09:00',
            end_time='13:00',
            location='Local externo',
            created_by=self.user,
            responsible=self.user,
            sector=sector,
            action_type_ref=self.action,
            requester_entity_type='Acao de Rua',
            street_action_details=[label],
        )
        report = EducationReport.objects.create(
            agenda=agenda,
            operation_date=date(2026, 7, 24),
            team=team,
            approximate_public=public,
            street_action_details=[label],
            status=EducationReport.ReportStatus.APPROVED,
            statistics_processed=True,
            created_by=self.user,
        )
        EducationAction.objects.create(
            report=report,
            agenda=agenda,
            type_action='Acao de Rua',
            institution_name='Local externo',
            approach=0,
        )
        generate_statistics_for_report(report)
        return report

    def test_category_audience_uses_report_approach_number_when_action_approach_is_zero(self):
        self.create_processed_street_report(team='GOLF', label='Bares', public=200)

        audience = _category_audience(date(2026, 7, 1), date(2026, 7, 31), {})

        self.assertEqual(audience['ACTION - Bares'], 200)
        self.assertEqual(audience['ACTION - Outros'], 0)

    def test_dashboard_categories_include_audience_and_only_official_teams(self):
        self.create_processed_street_report(team='GOLF', label='Bares', public=200)
        self.create_processed_street_report(team='Historico', label='Eventos', public=50)
        request = APIRequestFactory().get('/statistics/dashboard/', {
            'date_from': '2026-07-01', 'date_to': '2026-07-31',
        })
        force_authenticate(request, user=self.user)

        response = StatisticsDashboardView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        categories = {row['key']: row for row in response.data['categories']}
        self.assertEqual(categories['ACTION - Bares']['value'], 1)
        self.assertEqual(categories['ACTION - Bares']['audience'], 200)
        self.assertEqual([row['team'] for row in response.data['teams']], ['GOLF'])

    def test_dashboard_filter_teams_only_include_alfa_to_hotel(self):
        self.create_processed_street_report(team='GOLF', label='Bares', public=200)
        self.create_processed_street_report(team='Historico', label='Eventos', public=50)
        request = APIRequestFactory().get('/statistics/dashboard/filters/')
        force_authenticate(request, user=self.user)

        response = StatisticsDashboardFiltersView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['teams'], ['GOLF'])

    def test_escolinha_nota_10_is_classified_as_school(self):
        agenda = SimpleNamespace(action_type_ref=SimpleNamespace(name='Escolinha Nota 10'), action_type='', requester_entity_type='6', institution_location='Escola Municipal Pio X')
        action = SimpleNamespace(agenda=agenda, type_action='Escolinha Nota 10', institution_name='Escola Municipal Pio X', distribution_materials_distributed='')
        report = SimpleNamespace(id=1001, status='APPROVED', operation_date=date(2026, 7, 10), created_at=None, approximate_public=1, distribution_materials_distributed='', actions=SimpleNamespace(all=lambda: [action]), statistics_processed=False, statistics_processed_at=None, statistics_processed_by=None, save=lambda **kwargs: None)
        generate_statistics_for_report(report)
        totals = aggregate_official_statistics(ConsolidatedStatistic.objects.filter(traceability_id='report_1001', status='ACTIVE'))
        self.assertEqual(totals['ACTION - Escola'], 1)
        self.assertEqual(totals['ACTION - Outros'], 0)

    def test_missing_canonical_action_type_has_clear_error(self):
        self.action.delete()
        agenda = SimpleNamespace(action_type_ref=SimpleNamespace(name='A\u00e7\u00e3o'), action_type='', requester_entity_type='7')
        action = SimpleNamespace(agenda=agenda, type_action='A\u00e7\u00e3o', distribution_materials_distributed='')
        report = SimpleNamespace(id=1000, status='APPROVED', operation_date=date(2026, 7, 10), created_at=None, approximate_public=1, distribution_materials_distributed='', actions=SimpleNamespace(all=lambda: [action]), statistics_processed=False, statistics_processed_at=None, statistics_processed_by=None, save=lambda **kwargs: None)
        with self.assertRaisesMessage(ValueError, 'nao cadastrado'):
            generate_statistics_for_report(report)
