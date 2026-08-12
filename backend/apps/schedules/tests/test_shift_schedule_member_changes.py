from datetime import date
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.schedules.models import Agent, Chief, ShiftSchedule, ShiftScheduleChange, Support, Team
from apps.schedules.services import get_effective_members


class ShiftScheduleMemberChangeTests(APITestCase):
    def setUp(self):
        self.team = Team.objects.create(name='MC ALFA', is_active=True)
        self.other_team = Team.objects.create(name='MC BRAVO', is_active=True)
        self.admin = User.objects.create_user(
            email='admin-member-change@test.com',
            password='pwd',
            role=User.Role.ADMIN,
            full_name='Admin Member Change',
        )
        self.supervisor = User.objects.create_user(
            email='supervisor-member-change@test.com',
            password='pwd',
            role=User.Role.SUPERVISOR,
            full_name='Supervisor Member Change',
        )
        self.schedule = ShiftSchedule.objects.create(
            date=date(2026, 8, 3),
            team=self.team,
            created_by=self.admin,
        )
        self.chief = Chief.objects.create(name='Chief Alfa', team=self.team, is_active=True, source_id='user:101')
        self.agent = Agent.objects.create(name='Agent Alfa', team=self.team, is_active=True, source_id='user:102')
        self.support = Support.objects.create(name='Support Alfa', team=self.team, is_active=True, source_id='user:103')
        self.extra_chief = Chief.objects.create(name='Chief Bravo', team=self.other_team, is_active=True, source_id='user:201')
        self.extra_agent = Agent.objects.create(name='Agent Bravo', team=self.other_team, is_active=True, source_id='user:202')
        self.extra_support = Support.objects.create(name='Support Bravo', team=self.other_team, is_active=True, source_id='user:203')
        self.url = reverse('shift-schedules-member-change', args=[self.schedule.id])
        self.client.raise_request_exception = False

    def authenticate_admin(self):
        self.client.force_authenticate(self.admin)

    def test_remove_chief_with_reason(self):
        self.authenticate_admin()
        response = self.client.post(self.url, {
            'action': 'REMOVED',
            'member_type': 'CHIEF',
            'member_id': self.chief.id,
            'reason': 'Atestado medico',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.removed_chiefs.filter(id=self.chief.id).exists())
        record = ShiftScheduleChange.objects.get(schedule=self.schedule, member_type='CHIEF', member_id=self.chief.id)
        self.assertEqual(record.action, 'REMOVED')
        self.assertEqual(record.reason, 'Atestado medico')
        self.assertEqual(record.created_by, self.admin)
        self.assertIsNotNone(record.created_at)

    def test_remove_agent_with_reason(self):
        self.authenticate_admin()
        response = self.client.post(self.url, {
            'action': 'REMOVED',
            'member_type': 'AGENT',
            'member_id': self.agent.id,
            'reason': 'Remanejado para outra equipe',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.removed_agents.filter(id=self.agent.id).exists())

    def test_remove_support_with_reason(self):
        self.authenticate_admin()
        response = self.client.post(self.url, {
            'action': 'REMOVED',
            'member_type': 'SUPPORT',
            'member_id': self.support.id,
            'reason': 'Apoio deslocado',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.removed_supports.filter(id=self.support.id).exists())

    def test_prevent_removal_without_reason(self):
        self.authenticate_admin()
        response = self.client.post(self.url, {
            'action': 'REMOVED',
            'member_type': 'CHIEF',
            'member_id': self.chief.id,
            'reason': '   ',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.schedule.refresh_from_db()
        self.assertFalse(self.schedule.removed_chiefs.filter(id=self.chief.id).exists())
        self.assertEqual(ShiftScheduleChange.objects.count(), 0)

    def test_add_extra_chief_with_reason(self):
        self.authenticate_admin()
        response = self.client.post(self.url, {
            'action': 'EXTRA',
            'member_type': 'CHIEF',
            'member_id': self.extra_chief.id,
            'reason': 'Reforco de chefia',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.extra_chiefs.filter(id=self.extra_chief.id).exists())

    def test_add_extra_agent_with_reason(self):
        self.authenticate_admin()
        response = self.client.post(self.url, {
            'action': 'EXTRA',
            'member_type': 'AGENT',
            'member_id': self.extra_agent.id,
            'reason': 'Reforco operacional',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.extra_agents.filter(id=self.extra_agent.id).exists())

    def test_add_extra_support_with_reason(self):
        self.authenticate_admin()
        response = self.client.post(self.url, {
            'action': 'EXTRA',
            'member_type': 'SUPPORT',
            'member_id': self.extra_support.id,
            'reason': 'Apoio adicional',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.extra_supports.filter(id=self.extra_support.id).exists())

    def test_prevent_extra_without_reason(self):
        self.authenticate_admin()
        response = self.client.post(self.url, {
            'action': 'EXTRA',
            'member_type': 'AGENT',
            'member_id': self.extra_agent.id,
            'reason': '',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.schedule.refresh_from_db()
        self.assertFalse(self.schedule.extra_agents.filter(id=self.extra_agent.id).exists())
        self.assertEqual(ShiftScheduleChange.objects.count(), 0)

    def test_same_transaction_rolls_back_schedule_change(self):
        self.authenticate_admin()
        with patch('apps.schedules.views.ShiftScheduleChange.objects.create', side_effect=RuntimeError('boom')):
            response = self.client.post(self.url, {
                'action': 'EXTRA',
                'member_type': 'AGENT',
                'member_id': self.extra_agent.id,
                'reason': 'Reforco excepcional',
            }, format='json')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.schedule.refresh_from_db()
        self.assertFalse(self.schedule.extra_agents.filter(id=self.extra_agent.id).exists())
        self.assertEqual(ShiftScheduleChange.objects.count(), 0)

    def test_prevent_immediate_duplicate_extra(self):
        self.schedule.extra_agents.add(self.extra_agent)
        self.authenticate_admin()
        response = self.client.post(self.url, {
            'action': 'EXTRA',
            'member_type': 'AGENT',
            'member_id': self.extra_agent.id,
            'reason': 'Duplicado',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ShiftScheduleChange.objects.count(), 0)

    def test_reinclude_removed_extra_agent(self):
        self.schedule.extra_agents.add(self.extra_agent)
        self.schedule.removed_agents.add(self.extra_agent)
        removed_record = ShiftScheduleChange.objects.create(
            schedule=self.schedule,
            action='REMOVED',
            member_type='AGENT',
            member_id=self.extra_agent.id,
            member_name=self.extra_agent.name,
            reason='Troca anterior',
            created_by=self.admin,
        )

        self.authenticate_admin()
        response = self.client.post(self.url, {
            'action': 'EXTRA',
            'member_type': 'AGENT',
            'member_id': self.extra_agent.id,
            'reason': 'Reinclusao operacional',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.extra_agents.filter(id=self.extra_agent.id).exists())
        self.assertFalse(self.schedule.removed_agents.filter(id=self.extra_agent.id).exists())
        history = ShiftScheduleChange.objects.filter(
            schedule=self.schedule,
            member_type='AGENT',
            member_id=self.extra_agent.id,
        ).order_by('created_at')
        self.assertEqual(history.count(), 2)
        self.assertEqual(history.first().id, removed_record.id)
        self.assertEqual(list(history.values_list('action', flat=True)), ['REMOVED', 'EXTRA'])
        members = get_effective_members(self.schedule)
        self.assertIn(
            self.extra_agent.id,
            [member['id'] for member in members['agents'] if member.get('is_extra')],
        )

    def test_reinclude_removed_extra_chief(self):
        self.schedule.extra_chiefs.add(self.extra_chief)
        self.schedule.removed_chiefs.add(self.extra_chief)
        ShiftScheduleChange.objects.create(
            schedule=self.schedule,
            action='REMOVED',
            member_type='CHIEF',
            member_id=self.extra_chief.id,
            member_name=self.extra_chief.name,
            reason='Troca anterior',
            created_by=self.admin,
        )

        self.authenticate_admin()
        response = self.client.post(self.url, {
            'action': 'EXTRA',
            'member_type': 'CHIEF',
            'member_id': self.extra_chief.id,
            'reason': 'Reforco de retorno',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.extra_chiefs.filter(id=self.extra_chief.id).exists())
        self.assertFalse(self.schedule.removed_chiefs.filter(id=self.extra_chief.id).exists())
        members = get_effective_members(self.schedule)
        self.assertIn(
            self.extra_chief.id,
            [member['id'] for member in members['chiefs'] if member.get('is_extra')],
        )

    def test_reinclude_removed_extra_support(self):
        self.schedule.extra_supports.add(self.extra_support)
        self.schedule.removed_supports.add(self.extra_support)
        ShiftScheduleChange.objects.create(
            schedule=self.schedule,
            action='REMOVED',
            member_type='SUPPORT',
            member_id=self.extra_support.id,
            member_name=self.extra_support.name,
            reason='Troca anterior',
            created_by=self.admin,
        )

        self.authenticate_admin()
        response = self.client.post(self.url, {
            'action': 'EXTRA',
            'member_type': 'SUPPORT',
            'member_id': self.extra_support.id,
            'reason': 'Apoio recolocado',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.extra_supports.filter(id=self.extra_support.id).exists())
        self.assertFalse(self.schedule.removed_supports.filter(id=self.extra_support.id).exists())
        members = get_effective_members(self.schedule)
        self.assertIn(
            self.extra_support.id,
            [member['id'] for member in members['supports'] if member.get('is_extra')],
        )

    def test_reinclude_removed_extra_does_not_change_other_members(self):
        other_extra = Agent.objects.create(
            name='Agent Charlie',
            team=self.other_team,
            is_active=True,
            source_id='user:204',
        )
        other_removed = Agent.objects.create(
            name='Agent Delta',
            team=self.other_team,
            is_active=True,
            source_id='user:205',
        )
        self.schedule.extra_agents.add(self.extra_agent, other_extra)
        self.schedule.removed_agents.add(self.extra_agent, other_removed)

        self.authenticate_admin()
        response = self.client.post(self.url, {
            'action': 'EXTRA',
            'member_type': 'AGENT',
            'member_id': self.extra_agent.id,
            'reason': 'Reinclusao pontual',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.extra_agents.filter(id=other_extra.id).exists())
        self.assertTrue(self.schedule.removed_agents.filter(id=other_removed.id).exists())

    def test_history_is_returned_in_api_ordered_latest_first(self):
        self.authenticate_admin()
        first = self.client.post(self.url, {
            'action': 'EXTRA',
            'member_type': 'AGENT',
            'member_id': self.extra_agent.id,
            'reason': 'Primeiro registro',
        }, format='json')
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        second = self.client.post(self.url, {
            'action': 'REMOVED',
            'member_type': 'CHIEF',
            'member_id': self.chief.id,
            'reason': 'Segundo registro',
        }, format='json')

        self.assertEqual(second.status_code, status.HTTP_200_OK)
        history = second.data['member_changes']
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['reason'], 'Segundo registro')
        self.assertEqual(history[0]['created_by_name'], self.admin.full_name)
        self.assertEqual(history[1]['reason'], 'Primeiro registro')

    def test_legacy_schedule_without_history_remains_valid(self):
        self.authenticate_admin()
        response = self.client.get(reverse('shift-schedules-detail', args=[self.schedule.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['member_changes'], [])

    def test_permissions_not_expanded_for_supervisor(self):
        self.client.force_authenticate(self.supervisor)
        response = self.client.post(self.url, {
            'action': 'REMOVED',
            'member_type': 'CHIEF',
            'member_id': self.chief.id,
            'reason': 'Sem permissao',
        }, format='json')

        self.assertIn(response.status_code, {status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND})
