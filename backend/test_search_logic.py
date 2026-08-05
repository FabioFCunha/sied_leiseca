import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.schedules.views import AgendaViewSet
from apps.schedules.models import Agenda
import re

User = get_user_model()

def run_test_case(name, user, params):
    print(f"\n--- Caso: {name} ---")
    print(f"User Role: {user.role}, Params: {params}")
    factory = RequestFactory()
    request = factory.get('/agendas/')
    request.user = user
    request.query_params = params
    
    view = AgendaViewSet()
    view.request = request
    
    try:
        queryset = view.get_queryset()
        sql = str(queryset.query)
        print("SQL Generated:")
        
        # Format the SQL for easier reading by finding the WHERE clause
        where_idx = sql.find('WHERE')
        if where_idx != -1:
            print("WHERE " + sql[where_idx+6:])
        else:
            print("No WHERE clause (All records)")
            
    except Exception as e:
        print(f"Error: {e}")

# Create test users
admin_user = User(id=999, role='ADMIN', is_active=True, email='admin@test.com')
agent_user = User(id=888, role='USER', is_active=True, email='agent@test.com')

cases = [
    ("1. 5555", admin_user, {'source': 'requests', 'q': '5555'}),
    ("2. OS 5555", admin_user, {'source': 'requests', 'q': 'OS 5555'}),
    ("3. OS nº 5555", admin_user, {'source': 'requests', 'q': 'OS nº 5555'}),
    ("4. Prot. 5555", admin_user, {'source': 'requests', 'q': 'Prot. 5555'}),
    ("5. Protocolo 5555", admin_user, {'source': 'requests', 'q': 'Protocolo 5555'}),
    ("6. Pesquisa somente por data", admin_user, {'source': 'requests', 'date': '2026-07-28'}),
    ("7. Pesquisa por texto comum", admin_user, {'source': 'requests', 'q': 'Centro'}),
    ("8. Texto e data simultaneamente", admin_user, {'source': 'requests', 'q': 'Centro', 'date': '2026-07-28'}),
    ("9. Busca OS sem permissao", agent_user, {'source': 'requests', 'q': '5555'})
]

for name, user, params in cases:
    run_test_case(name, user, params)
