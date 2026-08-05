import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.schedules.models import EducationReport, EducationAction, AgendaMaterial

print("--- EducationReport distribution_materials_distributed ---")
for r in EducationReport.objects.exclude(distribution_materials_distributed__exact='').exclude(distribution_materials_distributed__isnull=True).values('id', 'distribution_materials_distributed')[:5]:
    print(r)

print("\n--- EducationAction distribution_materials_distributed ---")
for a in EducationAction.objects.exclude(distribution_materials_distributed__exact='').exclude(distribution_materials_distributed__isnull=True).values('id', 'distribution_materials_distributed')[:5]:
    print(a)

print("\n--- AgendaMaterial ---")
for m in AgendaMaterial.objects.select_related('kit', 'material').all()[:10]:
    print(f"ID: {m.id}, Kit: {m.kit.name if m.kit else None}, Material: {m.material.name if m.material else None}, Qtd: {m.quantity}")

