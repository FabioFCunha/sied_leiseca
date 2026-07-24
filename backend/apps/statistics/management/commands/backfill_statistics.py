from django.core.management.base import BaseCommand
from apps.schedules.models import EducationReport
from apps.statistics.services import generate_statistics_for_report
from django.db import transaction

class Command(BaseCommand):
    help = "Backfill statistics for all APPROVED EducationReports that have not been processed yet."

    def handle(self, *args, **options):
        reports = EducationReport.objects.filter(
            status=EducationReport.ReportStatus.APPROVED,
            statistics_processed=False
        )
        total = reports.count()
        self.stdout.write(f"Found {total} approved reports pending statistics backfill.")
        
        count = 0
        for report in reports:
            # Passing None for processed_by will result in:
            # - processed_by = NULL (foreign key)
            # - audit log 'changed_by' = 'system'
            # Which satisfies the requirement to clearly identify system processing.
            generate_statistics_for_report(report, processed_by=None)
            count += 1
            if count % 50 == 0:
                self.stdout.write(f"Processed {count}/{total} reports...")
                
        self.stdout.write(self.style.SUCCESS(f"Successfully backfilled {count} reports. Check the 'ConsolidatedStatistic' table and the 'statistics_processed' flag on 'EducationReport'."))
