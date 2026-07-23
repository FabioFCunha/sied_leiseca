from django.test import TestCase
from django.utils import timezone
from apps.statistics.models import ConsolidatedStatistic, StatisticCategoryMapping
from apps.statistics.services import generate_statistics_for_report, update_statistics_for_report, remove_statistics_for_report
from apps.schedules.models import ActionType

# A simple mock object for the report to avoid complex dependencies during this isolated test
class MockReport:
    def __init__(self, id, status, audience_total):
        self.id = id
        self.status = status
        self.audience_total = audience_total
        self.created_at = timezone.now()

class StatisticsModuleTests(TestCase):
    
    def setUp(self):
        self.action_type = ActionType.objects.create(name='Test Action')
        self.mapping = StatisticCategoryMapping.objects.create(
            original_name="TEST_CAT",
            indicator_type="AUDIENCE",
            sied_action_type=self.action_type
        )
    
    def test_historical_legacy_creation(self):
        """Histórico não mistura com operacional e não pode ter reference_date"""
        stat = ConsolidatedStatistic(
            reference_year=2020,
            indicator_type='AUDIENCE',
            value=100,
            methodology='HISTORICAL_LEGACY',
            traceability_id='legacy_2020_test'
        )
        stat.full_clean()
        stat.save()
        self.assertEqual(ConsolidatedStatistic.objects.count(), 1)
        
        # Test validation error if HISTORICAL_LEGACY has a exact reference date
        stat.reference_date = timezone.now().date()
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            stat.full_clean()

    def test_operational_creation_requires_date(self):
        """Operacional SIED obrigatoriamente precisa de reference_date"""
        stat = ConsolidatedStatistic(
            reference_year=2026,
            indicator_type='AUDIENCE',
            value=100,
            methodology='SIED_OPERATIONAL',
            traceability_id='test_oper'
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            stat.full_clean()
            
    def test_service_generates_statistics_only_when_approved(self):
        """Relatório devolvido ou pendente não gera estatística. Somente aprovado."""
        draft_report = MockReport(id=1, status='DRAFT', audience_total=50)
        generate_statistics_for_report(draft_report)
        self.assertEqual(ConsolidatedStatistic.objects.filter(methodology='SIED_OPERATIONAL').count(), 0)
        
        returned_report = MockReport(id=2, status='RETURNED', audience_total=50)
        generate_statistics_for_report(returned_report)
        self.assertEqual(ConsolidatedStatistic.objects.filter(methodology='SIED_OPERATIONAL').count(), 0)

        approved_report = MockReport(id=3, status='APPROVED', audience_total=75)
        generate_statistics_for_report(approved_report)
        self.assertEqual(ConsolidatedStatistic.objects.filter(methodology='SIED_OPERATIONAL').count(), 1)
        stat = ConsolidatedStatistic.objects.first()
        self.assertEqual(stat.value, 75)
        self.assertEqual(stat.traceability_id, 'report_3')

    def test_service_updates_and_keeps_traceability(self):
        """Retificação atualiza o valor correto e mantém vínculo"""
        report = MockReport(id=10, status='APPROVED', audience_total=100)
        generate_statistics_for_report(report)
        self.assertEqual(ConsolidatedStatistic.objects.get(traceability_id='report_10').value, 100)
        
        # Simula uma retificação (o valor mudou para 150)
        report.audience_total = 150
        update_statistics_for_report(report)
        
        # Não deve criar duplicado, deve substituir
        self.assertEqual(ConsolidatedStatistic.objects.filter(traceability_id='report_10').count(), 1)
        self.assertEqual(ConsolidatedStatistic.objects.get(traceability_id='report_10').value, 150)

    def test_service_removes_statistics(self):
        report = MockReport(id=20, status='APPROVED', audience_total=200)
        generate_statistics_for_report(report)
        self.assertEqual(ConsolidatedStatistic.objects.count(), 1)
        
        remove_statistics_for_report(report)
        self.assertEqual(ConsolidatedStatistic.objects.count(), 0)
