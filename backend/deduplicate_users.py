import os
import django
import unicodedata
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.schedules.models import Agent, Chief, Support

def normalize(name):
    # Remove accents and lowercase
    n = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    return n.strip().lower()

def deduplicate_model(model_class):
    records = model_class.objects.all()
    groups = defaultdict(list)
    
    for r in records:
        groups[normalize(r.name)].append(r)
        
    for norm_name, items in groups.items():
        if len(items) > 1:
            print(f"\nEncontrado grupo de duplicatas em {model_class.__name__}: {norm_name}")
            
            # Escolher qual manter ativo: 
            # 1. Aquele que não é tudo maiúsculo
            # 2. Aquele que tem CPF (se tiver)
            # Vamos ordenar para que o "melhor" fique em primeiro.
            
            def score(item):
                s = 0
                # Pontos se não for tudo maiúsculo (tem formatação de título/minúsculas)
                if not item.name.isupper():
                    s += 10
                # Pontos se tiver CPF
                if getattr(item, 'cpf', None):
                    s += 5
                # Pontos se já estiver ativo
                if item.is_active:
                    s += 2
                return s
                
            sorted_items = sorted(items, key=score, reverse=True)
            
            keep = sorted_items[0]
            print(f"  [MANTER ATIVO] {keep.name} (ID: {keep.id})")
            
            for disable in sorted_items[1:]:
                if disable.is_active:
                    disable.is_active = False
                    disable.save(update_fields=['is_active'])
                    print(f"  [DESATIVADO] {disable.name} (ID: {disable.id})")
                else:
                    print(f"  [JÁ INATIVO] {disable.name} (ID: {disable.id})")

if __name__ == "__main__":
    print("Iniciando desativação de duplicatas antigas/maiúsculas...")
    deduplicate_model(Agent)
    deduplicate_model(Chief)
    deduplicate_model(Support)
    print("\nConcluído!")
