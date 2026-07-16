from django.test import TestCase
from django.utils import timezone
from apps.schedules.models import (
    EducationReport, ShiftSchedule, Team, Chief, Agent, Support, ShiftSwapRequest, Agenda
)
from apps.accounts.models import User
from rest_framework.test import APIClient

class ReportFrequencyValidationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="test@chief.com", password="password", role="CHIEF")
        self.client.force_authenticate(user=self.user)
        
        self.team = Team.objects.create(name="Team Alpha", is_active=True)
        self.chief1 = Chief.objects.create(name="Chief 1", team=self.team, is_active=True, source_id="user:1")
        self.chief2 = Chief.objects.create(name="Chief 2", team=self.team, is_active=True, source_id="user:2")
        self.agent1 = Agent.objects.create(name="Agent 1", team=self.team, is_active=True, source_id="user:3")
        self.agent2_inactive = Agent.objects.create(name="Agent 2", team=self.team, is_active=False, source_id="user:4")
        
        self.schedule = ShiftSchedule.objects.create(
            date=timezone.localdate(),
            team=self.team,
            created_by=self.user
        )
        from apps.schedules.models import Sector
        self.sector = Sector.objects.create(name="Dummy Sector")
        self.agenda = Agenda.objects.create(
            date=self.schedule.date,
            start_time="08:00:00",
            end_time="17:00:00",
            team_ref=self.team,
            sector=self.sector,
            created_by=self.user,
            responsible=self.user,
            status=Agenda.Status.COMPLETED
        )
        
        self.report = EducationReport.objects.create(
            operation_date=self.schedule.date,
            agenda=self.agenda,
            team=self.team.name,
            status=EducationReport.ReportStatus.DRAFT,
            created_by=self.user,
            accessibility_conditions_met="YES"
        )
        from apps.schedules.models import EducationAction
        EducationAction.objects.create(report=self.report, type_action="Blitz")

    def test_inactive_member_ignored(self):
        # agent2_inactive is not active, so we don't include it in checked_members
        self.schedule.checked_members = {
            f"CHIEF_{self.chief1.id}": {"is_absent": False, "reason": ""},
            f"CHIEF_{self.chief2.id}": {"is_absent": False, "reason": ""},
            f"AGENT_{self.agent1.id}": {"is_absent": False, "reason": ""},
        }
        self.schedule.save()

        # Submit for review
        res = self.client.post(f"/api/education-reports/{self.report.id}/submit-for-review/")
        self.assertEqual(res.status_code, 200, res.data)
        
    def test_swap_request_handled(self):
        # chief2 is swapped out for a support
        target_team = Team.objects.create(name="Team Beta", is_active=True)
        support1 = Support.objects.create(name="Support 1", team=target_team, is_active=True, source_id="user:5")
        
        swap = ShiftSwapRequest.objects.create(
            schedule=self.schedule,
            target_team=target_team,
            requester=self.user,
            member_type=ShiftSwapRequest.MemberType.CHIEF,
            from_member_id=self.chief2.id,
            from_member_name=self.chief2.name,
            to_member_id=support1.id,
            to_member_name=support1.name,
            status=ShiftSwapRequest.Status.APPROVED,
            decided_by=self.user
        )
        
        # When swapped, the checked member should be CHIEF_swap-<id> instead of CHIEF_<chief2.id>
        self.schedule.checked_members = {
            f"CHIEF_{self.chief1.id}": {"is_absent": False, "reason": ""},
            f"CHIEF_swap-{swap.id}": {"is_absent": False, "reason": ""},
            f"AGENT_{self.agent1.id}": {"is_absent": False, "reason": ""},
        }
        self.schedule.save()

        res = self.client.post(f"/api/education-reports/{self.report.id}/submit-for-review/")
        self.assertEqual(res.status_code, 200, res.data)
        
    def test_manual_inclusion_ignored(self):
        # Inclusão manual is not expected by the validation since frontend ignores it
        from apps.schedules.models import ShiftManualInclusion
        ShiftManualInclusion.objects.create(
            schedule=self.schedule,
            member_id=999,
            member_name="Manual Guy",
            member_type="CHIEF",
            added_by=self.user
        )
        
        # Still just send the normal team members
        self.schedule.checked_members = {
            f"CHIEF_{self.chief1.id}": {"is_absent": False, "reason": ""},
            f"CHIEF_{self.chief2.id}": {"is_absent": False, "reason": ""},
            f"AGENT_{self.agent1.id}": {"is_absent": False, "reason": ""},
        }
        self.schedule.save()

        res = self.client.post(f"/api/education-reports/{self.report.id}/submit-for-review/")
        self.assertEqual(res.status_code, 200, res.data)
        
    def test_draft_save_reopen_submit(self):
        self.schedule.checked_members = {
            f"CHIEF_{self.chief1.id}": {"is_absent": False, "reason": ""},
            f"CHIEF_{self.chief2.id}": {"is_absent": False, "reason": ""},
            f"AGENT_{self.agent1.id}": {"is_absent": False, "reason": ""},
        }
        self.schedule.save()
        
        # Salvar rascunho (PATCH)
        res_patch = self.client.patch(f"/api/education-reports/{self.report.id}/", {
            "status": "DRAFT",
            "actions": [{"type_action": "Blitz"}],
            "accessibility_conditions_met": "YES"
        }, format="json")
        self.assertEqual(res_patch.status_code, 200)
        
        # Enviar logo após
        res_submit = self.client.post(f"/api/education-reports/{self.report.id}/submit-for-review/")
        self.assertEqual(res_submit.status_code, 200, res_submit.data)

    def test_all_present(self):
        self.schedule.checked_members = {
            f"CHIEF_{self.chief1.id}": {"is_absent": False, "reason": ""},
            f"CHIEF_{self.chief2.id}": {"is_absent": False, "reason": ""},
            f"AGENT_{self.agent1.id}": {"is_absent": False, "reason": ""},
        }
        self.schedule.save()
        res = self.client.post(f"/api/education-reports/{self.report.id}/submit-for-review/")
        self.assertEqual(res.status_code, 200, res.data)

    def test_justified_absence(self):
        from apps.schedules.models import ShiftAbsence
        # Marca chief2 como ausente na schedule
        ShiftAbsence.objects.create(
            schedule=self.schedule,
            member_type=ShiftAbsence.MemberType.CHIEF,
            member_id=self.chief2.id,
            member_name=self.chief2.name,
            reason="Atestado",
            created_by=self.user
        )
        self.schedule.absent_chiefs.add(self.chief2)
        
        self.schedule.checked_members = {
            f"CHIEF_{self.chief1.id}": {"is_absent": False, "reason": ""},
            f"CHIEF_{self.chief2.id}": {"is_absent": True, "reason": "Atestado"},
            f"AGENT_{self.agent1.id}": {"is_absent": False, "reason": ""},
        }
        self.schedule.save()
        res = self.client.post(f"/api/education-reports/{self.report.id}/submit-for-review/")
        self.assertEqual(res.status_code, 200, res.data)

    def test_removed_member_ignored(self):
        # Remove chief2
        self.schedule.removed_chiefs.add(self.chief2)
        # We don't include chief2 in checked_members
        self.schedule.checked_members = {
            f"CHIEF_{self.chief1.id}": {"is_absent": False, "reason": ""},
            f"AGENT_{self.agent1.id}": {"is_absent": False, "reason": ""},
        }
        self.schedule.save()
        res = self.client.post(f"/api/education-reports/{self.report.id}/submit-for-review/")
        self.assertEqual(res.status_code, 200, res.data)

    def test_extra_member_required(self):
        extra_agent = Agent.objects.create(name="Extra Agent", team=self.team, is_active=True, source_id="user:99")
        self.schedule.extra_agents.add(extra_agent)
        
        # If we omit the extra agent, it should fail
        self.schedule.checked_members = {
            f"CHIEF_{self.chief1.id}": {"is_absent": False, "reason": ""},
            f"CHIEF_{self.chief2.id}": {"is_absent": False, "reason": ""},
            f"AGENT_{self.agent1.id}": {"is_absent": False, "reason": ""},
        }
        self.schedule.save()
        res = self.client.post(f"/api/education-reports/{self.report.id}/submit-for-review/")
        self.assertEqual(res.status_code, 400)
        print(res.data)
        self.assertIn("Confira a frequência", res.data["detail"])
        
        # Now include the extra agent
        self.schedule.checked_members[f"AGENT_{extra_agent.id}"] = {"is_absent": False, "reason": ""}
        self.schedule.save()
        patch_data = {"status": "DRAFT", "actions": [{"type_action": "Blitz"}], "accessibility_conditions_met": "YES"}
        res_patch = self.client.patch(f"/api/education-reports/{self.report.id}/", patch_data, format='json')
        if res_patch.status_code != 200:
            print("PATCH ERROR:", res_patch.data)
        self.assertEqual(res_patch.status_code, 200)
        res = self.client.post(f"/api/education-reports/{self.report.id}/submit-for-review/")
        self.assertEqual(res.status_code, 200)

    def test_reopen_report(self):
        # Approve first
        self.report.status = EducationReport.ReportStatus.PENDING_REVIEW
        self.report.save()
        
        # Admin can reject/return it (in a real scenario, there's a return endpoint, but let's just simulate it being returned)
        self.report.status = EducationReport.ReportStatus.RETURNED
        self.report.save()
        
        self.schedule.checked_members = {
            f"CHIEF_{self.chief1.id}": {"is_absent": False, "reason": ""},
            f"CHIEF_{self.chief2.id}": {"is_absent": False, "reason": ""},
            f"AGENT_{self.agent1.id}": {"is_absent": False, "reason": ""},
        }
        self.schedule.save()
        
        # Re-submit
        res = self.client.post(f"/api/education-reports/{self.report.id}/submit-for-review/")
        self.assertEqual(res.status_code, 200, res.data)
