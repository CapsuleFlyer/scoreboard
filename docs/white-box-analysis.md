# **White-box testing –&#x20;**`Tournament.can_register()`

**Course:** SE3002 – Software Quality Engineering\
**Project:** Scoreboard\
**Source file:** `app/models.py`\
**Test file:** `tests/team/test_can_register.py`

## **1. Function under test**

The `can_register()` method determines whether a team can register for a tournament. It checks four conditions in sequence and returns immediately when one of them prevents registration.

```
def can_register(self):    """Check if registration is still possible"""    if not self.registration_open:        return False, "Registration is closed"    if self.status != 'registration':        return False, "Tournament has already started"    if self.registration_deadline and utc_now() > self.registration_deadline:        return False, "Registration deadline has passed"    if self.get_registered_team_count() >= self.max_teams:        return False, "Tournament is full"    return True, "OK"
```

The checks are performed in this order:

1. Registration must be open.
2. Tournament status must be `registration`.
3. The registration deadline must not have passed.
4. The number of registered teams must be below the maximum capacity.

If multiple conditions would reject registration, the first failing condition determines the returned message.

## **2. Control Flow Graph (CFG)**

The CFG represents the execution paths through the function. Each decision has two possible outcomes: True or False.

Entry

**D1: Registration closed?**

True

**Return: Closed**

False

**D2: Status incorrect?**

True

**Return: Started**

False

**D3: Deadline passed?**

True

**Return: Deadline passed**

False

**D4: Capacity reached?**

True

**Return: Full**

False

**Return: OK**

Exit

Conceptual flow: each rejection returns immediately; only the False path continues to the next decision.

### **CFG nodes**

| Node | Description                  |
| ---- | ---------------------------- |
| N1   | Entry                        |
| N2   | D1 – Registration-open check |
| N3   | Return registration closed   |
| N4   | D2 – Tournament-status check |
| N5   | Return tournament started    |
| N6   | D3 – Deadline check          |
| N7   | Return deadline passed       |
| N8   | D4 – Capacity check          |
| N9   | Return tournament full       |
| N10  | Return registration allowed  |
| N11  | Exit                         |

### **CFG edges**

| Edge | Connection       |
| ---- | ---------------- |
| E1   | N1 → N2          |
| E2   | N2 → N3 (True)   |
| E3   | N2 → N4 (False)  |
| E4   | N3 → N11         |
| E5   | N4 → N5 (True)   |
| E6   | N4 → N6 (False)  |
| E7   | N5 → N11         |
| E8   | N6 → N7 (True)   |
| E9   | N6 → N8 (False)  |
| E10  | N7 → N11         |
| E11  | N8 → N9 (True)   |
| E12  | N8 → N10 (False) |
| E13  | N9 → N11         |
| E14  | N10 → N11        |

## **3. Cyclomatic complexity – V(G)**

Cyclomatic complexity measures the number of linearly independent execution paths through a function.

Using the decision formula:

\\[ V(G)=D+1 \\]

There are four `if` decision statements.

\\[ V(G)=4+1=\boxed{5} \\]

We can verify this using the CFG formula:

\\[ V(G)=E-N+2P \\]

Where:

- E = 14 edges
- N = 11 nodes
- P = 1 connected component

\\[ V(G)=14-11+2(1)=\boxed{5} \\]

Therefore, the cyclomatic complexity is **5**, meaning five independent paths are required for a basis path set.

*Note:* This calculation treats the deadline expression as one compound `if` decision. If your instructor counts the short-circuit `and` as an additional decision point, the operator-aware complexity is 6. The CFG above abstracts the compound expression as one decision; an expanded CFG would split it into two decision nodes. We should confirm which convention your course expects before final submission.

### **Basis path testing**

| Path | Conditions                                         | Expected result      |
| ---- | -------------------------------------------------- | -------------------- |
| P1   | Registration is closed                             | Registration refused |
| P2   | Registration open, status is not `registration`    | Registration refused |
| P3   | Registration open, correct status, deadline passed | Registration refused |
| P4   | First three checks pass, capacity reached          | Registration refused |
| P5   | All checks pass                                    | Registration allowed |

Existing tests that exercise these paths include:

- `test_closed_registration_is_refused`
- `test_status_other_than_registration_is_refused`
- `test_deadline_in_the_past_is_refused`
- `test_full_tournament_is_refused`
- `test_all_conditions_pass`

## **4. Multiple Condition Coverage (MCC)**

MCC checks the combinations of atomic conditions within each decision.

### **D1 – Registration open**

Expression: `not self.registration_open`

| Test | Registration open | Decision |
| ---- | ----------------- | -------- |
| 1    | True              | False    |
| 2    | False             | True     |

Both outcomes are covered.

### **D2 – Tournament status**

Expression: `self.status != 'registration'`

| Test | Status is registration | Decision |
| ---- | ---------------------- | -------- |
| 1    | True                   | False    |
| 2    | False                  | True     |

The existing tests use `ready`, `in_progress`, `completed`, and `cancelled` as invalid statuses.

### **D3 – Registration deadline**

Expression:

```
self.registration_deadline and utc_now() > self.registration_deadline
```

Define:

- A = A deadline exists.
- B = Current time is later than the deadline.

| Test | A     | B             | A AND B    |
| ---- | ----- | ------------- | ---------- |
| 1    | False | Not evaluated | False      |
| 2    | True  | False         | False      |
| 3    | True  | True          | True       |
| 4    | False | True          | Infeasible |

The fourth combination is infeasible because Python uses short-circuit evaluation. When A is false, B is never evaluated.

Existing tests:

- `test_all_conditions_pass`
- `test_deadline_in_the_future_is_allowed`
- `test_deadline_in_the_past_is_refused`

### **D4 – Tournament capacity**

Expression:

```
self.get_registered_team_count() >= self.max_teams
```

| Test | Registered count >= maximum | Decision |
| ---- | --------------------------- | -------- |
| 1    | False                       | False    |
| 2    | True                        | True     |

The existing `test_capacity_boundary` checks values below, at, and above the maximum.

### **MCC summary**

| Decision | Number of atomic conditions | Feasible combinations |
| -------- | --------------------------- | --------------------- |
| D1       | 1                           | 2                     |
| D2       | 1                           | 2                     |
| D3       | 2                           | 3                     |
| D4       | 1                           | 2                     |

The MCC analysis is performed per decision. Because of early returns, not every possible combination across all four decisions can occur in a single execution.

## **5. Modified Condition/Decision Coverage (MC/DC)**

MC/DC verifies that each individual condition can independently affect the final outcome of its decision.

### **D1 – Registration open**

| Test | Registration open | Decision |
| ---- | ----------------- | -------- |
| A    | True              | False    |
| B    | False             | True     |

Pair: A and B. Changing the condition changes the decision.

### **D2 – Correct tournament status**

| Test | Status is registration | Decision |
| ---- | ---------------------- | -------- |
| A    | True                   | False    |
| B    | False                  | True     |

Pair: A and B. Changing the condition changes the decision.

### **D3 – Deadline**

| Test | Deadline exists (A) | Deadline passed (B) | Decision |
| ---- | ------------------- | ------------------- | -------- |
| A    | True                | True                | True     |
| B    | True                | False               | False    |
| C    | False               | Not evaluated       | False    |

- To demonstrate the independent effect of B, compare tests A and B. A remains true while B changes.
- To demonstrate A under masking MC/DC, compare tests A and C. A changes and the decision changes. B is masked in test C by short-circuit evaluation.

**Important:** This is masking MC/DC for A. Under strict unique-cause MC/DC, the expression does not provide a normal executable pair where B is evaluated and held fixed in both tests. We should not claim unique-cause coverage for that condition without confirming the convention required by your instructor.

### **D4 – Capacity**

| Test | Capacity reached | Decision |
| ---- | ---------------- | -------- |
| A    | False            | False    |
| B    | True             | True     |

Pair: A and B. Changing the capacity condition changes the decision.

### **MC/DC summary**

| Decision | Condition         | Pair        | Result                           |
| -------- | ----------------- | ----------- | -------------------------------- |
| D1       | Registration open | D1-A / D1-B | Demonstrated                     |
| D2       | Correct status    | D2-A / D2-B | Demonstrated                     |
| D3       | Deadline exists   | D3-A / D3-C | Demonstrated under masking MC/DC |
| D3       | Deadline passed   | D3-A / D3-B | Demonstrated                     |
| D4       | Capacity reached  | D4-A / D4-B | Demonstrated                     |

## **6. Existing unit test mapping**

The following tests already exist in `tests/team/test_can_register.py`.

| Test                                             | Purpose                                   |
| ------------------------------------------------ | ----------------------------------------- |
| `test_all_conditions_pass`                       | Successful registration                   |
| `test_closed_registration_is_refused`            | Closed registration                       |
| `test_status_other_than_registration_is_refused` | Invalid tournament statuses               |
| `test_deadline_in_the_past_is_refused`           | Expired deadline                          |
| `test_deadline_in_the_future_is_allowed`         | Future deadline                           |
| `test_full_tournament_is_refused`                | Tournament at capacity                    |
| `test_capacity_boundary`                         | Capacity boundary                         |
| `test_capacity_of_one`                           | Small capacity                            |
| `test_deadline_boundary`                         | Deadline equality and neighbouring values |
| `test_closed_wins_over_started`                  | First rejection takes precedence          |
| `test_started_wins_over_deadline`                | Status rejection takes precedence         |
| `test_deadline_wins_over_full`                   | Deadline rejection takes precedence       |
| `test_pending_team_counts_toward_the_cap`        | Pending teams count towards capacity      |
| `test_deadline_survives_a_database_reload`       | Database deadline defect                  |

## **7. Known limitations and observations**

There are a few important details worth recording:

1. The method uses early returns. Once a condition fails, the remaining conditions are skipped.
2. The deadline condition uses short-circuit evaluation, so the comparison is not performed if no deadline exists.
3. The deadline boundary uses `>` rather than `>=`. Therefore, a deadline exactly equal to the current time is not considered expired.
4. The database reload test is a strict expected failure (`xfail`) because SQLite returns a naive datetime while `utc_now()` returns a timezone-aware datetime. Comparing them raises a `TypeError`.
5. The model permits a nullable `max_teams` column, and comparing a numeric count against `None` could raise a `TypeError`. The test-basis notes identify this as a latent database-state issue rather than a normal registration flow.

## **8. Conclusion**

The `can_register()` method contains four main decision statements and five independent paths under the compound-decision CFG convention used above.

The existing tests exercise the rejection paths, successful registration, boundary values, and the precedence of rejection conditions. MCC and MC/DC analysis also identify the short-circuit behaviour of the deadline condition, which requires special treatment.

The analysis should be accompanied by a fresh execution of the focused test module and the relevant coverage report before it is submitted.
