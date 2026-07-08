import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.accounts.models import User

def grant_auditor_access(email):
    user = User.objects.filter(email=email).first()
    if user:
        user.is_superuser = True
        user.is_staff = True
        user.save()
        print(f"Sucesso! Acesso de auditoria concedido para o usuário: {email}")
    else:
        print(f"Erro: Nenhum usuário encontrado com o e-mail '{email}'.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python grant_auditor.py <email>")
    else:
        grant_auditor_access(sys.argv[1])
