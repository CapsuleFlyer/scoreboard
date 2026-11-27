# Dependency Vulnerability Audit

## Objective
To identify known vulnerabilities in the project's third-party Python dependencies using `pip-audit`.

## Initial Audit
The initial audit of `requirements.txt` identified 25 known vulnerabilities across 5 packages. The affected dependencies were updated to versions addressing the reported vulnerabilities.

Evidence: `docs/evidence/security/pip-audit-before.json`

## Audit After Dependency Updates
The production dependency audit was rerun after updating the dependencies.

Command:
```powershell
python -m pip_audit -r requirements.txt
```

Result:
```text
No known vulnerabilities found
```

Evidence: `docs/evidence/security/pip-audit.json`

## Dependency Consistency and Regression Testing
- `pip check`: No broken requirements found.
- Full test suite: 565 passed, 41 expected failures, 0 failed.

## Limitation
The development dependency audit using `requirements-dev.txt` could not be completed because pip reported a dependency-resolution error in its temporary audit environment. Therefore, the clean audit result applies to production dependencies listed in `requirements.txt`, not the complete development dependency set.
