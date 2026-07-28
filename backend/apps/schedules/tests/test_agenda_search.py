from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.schedules.models import Agenda, Sector

User = get_user_model()

class AgendaSearchTests(APITestCase):
    def setUp(self):
        # Create users
        self.admin = User.objects.create_user(
            email='admin@test.com', 
            password='password123', 
            role='ADMIN'
        )
        self.agent = User.objects.create_user(
            email='agent@test.com', 
            password='password123', 
            role='USER'
        )
        
        # Create sectors
        self.sector = Sector.objects.create(name='Test Sector')
        self.req_sector = Sector.objects.create(name='Solicitações externas')
        
        # Create Agendas
        # 1. Target OS: SO number 5555
        self.target_os = Agenda.objects.create(
            service_order_number=5555,
            title='Agenda Alvo 5555',
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector,
            origin=Agenda.Origin.PUBLIC_FORM,
            date='2026-07-28',
            start_time='08:00',
            end_time='10:00'
        )
        
        # 2. Conflicting year OS: SO number 2026
        self.year_os = Agenda.objects.create(
            service_order_number=2026,
            title='Agenda Ano 2026',
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector,
            origin=Agenda.Origin.PUBLIC_FORM,
            date='2026-07-29',
            start_time='08:00',
            end_time='10:00'
        )
        
        # 3. Text match OS
        self.text_os = Agenda.objects.create(
            title='Centro Cultural',
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector,
            origin=Agenda.Origin.PUBLIC_FORM,
            date='2026-07-28',
            start_time='08:00',
            end_time='10:00'
        )
        
        # 4. OS agent does not have permission to view (admin created, origin is public form, but agent is not responsible/creator)
        # We also set sector to req_sector to ensure it's a request, but since agent didn't create it, they shouldn't see it
        self.hidden_os = Agenda.objects.create(
            service_order_number=6666,
            title='OS Oculta Agent',
            created_by=self.admin,
            responsible=self.admin,
            sector=self.req_sector,
            origin=Agenda.Origin.PUBLIC_FORM,
            date='2026-07-28',
            start_time='08:00',
            end_time='10:00'
        )
        
        self.url = '/api/agendas/'

    def test_search_exact_number(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url, {'source': 'requests', 'q': '5555'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return exactly 1 result (Target OS)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.target_os.id)
        
    def test_search_os_prefix(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url, {'source': 'requests', 'q': 'OS 5555'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.target_os.id)
        
    def test_search_os_no_prefix(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url, {'source': 'requests', 'q': 'OS nº 5555 de 2026'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        # Should NOT return the OS 2026 because the regex isolates 5555
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.target_os.id)
        
    def test_search_protocol_date_mixed(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url, {'source': 'requests', 'q': 'Protocolo 5555 em 28/07/2026'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.target_os.id)
        
    def test_search_prefix_variations(self):
        self.client.force_authenticate(user=self.admin)
        
        variations = [
            'OS: 5555',
            'OS - 5555',
            'Prot nº 5555',
            'Protocolo: 5555',
            'OSnº5555',
        ]
        
        for variant in variations:
            response = self.client.get(self.url, {'source': 'requests', 'q': variant})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results = response.data['results']
            self.assertEqual(len(results), 1, f"Failed on variation: {variant}")
            self.assertEqual(results[0]['id'], self.target_os.id)
        
    def test_search_text_with_number(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url, {'source': 'requests', 'q': 'Centro 2026'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        # Because Centro 2026 doesn't match the OS/Prot prefix, and is not isdigit,
        # it should search textual fields. It will NOT search id=2026.
        # But wait, does text_os have 2026 in textual fields? No, its title is 'Centro Cultural'.
        # Wait, the search query is "Centro 2026", it will look for EXACTLY "Centro 2026" in icontains.
        # Since no OS has "Centro 2026", it should return 0 results, AND IT SHOULD NOT return OS 2026!
        self.assertEqual(len(results), 0)
        
    def test_search_by_date(self):
        self.client.force_authenticate(user=self.admin)
        # Search by date=2026-07-28
        response = self.client.get(self.url, {'source': 'requests', 'date': '2026-07-28'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        # Target OS, text OS, and hidden OS are on this date.
        # Since it's admin, they see all 3.
        self.assertEqual(len(results), 3)
        ids = [r['id'] for r in results]
        self.assertIn(self.target_os.id, ids)
        self.assertIn(self.text_os.id, ids)
        self.assertIn(self.hidden_os.id, ids)
        self.assertNotIn(self.year_os.id, ids) # because year_os is on 2026-07-29

    def test_search_permissions(self):
        self.client.force_authenticate(user=self.agent)
        # Agent tries to search for OS 6666
        response = self.client.get(self.url, {'source': 'requests', 'q': '6666'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        # Should be empty because agent has no permission to view OS 6666
        self.assertEqual(len(results), 0)
