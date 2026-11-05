import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "update_schedule.py"
SPEC = importlib.util.spec_from_file_location("update_schedule", SCRIPT)
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)


def row(section="Sports - Drop-In", date="2026-09-08", course_id=None):
    return {
        "Location ID": 3643,
        "Course Title": "Pickleball",
        "Age Min": "19",
        "Age Max": "None",
        "First Date": date,
        "Start Hour": 18,
        "Start Minute": 0,
        "End Hour": 20,
        "End Min": 0,
        "DayOftheWeek": "Tuesday",
        "Section": section,
        "Course_ID": course_id,
    }


def session(identifier, centre, date):
    return {
        "id": identifier,
        "centre": centre,
        "date": date,
        "name": "Pickleball",
        "time": "06:00 PM - 08:00 PM",
        "access": "dropin",
    }


class UpdateScheduleTests(unittest.TestCase):
    def test_combines_matching_dropin_and_reserve_rows(self):
        rows = [row(), row("Reserve a Spot - Sports", course_id=200695)]
        for location_id in updater.CENTRES:
            rows.append({"Location ID": location_id})
        old_minimum = updater.MIN_SESSION_COUNT
        updater.MIN_SESSION_COUNT = 1
        try:
            sessions = updater.build_sessions(rows)
        finally:
            updater.MIN_SESSION_COUNT = old_minimum
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["access"], "both")
        self.assertEqual(sessions[0]["reserveId"], 200695)
        self.assertEqual(sessions[0]["id"], "city-canoe-2026-09-08-1800-pickleball")

    def test_reserve_session_requires_course_id(self):
        rows = [row("Reserve a Spot - Sports")]
        for location_id in updater.CENTRES:
            rows.append({"Location ID": location_id})
        with self.assertRaisesRegex(ValueError, "invalid Course_ID"):
            updater.build_sessions(rows)

    def test_only_exact_19_plus_age_group_is_tracked(self):
        adult = row()
        senior = {**row(), "Age Min": "60"}
        family = {**row(), "Age Min": "5", "Course Title": "Badminton with Family"}
        self.assertTrue(updater.is_tracked(adult))
        self.assertFalse(updater.is_tracked(senior))
        self.assertFalse(updater.is_tracked(family))

    def test_merge_preserves_only_history_before_new_source_window(self):
        existing = [
            {"id": "old", "date": "2026-09-07", "time": "01:00 PM", "centre": "canoe", "name": "Pickleball"},
            {"id": "replace", "date": "2026-09-08", "time": "01:00 PM", "centre": "canoe", "name": "Pickleball"},
        ]
        fresh = [
            {"id": "new", "date": "2026-09-08", "time": "02:00 PM", "centre": "canoe", "name": "Pickleball"}
        ]
        merged = updater.merge_sessions(existing, fresh)
        self.assertEqual([session["id"] for session in merged], ["old", "new"])

    def test_fresh_schedule_requires_every_centre(self):
        fresh = [session(str(index), centre, "2026-09-08") for index, centre in enumerate(updater.CENTRES.values())]
        fresh.append(session("later", "canoe", "2026-09-22"))
        updater.validate_fresh_sessions(fresh, [])

        with self.assertRaisesRegex(ValueError, "eastbayfront"):
            updater.validate_fresh_sessions(
                [item for item in fresh if item["centre"] != "eastbayfront"], []
            )

    def test_fresh_schedule_requires_two_week_window(self):
        fresh = [session(str(index), centre, "2026-09-08") for index, centre in enumerate(updater.CENTRES.values())]
        with self.assertRaisesRegex(ValueError, "covers only 0 days"):
            updater.validate_fresh_sessions(fresh, [])

    def test_fresh_schedule_rejects_large_count_drop(self):
        fresh = [session(str(index), centre, "2026-09-08") for index, centre in enumerate(updater.CENTRES.values())]
        fresh.append(session("later", "canoe", "2026-09-22"))
        existing = [
            session(f"existing-{index}", "canoe", "2026-09-08") for index in range(13)
        ]
        with self.assertRaisesRegex(ValueError, "fell from 13 to 6"):
            updater.validate_fresh_sessions(fresh, existing)


if __name__ == "__main__":
    unittest.main()
