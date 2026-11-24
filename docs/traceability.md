# Traceability matrix (DRAFT: requirement to automated tests)

Status: test names are from the files in `tests/team/`. A cell only counts as covered after you have run the test and it passed (or xfailed for the listed defect). Defect issue numbers: take them from `docs/defect-issue-map.md` (not copied here to avoid errors).

| Requirement | Rule | Tests (file :: name or group) | Defects |
|---|---|---|---|
| FR1 code lookup | | `test_register_routes.py` join/tournament-page tests; `test_api_register.py::test_validate_*`; `test_api_generated.py` validateCode cases | |
| FR2 create team, confirm unless required | 3 | `test_register_routes.py` registration tests; `test_api_register.py::test_register_success_*`, `test_register_waits_for_admin_*` | |
| FR3 refuse when closed/started/deadline/full | 2 | `test_can_register.py` (decision table, order); `test_api_register.py::test_register_refused_when_rule_2_fails`, `test_rule_2_is_checked_before_field_validation` | DR-03 (deadline), DR-11 |
| FR4 duplicate name | | `test_register_routes.py`; `test_api_register.py::test_register_duplicate_*`; `test_admin_registration.py::test_manual_add_refuses_duplicate_*` | DR-04 |
| FR5 conditional fields | 4 | `test_register_routes.py` conditional tests; `test_api_register.py::test_register_requires_email_*`; `test_api_generated.py` | DR-06 |
| FR6 anonymous blocked | roles | `test_admin_registration.py::test_anonymous_is_redirected_*` (6 routes); `test_sanitizers_auth_models.py::test_login_required_*` | DR-12 (CSRF, to check with tokens) |
| FR7 confirm | 3 | `test_admin_registration.py::test_confirm_*` | DR-02, DR-09 |
| FR8 reject | 3 | `test_admin_registration.py::test_reject_*` | DR-02, DR-09 |
| FR9 check-in toggle | 3 | `test_admin_registration.py::test_checkin_*` | DR-09 |
| FR10 manual add, full, duplicate | 1 | `test_admin_registration.py::test_manual_add_*` | DR-05, DR-07 |
| FR11 team must belong to tournament | | `test_admin_registration.py::*_from_another_tournament_is_refused` | |
| FR12 toggle registration | 2 | `test_admin_registration.py::test_toggle_*` | |
| Rule 1 boundary (name 1-20, count vs max) | 1 | generated BVA in `test_api_generated.py`; `test_register_routes.py`; `test_manual_add_boundary_*`; sanitizer boundary tests | DR-05 |
| Shared record (count vs max_teams) | | `test_api_register.py::test_shared_count_*`, `test_pending_teams_use_capacity`; `test_admin_registration.py::test_reject_deletes_*`, `test_manual_add_refuses_when_full_*` | DR-08 |
| Mutation analysis | all | `scripts/mutate_rules.py` report (to be produced) | |
