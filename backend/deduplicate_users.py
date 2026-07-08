import os
import django
import unicodedata
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.schedules.models import Agent, Chief, Support, Agenda, ShiftSchedule, ShiftAbsence

def normalize(name):
    # Remove accents and lowercase
    n = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    return n.strip().lower()

def merge_duplicates(model_class, member_type_enum):
    records = model_class.objects.all()
    groups = defaultdict(list)
    
    for r in records:
        groups[normalize(r.name)].append(r)
        
    for norm_name, items in groups.items():
        if len(items) > 1:
            print(f"\n[{model_class.__name__}] Mesclando duplicatas de: {norm_name}")
            
            def score(item):
                s = 0
                if not item.name.isupper(): s += 10
                if getattr(item, 'cpf', None): s += 5
                if getattr(item, 'is_active', False): s += 2
                return s
                
            sorted_items = sorted(items, key=score, reverse=True)
            keep = sorted_items[0]
            print(f"  [MANTER] {keep.name} (ID: {keep.id})")
            
            for remove_obj in sorted_items[1:]:
                print(f"  [REMOVER E TRANSFERIR] {remove_obj.name} (ID: {remove_obj.id})")
                
                # 1. Agendas
                if model_class == Agent:
                    for agenda in remove_obj.agendas.all():
                        agenda.agents_ref.add(keep)
                        agenda.agents_ref.remove(remove_obj)
                elif model_class == Chief:
                    agendas = Agenda.objects.filter(chief_ref=remove_obj)
                    agendas.update(chief_ref=keep)
                elif model_class == Support:
                    Agenda.objects.filter(support_1_ref=remove_obj).update(support_1_ref=keep)
                    Agenda.objects.filter(support_2_ref=remove_obj).update(support_2_ref=keep)

                # 2. ShiftSchedules
                if model_class == Agent:
                    for schedule in remove_obj.extra_shift_schedules.all():
                        schedule.extra_agents.add(keep)
                        schedule.extra_agents.remove(remove_obj)
                    for schedule in remove_obj.removed_shift_schedules.all():
                        schedule.removed_agents.add(keep)
                        schedule.removed_agents.remove(remove_obj)
                    for schedule in remove_obj.absent_shift_schedules.all():
                        schedule.absent_agents.add(keep)
                        schedule.absent_agents.remove(remove_obj)
                        
                elif model_class == Chief:
                    for schedule in remove_obj.extra_shift_schedules.all():
                        schedule.extra_chiefs.add(keep)
                        schedule.extra_chiefs.remove(remove_obj)
                    for schedule in remove_obj.removed_shift_schedules.all():
                        schedule.removed_chiefs.add(keep)
                        schedule.removed_chiefs.remove(remove_obj)
                    for schedule in remove_obj.absent_shift_schedules.all():
                        schedule.absent_chiefs.add(keep)
                        schedule.absent_chiefs.remove(remove_obj)
                        
                elif model_class == Support:
                    for schedule in remove_obj.extra_shift_schedules.all():
                        schedule.extra_supports.add(keep)
                        schedule.extra_supports.remove(remove_obj)
                    for schedule in remove_obj.removed_shift_schedules.all():
                        schedule.removed_supports.add(keep)
                        schedule.removed_supports.remove(remove_obj)
                    for schedule in remove_obj.absent_shift_schedules.all():
                        schedule.absent_supports.add(keep)
                        schedule.absent_supports.remove(remove_obj)
                
                # 3. ShiftAbsence
                if member_type_enum:
                    ShiftAbsence.objects.filter(
                        member_type=member_type_enum, 
                        member_id=remove_obj.id
                    ).update(member_id=keep.id)
                
                # Finally delete the duplicate
                remove_obj.delete()

if __name__ == "__main__":
    print("Iniciando mesclagem definitiva de duplicatas...")
    merge_duplicates(Agent, "AGENT")
    merge_duplicates(Chief, "CHIEF")
    merge_duplicates(Support, "SUPPORT")
    print("\nConcluído!")
