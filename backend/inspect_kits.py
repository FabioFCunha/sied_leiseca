import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.schedules.models import Kit, Material
print("--- KITS ---")
for k in Kit.objects.all():
    print(k.id, k.name)
print("--- MATERIALS ---")
for m in Material.objects.all():
    print(m.id, m.name)
