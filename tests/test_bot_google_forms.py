from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import Bot_GoogleForm_Intelligent as core


class BotGoogleFormsTests(unittest.TestCase):
    def test_normalize_form_urls(self) -> None:
        url_view, url_post = core.normalize_form_urls(
            "https://docs.google.com/forms/d/e/test/formResponse?usp=sharing"
        )
        self.assertEqual(url_view, "https://docs.google.com/forms/d/e/test/viewform")
        self.assertEqual(url_post, "https://docs.google.com/forms/d/e/test/formResponse")

    def test_extract_hidden_fields(self) -> None:
        html = (
            '<input type="hidden" name="fbzx" value="abc">'
            '<input type="hidden" name="pageHistory" value="0">'
        )
        self.assertEqual(core.extract_hidden_fields(html), {"fbzx": "abc", "pageHistory": "0"})

    def test_build_question_for_grid_multi(self) -> None:
        sample = [
            None,
            "Grille multiple",
            None,
            8,
            [
                [101, [["A"], ["B"]], 1, ["Ligne 1"], [], None, [], []],
                [102, [["A"], ["B"]], 1, ["Ligne 2"], [], None, [], []],
            ],
        ]
        question = core.build_question(sample)
        self.assertIsNotNone(question)
        self.assertEqual(question["type"], 8)
        self.assertTrue(question["supported"])
        self.assertEqual(len(question["grid_rows"]), 2)

    def test_parse_inputs(self) -> None:
        self.assertEqual(core.parse_positive_integer("5"), 5)
        self.assertEqual(core.parse_non_negative_integer("0"), 0)
        self.assertEqual(core.parse_profile("equilibree"), "equilibre")
        self.assertEqual(core.parse_time_input("09:45")["display"], "09:45")
        self.assertEqual(core.parse_date_input("30/04/2026", True)["display"], "30/04/2026")
        with self.assertRaises(ValueError):
            core.parse_delay_value("-1")

    def test_random_email_answer_looks_like_email(self) -> None:
        random_answer = core.random_text_answer(
            {
                "type": 0,
                "text": "Votre email",
                "required": True,
                "options": [],
            },
            profile="equilibre",
        )
        self.assertIn("@", random_answer)

    def test_build_payload_supports_grid_multi(self) -> None:
        form_data = {
            "hidden_fields": {"fbzx": "abc"},
            "questions": [
                {
                    "field_name": "entry.1",
                    "type": 8,
                    "text": "Grille",
                    "type_label": "Grille a cases",
                    "required": True,
                    "options": ["Oui", "Non"],
                    "row_labels": ["L1", "L2"],
                    "supported": True,
                    "includes_year": False,
                    "is_duration": False,
                    "grid_rows": [
                        {"entry_id": "1", "field_name": "entry.1", "label": "L1"},
                        {"entry_id": "2", "field_name": "entry.2", "label": "L2"},
                    ],
                }
            ],
        }
        answers = {
            "entry.1": core.build_grid_multi_answer(
                [
                    {"field_name": "entry.1", "label": "L1", "values": ["Oui"]},
                    {"field_name": "entry.2", "label": "L2", "values": ["Oui", "Non"]},
                ]
            )
        }
        payload = core.build_payload(form_data, answers)
        self.assertIn(("fbzx", "abc"), payload)
        self.assertIn(("entry.1", "Oui"), payload)
        self.assertIn(("entry.2", "Non"), payload)

    def test_simulate_submission_builds_report_data(self) -> None:
        form_data = {
            "title": "Formulaire test",
            "url_view": "https://example.com/viewform",
            "url_post": "https://example.com/formResponse",
            "hidden_fields": {"fbzx": "abc"},
            "questions": [
                {
                    "field_name": "entry.1",
                    "type": 0,
                    "text": "Nom",
                    "type_label": "Reponse courte",
                    "required": True,
                    "options": [],
                    "row_labels": [],
                    "supported": True,
                    "includes_year": False,
                    "is_duration": False,
                    "grid_rows": [],
                }
            ],
        }
        simulation = core.simulate_submission(form_data, {"entry.1": "Mathias"}, label="test")
        self.assertEqual(simulation["filled_count"], 1)
        self.assertEqual(simulation["payload_count"], 2)
        self.assertIn("Nom", simulation["summary_text"])

    def test_run_random_submissions_can_stop_cleanly(self) -> None:
        form_data = {
            "title": "Formulaire test",
            "url_view": "https://example.com/viewform",
            "url_post": "https://example.com/formResponse",
            "hidden_fields": {},
            "questions": [
                {
                    "field_name": "entry.1",
                    "type": 0,
                    "text": "Nom",
                    "type_label": "Reponse courte",
                    "required": True,
                    "options": [],
                    "row_labels": [],
                    "supported": True,
                    "includes_year": False,
                    "is_duration": False,
                    "grid_rows": [],
                }
            ],
        }

        calls = {"count": 0}
        progress_updates: list[dict[str, object]] = []

        def stop_requested() -> bool:
            calls["count"] += 1
            return calls["count"] >= 2

        summary = core.run_random_submissions(
            form_data,
            5,
            profile="equilibre",
            min_delay=0,
            max_delay=0,
            simulate_only=True,
            on_progress=progress_updates.append,
            stop_requested=stop_requested,
        )
        self.assertTrue(summary["stopped"])
        self.assertLess(summary["sent_count"], 5)
        self.assertEqual(summary["processed_count"], summary["success_count"] + summary["error_count"])
        self.assertEqual(summary["pending_count"], summary["requested_count"] - summary["processed_count"])
        self.assertEqual(len(progress_updates), 1)
        self.assertEqual(progress_updates[0]["processed_count"], 1)
        self.assertEqual(progress_updates[0]["pending_count"], 4)

    def test_run_random_submissions_retries_before_success(self) -> None:
        form_data = {
            "title": "Formulaire test",
            "url_view": "https://example.com/viewform",
            "url_post": "https://example.com/formResponse",
            "hidden_fields": {},
            "questions": [
                {
                    "field_name": "entry.1",
                    "type": 0,
                    "text": "Nom",
                    "type_label": "Reponse courte",
                    "required": True,
                    "options": [],
                    "row_labels": [],
                    "supported": True,
                    "includes_year": False,
                    "is_duration": False,
                    "grid_rows": [],
                }
            ],
        }

        progress_updates: list[dict[str, object]] = []
        attempts = {"count": 0}

        def flaky_submit(_form_data, _answers) -> None:
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("Erreur temporaire")

        with patch.object(core, "submit_form", side_effect=flaky_submit):
            summary = core.run_random_submissions(
                form_data,
                1,
                profile="equilibre",
                min_delay=0,
                max_delay=0,
                simulate_only=False,
                max_retries=1,
                on_progress=progress_updates.append,
            )

        self.assertEqual(summary["success_count"], 1)
        self.assertEqual(summary["error_count"], 0)
        self.assertEqual(summary["retry_count_total"], 1)
        self.assertEqual(attempts["count"], 2)
        self.assertEqual(progress_updates[0]["retry_count_total"], 1)
        self.assertEqual(progress_updates[0]["pending_count"], 0)

    def test_parse_form_with_mocked_response(self) -> None:
        sample_payload = [
            None,
            [
                None,
                [
                    [None, "Nom", None, 0, [[123, None, 1, [], [], None, [], []]]],
                    [None, "Grille", None, 7, [[124, [["Oui"], ["Non"]], 1, ["Ligne 1"], [], None, [], []]]],
                ],
                None,
                None,
                None,
                None,
                None,
                None,
                "Mon formulaire",
            ],
        ]
        html = (
            '<html><body><input type="hidden" name="fbzx" value="abc"><script>'
            f"var FB_PUBLIC_LOAD_DATA_ = {json.dumps(sample_payload)};"
            "</script></body></html>"
        )

        class DummyResponse:
            status_code = 200

            def __init__(self, text: str):
                self.text = text

            def raise_for_status(self) -> None:
                return None

        with patch.object(core.requests, "get", return_value=DummyResponse(html)):
            parsed = core.parse_form("https://docs.google.com/forms/d/e/test/viewform")
        self.assertEqual(parsed["title"], "Mon formulaire")
        self.assertEqual(len(parsed["questions"]), 2)


if __name__ == "__main__":
    unittest.main()
