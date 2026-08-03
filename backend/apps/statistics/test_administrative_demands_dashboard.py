from datetime import date

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.schedules.models import Agenda, Sector, Team
from apps.statistics.dashboard import dashboard_payload
from apps.statistics.views import StatisticsDashboardFiltersView


class AdministrativeDemandsDashboardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(email="admin-demand-stats@example.com", password="test")
        self.sector, _ = Sector.objects.get_or_create(name="Estatisticas")
        self.team, _ = Team.objects.get_or_create(name="GOLF")

    def create_agenda(self, *, agenda_date=date(2026, 7, 20), city="Rio de Janeiro", team_name="GOLF", institution="Sede Administrativa", requester_entity_type="Demanda Administrativa", administrative_demand_type="TRAVEL", status=Agenda.Status.PENDING, action_type="Palestra"):
        return Agenda.objects.create(
            title=f"Demanda {administrative_demand_type or 'sem subtipo'}",
            description="Demanda administrativa",
            date=agenda_date,
            start_time="09:00",
            end_time="10:00",
            location=institution,
            created_by=self.user,
            responsible=self.user,
            sector=self.sector,
            origin=Agenda.Origin.INTERNAL,
            requester_entity_type=requester_entity_type,
            administrative_demand_type=administrative_demand_type,
            city=city,
            team_name=team_name,
            team_ref=self.team if team_name == "GOLF" else None,
            institution_location=institution,
            action_type=action_type,
            status=status,
        )

    def test_dashboard_payload_counts_travel_interview_meeting_and_preserves_other_fields(self):
        self.create_agenda(administrative_demand_type="TRAVEL")
        self.create_agenda(administrative_demand_type="TRAVEL")
        self.create_agenda(administrative_demand_type="INTERVIEW")
        self.create_agenda(administrative_demand_type="MEETING")

        payload = dashboard_payload(date(2026, 7, 1), date(2026, 7, 31), {})

        self.assertIn("summary", payload)
        self.assertIn("categories", payload)
        self.assertIn("administrative_demands", payload)
        self.assertEqual(payload["administrative_demands"]["total"], 4)
        items = {item["code"]: item for item in payload["administrative_demands"]["items"]}
        self.assertEqual(items["TRAVEL"]["value"], 2)
        self.assertEqual(items["INTERVIEW"]["value"], 1)
        self.assertEqual(items["MEETING"]["value"], 1)
        self.assertEqual(items["TRAVEL"]["percentage"], 50.0)
        self.assertEqual(items["INTERVIEW"]["percentage"], 25.0)
        self.assertEqual(items["MEETING"]["percentage"], 25.0)

    def test_dashboard_payload_excludes_cancelled_and_rejected(self):
        self.create_agenda(administrative_demand_type="TRAVEL", status=Agenda.Status.CANCELLED)
        self.create_agenda(administrative_demand_type="INTERVIEW", status="REJECTED")
        self.create_agenda(administrative_demand_type="MEETING", status=Agenda.Status.APPROVED)

        payload = dashboard_payload(date(2026, 7, 1), date(2026, 7, 31), {})

        self.assertEqual(payload["administrative_demands"]["total"], 1)
        items = {item["code"]: item for item in payload["administrative_demands"]["items"]}
        self.assertEqual(items["TRAVEL"]["value"], 0)
        self.assertEqual(items["INTERVIEW"]["value"], 0)
        self.assertEqual(items["MEETING"]["value"], 1)

    def test_dashboard_payload_respects_period_municipality_team_and_institution_filters(self):
        self.create_agenda(agenda_date=date(2026, 7, 10), city="Rio de Janeiro", team_name="GOLF", institution="Sede Centro", administrative_demand_type="TRAVEL")
        self.create_agenda(agenda_date=date(2026, 7, 22), city="Niteroi", team_name="ALFA", institution="Sede Niteroi", administrative_demand_type="INTERVIEW")

        by_period = dashboard_payload(date(2026, 7, 1), date(2026, 7, 15), {})
        by_city = dashboard_payload(date(2026, 7, 1), date(2026, 7, 31), {"municipality": "Niteroi", "team": "", "institution": "", "entity": "", "action_type": ""})
        by_team = dashboard_payload(date(2026, 7, 1), date(2026, 7, 31), {"municipality": "", "team": "GOLF", "institution": "", "entity": "", "action_type": ""})
        by_institution = dashboard_payload(date(2026, 7, 1), date(2026, 7, 31), {"municipality": "", "team": "", "institution": "Niteroi", "entity": "", "action_type": ""})

        self.assertEqual(by_period["administrative_demands"]["total"], 1)
        self.assertEqual({item["code"]: item["value"] for item in by_city["administrative_demands"]["items"]}["INTERVIEW"], 1)
        self.assertEqual({item["code"]: item["value"] for item in by_team["administrative_demands"]["items"]}["TRAVEL"], 1)
        self.assertEqual({item["code"]: item["value"] for item in by_institution["administrative_demands"]["items"]}["INTERVIEW"], 1)

    def test_dashboard_payload_respects_entity_filter_and_returns_zero_for_other_categories(self):
        self.create_agenda(administrative_demand_type="TRAVEL")
        self.create_agenda(administrative_demand_type="INTERVIEW")

        selected = dashboard_payload(date(2026, 7, 1), date(2026, 7, 31), {"municipality": "", "team": "", "institution": "", "entity": "Demanda Administrativa", "action_type": ""})
        other = dashboard_payload(date(2026, 7, 1), date(2026, 7, 31), {"municipality": "", "team": "", "institution": "", "entity": "A??o de Rua", "action_type": ""})

        self.assertEqual(selected["administrative_demands"]["total"], 2)
        self.assertEqual(other["administrative_demands"]["total"], 0)
        self.assertTrue(all(item["value"] == 0 for item in other["administrative_demands"]["items"]))

    def test_dashboard_payload_respects_action_type_and_does_not_depend_on_reports_or_statistics_processed(self):
        self.create_agenda(administrative_demand_type="TRAVEL", action_type="Reuni?o")
        self.create_agenda(administrative_demand_type="MEETING", action_type="Palestra")

        filtered = dashboard_payload(date(2026, 7, 1), date(2026, 7, 31), {"municipality": "", "team": "", "institution": "", "entity": "", "action_type": "Reuni?o"})

        self.assertEqual(filtered["administrative_demands"]["total"], 1)
        self.assertEqual({item["code"]: item["value"] for item in filtered["administrative_demands"]["items"]}["TRAVEL"], 1)

    def test_dashboard_payload_is_not_limited_to_500_agendas(self):
        agendas = [
            Agenda(
                title=f"Demanda {index}",
                description="Demanda administrativa",
                date=date(2026, 7, 20),
                start_time="09:00",
                end_time="10:00",
                location="Sede",
                created_by=self.user,
                responsible=self.user,
                sector=self.sector,
                origin=Agenda.Origin.INTERNAL,
                requester_entity_type="Demanda Administrativa",
                administrative_demand_type="TRAVEL",
                city="Rio de Janeiro",
                team_name="GOLF",
                institution_location="Sede",
                action_type="Palestra",
                status=Agenda.Status.PENDING,
            )
            for index in range(501)
        ]
        Agenda.objects.bulk_create(agendas)

        payload = dashboard_payload(date(2026, 7, 1), date(2026, 7, 31), {})

        self.assertEqual(payload["administrative_demands"]["total"], 501)
        self.assertEqual({item["code"]: item["value"] for item in payload["administrative_demands"]["items"]}["TRAVEL"], 501)

    def test_dashboard_filters_view_includes_demanda_administrativa_category(self):
        request = APIRequestFactory().get('/statistics/dashboard/filters/')
        force_authenticate(request, user=self.user)

        response = StatisticsDashboardFiltersView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Demanda Administrativa", response.data["entities"])
