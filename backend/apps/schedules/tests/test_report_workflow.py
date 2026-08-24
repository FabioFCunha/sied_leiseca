from datetime import date
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.schedules.models import ActionType, EducationAction, EducationReport, Agenda, Kit
from apps.schedules.serializers import EducationActionSerializer, EducationReportSerializer
from apps.statistics.models import ConsolidatedStatistic
from apps.statistics.services import generate_statistics_for_report

User = get_user_model()

class EducationReportWorkflowTests(APITestCase):
    def setUp(self):
        # Create users
        self.admin = User.objects.create_user(email="admin@teste.com", password="pwd", role=User.Role.ADMIN)
        self.manager = User.objects.create_user(email="manager@teste.com", password="pwd", role=User.Role.MANAGER)
        self.chief = User.objects.create_user(email="chief@teste.com", password="pwd", role=User.Role.SUPERVISOR)
        self.agent = User.objects.create_user(email="agent@teste.com", password="pwd", role=User.Role.USER)
        self.visitor = User.objects.create_user(email="visitor@teste.com", password="pwd", role=User.Role.VISITOR)

        from apps.schedules.models import Sector
        self.sector = Sector.objects.create(name="Test Sector")

        # Create agenda
        self.chief = User.objects.create_user(email="chief@example.com", password="password", role=User.Role.USER, sector=self.sector)

        from apps.schedules.models import Team, ShiftSchedule
        self.team = Team.objects.create(name="Team A")
        ActionType.objects.update_or_create(
            name="Palestra",
            defaults={"is_active": True, "category": ActionType.Category.LECTURE},
        )
        ActionType.objects.update_or_create(
            name="Praia",
            defaults={"is_active": True, "category": ActionType.Category.EDUCATIONAL_ACTION},
        )
        ActionType.objects.update_or_create(
            name="Ação Educativa",
            defaults={"is_active": True, "category": ActionType.Category.EDUCATIONAL_ACTION},
        )

        self.agenda = Agenda.objects.create(
            title="Acao Teste",
            date="2026-07-01",
            start_time="09:00",
            end_time="10:00",
            status=Agenda.Status.COMPLETED,
            origin=Agenda.Origin.PUBLIC_FORM,
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector,
            team_ref=self.team,
        )

        self.schedule = ShiftSchedule.objects.create(
            team=self.team,
            date=self.agenda.date,
            created_by=self.admin,
        )

        # Create report as draft
        self.report = EducationReport.objects.create(
            agenda=self.agenda,
            created_by=self.chief,
            status=EducationReport.ReportStatus.DRAFT,
            team="Team A",
            operation_date="2026-07-01",
        )

    def test_educational_action_catalog_type_is_accepted(self):
        serializer = EducationActionSerializer(data={"type_action": "Ação Educativa"})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_active_operational_duplicate_is_preferred_over_inactive_legacy(self):
        ActionType.objects.update_or_create(
            name="AÇÃO EDUCATIVA",
            defaults={"is_active": False, "category": ActionType.Category.EDUCATIONAL_ACTION},
        )
        serializer = EducationActionSerializer(data={"type_action": "Ação Educativa"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        action = serializer.save(report=self.report, agenda=self.agenda)
        self.assertEqual(action.type_action, "Ação Educativa")

    def test_only_inactive_legacy_action_type_is_rejected(self):
        ActionType.objects.filter(name__iexact="Ação Educativa").update(
            is_active=False,
            category=ActionType.Category.EDUCATIONAL_ACTION,
        )
        serializer = EducationActionSerializer(data={"type_action": "Ação Educativa"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("type_action", serializer.errors)
        self.assertIn("não está disponível", str(serializer.errors["type_action"][0]))

    def test_program_indicator_remains_rejected_as_action_type(self):
        ActionType.objects.update_or_create(
            name="Escola Nota 10",
            defaults={"is_active": True, "category": ActionType.Category.PROGRAM_INDICATOR},
        )
        serializer = EducationActionSerializer(data={"type_action": "Escola Nota 10"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("type_action", serializer.errors)

    def test_street_action_events_is_accepted_and_updates_its_counter(self):
        serializer = EducationActionSerializer(data={
            "type_action": "Eventos",
            "action_mode": "STREET",
            "approached_actions": 50,
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        action = serializer.save(report=self.report, agenda=self.agenda)
        self.assertEqual(action.type_action, "Eventos")
        self.assertEqual(action.educational_actions, 1)
        self.assertEqual(action.events, 1)

    def test_street_action_rejects_unknown_subtype(self):
        serializer = EducationActionSerializer(data={
            "type_action": "Tipo livre",
            "action_mode": "STREET",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("type_action", serializer.errors)
        self.assertIn("subtipo válido", str(serializer.errors["type_action"][0]))

    def test_report_can_be_rectified_with_second_street_action(self):
        serializer = EducationReportSerializer(
            instance=self.report,
            data={
                "agenda": self.agenda.id,
                "operation_date": "2026-07-01",
                "team": "Team A",
                "status": EducationReport.ReportStatus.RETURNED,
                "actions": [
                    {
                        "type_action": "Palestra",
                        "action_mode": "LECTURE",
                    },
                    {
                        "type_action": "Eventos",
                        "action_mode": "STREET",
                        "approached_actions": 50,
                    },
                ],
            },
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        report = serializer.save()
        self.assertEqual(report.actions.count(), 2)
        street_action = report.actions.get(type_action="Eventos")
        self.assertEqual(street_action.events, 1)

    def test_chief_cannot_approve_or_return(self):
        self.client.force_authenticate(user=self.chief)
        self.report.status = EducationReport.ReportStatus.PENDING_REVIEW
        self.report.save()

        response = self.client.post(f"/api/education-reports/{self.report.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(f"/api/education-reports/{self.report.id}/return-for-correction/", {"notes": "fix it"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_agent_and_visitor_cannot_approve(self):
        self.report.status = EducationReport.ReportStatus.PENDING_REVIEW
        self.report.save()

        for user in [self.agent, self.visitor]:
            self.client.force_authenticate(user=user)
            response = self.client.post(f"/api/education-reports/{self.report.id}/approve/")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_approve_and_return(self):
        self.client.force_authenticate(user=self.manager)
        self.report.status = EducationReport.ReportStatus.PENDING_REVIEW
        self.report.save()

        response = self.client.post(f"/api/education-reports/{self.report.id}/return-for-correction/", {"notes": "needs fix"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, EducationReport.ReportStatus.RETURNED)

        self.report.status = EducationReport.ReportStatus.PENDING_REVIEW
        self.report.save()

        response = self.client.post(f"/api/education-reports/{self.report.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, EducationReport.ReportStatus.APPROVED)
        self.assertTrue(self.report.statistics_processed)

    def test_approve_already_approved_report_returns_400(self):
        self.client.force_authenticate(user=self.manager)
        self.report.status = EducationReport.ReportStatus.PENDING_REVIEW
        self.report.save()

        # 1. Primeira aprovação deve retornar 200 e alterar o status para APPROVED
        response1 = self.client.post(f"/api/education-reports/{self.report.id}/approve/")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, EducationReport.ReportStatus.APPROVED)

        # 2. Segunda aprovação deve retornar 400 com a mensagem correta e manter o status como APPROVED
        response2 = self.client.post(f"/api/education-reports/{self.report.id}/approve/")
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response2.data["detail"], "Apenas relatórios aguardando conferência podem ser aprovados.")
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, EducationReport.ReportStatus.APPROVED)

    def test_approve_draft_report_returns_400_and_does_not_change_status(self):
        self.client.force_authenticate(user=self.manager)
        self.report.status = EducationReport.ReportStatus.DRAFT
        self.report.save()

        response = self.client.post(f"/api/education-reports/{self.report.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Apenas relatórios aguardando conferência podem ser aprovados.")

        # O status permanece DRAFT
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, EducationReport.ReportStatus.DRAFT)

    def test_admin_can_edit_approved_report_via_put_or_patch(self):
        self.client.force_authenticate(user=self.admin)
        self.report.status = EducationReport.ReportStatus.APPROVED
        self.report.save()

        # PUT
        response = self.client.put(f"/api/education-reports/{self.report.id}/", {
            "team": "Team B",
            "agenda": self.agenda.id,
            "operation_date": "2026-07-01",
            "actions": [],
            "accessibility_conditions_met": "YES"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # PATCH
        response = self.client.patch(f"/api/education-reports/{self.report.id}/", {
            "status": "APPROVED"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_editing_approved_report_reprocesses_statistics(self):
        self.client.force_authenticate(user=self.admin)
        Kit.objects.get_or_create(name="Certificados")
        Kit.objects.get_or_create(name="Revistinha")
        self.report.status = EducationReport.ReportStatus.APPROVED
        self.report.operation_date = date(2026, 7, 1)
        self.report.approximate_public = 1
        self.report.accessibility_conditions_met = "YES"
        self.report.save()
        EducationAction.objects.create(
            report=self.report,
            agenda=self.agenda,
            type_action="Praia",
            place_action="Local original",
            start_time="09:00",
            final_hour="10:00",
            approached_actions=50,
            distribution_materials_distributed="Certificados | 2",
        )
        generate_statistics_for_report(self.report, processed_by=self.admin)

        response = self.client.put(f"/api/education-reports/{self.report.id}/", {
            "agenda": self.agenda.id,
            "team": "Team A",
            "operation_date": "2026-07-01",
            "approximate_public": 1,
            "accessibility_conditions_met": "YES",
            "actions": [{
                "type_action": "Praia",
                "place_action": "Local corrigido",
                "start_time": "09:00",
                "final_hour": "10:00",
                "approached_actions": 200,
                "distribution_materials_distributed": "Certificados | 5\nRevistinha | 7",
            }],
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stats = ConsolidatedStatistic.objects.filter(traceability_id=f"report_{self.report.id}", status="ACTIVE")
        audience = stats.get(indicator_type="AUDIENCE", category_action_type__isnull=True, category_entity_type__isnull=True)
        materials = stats.get(indicator_type="MATERIAL", category_action_type__isnull=True, category_entity_type__isnull=True)
        certificados = stats.get(indicator_type="MATERIAL", category_action_type__isnull=True, category_entity_type="CERTIFICADOS ENTREGUES")
        revistinhas = stats.get(indicator_type="MATERIAL", category_action_type__isnull=True, category_entity_type="REVISTINHA SOPRINHO")
        self.assertEqual(audience.value, 200)
        self.assertEqual(materials.value, 12)
        self.assertEqual(certificados.value, 5)
        self.assertEqual(revistinhas.value, 7)

    def test_status_cannot_be_changed_via_payload(self):
        self.client.force_authenticate(user=self.admin)

        # Try to create directly as APPROVED
        response = self.client.post("/api/education-reports/", {
            "agenda": self.agenda.id,
            "team": "Team D",
            "operation_date": "2026-07-01",
            "status": "APPROVED",
            "actions": [],
            "accessibility_conditions_met": "YES"
        }, format="json")
        if response.status_code != 201:
            print(response.json())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_report = EducationReport.objects.get(id=response.data["id"])
        self.assertEqual(new_report.status, EducationReport.ReportStatus.DRAFT)

        # Try to patch status to APPROVED
        response = self.client.patch(f"/api/education-reports/{new_report.id}/", {
            "status": "APPROVED"
        }, format="json")
        if response.status_code != 200:
            print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_report.refresh_from_db()
        self.assertEqual(new_report.status, EducationReport.ReportStatus.DRAFT)

    def test_create_draft_and_submit(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post("/api/education-reports/", {
            "agenda": self.agenda.id,
            "team": "Team E",
            "operation_date": "2026-07-01",
            "actions": [],
            "accessibility_conditions_met": "YES"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        report_id = response.data["id"]

        response = self.client.post(f"/api/education-reports/{report_id}/submit-for-review/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        report = EducationReport.objects.get(id=report_id)
        self.assertEqual(report.status, EducationReport.ReportStatus.PENDING_REVIEW)

    def test_prevent_duplicate_reports_same_agenda_and_team(self):
        self.client.force_authenticate(user=self.admin)

        response1 = self.client.post("/api/education-reports/", {
            "agenda": self.agenda.id,
            "team": "Team F",
            "operation_date": "2026-07-01",
            "actions": [],
            "accessibility_conditions_met": "YES"
        }, format="json")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        response2 = self.client.post("/api/education-reports/", {
            "agenda": self.agenda.id,
            "team": "Team F",
            "operation_date": "2026-07-01",
            "actions": [],
            "accessibility_conditions_met": "YES"
        }, format="json")
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Já existe um relatório técnico", str(response2.data))

    def test_update_own_report_without_duplication_error(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post("/api/education-reports/", {
            "agenda": self.agenda.id,
            "team": "Team C",
            "operation_date": "2026-07-01",
            "actions": [],
            "accessibility_conditions_met": "YES"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        report_id = response.data["id"]

        response = self.client.patch(f"/api/education-reports/{report_id}/", {
            "team": "Team G",
            "general_observations": "Updated"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["general_observations"], "Updated")

    def test_return_correct_and_resubmit(self):
        self.client.force_authenticate(user=self.manager)

        report = EducationReport.objects.create(
            agenda=self.agenda,
            created_by=self.chief,
            status=EducationReport.ReportStatus.PENDING_REVIEW,
            team="Team H",
            operation_date="2026-07-01",
        )

        response = self.client.post(f"/api/education-reports/{report.id}/return-for-correction/", {"notes": "fix"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(f"/api/education-reports/{report.id}/", {
            "general_observations": "Fixed"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(f"/api/education-reports/{report.id}/submit-for-review/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, EducationReport.ReportStatus.PENDING_REVIEW)

    # ------------------------------------------------------------------
    # VISITOR profile tests (new — constraint #2)
    # ------------------------------------------------------------------

    def test_visitor_can_only_see_approved_reports(self):
        """VISITOR deve visualizar apenas relatórios com status APPROVED na listagem."""
        # Create a draft report (must be invisible to VISITOR)
        draft_report = EducationReport.objects.create(
            agenda=self.agenda,
            created_by=self.admin,
            status=EducationReport.ReportStatus.DRAFT,
            team="Team VISITOR-Draft",
            operation_date="2026-07-01",
        )
        # Create an approved report (must be visible to VISITOR)
        approved_report = EducationReport.objects.create(
            agenda=self.agenda,
            created_by=self.admin,
            status=EducationReport.ReportStatus.APPROVED,
            team="Team VISITOR-Approved",
            operation_date="2026-07-01",
        )

        self.client.force_authenticate(user=self.visitor)
        response = self.client.get("/api/education-reports/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        result_ids = [r["id"] for r in response.data.get("results", response.data)]
        self.assertIn(approved_report.id, result_ids, "VISITOR deve ver relatório APPROVED")
        self.assertNotIn(draft_report.id, result_ids, "VISITOR não deve ver relatório DRAFT")

        # Retrieve of a non-approved report must return 404
        response_draft = self.client.get(f"/api/education-reports/{draft_report.id}/")
        self.assertEqual(
            response_draft.status_code,
            status.HTTP_404_NOT_FOUND,
            "VISITOR deve receber 404 ao tentar recuperar relatório não aprovado",
        )

        # Retrieve of an approved report must return 200
        response_approved = self.client.get(f"/api/education-reports/{approved_report.id}/")
        self.assertEqual(
            response_approved.status_code,
            status.HTTP_200_OK,
            "VISITOR deve conseguir recuperar relatório APPROVED",
        )

    def test_visitor_cannot_perform_any_writes(self):
        """VISITOR deve receber 403 em todas as ações de escrita do EducationReportViewSet."""
        # Create an approved report to use as target for actions
        approved_report = EducationReport.objects.create(
            agenda=self.agenda,
            created_by=self.admin,
            status=EducationReport.ReportStatus.APPROVED,
            team="Team VISITOR-Write",
            operation_date="2026-07-01",
        )

        self.client.force_authenticate(user=self.visitor)

        # Standard write actions
        response = self.client.post("/api/education-reports/", {"team": "X", "operation_date": "2026-07-01"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, "create deve retornar 403 para VISITOR")

        response = self.client.put(f"/api/education-reports/{approved_report.id}/", {"team": "X"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, "update deve retornar 403 para VISITOR")

        response = self.client.patch(f"/api/education-reports/{approved_report.id}/", {"team": "X"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, "partial_update deve retornar 403 para VISITOR")

        response = self.client.delete(f"/api/education-reports/{approved_report.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, "destroy deve retornar 403 para VISITOR")

        # Custom write actions
        response = self.client.post(f"/api/education-reports/{approved_report.id}/submit-for-review/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, "submit-for-review deve retornar 403 para VISITOR")

        response = self.client.post(f"/api/education-reports/{approved_report.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, "approve deve retornar 403 para VISITOR")

        response = self.client.post(f"/api/education-reports/{approved_report.id}/return-for-correction/", {"notes": "x"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, "return-for-correction deve retornar 403 para VISITOR")

        response = self.client.post(f"/api/education-reports/{approved_report.id}/process-statistics/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, "process-statistics deve retornar 403 para VISITOR")
