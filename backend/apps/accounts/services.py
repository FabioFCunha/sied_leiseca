from django.db import transaction

def deactivate_user_dependencies(user):
    """
    Desativa as entidades operacionais (Chief, Agent, Support) atreladas a este usuário.
    TODO: Refatorar para usar OneToOneField em vez de pesquisa por string em source_id, 
    permitindo que o banco de dados garanta a integridade estrutural no futuro.
    """
    from apps.schedules.models import Chief, Agent, Support
    from apps.accounts.serializers import get_safe_lookup_query, deactivate_other_user_lookups
    
    q = get_safe_lookup_query(user)
        
    Chief.objects.filter(q).update(is_active=False)
    Agent.objects.filter(q).update(is_active=False)
    Support.objects.filter(q).update(is_active=False)
    
    deactivate_other_user_lookups(user)

def deactivate_user(user):
    """
    Serviço central de inativação de usuário (Soft Delete).
    Marca o usuário como inativo e propaga a inativação para todas as suas dependências operacionais.
    """
    with transaction.atomic():
        user.is_active = False
        user.save(update_fields=["is_active"])
        deactivate_user_dependencies(user)
