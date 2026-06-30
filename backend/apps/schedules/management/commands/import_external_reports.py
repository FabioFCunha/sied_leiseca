import json
import os
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, is_naive
from django.db import transaction
from apps.schedules.models import Agenda, EducationReport, EducationAction

class Command(BaseCommand):
    help = "Imports education reports from exported JSON data"

    def handle(self, *args, **options):
        from django.conf import settings
        json_path = os.path.join(settings.BASE_DIR, 'external_reports.json')
        # Update any previously imported reports that were left as DRAFT
        updated = EducationReport.objects.filter(source_id__startswith="external:", status="DRAFT").update(status=EducationReport.ReportStatus.SUBMITTED)
        if updated:
            self.stdout.write(self.style.SUCCESS(f"Updated {updated} previously imported reports to SUBMITTED status."))

        team_map = {
            'A': 'ALFA', 'B': 'BRAVO', 'C': 'CHARLIE', 'D': 'DELTA', 
            'E': 'ECHO', 'F': 'FOX', 'G': 'GOLF', 'H': 'HOTEL', 
            'I': 'INDIA', 'J': 'JULIET', 'K': 'KILO', 'L': 'LIMA', 'M': 'MIKE'
        }

        # Try to link any reports that are missing an agenda
        unlinked = EducationReport.objects.filter(source_id__startswith="external:", agenda__isnull=True)
        linked_count = 0
        for r in unlinked:
            r_team = team_map.get(r.team, r.team).lower()
            agendas = Agenda.objects.filter(date=r.operation_date)
            agendas = [a for a in agendas if (a.sector and a.sector.name.lower().startswith(r_team)) or a.team_name.lower().startswith(r_team)]
            if agendas:
                r.agenda = agendas[0]
                r.save(update_fields=['agenda'])
                linked_count += 1
        if linked_count:
            self.stdout.write(self.style.SUCCESS(f"Linked {linked_count} previously unlinked reports to agendas."))

        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            reports_data = data["reports"]
            actions_data = data["actions"]
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to load JSON: {e}"))
            return

        self.stdout.write("Loaded external_reports.json.")

        # Group actions by report id
        actions_by_report = {}
        for action in actions_data:
            report_id = action[1]
            if report_id not in actions_by_report:
                actions_by_report[report_id] = []
            actions_by_report[report_id].append(action)

        imported = 0
        skipped = 0

        from django.contrib.auth import get_user_model
        User = get_user_model()
        system_user = User.objects.filter(is_superuser=True).first()
        if not system_user:
            self.stdout.write(self.style.ERROR("No superuser found to assign to created_by."))
            return

        with transaction.atomic():
            for row in reports_data:
                external_id = row[0]
                team = row[2] or ""
                operation_date = row[3]
                
                # Try to find corresponding Agenda
                agenda = None
                if operation_date and team:
                    # Match by date and (sector__name or team_name) using phonetic prefix
                    r_team = team_map.get(team, team).lower()
                    agendas = Agenda.objects.filter(date=operation_date)
                    agendas = [a for a in agendas if (a.sector and a.sector.name.lower().startswith(r_team)) or a.team_name.lower().startswith(r_team)]
                    if agendas:
                        agenda = agendas[0] # Take the first match

                # Check if report already exists by source_id
                source_id = f"external:{external_id}"
                
                # Check if we already imported this
                if EducationReport.objects.filter(source_id=source_id).exists():
                    skipped += 1
                    continue

                def mk_aware(dt):
                    if not dt: return None
                    return make_aware(dt) if is_naive(dt) else dt

                report = EducationReport.objects.create(
                    created_by=system_user,
                    status=EducationReport.ReportStatus.SUBMITTED,
                    agenda=agenda,
                    source_id=source_id,
                    team=team,
                    operation_date=operation_date,
                    education_pcd=row[4] or "",
                    education_agents=row[5] or "",
                    changes_staff=row[6] or "",
                    breathalyzers=row[7] or "",
                    cars=row[8] or "",
                    changes_general=row[9] or "",
                    contact_received=row[10] or "",
                    occurrence_observation=row[11] or "",
                    lat=row[12],
                    lng=row[13],
                )
                imported += 1

                # Create actions
                for act in actions_by_report.get(external_id, []):
                    materials = []
                    def add_mat(qty, name):
                        if qty and int(qty) > 0:
                            materials.append(f"{name} | {qty}")
                    
                    add_mat(act[12], "Folder")
                    add_mat(act[13], "Cricri")
                    add_mat(act[14], "Viseira/Vetarola")
                    add_mat(act[15], "Adesivos")
                    add_mat(act[16], "Certificado Dinâmica")
                    add_mat(act[17], "Gibi")
                    add_mat(act[18], "Certificado Participação")

                    distribution_distributed = "\\n".join(materials)

                    EducationAction.objects.create(
                        report=report,
                        agenda=agenda,
                        source_id=f"external_action:{act[0]}",
                        place_action=act[2] or "",
                        type_action=act[3] or "",
                        type_audience=act[4] or "",
                        institution_name=act[5] or "",
                        start_time=act[6] or "",
                        final_hour=act[7] or "",
                        approach=act[8] or 0,
                        tests=act[9] or 0,
                        used_caps=act[10] or 0,
                        available_caps=act[11] or 0,
                        distribution_materials_distributed=distribution_distributed,
                    )
                    
        self.stdout.write(self.style.SUCCESS(f"Finished importing. Imported: {imported}, Skipped: {skipped}"))
