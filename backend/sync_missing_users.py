import os
import django
from django.utils.text import slugify

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.accounts.models import User
from apps.schedules.models import Agent, Chief, Support
from apps.accounts.serializers import sync_user_lookup

models = [
    (Agent, User.Role.USER),
    (Chief, User.Role.SUPERVISOR),
    (Support, User.Role.SUPPORT)
]

print("Verificando trabalhadores sem usuário no sistema...")
created_count = 0

for model, role in models:
    for lookup in model.objects.filter(is_active=True):
        cpf = "".join(filter(str.isdigit, lookup.cpf or ""))
        if cpf:
            user = User.objects.filter(cpf=cpf).first() or User.objects.filter(full_name__iexact=lookup.name).first()
        else:
            user = User.objects.filter(full_name__iexact=lookup.name).first()
        
        if not user:
            # Generate a placeholder email
            base_email = f"{slugify(lookup.name)}@sem-email.local"
            email = base_email
            counter = 1
            while User.objects.filter(email=email).exists():
                email = f"{base_email.split('@')[0]}{counter}@sem-email.local"
                counter += 1
            
            # Create the User
            user = User(
                email=email,
                username=email,
                full_name=lookup.name,
                cpf=cpf,
                role=role,
                is_active=True
            )
            user.set_unusable_password()
            user.save()
            
            # Re-sync to ensure the lookup table points to this new User
            sync_user_lookup(user, team=lookup.team, clear_team=not lookup.team)
            
            created_count += 1
            print(f"Criado usuário para: {lookup.name} (Papel: {role})")

print(f"\nFinalizado! {created_count} novos usuários foram criados.")
