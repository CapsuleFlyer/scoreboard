PS C:\Users\User\Documents\GitHub\scoreboard> python -m pytest tests/team/test_admin_registration.py::test_manual_add_keeps_a_20_character_team_name -v
============================================================================ test session starts ============================================================================
platform win32 -- Python 3.12.10, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\User\Documents\GitHub\scoreboard
plugins: platformdirs-4.14.8, cov-7.1.0, flask-1.3.0
collected 1 item                                                                                                                                                             

tests/team/test_admin_registration.py::test_manual_add_keeps_a_20_character_team_name FAILED                                                                           [100%]

================================================================================= FAILURES ==================================================================================
______________________________________________________________ test_manual_add_keeps_a_20_character_team_name _______________________________________________________________

app = <Flask 'app'>, authenticated_client = <FlaskClient <Flask 'app'>>

    def test_manual_add_keeps_a_20_character_team_name(app, authenticated_client):
        t = make_tournament()
        add(authenticated_client, t.id, name="A" * 20, player1="P" * 30)
        team = Team.query.filter_by(tournament_id=t.id).one()
>       assert len(team.name) == 20 and len(team.player1) == 30
E       AssertionError: assert (8 == 20)
E        +  where 8 = len('AAAAAAAA')
E        +    where 'AAAAAAAA' = <Team 1>.name

tests\team\test_admin_registration.py:242: AssertionError
========================================================================== short test summary info ==========================================================================
FAILED tests/team/test_admin_registration.py::test_manual_add_keeps_a_20_character_team_name - AssertionError: assert (8 == 20)
============================================================================= 1 failed in 0.79s =============================================================================









PS C:\Users\User\Documents\GitHub\scoreboard> python -m pytest tests/team/test_admin_registration.py::test_manual_add_keeps_a_20_character_team_name -v
============================================================================ test session starts ============================================================================
platform win32 -- Python 3.12.10, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\User\Documents\GitHub\scoreboard
plugins: platformdirs-4.14.8, cov-7.1.0, flask-1.3.0
collected 1 item                                                                                                                                                             

tests/team/test_admin_registration.py::test_manual_add_keeps_a_20_character_team_name PASSED                                                                           [100%]

============================================================================= 1 passed in 0.59s =============================================================================








PS C:\Users\User\Documents\GitHub\scoreboard> python -m pytest tests/team/test_admin_registration.py -v
============================================================================ test session starts ============================================================================
platform win32 -- Python 3.12.10, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\User\Documents\GitHub\scoreboard
plugins: platformdirs-4.14.8, cov-7.1.0, flask-1.3.0
collected 33 items                                                                                                                                                           

tests/team/test_admin_registration.py::test_anonymous_is_redirected_to_login_and_nothing_changes[get-/admin/tournament/{t}/registrations] PASSED                       [  3%]
tests/team/test_admin_registration.py::test_anonymous_is_redirected_to_login_and_nothing_changes[post-/admin/tournament/{t}/team/{m}/confirm] PASSED                   [  6%]
tests/team/test_admin_registration.py::test_anonymous_is_redirected_to_login_and_nothing_changes[post-/admin/tournament/{t}/team/{m}/reject] PASSED                    [  9%]
tests/team/test_admin_registration.py::test_anonymous_is_redirected_to_login_and_nothing_changes[post-/admin/tournament/{t}/team/{m}/checkin] PASSED                   [ 12%]
tests/team/test_admin_registration.py::test_anonymous_is_redirected_to_login_and_nothing_changes[post-/admin/tournament/{t}/team/add] PASSED                           [ 15%]
tests/team/test_admin_registration.py::test_anonymous_is_redirected_to_login_and_nothing_changes[post-/admin/tournament/{t}/registration/toggle] PASSED                [ 18%]
tests/team/test_admin_registration.py::test_registrations_page_lists_pending_and_confirmed_teams PASSED                                                                [ 21%]
tests/team/test_admin_registration.py::test_registrations_page_for_missing_tournament_is_404 XFAIL (DR-02: the 404 page calls url_for('ui.index'), so a missing to...) [ 24%]
tests/team/test_admin_registration.py::test_confirm_pending_team PASSED                                                                                                [ 27%]
tests/team/test_admin_registration.py::test_confirm_is_idempotent_on_a_confirmed_team PASSED                                                                           [ 30%]
tests/team/test_admin_registration.py::test_confirm_team_from_another_tournament_is_refused PASSED                                                                     [ 33%]
tests/team/test_admin_registration.py::test_confirm_missing_team_is_404 XFAIL (DR-02: get_or_404 renders the broken 404 page)                                          [ 36%]
tests/team/test_admin_registration.py::test_reject_deletes_team_and_frees_the_slot PASSED                                                                              [ 39%]
tests/team/test_admin_registration.py::test_reject_works_on_a_confirmed_team_too PASSED                                                                                [ 42%]
tests/team/test_admin_registration.py::test_reject_team_from_another_tournament_is_refused PASSED                                                                      [ 45%]
tests/team/test_admin_registration.py::test_reject_twice_second_call_cannot_find_the_team PASSED                                                                       [ 48%]
tests/team/test_admin_registration.py::test_checkin_toggles_on_then_off PASSED                                                                                         [ 51%]
tests/team/test_admin_registration.py::test_checkin_does_not_change_confirmation PASSED                                                                                [ 54%]
tests/team/test_admin_registration.py::test_checkin_team_from_another_tournament_is_refused PASSED                                                                     [ 57%]
tests/team/test_admin_registration.py::test_manual_add_creates_a_confirmed_team PASSED                                                                                 [ 60%]
tests/team/test_admin_registration.py::test_manual_add_requires_all_three_fields[name] PASSED                                                                          [ 63%]
tests/team/test_admin_registration.py::test_manual_add_requires_all_three_fields[player1] PASSED                                                                       [ 66%]
tests/team/test_admin_registration.py::test_manual_add_requires_all_three_fields[player2] PASSED                                                                       [ 69%]
tests/team/test_admin_registration.py::test_manual_add_refuses_duplicate_name_ignoring_case PASSED                                                                     [ 72%]
tests/team/test_admin_registration.py::test_manual_add_allows_same_name_in_another_tournament PASSED                                                                   [ 75%]
tests/team/test_admin_registration.py::test_manual_add_refuses_when_full_then_succeeds_after_a_slot_is_freed PASSED                                                    [ 78%]
tests/team/test_admin_registration.py::test_manual_add_boundary_count_one_below_max_is_accepted PASSED                                                                 [ 81%]
tests/team/test_admin_registration.py::test_manual_add_strips_unsafe_characters PASSED                                                                                 [ 84%]
tests/team/test_admin_registration.py::test_manual_add_keeps_a_20_character_team_name PASSED                                                                           [ 87%]
tests/team/test_admin_registration.py::test_manual_add_keeps_names_within_new_limits PASSED                                                                            [ 90%]
tests/team/test_admin_registration.py::test_manual_add_is_refused_when_registration_is_closed XFAIL (DR-07: manual add does not call can_register(), so it works w...) [ 93%]
tests/team/test_admin_registration.py::test_manual_add_is_refused_after_the_tournament_started XFAIL (DR-07: manual add ignores tournament status)                     [ 96%]
tests/team/test_admin_registration.py::test_toggle_closes_then_reopens_and_public_rule_follows PASSED                                                                  [100%]

======================================================================= 29 passed, 4 xfailed in 7.99s =======================================================================
