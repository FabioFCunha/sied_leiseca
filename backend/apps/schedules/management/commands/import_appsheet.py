import csv
import re
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from apps.schedules.models import Agenda, Sector
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = "Import agendas from AppSheet CSV file"

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the CSV file')

    def handle(self, *args, **kwargs):
        csv_path = kwargs['csv_path']
        self.stdout.write(f"Reading from: {csv_path}")

        default_user = User.objects.filter(is_active=True).first()
        default_sector = Sector.objects.first()

        count_created = 0
        count_skipped = 0

        with open(csv_path, encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            headers = next(reader)
            for row_idx, row in enumerate(reader, start=2):
                if not any(row):
                    continue

                source_id = row[0].strip() if len(row) > 0 else f"appsheet:row_{row_idx}"
                if not source_id:
                    source_id = f"appsheet:row_{row_idx}"
                else:
                    source_id = f"appsheet:{source_id}"
                
                date_str = row[1].strip() if len(row) > 1 else ""
                
                if not date_str:
                    self.stdout.write(f"Skipping row {row_idx}: missing date")
                    count_skipped += 1
                    continue

                vehicle = row[2].strip() if len(row) > 2 else ""
                team_name = row[3].strip() if len(row) > 3 else ""
                chief_name = row[4].strip() if len(row) > 4 else ""
                team_phone = row[5].strip() if len(row) > 5 else ""
                agents = row[6].strip() if len(row) > 6 else ""
                support_1 = row[7].strip() if len(row) > 7 else ""
                support_2 = row[8].strip() if len(row) > 8 else ""
                action_type = row[9].strip() if len(row) > 9 else ""
                institution_location = row[10].strip() if len(row) > 10 else ""
                qtd_str = row[11].strip() if len(row) > 11 else ""
                horario_str = row[12].strip() if len(row) > 12 else ""
                address = row[13].strip() if len(row) > 13 else ""
                neighborhood = row[14].strip() if len(row) > 14 else ""
                city = row[15].strip() if len(row) > 15 else ""
                responsible_name = row[16].strip() if len(row) > 16 else ""
                responsible_phone = row[17].strip() if len(row) > 17 else ""
                email = row[18].strip() if len(row) > 18 else ""
                location = row[19].strip() if len(row) > 19 else ""
                audience = row[20].strip() if len(row) > 20 else ""
                activity_type = row[21].strip() if len(row) > 21 else ""
                notes = row[22].strip() if len(row) > 22 else ""
                status_raw = row[23].strip().upper() if len(row) > 23 else ""

                # Parse date
                try:
                    dt = datetime.strptime(date_str, "%d/%m/%Y").date()
                except ValueError:
                    try:
                        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
                    except ValueError:
                        try:
                            # Sometimes month/day/year like m/d/yyyy
                            dt = datetime.strptime(date_str, "%m/%d/%Y").date()
                        except ValueError:
                            self.stdout.write(f"Skipping row {row_idx}: invalid date format: {date_str}")
                            count_skipped += 1
                            continue

                # Parse time
                try:
                    if len(horario_str) == 5:
                        start_time = datetime.strptime(horario_str, "%H:%M").time()
                    elif len(horario_str) == 8:
                        start_time = datetime.strptime(horario_str, "%H:%M:%S").time()
                    else:
                        start_time = datetime.strptime("09:00:00", "%H:%M:%S").time()
                except ValueError:
                    start_time = datetime.strptime("09:00:00", "%H:%M:%S").time()

                end_time_dt = datetime.combine(dt, start_time) + timedelta(hours=2)
                end_time = end_time_dt.time()

                # Quantity
                quantity = None
                if qtd_str:
                    nums = re.findall(r'\d+', qtd_str)
                    if nums: quantity = int(nums[0])

                # Status
                status = Agenda.Status.PENDING
                if status_raw == "CONFIRMADO":
                    status = Agenda.Status.APPROVED
                elif status_raw in ["NÃO CONFIRMADO", "NAO CONFIRMADO", "CANCELADO"]:
                    status = Agenda.Status.CANCELLED
                elif status_raw in ["REALIZADA", "REALIZADO", "OK", "CONCLUIDO", "CONCLUÍDO"]:
                    status = Agenda.Status.COMPLETED

                # Title
                title_suffix = institution_location or location or team_name or action_type or "Sem Título"
                title = f"AppSheet - {title_suffix}"
                if len(title) > 175:
                    title = title[:175] + "..."

                defaults={
                    'title': title,
                    'origin': Agenda.Origin.INTERNAL,
                    'status': status,
                    'date': dt,
                    'start_time': start_time,
                    'end_time': end_time,
                    'vehicle': vehicle,
                    'team_name': team_name,
                    'chief_name': chief_name,
                    'team_phone': team_phone,
                    'agents': agents,
                    'support_1': support_1,
                    'support_2': support_2,
                    'action_type': action_type,
                    'institution_location': institution_location,
                    'quantity': quantity,
                    'address': address,
                    'neighborhood': neighborhood,
                    'city': city,
                    'external_responsible': responsible_name,
                    'external_responsible_phone': responsible_phone,
                    'external_email': email,
                    'location': location,
                    'audience': audience,
                    'activity_type': activity_type,
                    'notes': notes,
                    'created_by': default_user,
                    'responsible': default_user,
                    'sector': default_sector,
                }

                # Kits parsing mapping (idx 24 is Kit 1)
                for k_num in range(1, 8):
                    base_idx = 24 + (k_num - 1) * 3
                    if len(row) > base_idx + 2:
                        kit_name = row[base_idx].strip()
                        kit_qtd_str = row[base_idx+1].strip()
                        kit_mat = row[base_idx+2].strip()
                        
                        k_qtd = None
                        if kit_qtd_str:
                            nums = re.findall(r'\d+', kit_qtd_str)
                            if nums: k_qtd = int(nums[0])
                        
                        defaults[f'kit_{k_num}'] = kit_name
                        defaults[f'kit_{k_num}_quantity'] = k_qtd
                        defaults[f'material_{k_num}'] = kit_mat

                Agenda.objects.update_or_create(
                    source_id=source_id,
                    defaults=defaults
                )
                count_created += 1

        self.stdout.write(self.style.SUCCESS(f"Finished! Imported {count_created} rows. Skipped {count_skipped} rows."))
