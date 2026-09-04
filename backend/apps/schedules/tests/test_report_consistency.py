from django.test import SimpleTestCase

from apps.schedules.report_consistency import education_action_consistency_errors


class EducationReportConsistencyTests(SimpleTestCase):
    def action(self, start, end, public, kits):
        return {
            "action_mode": "LECTURE",
            "type_action": "Palestra",
            "start_time": start,
            "final_hour": end,
            "approached_lectures": public,
            "distribution_materials_distributed": f"KIT COM 7 REVISTINHAS | {kits}",
        }

    def test_rejects_distributed_quantity_above_action_audience(self):
        errors = education_action_consistency_errors([
            self.action("09:00", "10:00", 50, 51),
        ])
        self.assertIn("não pode ser maior", str(errors))

    def test_rejects_overlapping_action_times(self):
        errors = education_action_consistency_errors([
            self.action("09:00", "11:00", 50, 20),
            self.action("10:30", "12:00", 30, 10),
        ])
        self.assertIn("horários sobrepostos", str(errors))

    def test_accepts_adjacent_times_and_material_not_above_audience(self):
        errors = education_action_consistency_errors([
            self.action("09:00", "11:00", 50, 50),
            self.action("11:00", "12:00", 30, 10),
        ])
        self.assertEqual(errors, {})

    def test_accepts_activity_that_crosses_midnight(self):
        errors = education_action_consistency_errors([
            self.action("21:00", "01:00", 50, 20),
        ])
        self.assertEqual(errors, {})
