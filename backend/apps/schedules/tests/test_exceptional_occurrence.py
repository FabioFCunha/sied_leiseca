from datetime import date, time

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.schedules.models import Agenda, EducationReport, Sector
from apps.schedules.serializers import EducationReportSerializer

User = get_user_model()


class EducationReportExceptionalOccurrenceTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin.exception@example.com",
            password="pwd",
            role=User.Role.ADMIN,
            full_name="Admin Exception",
        )
        self.sector = Sector.objects.create(name="Setor Exception")
        self.agenda = Agenda.objects.create(
            title="Relatorio Tecnico",
            description="Agenda para testes",
            date=date(2026, 8, 4),
            start_time=time(9, 0),
            end_time=time(10, 0),
            location="Local Teste",
            status=Agenda.Status.APPROVED,
            origin=Agenda.Origin.PUBLIC_FORM,
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector,
        )
        self.client.force_authenticate(user=self.admin)

    def base_payload(self):
        return {
            "agenda": self.agenda.id,
            "team": "Equipe Teste",
            "operation_date": "2026-08-04",
            "accessibility_conditions_met": "YES",
            "actions": [],
            "general_observations": "Observacao geral preservada",
            "occurrence_observation": "Observacao legado preservada",
        }

    def occurrence_payload(self):
        payload = self.base_payload()
        payload.update({
            "has_exceptional_occurrence": True,
            "exceptional_occurrence_type": EducationReport.ExceptionalOccurrenceType.VEHICLE_BREAKDOWN,
            "exceptional_occurrence_description": "Pane antes do inicio da atividade.",
            "exceptional_occurrence_actions_taken": "Equipe acionou apoio e reorganizou a chegada.",
            "exceptional_occurrence_impact": EducationReport.ExceptionalOccurrenceImpact.PARTIAL,
        })
        return payload

    def create_report(self, payload=None):
        response = self.client.post("/api/education-reports/", payload or self.base_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        return response

    def test_report_without_exceptional_occurrence_is_valid_and_defaults_are_returned(self):
        response = self.create_report()
        report = EducationReport.objects.get(id=response.data["id"])

        self.assertFalse(report.has_exceptional_occurrence)
        self.assertEqual(report.exceptional_occurrence_type, "")
        self.assertEqual(report.exceptional_occurrence_description, "")
        self.assertEqual(report.exceptional_occurrence_actions_taken, "")
        self.assertEqual(report.exceptional_occurrence_impact, "")

        self.assertIn("has_exceptional_occurrence", response.data)
        self.assertIn("exceptional_occurrence_type", response.data)
        self.assertIn("exceptional_occurrence_description", response.data)
        self.assertIn("exceptional_occurrence_actions_taken", response.data)
        self.assertIn("exceptional_occurrence_impact", response.data)

    def test_complete_exceptional_occurrence_is_accepted_and_returned_on_create_update_and_read(self):
        response = self.create_report(self.occurrence_payload())
        report_id = response.data["id"]

        self.assertTrue(response.data["has_exceptional_occurrence"])
        self.assertEqual(
            response.data["exceptional_occurrence_type"],
            EducationReport.ExceptionalOccurrenceType.VEHICLE_BREAKDOWN,
        )

        update_payload = self.occurrence_payload()
        update_payload["exceptional_occurrence_description"] = "Pane resolvida com troca de viatura."
        update_payload["exceptional_occurrence_actions_taken"] = "Chefia acionou substituicao operacional."
        put_response = self.client.put(f"/api/education-reports/{report_id}/", update_payload, format="json")
        self.assertEqual(put_response.status_code, status.HTTP_200_OK, put_response.json())
        self.assertEqual(put_response.data["exceptional_occurrence_description"], update_payload["exceptional_occurrence_description"])

        get_response = self.client.get(f"/api/education-reports/{report_id}/")
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data["exceptional_occurrence_actions_taken"], update_payload["exceptional_occurrence_actions_taken"])

    def test_missing_type_is_rejected(self):
        payload = self.occurrence_payload()
        payload["exceptional_occurrence_type"] = ""
        response = self.client.post("/api/education-reports/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exceptional_occurrence_type", response.data)

    def test_missing_description_is_rejected(self):
        payload = self.occurrence_payload()
        payload["exceptional_occurrence_description"] = ""
        response = self.client.post("/api/education-reports/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exceptional_occurrence_description", response.data)

    def test_missing_actions_taken_is_rejected(self):
        payload = self.occurrence_payload()
        payload["exceptional_occurrence_actions_taken"] = ""
        response = self.client.post("/api/education-reports/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exceptional_occurrence_actions_taken", response.data)

    def test_missing_impact_is_rejected(self):
        payload = self.occurrence_payload()
        payload["exceptional_occurrence_impact"] = ""
        response = self.client.post("/api/education-reports/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exceptional_occurrence_impact", response.data)

    def test_invalid_type_is_rejected(self):
        payload = self.occurrence_payload()
        payload["exceptional_occurrence_type"] = "INVALID"
        response = self.client.post("/api/education-reports/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exceptional_occurrence_type", response.data)

    def test_invalid_impact_is_rejected(self):
        payload = self.occurrence_payload()
        payload["exceptional_occurrence_impact"] = "INVALID"
        response = self.client.post("/api/education-reports/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exceptional_occurrence_impact", response.data)

    def test_marking_false_clears_detailed_fields_and_preserves_legacy_observations(self):
        response = self.create_report(self.occurrence_payload())
        report_id = response.data["id"]

        patch_response = self.client.patch(
            f"/api/education-reports/{report_id}/",
            {
                "has_exceptional_occurrence": False,
                "general_observations": "Observacao geral preservada",
                "occurrence_observation": "Observacao legado preservada",
            },
            format="json",
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK, patch_response.json())

        report = EducationReport.objects.get(id=report_id)
        self.assertFalse(report.has_exceptional_occurrence)
        self.assertEqual(report.exceptional_occurrence_type, "")
        self.assertEqual(report.exceptional_occurrence_description, "")
        self.assertEqual(report.exceptional_occurrence_actions_taken, "")
        self.assertEqual(report.exceptional_occurrence_impact, "")
        self.assertEqual(report.general_observations, "Observacao geral preservada")
        self.assertEqual(report.occurrence_observation, "Observacao legado preservada")

    def test_partial_patch_preserves_existing_exceptional_occurrence_values(self):
        response = self.create_report(self.occurrence_payload())
        report_id = response.data["id"]

        patch_response = self.client.patch(
            f"/api/education-reports/{report_id}/",
            {"exceptional_occurrence_description": "Descricao atualizada via PATCH."},
            format="json",
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK, patch_response.json())
        self.assertEqual(
            patch_response.data["exceptional_occurrence_type"],
            EducationReport.ExceptionalOccurrenceType.VEHICLE_BREAKDOWN,
        )
        self.assertEqual(
            patch_response.data["exceptional_occurrence_impact"],
            EducationReport.ExceptionalOccurrenceImpact.PARTIAL,
        )
        self.assertEqual(
            patch_response.data["exceptional_occurrence_actions_taken"],
            "Equipe acionou apoio e reorganizou a chegada.",
        )

    def test_legacy_report_serializes_normally(self):
        report = EducationReport.objects.create(
            agenda=self.agenda,
            created_by=self.admin,
            team="Equipe Legado",
            operation_date=date(2026, 8, 4),
            general_observations="Texto legado",
            occurrence_observation="Ocorrencia legado",
        )
        data = EducationReportSerializer(report).data

        self.assertFalse(data["has_exceptional_occurrence"])
        self.assertEqual(data["exceptional_occurrence_type"], "")
        self.assertEqual(data["exceptional_occurrence_description"], "")
        self.assertEqual(data["exceptional_occurrence_actions_taken"], "")
        self.assertEqual(data["exceptional_occurrence_impact"], "")
        self.assertEqual(data["general_observations"], "Texto legado")
        self.assertEqual(data["occurrence_observation"], "Ocorrencia legado")
