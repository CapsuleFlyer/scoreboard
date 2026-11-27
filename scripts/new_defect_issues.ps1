<#
Creates GitHub issues for DR-14..DR-21. Run only for defects whose strict xfail test your run
reported as xfailed (see docs/defect-drafts-2.md). Needs `gh` logged in.
  powershell -File scripts/new_defect_issues.ps1 -Ids DR-14,DR-15 -Repo CapsuleFlyer/scoreboard
#>
param(
  [Parameter(Mandatory = $true)][string[]]$Ids,
  [string]$Repo = "CapsuleFlyer/scoreboard",
  [string]$RunDate = (Get-Date -Format "yyyy-MM-dd")
)

$defects = @{
  "DR-14" = @{ title = "Input pages (iPad, remote, tournament, match) crash with NameError"; sev = "major"; pri = "P2"; cat = "error-handling"
    body = "Summary: app/blueprints/input.py calls db.get_or_404 but never imports db, so /input/tournament/<id>, /remote, /ipad and /input/match/<id> raise NameError (500). Pairing a TV that has a tournament redirects to the iPad page.`nSteps: log in, create a tournament, open /input/tournament/<id>/ipad.`nExpected: the page renders. Actual: HTTP 500.`nEvidence: test_auth_input_display.py::test_input_pages_for_an_existing_record_render (strict xfail)." }
  "DR-15" = @{ title = "Custom display or TV message crashes: sanitize_message not imported in api.py"; sev = "major"; pri = "P2"; cat = "validation"
    body = "Summary: api.py calls sanitize_message in set_display_mode and control_tv but only imports sanitize_text, so any request with custom_message raises NameError (500).`nSteps: POST /api/display/mode with {`"custom_message`":`"Hello`"}.`nExpected: 200 and the message stored escaped. Actual: 500.`nEvidence: test_api_match_display.py::test_set_display_mode_with_a_custom_message and ::test_control_tv_with_a_custom_message (strict xfail)." }
  "DR-16" = @{ title = "API tokens with an expiry date crash every request (naive vs aware datetime)"; sev = "major"; pri = "P2"; cat = "date-time"
    body = "Summary: APIToken.validate_token compares token.expires_at (naive when read from SQLite) with datetime.now(timezone.utc) (aware), raising TypeError. Same root cause as DR-03.`nSteps: create a token with expires_days, call any /ext/v1 endpoint with it.`nExpected: 200 before expiry, 401 after. Actual: 500.`nEvidence: test_external_api.py::test_token_expiry_is_honoured (strict xfail, 2 cases)." }
  "DR-17" = @{ title = "Timer and display-mode endpoints change state without login"; sev = "major"; pri = "P2"; cat = "access-control"
    body = "Summary: POST /api/tournament/<id>/timer and POST /api/display/mode have no login or token check, so any visitor can change the timer and what the TV shows.`nSteps: POST without a session.`nExpected: 401 or redirect to login. Actual: 200 and state changed.`nEvidence: test_api_match_display.py::test_timer_update_requires_login and ::test_display_mode_requires_login (strict xfail)." }
  "DR-18" = @{ title = "Tournament-scoped API token can read other tournaments"; sev = "minor"; pri = "P3"; cat = "access-control"
    body = "Summary: tokens can be created for one tournament (tournament_id) but require_token never compares it with the tournament in the URL.`nSteps: create a token for tournament A, GET /ext/v1/tournament/<B id>.`nExpected: 403. Actual: 200.`nEvidence: test_external_api.py::test_token_scoped_to_one_tournament_cannot_read_another (strict xfail)." }
  "DR-19" = @{ title = "External API answers 500 for a non-numeric score"; sev = "minor"; pri = "P3"; cat = "error-handling"
    body = "Summary: update_match_score calls int() on the submitted value without validation, so a non-numeric score raises ValueError (500).`nSteps: POST /ext/v1/match/<id>/score with {`"team1_score`":`"abc`"}.`nExpected: 400 with an error. Actual: 500.`nEvidence: test_external_api.py::test_update_score_with_a_non_numeric_value_is_a_client_error (strict xfail)." }
  "DR-20" = @{ title = "Winner team chosen on the display is not stored"; sev = "minor"; pri = "P3"; cat = "state-rules"
    body = "Summary: set_display_mode assigns state.winner_team_id, but DisplayState has no such column, so the value lives only on the Python object and is lost when the state is reloaded (new request, restart).`nSteps: POST /api/display/mode with {`"mode`":`"winner`",`"winner_team_id`":1}, then GET /api/display/state in a new session.`nExpected: winner_team in the response. Actual: missing.`nEvidence: test_coverage_gaps.py::test_display_mode_winner_team_is_persisted (strict xfail)." }
  "DR-21" = @{ title = "Registration success message appears on the next page visit"; sev = "minor"; pri = "P3"; cat = "state-rules"
    body = "Summary: register_team flashes a success message, but the success page does not display flashed messages, so the message stays queued and appears on the next page that shows them (for example when the visitor reopens the tournament page).`nSteps: register a team, then open /register/tournament/<code> again.`nExpected: no old success message. Actual: Team registered! Awaiting admin confirmation. is shown again.`nEvidence: test_uc1_public_registration.py::test_uc1_success_message_does_not_reappear_on_the_next_visit (strict xfail); seen in the browser run of 2026-11-27." }
}

foreach ($id in $Ids) {
  if (-not $defects.ContainsKey($id)) { Write-Host "Unknown id $id"; continue }
  $d = $defects[$id]
  $found = gh issue list --repo $Repo --state all --search "$($d.title) in:title" --json number --jq ".[].number"
  if ($found) { Write-Host "$id already exists as #$found, skipping"; continue }
  $f = New-TemporaryFile
  Set-Content -Path $f -Value ("Draft ID: $id`n`n" + $d.body + "`nRUN on Windows, ${RunDate}.`nSeverity: $($d.sev). Priority: $($d.pri). Triage: confirm owner and fix plan.") -Encoding utf8
  gh issue create --repo $Repo --title "[DEFECT] $($d.title)" --body-file $f `
    --label "type:defect" --label "status:confirmed" --label "severity:$($d.sev)" --label "priority:$($d.pri)" --label "cat:$($d.cat)"
  Remove-Item $f
}
