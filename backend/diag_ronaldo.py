import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.schedules.models import ShiftSchedule, Agenda, EducationReport, Agent, Support

User = get_user_model()

def diagnose_user(cpf=None, name=None):
    print(f"\n--- Diagnosticando: {name or cpf} ---")
    if cpf:
        user = User.objects.filter(cpf=cpf).first()
    elif name:
        user = User.objects.filter(full_name__icontains=name).first()
    
    if not user:
        print(f"Usuário não encontrado.")
        return

    print(f"- ID do usuário: {user.id}")
    print(f"- source_id: {getattr(user, 'source_id', 'N/A')}")
    print(f"- CPF: {user.cpf}")
    print(f"- função operacional: {getattr(user, 'role', 'N/A')}")
    
    agent = Agent.objects.filter(user=user).first()
    support = Support.objects.filter(user=user).first()
    
    print(f"- Agent relacionado: {agent.id if agent else 'Não'}")
    print(f"- Support relacionado: {support.id if support else 'Não'}")
    
    # vínculos na escala
    scales_agent = ShiftSchedule.objects.filter(agents=user).count()
    scales_support = ShiftSchedule.objects.filter(supports=user).count()
    print(f"- vínculo na escala como agente (count): {scales_agent}")
    print(f"- vínculo na escala como apoio (count): {scales_support}")
    
    # vínculos no relatório (EducationReport)
    reports_agent = EducationReport.objects.filter(agents=user).count()
    reports_support = EducationReport.objects.filter(supports=user).count()
    print(f"- vínculo no relatório como agente (count): {reports_agent}")
    print(f"- vínculo no relatório como apoio (count): {reports_support}")

if __name__ == '__main__':
    diagnose_user(cpf='01229890742', name='Ronaldo')
    diagnose_user(name='Fernanda Cristina')
