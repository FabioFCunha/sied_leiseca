import csv
import re
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.schedules.models import Agenda, Sector
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = "Import agendas from a Google Forms CSV file"

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

                timestamp_str = row[1] if len(row) > 1 else ""
                date_str = row[2] if len(row) > 2 else ""
                modalidade = row[4] if len(row) > 4 else ""
                instituicao = row[5] if len(row) > 5 else ""
                qtd_acoes = row[6] if len(row) > 6 else ""
                horario_str = row[7] if len(row) > 7 else ""
                endereco = row[10] if len(row) > 10 else ""
                bairro = row[11] if len(row) > 11 else ""
                cidade = row[12] if len(row) > 12 else ""
                estado = row[13] if len(row) > 13 else ""
                nome = row[14] if len(row) > 14 else ""
                telefone = row[15] if len(row) > 15 else ""
                email = (row[16] if len(row) > 16 else "") or (row[24] if len(row) > 24 else "")
                desc_entidade = row[17] if len(row) > 17 else ""
                participantes_str = row[18] if len(row) > 18 else ""
                faixa_etaria = row[19] if len(row) > 19 else ""
                rampas = row[20] if len(row) > 20 else ""
                elevadores = row[21] if len(row) > 21 else ""
                banheiro = row[22] if len(row) > 22 else ""
                recursos = row[23] if len(row) > 23 else ""
                cpf = row[27] if len(row) > 27 else ""
                cargo = row[28] if len(row) > 28 else ""
                comentarios = row[29] if len(row) > 29 else ""

                if not date_str or not instituicao:
                    self.stdout.write(f"Skipping row {row_idx}: missing date or institution")
                    count_skipped += 1
                    continue

                # Parse date
                try:
                    dt = datetime.strptime(date_str, "%d/%m/%Y").date()
                except ValueError:
                    try:
                        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
                    except ValueError:
                        self.stdout.write(f"Skipping row {row_idx}: invalid date format: {date_str}")
                        count_skipped += 1
                        continue

                # Parse time
                try:
                    if len(horario_str) == 5:
                        start_time = datetime.strptime(horario_str, "%H:%M").time()
                    else:
                        start_time = datetime.strptime(horario_str, "%H:%M:%S").time()
                except ValueError:
                    start_time = datetime.strptime("09:00:00", "%H:%M:%S").time()

                # End time + 2h
                end_time_dt = datetime.combine(dt, start_time) + timedelta(hours=2)
                end_time = end_time_dt.time()

                # Parse participants
                nums = re.findall(r'\d+', participantes_str)
                expected_participants = int(nums[0]) if nums else 0

                # Location string
                loc_parts = [p for p in [endereco, bairro, cidade, estado] if p]
                location = ", ".join(loc_parts)

                # Description block
                description_parts = []
                if modalidade: description_parts.append(f"Modalidade: {modalidade}")
                if qtd_acoes: description_parts.append(f"Quantidade de ações: {qtd_acoes}")
                if desc_entidade: description_parts.append(f"Descrição Entidade: {desc_entidade}")
                if faixa_etaria: description_parts.append(f"Faixa etária: {faixa_etaria}")
                if recursos: description_parts.append(f"Recursos: {recursos}")
                if rampas or elevadores or banheiro:
                    description_parts.append(f"Acessibilidade -> Rampas: {rampas} | Elevadores: {elevadores} | Banheiro: {banheiro}")
                if cargo: description_parts.append(f"Cargo Requisitante: {cargo}")
                if comentarios: description_parts.append(f"Comentários: {comentarios}")

                description = "\n".join(description_parts)

                source_id = f"forms:row_{row_idx}"

                Agenda.objects.update_or_create(
                    source_id=source_id,
                    defaults={
                        'title': f"Solicitação - {instituicao}",
                        'origin': Agenda.Origin.PUBLIC_FORM,
                        'status': Agenda.Status.PENDING,
                        'description': description,
                        'date': dt,
                        'start_time': start_time,
                        'end_time': end_time,
                        'location': location,
                        'city': cidade,
                        'state': estado,
                        'address': endereco,
                        'neighborhood': bairro,
                        'institution_location': instituicao,
                        'external_responsible': nome,
                        'requester_cpf': re.sub(r'\D', '', cpf) if cpf else "",
                        'external_email': email,
                        'external_responsible_phone': telefone,
                        'quantity': expected_participants,
                        'created_by': default_user,
                        'responsible': default_user,
                        'sector': default_sector,
                    }
                )
                count_created += 1

        self.stdout.write(self.style.SUCCESS(f"Finished! Imported {count_created} rows. Skipped {count_skipped} rows."))
