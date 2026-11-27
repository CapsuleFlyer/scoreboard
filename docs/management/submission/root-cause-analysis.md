# Root Cause Analyses — 5 Whys and Fishbone

These analyses use the known defect descriptions in the project record. Confirm each description against the corresponding GitHub issue and current source before treating the analysis as final.

## DR-03 — Naive versus timezone-aware datetime

**Problem:** A datetime operation can fail or behave inconsistently when one value is timezone-naive and another is timezone-aware. Test output also showed use of deprecated `datetime.utcnow()`.

### 5 Whys

1. **Why did the operation fail or produce inconsistent time handling?** The code path mixed datetime values with different timezone-awareness.
2. **Why were the values different?** Some values were created without timezone information while others were timezone-aware.
3. **Why were both conventions present?** Time creation and persistence did not consistently enforce one UTC representation.
4. **Why was the inconsistency not caught earlier?** Tests did not cover the relevant naive/aware combination across the affected path.
5. **Why was there no consistent guard?** The project lacked an enforced datetime convention and centralised conversion/validation at the relevant boundary.

**Likely root cause:** Inconsistent datetime normalisation and insufficient tests for mixed timezone-awareness. Validate this against the actual failing code path.

### Fishbone (Ishikawa)

| Category | Possible contributing cause |
|---|---|
| People | Contributors may have used different datetime conventions |
| Process | No explicit project-wide rule requiring timezone-aware UTC values |
| Code | Naive and aware datetime values meet in the same path |
| Tests | Missing regression test for mixed-awareness values |
| Tools | Deprecated `utcnow()` usage can encourage naive UTC values |
| Data | Existing persisted values may not contain timezone metadata |

**Corrective actions:** Adopt timezone-aware UTC creation (for example, `datetime.now(timezone.utc)` or the project's supported equivalent), normalise values at input/persistence boundaries, add regression tests, and review existing stored values before changing interpretation.

**Verification:** Add tests for aware/aware and legacy-value handling; run the relevant suite and confirm no naive/aware comparison exception remains.

## DR-14 — Missing `db` import in input blueprint

**Problem:** A code path in the input blueprint references `db` without importing or otherwise defining it in that module.

### 5 Whys

1. **Why did the route fail when it reached the database operation?** The module referenced `db` that was not available in its namespace.
2. **Why was `db` unavailable?** The required database object was not imported or injected into the module.
3. **Why was the missing dependency not caught?** The affected route/module path was not exercised by a test that reached the database call.
4. **Why was the route not covered adequately?** Tests may have focused on other blueprints or mocked the relevant path before the unresolved name was evaluated.
5. **Why was there no earlier detection?** Import/name-resolution checks and route-level integration coverage were insufficient for this path.

**Likely root cause:** An undeclared module dependency combined with missing route-level regression coverage. Confirm the exact reference and fix in the current source.

### Fishbone (Ishikawa)

| Category | Possible contributing cause |
|---|---|
| People | A module split/refactor may have omitted a dependency |
| Process | No checklist for imports and dependencies during refactoring |
| Code | `db` referenced without a local import or explicit injection |
| Tests | No test exercises the affected route through the database call |
| Tools | Static analysis may not have been configured to catch this exact path |
| Architecture | Database access is coupled to blueprint module globals |

**Corrective actions:** Import the database object from the project's canonical extension/module, or inject it through the established application pattern; add a route-level regression test; run lint/static analysis and the relevant test suite.

**Verification:** The affected route should execute without `NameError`, and the new regression test should fail if the dependency is removed again.
