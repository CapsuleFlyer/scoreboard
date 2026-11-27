# White-box Testing – `Tournament.can_register()`

**Course:** SE3002 – Software Quality Engineering  
**Project:** Scoreboard  
**Source file:** `app/models.py`  
**Test file:** `tests/team/test_can_register.py`

---

## 1. Function under test

The `Tournament.can_register()` method determines whether a team can register for a tournament. It evaluates the registration rules in sequence and immediately returns a rejection result when a rule is violated.

```python
def can_register(self):
    """Check if registration is still possible"""
    if not self.registration_open:
        return False, "Registration is closed"
    if self.status != 'registration':
        return False, "Tournament has already started"
    if self.registration_deadline and utc_now() > self.registration_deadline:
        return False, "Registration deadline has passed"
    if self.get_registered_team_count() >= self.max_teams:
        return False, "Tournament is full"
    return True, "OK"
```

The method checks four business rules:

1. Registration must be open.
2. The tournament status must be `registration`.
3. The registration deadline must not have passed.
4. The registered team count must be below the maximum capacity.

The order of these checks matters. If multiple rules would reject registration, the first failed rule determines the returned message. The method also uses short-circuit evaluation in the deadline condition.

## 2. Control Flow Graph (CFG)

The CFG represents the possible execution paths through the method.

For this analysis, the deadline expression is expanded into two separate decision points because Python evaluates the `and` operator using short-circuit evaluation:

- **A:** A registration deadline exists.
- **B:** The current time is later than the deadline.

If A is false, B is not evaluated. This is represented explicitly in the CFG.

### 2.1 CFG structure

```text
                         [N1: Entry]
                              |
                              v
                 [N2: D1 - Registration closed?]
                         /             \
                      True             False
                       |                 |
                       v                 v
              [N3: Return closed]  [N4: D2 - Status incorrect?]
                       |                 /          \
                       |              True          False
                       |               |              |
                       |               v              v
                       |       [N5: Return started] [N6: A - Deadline exists?]
                       |               |              /          \
                       |               |           True          False
                       |               |             |             |
                       |               |             v             |
                       |               |       [N7: B - Deadline passed?]
                       |               |          /          \      |
                       |               |       True          False  |
                       |               |         |              |   |
                       |               |         v              |   |
                       |               | [N8: Return deadline]   |   |
                       |               |         |              |   |
                       |               |         |              |   |
                       |               |         |              v   v
                       |               |         |    [N9: D4 - Capacity reached?]
                       |               |         |          /          \
                       |               |         |       True          False
                       |               |         |         |              |
                       |               |         |         v              v
                       |               |         |  [N10: Return full] [N11: Return OK]
                       |               |         |         |              |
                       v               v         v         v              v
                              [N12: Exit]
```

### 2.2 CFG nodes

| Node | Description |
|---|---|
| N1 | Entry |
| N2 | D1 – Registration closed? |
| N3 | Return registration closed |
| N4 | D2 – Tournament status incorrect? |
| N5 | Return tournament already started |
| N6 | A – Registration deadline exists? |
| N7 | B – Current time is later than the deadline? |
| N8 | Return deadline passed |
| N9 | D4 – Tournament capacity reached? |
| N10 | Return tournament full |
| N11 | Return registration allowed |
| N12 | Exit |

### 2.3 CFG edges

| Edge | Connection | Outcome |
|---|---|---|
| E1 | N1 → N2 | Entry |
| E2 | N2 → N3 | True |
| E3 | N2 → N4 | False |
| E4 | N3 → N12 | Return |
| E5 | N4 → N5 | True |
| E6 | N4 → N6 | False |
| E7 | N5 → N12 | Return |
| E8 | N6 → N7 | True |
| E9 | N6 → N9 | False – B is skipped |
| E10 | N7 → N8 | True |
| E11 | N7 → N9 | False |
| E12 | N8 → N12 | Return |
| E13 | N9 → N10 | True |
| E14 | N9 → N11 | False |
| E15 | N10 → N12 | Return |
| E16 | N11 → N12 | Return |

## 3. Cyclomatic complexity – V(G)

Cyclomatic complexity measures the number of linearly independent paths through a function.

The decision-point formula is:

\[
V(G)=D+1
\]

The expanded CFG contains five decision points:

1. D1 – Registration closed?
2. D2 – Status incorrect?
3. A – Deadline exists?
4. B – Deadline passed?
5. D4 – Capacity reached?

Therefore:

\[
V(G)=5+1=\boxed{6}
\]

The result can also be verified using the CFG formula:

\[
V(G)=E-N+2P
\]

Where:

- E = 16 edges
- N = 12 nodes
- P = 1 connected component

\[
V(G)=16-12+2(1)=\boxed{6}
\]

Therefore, the cyclomatic complexity of `can_register()` is **6** when the short-circuit deadline expression is represented using separate decision nodes.

This means that six linearly independent paths form a basis path set.

### 3.1 Basis path testing

The following six paths form a basis path set for the expanded CFG.

| Path | Conditions | Expected result |
|---|---|---|
| P1 | Registration is closed | Registration refused |
| P2 | Registration open; status is incorrect | Registration refused |
| P3 | Registration open; correct status; no deadline; capacity available | Registration allowed |
| P4 | Registration open; correct status; deadline exists and has passed | Registration refused |
| P5 | Registration open; correct status; future deadline; capacity available | Registration allowed |
| P6 | Registration open; correct status; no deadline; capacity reached | Registration refused |

Existing tests that exercise these paths include:

- P1: `test_closed_registration_is_refused`
- P2: `test_status_other_than_registration_is_refused`
- P3: `test_all_conditions_pass`
- P4: `test_deadline_in_the_past_is_refused`
- P5: `test_deadline_in_the_future_is_allowed`
- P6: `test_full_tournament_is_refused`

These paths demonstrate the different outcomes and the short-circuit behaviour of the function. They do not replace the separate requirement to achieve statement and branch coverage across all server-side business logic.

## 4. Multiple Condition Coverage (MCC)

Multiple Condition Coverage checks the combinations of atomic conditions within a decision.

For decisions containing only one atomic condition, both possible outcomes are considered. For the deadline expression, all four logical combinations of its two atomic conditions are identified.

### 4.1 D1 – Registration open

Expression:

```python
not self.registration_open
```

| Test | Registration open | Decision result |
|---|---|---|
| 1 | True | False – continue |
| 2 | False | True – reject |

Both possible outcomes are covered.

### 4.2 D2 – Tournament status

Expression:

```python
self.status != 'registration'
```

| Test | Status is `registration` | Decision result |
|---|---|---|
| 1 | True | False – continue |
| 2 | False | True – reject |

The existing tests check several invalid statuses, including `ready`, `in_progress`, `completed`, and `cancelled`.

### 4.3 D3 – Registration deadline

Expression:

```python
self.registration_deadline and utc_now() > self.registration_deadline
```

Define the atomic conditions:

- **A:** A registration deadline exists.
- **B:** The current time is later than the deadline.

The complete logical MCC table is:

| Test | A: Deadline exists | B: Deadline passed | A AND B |
|---|---|---|---|
| 1 | False | False | False |
| 2 | False | True | False |
| 3 | True | False | False |
| 4 | True | True | True |

**Short-circuit limitation:** Rows 1 and 2 are not distinguishable as executable evaluations of B. When A is false, Python skips the comparison entirely. Therefore, row 2 is a logical combination in the MCC truth table, but it cannot be executed as a test in the actual implementation.

The three executable outcomes are:

- No deadline exists: the expression evaluates as false.
- A future deadline exists: the expression evaluates as false.
- An expired deadline exists: the expression evaluates as true.

Existing tests:

- `test_all_conditions_pass`
- `test_deadline_in_the_future_is_allowed`
- `test_deadline_in_the_past_is_refused`

### 4.4 D4 – Tournament capacity

Expression:

```python
self.get_registered_team_count() >= self.max_teams
```

| Test | Registered count >= maximum | Decision result |
|---|---|---|
| 1 | False | False – continue |
| 2 | True | True – reject |

The existing `test_capacity_boundary` checks values below, at, and above the maximum capacity.

### 4.5 MCC summary

| Decision | Atomic conditions | Logical combinations | Executable combinations |
|---|---:|---:|---:|
| D1 – Registration | 1 | 2 | 2 |
| D2 – Status | 1 | 2 | 2 |
| D3 – Deadline | 2 | 4 | 3 |
| D4 – Capacity | 1 | 2 | 2 |

MCC is evaluated separately for each decision. The four decisions do not need to be combined into one table because the function uses sequential checks and early returns.

The deadline decision has four logical combinations, but only three executable combinations because of short-circuit evaluation. This limitation is documented rather than treating the skipped condition as tested.

## 5. Modified Condition/Decision Coverage (MC/DC)

MC/DC verifies that every atomic condition can independently affect the outcome of its decision.

For each condition, a pair of test cases must demonstrate that changing that condition changes the overall decision result, while the effects of other conditions are controlled or appropriately masked.

### 5.1 D1 – Registration open

Expression:

```python
not self.registration_open
```

| Test | Registration open | Decision |
|---|---|---|
| D1-A | True | False |
| D1-B | False | True |

**MC/DC pair:** D1-A and D1-B.

Changing the registration-open condition changes the decision result.

### 5.2 D2 – Correct tournament status

Expression:

```python
self.status != 'registration'
```

| Test | Status is `registration` | Decision |
|---|---|---|
| D2-A | True | False |
| D2-B | False | True |

**MC/DC pair:** D2-A and D2-B.

Changing the status condition changes the decision result.

### 5.3 D3 – Registration deadline

Expression:

```python
self.registration_deadline and utc_now() > self.registration_deadline
```

Conditions:

- A = A deadline exists.
- B = Current time is later than the deadline.

| Test | A | B | Decision |
|---|---|---|---|
| D3-A | True | True | True |
| D3-B | True | False | False |
| D3-C | False | Not evaluated | False |

**Independent effect of B:**

Compare D3-A and D3-B.

- A remains true in both tests.
- B changes from true to false.
- The overall decision changes from true to false.

Therefore, B independently affects the deadline decision.

**Independent effect of A – masking MC/DC:**

Compare D3-A and D3-C.

- A changes from true to false.
- The overall decision changes from true to false.
- B is masked in D3-C because it is not evaluated when A is false.

This demonstrates the effect of A using masking MC/DC.

**Important limitation:** This is a masking MC/DC pair for A. A conventional unique-cause pair would require the other condition to be held fixed and independently evaluated. That cannot be demonstrated through the normal execution of this short-circuit expression when A is false. The limitation is caused by the implementation's evaluation order and is explicitly documented.

### 5.4 D4 – Tournament capacity

Expression:

```python
self.get_registered_team_count() >= self.max_teams
```

| Test | Capacity reached | Decision |
|---|---|---|
| D4-A | False | False |
| D4-B | True | True |

**MC/DC pair:** D4-A and D4-B.

Changing the capacity condition changes the decision result.

### 5.5 MC/DC summary

| Decision | Condition | Pair | Result |
|---|---|---|---|
| D1 | Registration open | D1-A / D1-B | Demonstrated |
| D2 | Correct status | D2-A / D2-B | Demonstrated |
| D3 | Deadline exists (A) | D3-A / D3-C | Demonstrated using masking MC/DC |
| D3 | Deadline passed (B) | D3-A / D3-B | Demonstrated |
| D4 | Capacity reached | D4-A / D4-B | Demonstrated |

The MC/DC pairs are identified from the MCC combinations. The deadline condition requires the masking explanation because of Python's short-circuit evaluation.

## 6. Existing unit test mapping

The following tests exist in `tests/team/test_can_register.py`.

| Test | Purpose |
|---|---|
| `test_all_conditions_pass` | Successful registration when all rules pass |
| `test_closed_registration_is_refused` | Registration closed |
| `test_status_other_than_registration_is_refused` | Invalid tournament statuses |
| `test_deadline_in_the_past_is_refused` | Expired registration deadline |
| `test_deadline_in_the_future_is_allowed` | Future registration deadline |
| `test_full_tournament_is_refused` | Tournament at capacity |
| `test_capacity_boundary` | Values below, at, and above maximum capacity |
| `test_capacity_of_one` | Small tournament capacity |
| `test_deadline_boundary` | Deadline equality and neighbouring values |
| `test_closed_wins_over_started` | Registration-closed rejection takes precedence |
| `test_started_wins_over_deadline` | Status rejection takes precedence |
| `test_deadline_wins_over_full` | Deadline rejection takes precedence |
| `test_pending_team_counts_toward_the_cap` | Pending teams count towards capacity |
| `test_deadline_survives_a_database_reload` | Database deadline persistence defect |

The test suite covers the individual business rules, their boundaries, and the order in which rejection conditions are evaluated.

The database reload test is a strict expected failure. It documents an existing defect and should not be counted as a passing functional test.

## 7. Known limitations and observations

1. **Early returns:** Once a condition fails, the method immediately returns. Later decisions are not evaluated during that execution.
2. **Short-circuit evaluation:** The deadline comparison is only evaluated when a deadline exists.
3. **Deadline boundary:** The method uses `>` rather than `>=`. A deadline exactly equal to the current time is therefore not considered expired.
4. **Database datetime issue:** SQLite returns a naive datetime after reloading a stored deadline, while `utc_now()` returns a timezone-aware datetime. Comparing them raises a `TypeError`. This is documented by `test_deadline_survives_a_database_reload`.
5. **Nullable maximum capacity:** The model permits a nullable `max_teams` value. If it is actually `None`, comparing the registered team count against it can raise a `TypeError`. The test-basis notes identify this as a latent database-state issue rather than a normal registration flow.

These observations should be linked to the project's defect and risk documentation where applicable.

## 8. Coverage requirements and evidence

The analysis above focuses on `Tournament.can_register()`, which is the selected critical module for detailed MCC and MC/DC analysis.

However, the assignment requires **100% statement and branch coverage of all server-side business logic**, not only this method.

The focused unit tests provide evidence for the behaviour of `can_register()`. The broader coverage report must separately demonstrate the coverage of the complete server-side business-logic scope.

The final submission should include:

- A fresh pytest execution report.
- A statement and branch coverage report for all server-side business logic.
- The scoped coverage report used to verify the required coverage target.
- An explanation of any uncovered statements or branches, including whether they are unreachable, environment-dependent, or associated with a known defect.
- A comparison of the hand-calculated cyclomatic complexity with the complexity reported by SonarQube.

Coverage should be reported from an actual test run. No uncovered code should be described as covered simply because it is difficult to reach.

## 9. Conclusion

`Tournament.can_register()` implements four sequential registration rules. Its deadline condition contains two atomic Boolean conditions, making it the main focus of the MCC and MC/DC analysis.

Using an expanded CFG that represents short-circuit evaluation, the method has 12 nodes, 16 edges, and a cyclomatic complexity of **6**.

The MCC analysis identifies all logical combinations for the deadline decision and documents the combination that cannot be executed because of short-circuit evaluation. The MC/DC analysis identifies the independent-effect pairs, using masking MC/DC for the deadline-exists condition.

The existing unit tests exercise the main registration outcomes, boundaries, and rejection precedence. These results support the critical-module analysis, while the separate whole-business-logic coverage report is required to demonstrate compliance with the assignment's 100% statement and branch coverage target.