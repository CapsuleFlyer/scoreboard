# Usability and Accessibility Evaluation

**Course:** SE3002 – Software Quality Engineering  
**Project:** Scoreboard  
**Evaluation date:** 27 November 2026

## 1. Objective

The purpose of this evaluation was to assess the usability and accessibility of the Scoreboard application, identify accessibility problems affecting users, and compare the application before and after accessibility-related changes.

The evaluation used:

- **axe-core:** Automated accessibility testing through `axe-playwright-python`.
- **Lighthouse:** Accessibility, Best Practices and SEO audits.
- **Playwright:** Browser automation to access and scan the application's main screens.

The evaluation covered four screens:

1. Public tournament registration form.
2. Public registration code-entry page.
3. Administrator login page.
4. Administrator registrations page.

## 2. Testing Environment and Method

The scans were performed on Windows using Python, Playwright, Chromium and Lighthouse.

The before and after Lighthouse scans used:

- **Before revision:** `483f4ff`
- **After revision:** `1e57c85`
- **Lighthouse version:** 13.6.0

The before revision was checked out separately using Git worktrees to avoid changing the main working directory. The after scans were performed against the updated application.

The axe-core scans were performed using the `A11Y_LABEL` environment variable to separate the reports:

```powershell
$env:A11Y_LABEL="before"
python -m pytest tests/team/e2e/test_e2e_accessibility.py -v -s
```

After the accessibility-related changes:

```powershell
$env:A11Y_LABEL="after"
python -m pytest tests/team/e2e/test_e2e_accessibility.py -v -s
```

All four after-scan tests completed successfully.

The comparison script was then executed for each screen:

```powershell
python scripts/a11y_compare.py register-form
python scripts/a11y_compare.py register-index
python scripts/a11y_compare.py admin-login
python scripts/a11y_compare.py admin-registrations
```

The comparison identifies issues using the accessibility rule ID and affected target selector. This allows individual findings to be tracked across the two scans.

## 3. Accessibility Changes

Accessibility-related changes were made to the public registration form and code-entry page.

The changes included:

- Associating visible form labels with their inputs using matching `for` and `id` attributes.
- Adding `aria-describedby` attributes to connect inputs with their character-counter descriptions.
- Adding accessible names to the registration code input.
- Adding `aria-label` attributes to alert close buttons.

These changes were intended to improve the information available to assistive technologies, particularly screen-reader users.

The administrator registration page was also evaluated. Its remaining form-label issues are documented below rather than being treated as resolved.

## 4. axe-core Results

The following table summarises the before and after axe-core comparison.

| Screen | Before issues | After issues | Resolved | Remaining | New |
|---|---:|---:|---:|---:|---:|
| Public registration form | 3 | 3 | 0 | 3 | 0 |
| Code-entry page | 1 | 1 | 0 | 1 | 0 |
| Administrator login | 1 | 1 | 0 | 1 | 0 |
| Administrator registrations | 7 | 7 | 0 | 7 | 0 |
| **Total** | **12** | **12** | **0** | **12** | **0** |

### 4.1 Remaining Findings

**Public registration form**

| Rule | Impact | Affected element |
|---|---|---|
| `color-contrast` | Serious | `.btn` |
| `color-contrast` | Serious | `.spots-badge` |
| `heading-order` | Moderate | `.mb-4` |

The contrast findings indicate that some text does not have sufficient contrast against its background. The heading-order finding indicates an issue with the semantic heading hierarchy.

**Public code-entry page**

| Rule | Impact | Affected element |
|---|---|---|
| `color-contrast` | Serious | `.btn` |

The button's text contrast should be improved to make it easier to read.

**Administrator login**

| Rule | Impact | Affected element |
|---|---|---|
| `page-has-heading-one` | Moderate | `html` |

The page does not expose a primary level-one heading. Adding an appropriate main heading would improve its semantic structure.

**Administrator registrations**

| Rule | Impact | Affected element |
|---|---|---|
| `color-contrast` | Serious | `.btn-ru` |
| `heading-order` | Moderate | `.col-md-4 > .card:nth-child(1) > .card-header > h5` |
| `label` | Critical | `#add-player1` |
| `label` | Critical | `#add-player2` |
| `label` | Critical | `#add-team-name` |
| `label` | Critical | `#reg-code` |
| `label` | Critical | `#reg-url` |

The five form controls lack properly associated labels. This can prevent screen-reader users from understanding the purpose of the fields.

### 4.2 axe-core Comparison

The comparison found no new issues, but it also found no issues that could be confirmed as resolved.

Therefore, the axe-core results do not demonstrate a reduction in violations. The findings remain documented as outstanding accessibility work.

## 5. Lighthouse Results

Lighthouse was used to evaluate the public registration form and administrator registrations page.

The following scores were obtained:

| Screen | Category | Before | After | Difference |
|---|---|---:|---:|---:|
| Public registration | Accessibility | 80 | 86 | +6 |
| Public registration | Best Practices | 96 | 96 | 0 |
| Public registration | SEO | 91 | 83 | -8 |
| Administrator registrations | Accessibility | 76 | 76 | 0 |
| Administrator registrations | Best Practices | 96 | 96 | 0 |
| Administrator registrations | SEO | 91 | 83 | -8 |

### 5.1 Interpretation

The public registration form's accessibility score increased from 80 to 86, representing a six-point improvement.

The administrator registrations page remained at 76, showing no change in its overall accessibility score.

Best Practices remained unchanged at 96 on both pages.

SEO decreased from 91 to 83 on both pages. This is recorded separately from the accessibility results and should not be interpreted as an accessibility regression without further investigation.

### 5.2 Remaining Lighthouse Audits

The reports continued to identify the following accessibility problems:

| Lighthouse audit | Public registration | Administrator registrations |
|---|---|---|
| Buttons do not have an accessible name | Failed | Failed |
| Background and foreground colors do not have sufficient contrast | Failed | Failed |
| Heading elements are not in sequentially descending order | Failed | Failed |
| Form elements do not have associated labels | Not reported | Failed |

The after reports also included five passing ARIA-related audits:

- ARIA attributes match their roles.
- ARIA attributes are used as specified for the element's role.
- Elements use only permitted ARIA attributes.
- ARIA attributes have valid values.
- ARIA attributes are valid and not misspelled.

These checks passed in the after reports. However, the corresponding before scores were unavailable, so they cannot be counted as confirmed improvements.

## 6. Combined Findings and Proposed Improvements

Findings reported by both tools are considered together to avoid counting the same underlying problem twice.

| Finding | User impact | Proposed improvement | Status |
|---|---|---|---|
| Insufficient text contrast | Users with visual impairments may struggle to read text. | Adjust foreground and background colours to meet WCAG contrast requirements. | Remaining |
| Incorrect heading hierarchy | Screen-reader users may find the page structure difficult to navigate. | Use sequential heading levels. | Remaining |
| Unnamed buttons | Screen readers may announce buttons without explaining their purpose. | Provide meaningful accessible names using text or ARIA labels. | Remaining |
| Unlabelled administrator inputs | Screen-reader users may not know what information a field requires. | Associate each input with a visible label. | Remaining |
| Missing main heading on login page | The page has a weaker semantic structure. | Add an appropriate level-one heading. | Remaining |

## 7. Overall Evaluation

The evaluation successfully produced before and after accessibility evidence for four application screens using axe-core and two screens using Lighthouse.

The public registration form's Lighthouse accessibility score improved from 80 to 86. The administrator registrations page remained at 76.

The axe-core comparison reported 12 issues before and 12 after, with no new findings and no confirmed resolved findings. This indicates that the accessibility changes did not produce a measurable reduction in the recorded axe-core violations.

Several accessibility problems remain, particularly insufficient colour contrast, heading hierarchy, unnamed buttons and missing labels on administrator form controls.

The results provide a documented baseline for further accessibility improvements. The evaluation also demonstrates why multiple accessibility tools are useful: Lighthouse provides an overall category score, while axe-core identifies individual rules and affected elements.

## 8. Evidence and Report Locations

All generated reports are retained in the repository.

**axe-core reports**

- `docs/evidence/accessibility/before/`
- `docs/evidence/accessibility/after/`

**Lighthouse reports**

- `docs/evidence/lighthouse/before/register-form.report.json`
- `docs/evidence/lighthouse/before/register-form.report.html`
- `docs/evidence/lighthouse/before/admin-registrations.report.json`
- `docs/evidence/lighthouse/before/admin-registrations.report.html`
- `docs/evidence/lighthouse/after/register-form.report.json`
- `docs/evidence/lighthouse/after/register-form.report.html`
- `docs/evidence/lighthouse/after/admin-registrations.report.json`
- `docs/evidence/lighthouse/after/admin-registrations.report.html`

**Comparison script**

- `scripts/a11y_compare.py`

The Lighthouse JSON files contain the full audit results, while the HTML files provide browser-readable reports.

The generated `lh-headers.json` file contains an administrator session cookie and must remain excluded from version control.
