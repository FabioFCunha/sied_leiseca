import psycopg2
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, is_naive
from django.db import transaction
from apps.schedules.models import Agenda, EducationReport, EducationAction

class Command(BaseCommand):
    help = "Imports education reports from external PostgreSQL database"

    def handle(self, *args, **options):
        # Database connection details
        host = "10.11.89.202"
        port = 5432
        user = "looker"
        password = "eef016c359387b02def0ba508dccdadf593b0b1d"
        dbname = "horus"

        try:
            conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
            cur = conn.cursor()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to connect to db: {e}"))
            return

        self.stdout.write("Connected to external database.")

        cur.execute("""
            SELECT id, user_id, team, operation_date, "educationPcd_id", "educationAgents_id",
                   changes_staff, breathalyzers, cars_id, changes_general, contact_received,
                   occurrence_observation, lat, lng, created_at, updated_at
            FROM reducols_sections
        """)
        reports_data = cur.fetchall()

        cur.execute("""
            SELECT id, reducols_section_id, place_action, type_action, type_audience, institution_name,
                   start_time, final_hour, approach, tests, used_caps, available_caps,
                   distributed_folders, cricris, vetarolas, used_adhesives, sequence_certificates, gibis, distributed_certificates
            FROM reducols_section_twos
        """)
        actions_data = cur.fetchall()

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
                    # Match by date and (sector__name or team_name)
                    agendas = Agenda.objects.filter(date=operation_date)
                    agendas = [a for a in agendas if (a.sector and a.sector.name.lower() == team.lower()) or a.team_name.lower() == team.lower()]
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
                    
        cur.close()
        conn.close()

        self.stdout.write(self.style.SUCCESS(f"Finished importing. Imported: {imported}, Skipped: {skipped}"))
