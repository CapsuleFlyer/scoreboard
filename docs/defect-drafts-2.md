# Defect drafts DR-14 to DR-21 (whole-app tests)

Found by reading the source while writing the whole-app tests. Each one is held in a **strict xfail** test, so it is CONFIRMED only when that test is reported as `xfailed` on your machine. If a test reports `XPASS(strict)` / FAILED, my reading was wrong: do not file that defect. Severity and priority are proposals; score them yourself.

| ID | Title | Test that holds it | Proposed |
|---|---|---|---|
| DR-14 | iPad/remote/match input pages crash: `input.py` never imports `db` (NameError) | `test_auth_input_display.py::test_input_pages_for_an_existing_record_render` (4 params) | major, P2, cat:error-handling. Pairing a TV that has a tournament redirects to one of these pages |
| DR-15 | Custom TV/display message crashes: `api.py` uses `sanitize_message` without importing it | `test_api_match_display.py::test_set_display_mode_with_a_custom_message`, `::test_control_tv_with_a_custom_message` | major, P2, cat:validation |
| DR-16 | Any API token with an expiry date crashes the request: naive vs aware datetime in `APIToken.validate_token` | `test_team_external_api.py::test_token_expiry_is_honoured` (2 params) | major, P2, cat:date-time (same root cause as DR-03) |
| DR-17 | State-changing endpoints with no login: `/api/tournament/<id>/timer`, `/api/display/mode` | `test_api_match_display.py::test_timer_update_requires_login`, `::test_display_mode_requires_login` | major, P2, cat:access-control |
| DR-18 | API token scoped to one tournament can read any tournament (`tournament_id` never checked) | `test_team_external_api.py::test_token_scoped_to_one_tournament_cannot_read_another` | minor, P3, cat:access-control |
| DR-19 | Non-numeric score in the external API gives 500 instead of 400 (`int()` ValueError) | `test_team_external_api.py::test_update_score_with_a_non_numeric_value_is_a_client_error` | minor, P3, cat:error-handling |

| DR-20 | The winner team chosen on the display is not stored (`winner_team_id` is not a DisplayState column), so it is lost when the state is reloaded | `test_coverage_gaps.py::test_display_mode_winner_team_is_persisted` | minor, P3, cat:state-rules |

| DR-21 | The registration success message is queued and shown on the NEXT page visit (the success page does not display it) | `test_uc1_public_registration.py::test_uc1_success_message_does_not_reappear_on_the_next_visit` | minor, P3, cat:state-rules. Seen in the 2026-11-27 browser run: after registering, reopening the tournament page showed "Team ... registered! Awaiting admin confirmation." |

Other observations (not filed, decide yourself): `create_api_token` reads `request.get_json() or request.form`, but Flask answers 415 to a form post before the fallback is reached; `/api/test/generate-brackets` is a test helper shipped in the production blueprint (login required, cleans up after itself, but creates 4 x 5 tournaments with up to 64 teams per call).

## Issue bodies
Use `scripts/new_defect_issues.ps1 -Ids DR-14,DR-15` (only the ones your run confirmed). Evidence line in every body: "RUN on Windows, <date>: strict xfail test <name> reports xfailed" (the script asks you for the date).
