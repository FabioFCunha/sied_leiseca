from datetime import date
from types import SimpleNamespace
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.schedules.models import ActionType, Agenda, EducationAction, EducationReport, Sector
from apps.statistics.models import ConsolidatedStatistic
from apps.statistics.services import _distribution_material_breakdown, _parse_materials, aggregate_official_rows, aggregate_official_statistics, generate_statistics_for_report, reached_audience_for_report
from apps.statistics.dashboard import _annual_series, _category_audience, _distribution_material_card_totals, _rankings, comparison_period, dashboard_payload, derived_totals, variation
from apps.statistics.historical_baseline import HISTORICAL_BASELINE
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

    def audience_report(self, *, approximate_public=0, city='Niteroi', team='ALFA', actions=()):
        sector, _ = Sector.objects.get_or_create(name='Educacao')
        agenda = Agenda.objects.create(
            title='Relatorio de publico', description='Teste de publico alcançado',
            date=date(2026, 7, 12), start_time='09:00', end_time='10:00',
            location='Local', city=city, created_by=self.user, responsible=self.user,
            sector=sector, action_type_ref=self.lecture, requester_entity_type='Outro',
        )
        report = EducationReport.objects.create(
            agenda=agenda, operation_date=agenda.date, team=team,
            approximate_public=approximate_public,
            status=EducationReport.ReportStatus.APPROVED,
            statistics_processed=True, created_by=self.user,
        )
        for values in actions:
            EducationAction.objects.create(report=report, agenda=agenda, **values)
        return report

    def test_reached_audience_uses_pdf_rule_and_ignores_estimated_public(self):
        report = self.audience_report(
            approximate_public=500000,
            actions=({'start_time': '09:00', 'approach': 200, 'approached_lectures': 1200},),
        )

        self.assertEqual(reached_audience_for_report(report), 1200)
        generate_statistics_for_report(report)
        totals = aggregate_official_statistics(
            ConsolidatedStatistic.objects.filter(traceability_id=f'report_{report.id}', status='ACTIVE')
        )
        self.assertEqual(totals['AUDIENCE - Geral'], 1200)
        self.assertEqual(dashboard_payload(date(2026, 7, 1), date(2026, 7, 31), {})['summary']['AUDIENCE - Geral'], 1200)

    def test_reached_audience_uses_actions_when_first_lecture_is_zero(self):
        report = self.audience_report(
            approximate_public=500000,
            actions=({'start_time': '09:00', 'approach': 200, 'approached_lectures': 0, 'approached_actions': 80},),
        )
        self.assertEqual(reached_audience_for_report(report), 80)

    def test_reached_audience_keeps_zero_for_structured_actions(self):
        report = self.audience_report(
            approximate_public=999,
            actions=({'start_time': '09:00', 'approach': 777, 'approached_lectures': 0, 'approached_actions': 0},),
        )
        self.assertEqual(reached_audience_for_report(report), 0)

    def test_reached_audience_uses_legacy_approximate_public_only_without_actions(self):
        report = self.audience_report(approximate_public=64)
        self.assertEqual(reached_audience_for_report(report), 64)

    def test_reached_audience_orders_actions_like_the_pdf(self):
        report = self.audience_report(
            approximate_public=999,
            actions=(
                {'start_time': '11:00', 'approached_actions': 40},
                {'start_time': '08:00', 'approached_lectures': 100, 'approached_actions': 90},
                {'start_time': '12:00', 'approached_actions': 60},
            ),
        )
        self.assertEqual(reached_audience_for_report(report), 200)

    def test_rankings_use_reached_audience_instead_of_estimated_public(self):
        report = self.audience_report(
            approximate_public=500000, city='Cidade PDF', team='ALFA',
            actions=({'start_time': '09:00', 'approach': 200, 'approached_lectures': 1200},),
        )
        rankings = _rankings(date(2026, 7, 1), date(2026, 7, 31), {})

        self.assertEqual(next(row for row in rankings['municipalities'] if row['agenda__city'] == 'Cidade PDF')['audience'], 1200)
        self.assertEqual(next(row for row in rankings['teams'] if row['team'] == report.team)['audience'], 1200)

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

    def test_annual_distribution_materials_keep_named_totals(self):
        breakdown = _distribution_material_breakdown(
            'Revistinha Soprinho | 5\nKIT COM 7 REVISTINHAS | 2\nVENTAROLA FUTEBOL | 3'
        )
        self.assertEqual(breakdown['REVISTINHA SOPRINHO'], 5)
        self.assertEqual(breakdown['KIT COM 7 REVISTINHAS'], 2)
        self.assertEqual(breakdown['VENTAROLA FUTEBOL'], 3)
        totals = aggregate_official_rows([
            {'indicator_type': 'MATERIAL', 'category_action_type__name': None, 'category_entity_type': 'REVISTINHA SOPRINHO', 'total': 5},
            {'indicator_type': 'MATERIAL', 'category_action_type__name': None, 'category_entity_type': 'KIT COM 7 REVISTINHAS', 'total': 2},
            {'indicator_type': 'MATERIAL', 'category_action_type__name': None, 'category_entity_type': 'VENTAROLA FUTEBOL', 'total': 3},
        ])
        self.assertEqual(totals['MATERIAL - Soprinho'], 5)
        self.assertEqual(totals['MATERIAL - Kit com 7 Revistinhas'], 2)
        self.assertEqual(totals['MATERIAL - Ventarola Futebol'], 3)

    def test_distribution_material_cards_use_only_approved_reports_after_cutoff(self):
        included = EducationReport.objects.create(
            operation_date=date(2026, 7, 9),
            team='ALFA',
            status=EducationReport.ReportStatus.APPROVED,
            accessibility_conditions_met='YES',
            created_by=self.user,
            distribution_materials_distributed=(
                'Revistinha Soprinho | 100\n'
                'Kit com 7 Revistinhas | 20\n'
                'Ventarola Futebol | 10\n'
                'Outro material de distribuição | 4'
            ),
            equipment_materials_distributed='Material de apoio | 999',
            materials_spent='Material de dinâmica | 999',
        )
        # Report-level data wins over action-level data, preventing duplicate counts.
        EducationAction.objects.create(
            report=included,
            distribution_materials_distributed='Revistinha Soprinho | 100\nKit com 7 Revistinhas | 20\nVentarola Futebol | 10',
        )
        action_only = EducationReport.objects.create(
            operation_date=date(2026, 7, 10),
            team='ALFA',
            status=EducationReport.ReportStatus.APPROVED,
            accessibility_conditions_met='YES',
            created_by=self.user,
        )
        EducationAction.objects.create(
            report=action_only,
            distribution_materials_distributed='Kit com 7 Revistinhas | 3',
        )
        EducationReport.objects.create(
            operation_date=date(2026, 7, 8),
            team='ALFA',
            status=EducationReport.ReportStatus.APPROVED,
            accessibility_conditions_met='YES',
            created_by=self.user,
            distribution_materials_distributed='Kit com 7 Revistinhas | 999',
        )
        EducationReport.objects.create(
            operation_date=date(2026, 7, 10),
            team='ALFA',
            status=EducationReport.ReportStatus.DRAFT,
            accessibility_conditions_met='YES',
            created_by=self.user,
            distribution_materials_distributed='Kit com 7 Revistinhas | 999',
        )

        totals = _distribution_material_card_totals(
            date(2026, 7, 1), date(2026, 7, 31), {}
        )

        self.assertEqual(totals['total'], 137)
        self.assertEqual(totals['kits_with_seven_comics'], 23)
        self.assertNotEqual(totals['kits_with_seven_comics'], 23 * 7)
        self.assertEqual(totals['total'] - totals['kits_with_seven_comics'], 114)

        payload = dashboard_payload(date(2026, 7, 1), date(2026, 7, 31), {})
        self.assertEqual(payload['summary']['MATERIAL - Geral'], 137)
        self.assertEqual(payload['summary']['MATERIAL - Kit com 7 Revistinhas'], 23)

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
    def test_dashboard_visual_monthly_distributes_2026_historical_average_without_changing_official_monthly(self):
        request = APIRequestFactory().get('/statistics/dashboard/', {
            'date_from': '2026-01-01', 'date_to': '2026-07-24',
        })
        force_authenticate(request, user=self.user)

        response = StatisticsDashboardView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        official_january = response.data['monthly'][0]['values']
        visual_january = response.data['visual_monthly'][0]['values']
        self.assertEqual(official_january.get('ACTION - Geral', 0), 0)
        self.assertAlmostEqual(visual_january['ACTION - Geral'], 502 / 6)
        self.assertAlmostEqual(visual_january['AUDIENCE - Geral'], 84703 / 6)

    def test_dashboard_annual_series_includes_spreadsheet_history(self):
        self.stat('AUDIENCE', 100, reference_date=date(2026, 7, 10), trace='sied')
        request = APIRequestFactory().get('/statistics/dashboard/')
        force_authenticate(request, user=self.user)
        response = StatisticsDashboardView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        annual = {row['year']: row['values'] for row in response.data['annual']}
        self.assertEqual(annual[2011]['AUDIENCE - Geral'], 766996)
        self.assertEqual(annual[2025]['ACTION - Geral'], 1541)
        self.assertEqual(annual[2026]['AUDIENCE - Geral'], 84803)

    def test_annual_series_hides_only_2018_street_actions_total(self):
        annual = {
            row['year']: row['values']
            for row in _annual_series(date(2026, 7, 1), date.today(), {})
        }

        self.assertEqual(annual[2018]['STREET_ACTIONS - Geral'], 0)
        self.assertEqual(annual[2018]['LECTURES - Geral'], 310)
        self.assertEqual(annual[2018]['ACTION - Geral'], 726)
        self.assertEqual(
            annual[2019]['STREET_ACTIONS - Geral'],
            derived_totals(HISTORICAL_BASELINE[2019])['STREET_ACTIONS - Geral'],
        )
        self.assertEqual(HISTORICAL_BASELINE[2018]['ACTION - Geral'], 726)
        self.assertEqual(HISTORICAL_BASELINE[2018]['LECTURES - Geral'], 310)

    def test_annual_2026_hybrid_series_combines_baseline_and_operational_street_actions(self):
        self.stat('ACTION', 231, action=self.action, entity='TOTAL', trace='2026-action-total')
        self.stat('ACTION', 100, action=self.lecture, entity='ESCOLA', trace='2026-lectures')
        for entity, value in {
            'BARES': 11,
            'ESPORTES': 6,
            'PRAIA': 3,
            'EVENTOS': 41,
            'SHOPPING': 11,
            'PRACAS': 30,
            'PONTOS TURISTICOS': 6,
            'OUTROS': 16,
            'FISCALIZACAO': 7,
        }.items():
            self.stat('ACTION', value, action=self.action, entity=entity, trace=f'2026-{entity}')
        self.stat('AUDIENCE', 23829, trace='2026-audience-total')
        self.stat('AUDIENCE', 3904, action=self.lecture, entity='TOTAL', trace='2026-audience-lectures')
        self.stat('AUDIENCE', 19925, action=self.action, entity='TOTAL', trace='2026-audience-actions')

        request = APIRequestFactory().get('/statistics/dashboard/')
        force_authenticate(request, user=self.user)
        response = StatisticsDashboardView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        annual = {row['year']: row['values'] for row in response.data['annual']}
        values = annual[2026]
        self.assertEqual(HISTORICAL_BASELINE[2026]['ACTION - Geral'], 502)
        self.assertEqual(values['STREET_ACTIONS - Geral'], 633)
        self.assertEqual(values['ACTION - Bares'], 28)
        self.assertEqual(values['ACTION - Pedágio'], 2)
        self.assertEqual(values['ACTION - Praças Esportivas'], 13)
        self.assertEqual(values['ACTION - Praia'], 27)
        self.assertEqual(values['ACTION - Eventos'], 116)
        self.assertEqual(values['ACTION - Shopping'], 21)
        self.assertEqual(values['ACTION - Praças/Parques Públicos'], 30)
        self.assertEqual(values['ACTION - Pontos turísticos'], 6)
        self.assertEqual(values['ACTION - Ação Social'], 1)
        self.assertEqual(values['ACTION - Outros'], 382)
        self.assertEqual(values['ACTION - Ação conjunta com a fiscalização'], 7)
        self.assertEqual(sum(values[key] for key in (
            'ACTION - Bares',
            'ACTION - Pedágio',
            'ACTION - Praças Esportivas',
            'ACTION - Praia',
            'ACTION - Eventos',
            'ACTION - Shopping',
            'ACTION - Praças/Parques Públicos',
            'ACTION - Pontos turísticos',
            'ACTION - Ação Social',
            'ACTION - Outros',
            'ACTION - Ação conjunta com a fiscalização',
        )), 633)
        self.assertEqual(values['AUDIENCE - PALESTRAS'], 18073)
        self.assertEqual(values['AUDIENCE - ACOES'], 90459)
        self.assertEqual(values['AUDIENCE - Geral'], 108532)

    def test_comparison_period_agosto_completo(self):
        period = comparison_period(date(2026, 8, 1), date(2026, 8, 31))
        self.assertEqual(period['from'], date(2026, 7, 1))
        self.assertEqual(period['to'], date(2026, 7, 31))
        self.assertEqual(period['type'], 'previous_month')
        self.assertEqual(period['label'], 'vs. 01/07/2026 a 31/07/2026')

    def test_comparison_period_agosto_parcial(self):
        period = comparison_period(date(2026, 8, 1), date(2026, 8, 10))
        self.assertEqual(period['from'], date(2026, 7, 1))
        self.assertEqual(period['to'], date(2026, 7, 10))
        self.assertEqual(period['type'], 'previous_month')
        self.assertEqual(period['label'], 'vs. 01/07/2026 a 10/07/2026')

    def test_comparison_period_intervalo_parcial(self):
        period = comparison_period(date(2026, 8, 5), date(2026, 8, 10))
        self.assertEqual(period['from'], date(2026, 7, 5))
        self.assertEqual(period['to'], date(2026, 7, 10))

    def test_comparison_period_virada_de_ano(self):
        period = comparison_period(date(2026, 1, 1), date(2026, 1, 31))
        self.assertEqual(period['from'], date(2025, 12, 1))
        self.assertEqual(period['to'], date(2025, 12, 31))
        self.assertEqual(period['label'], 'vs. 01/12/2025 a 31/12/2025')

    def test_comparison_period_dia_31(self):
        period = comparison_period(date(2026, 3, 31), date(2026, 3, 31))
        self.assertEqual(period['from'], date(2026, 2, 28))
        self.assertEqual(period['to'], date(2026, 2, 28))
        self.assertEqual(period['label'], 'vs. 28/02/2026 a 28/02/2026')

    def test_variation_anterior_0_atual_maior_que_0(self):
        var = variation(10, 0)
        self.assertEqual(var['status'], 'NEW')
        self.assertIsNone(var['percentage'])

    def test_variation_anterior_0_atual_0(self):
        var = variation(0, 0)
        self.assertEqual(var['status'], 'STABLE')
        self.assertEqual(var['percentage'], 0)

    def test_legacy_street_action_uses_report_type_action_subcategory(self):
        agenda = SimpleNamespace(
            action_type_ref=SimpleNamespace(name='Ação de Rua'),
            action_type='',
            requester_entity_type='6',
            street_action_details=[],
            institution_location='Local antigo',
        )
        action = SimpleNamespace(
            agenda=agenda,
            type_action='Bares',
            approached_actions=100,
            approached_lectures=0,
            approach=0,
            street_action_details=[],
            distribution_materials_distributed='',
        )
        report = SimpleNamespace(id=2001, status='APPROVED', operation_date=date(2026, 7, 9), created_at=None, approximate_public=0, street_action_details=[], distribution_materials_distributed='', actions=SimpleNamespace(all=lambda: [action]), statistics_processed=False, statistics_processed_at=None, statistics_processed_by=None, save=lambda **kwargs: None)

        generate_statistics_for_report(report)
        totals = aggregate_official_statistics(ConsolidatedStatistic.objects.filter(traceability_id='report_2001', status='ACTIVE'))

        self.assertEqual(totals['ACTION - Bares'], 1)
        self.assertEqual(totals['ACTION - Outros'], 0)
        self.assertEqual(totals['AUDIENCE - Geral'], 100)

    def test_legacy_street_action_uses_agenda_action_type_subcategory(self):
        agenda = SimpleNamespace(
            action_type_ref=SimpleNamespace(name='A??o de Rua'),
            action_type='Bares',
            requester_entity_type='6',
            street_action_details=[],
            institution_location='Local antigo',
        )
        action = SimpleNamespace(
            agenda=agenda,
            type_action='A??o de educa??o/conscientiza??o',
            approached_actions=80,
            approached_lectures=0,
            approach=0,
            street_action_details=[],
            distribution_materials_distributed='',
        )
        report = SimpleNamespace(id=2002, status='APPROVED', operation_date=date(2026, 7, 9), created_at=None, approximate_public=0, street_action_details=[], distribution_materials_distributed='', actions=SimpleNamespace(all=lambda: [action]), statistics_processed=False, statistics_processed_at=None, statistics_processed_by=None, save=lambda **kwargs: None)

        generate_statistics_for_report(report)
        totals = aggregate_official_statistics(ConsolidatedStatistic.objects.filter(traceability_id='report_2002', status='ACTIVE'))

        self.assertEqual(totals['ACTION - Bares'], 1)
        self.assertEqual(totals['ACTION - Outros'], 0)
        self.assertEqual(totals['AUDIENCE - Geral'], 80)

    def test_generate_uses_action_approached_actions_as_reached_public(self):
        agenda = SimpleNamespace(action_type_ref=self.action, action_type='', requester_entity_type='7')
        action = SimpleNamespace(
            agenda=agenda,
            type_action='Ação',
            approached_actions=382,
            approached_lectures=0,
            approach=0,
            distribution_materials_distributed='',
        )
        report = SimpleNamespace(id=1999, status='APPROVED', operation_date=date(2026, 7, 10), created_at=None, approximate_public=1, distribution_materials_distributed='', actions=SimpleNamespace(all=lambda: [action]), statistics_processed=False, statistics_processed_at=None, statistics_processed_by=None, save=lambda **kwargs: None)

        generate_statistics_for_report(report)
        totals = aggregate_official_statistics(ConsolidatedStatistic.objects.filter(traceability_id='report_1999', status='ACTIVE'))

        self.assertEqual(totals['AUDIENCE - Geral'], 382)
        self.assertEqual(totals['AUDIENCE - ACOES'], 382)

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
            approached_actions=public,
            approached_lectures=0,
            approach=0,
            distribution_materials_distributed='',
            bars=1 if label == 'Bares' else 0,
            tolls=1 if label == 'Pedagio' else 0,
            sports=1 if label == 'Pracas Esportivas' else 0,
            beach=1 if label == 'Praia' else 0,
            events=1 if label == 'Eventos' else 0,
            shopping=1 if label == 'Shopping/Centro Comerciais' else 0,
            parks=1 if label == 'Pracas/Parques Publicos' else 0,
            tourist_spots=1 if label == 'Pontos turisticos' else 0,
            social_actions=0,
            joint_inspections=1 if label == 'Acao conjunta com a fiscalizacao' else 0,
            other_actions=0,
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

    def test_street_action_counter_classifies_bares_when_details_are_empty(self):
        agenda = SimpleNamespace(
            action_type_ref=SimpleNamespace(name='Acao de Rua'),
            action_type='',
            requester_entity_type='6',
            institution_location='Acao externa',
            street_action_details=[],
        )
        action = SimpleNamespace(
            agenda=agenda,
            type_action='Acao de Rua',
            institution_name='Acao externa',
            approached_actions=200,
            approached_lectures=0,
            approach=0,
            distribution_materials_distributed='',
            bars=1,
        )
        report = SimpleNamespace(
            id=1015,
            status='APPROVED',
            operation_date=date(2026, 7, 24),
            created_at=None,
            approximate_public=200,
            street_action_details=[],
            distribution_materials_distributed='',
            actions=SimpleNamespace(all=lambda: [action]),
            statistics_processed=False,
            statistics_processed_at=None,
            statistics_processed_by=None,
            save=lambda **kwargs: None,
        )
        generate_statistics_for_report(report)
        totals = aggregate_official_statistics(ConsolidatedStatistic.objects.filter(traceability_id='report_1015', status='ACTIVE'))
        self.assertEqual(totals['ACTION - Bares'], 1)
        self.assertEqual(totals['ACTION - Outros'], 0)
        self.assertEqual(totals['AUDIENCE - ACOES'], 200)

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
        counter_values = {
            'Bares': {'bars': 1},
            'Eventos': {'events': 1},
        }.get(label, {})
        EducationAction.objects.create(
            report=report,
            agenda=agenda,
            type_action='Acao de Rua',
            institution_name='Local externo',
            approach=0,
            approached_actions=public,
            **counter_values,
        )
        generate_statistics_for_report(report)
        return report

    def test_category_audience_uses_report_approach_number_when_action_approach_is_zero(self):
        self.create_processed_street_report(team='GOLF', label='Bares', public=200)

        audience = _category_audience(date(2026, 7, 1), date(2026, 7, 31), {})

        self.assertEqual(audience['ACTION - Bares'], 200)
        self.assertEqual(audience['ACTION - Outros'], 0)

    def test_dashboard_additional_cards_do_not_change_reached_public(self):
        sector, _ = Sector.objects.get_or_create(name='Educacao')
        agenda = Agenda.objects.create(
            title='Solicitacao com publico previsto',
            description='Demanda recebida',
            date=date(2026, 7, 20),
            start_time='09:00',
            end_time='10:00',
            location='Escola Modelo',
            created_by=self.user,
            responsible=self.user,
            sector=sector,
            origin=Agenda.Origin.PUBLIC_FORM,
            audience='150',
            participant_range='30 a 50',
        )
        report = EducationReport.objects.create(
            agenda=agenda,
            operation_date=date(2026, 7, 20),
            team='GOLF',
            approximate_public=80,
            status=EducationReport.ReportStatus.APPROVED,
            statistics_processed=True,
            created_by=self.user,
        )
        generate_statistics_for_report(report)
        request = APIRequestFactory().get('/statistics/dashboard/', {
            'date_from': '2026-07-01', 'date_to': '2026-07-31',
        })
        force_authenticate(request, user=self.user)

        response = StatisticsDashboardView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['summary']['AUDIENCE - Geral'], 80)
        self.assertEqual(response.data['summary']['EXPECTED_PUBLIC'], 150)
        self.assertEqual(response.data['summary']['REPORTS_WITHOUT_PUBLIC'], 0)

    def test_expected_public_uses_participant_range_and_reports_without_public(self):
        sector, _ = Sector.objects.get_or_create(name='Educacao')
        agenda = Agenda.objects.create(
            title='Solicitacao com faixa',
            description='Demanda recebida',
            date=date(2026, 7, 21),
            start_time='09:00',
            end_time='10:00',
            location='Empresa Modelo',
            created_by=self.user,
            responsible=self.user,
            sector=sector,
            origin=Agenda.Origin.INTERNAL,
            audience='',
            participant_range='51 a 100',
        )
        report = EducationReport.objects.create(
            agenda=agenda,
            operation_date=date(2026, 7, 21),
            team='GOLF',
            approximate_public=0,
            status=EducationReport.ReportStatus.APPROVED,
            statistics_processed=True,
            created_by=self.user,
        )
        generate_statistics_for_report(report)
        request = APIRequestFactory().get('/statistics/dashboard/', {
            'date_from': '2026-07-01', 'date_to': '2026-07-31',
        })
        force_authenticate(request, user=self.user)

        response = StatisticsDashboardView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['summary']['AUDIENCE - Geral'], 0)
        self.assertEqual(response.data['summary']['EXPECTED_PUBLIC'], 100)
        self.assertEqual(response.data['summary']['REPORTS_WITHOUT_PUBLIC'], 1)

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

    def test_dashboard_municipalities_exclude_zero_rows(self):
        self.create_processed_street_report(team='GOLF', label='Bares', public=200)
        request = APIRequestFactory().get('/statistics/dashboard/', {
            'date_from': '2026-07-01', 'date_to': '2026-07-31',
        })
        force_authenticate(request, user=self.user)

        response = StatisticsDashboardView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['municipalities'])
        for row in response.data['municipalities']:
            self.assertTrue(row['actions'] > 0 or row['audience'] > 0)

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
