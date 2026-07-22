import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('187.127.45.148', username='root', password='eeX1d3Vnbp#rbN&)')

cmd = """
from django.contrib.auth import get_user_model
User = get_user_model()
from apps.schedules.models import ShiftSchedule
from django.db.models import Q

user = User.objects.filter(full_name__icontains="Thayrone").first()

q_filter = Q()
if user.sector_id and user.sector and user.sector.name:
    q_filter |= Q(team__name__iexact=user.sector.name)

from apps.schedules.models import Chief, Agent, Support
source_id = f"user:{user.id}"
chief_fallback_q = Q()
cpf_numeros = "".join(char for char in str(user.cpf or "") if char.isdigit())
if cpf_numeros and len(cpf_numeros) == 11:
    formatted_cpf = f"{cpf_numeros[:3]}.{cpf_numeros[3:6]}.{cpf_numeros[6:9]}-{cpf_numeros[9:]}"
    chief_fallback_q |= Q(cpf=cpf_numeros) | Q(cpf=formatted_cpf)
elif cpf_numeros:
    chief_fallback_q |= Q(cpf=cpf_numeros)
    
agent_support_fallback_q = Q()
if cpf_numeros and len(cpf_numeros) == 11:
    agent_support_fallback_q |= Q(cpf=cpf_numeros) | Q(cpf=formatted_cpf)
elif cpf_numeros:
    agent_support_fallback_q |= Q(cpf=cpf_numeros)
if user.full_name and user.sector_id and user.sector and user.sector.name:
    agent_support_fallback_q |= Q(name__iexact=user.full_name, team__name__iexact=user.sector.name)
    
agent_ids = list(Agent.objects.filter(Q(source_id=source_id) | agent_support_fallback_q).values_list("id", flat=True))
print("Agent IDs:", agent_ids)

if agent_ids:
    q_filter |= Q(extra_agents__in=agent_ids)
    agent_team_ids = Agent.objects.filter(id__in=agent_ids, team__isnull=False).values_list('team_id', flat=True)
    if agent_team_ids:
        q_filter |= Q(team_id__in=agent_team_ids)

qs = ShiftSchedule.objects.filter(q_filter).distinct()
print("Schedules in July (filter):", qs.filter(date__gte="2026-07-01", date__lte="2026-07-31").count())
"""
stdin, stdout, stderr = client.exec_command('docker exec -i sied_backend python manage.py shell')
stdin.write(cmd)
stdin.channel.shutdown_write()

print("STDOUT:", stdout.read().decode('utf-8', errors='ignore'))
print("STDERR:", stderr.read().decode('utf-8', errors='ignore'))
