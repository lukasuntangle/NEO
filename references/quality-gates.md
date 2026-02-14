# Quality Gates (Sentinels)

Phase 5 of the Neo Orchestrator workflow. Four independent quality gates must all pass before code reaches Zion. Each gate targets a different failure category to provide defense in depth.

---

## Gate 1: Agent Smith -- Blind Code Review

**Agent:** Smith (opus)
**Purpose:** Catch code quality issues, logic errors, convention violations, and design flaws through an unbiased review.

### Preparation

The `blind-review-prep.sh` script sanitizes the diff before Smith sees it:

1. **Strips author information:** No git blame, no commit author, no agent name.
2. **Strips commit messages:** Smith cannot infer intent from commit messages -- only the code speaks.
3. **Strips file paths outside the diff:** Smith sees relative paths within the diff but cannot identify the broader project structure to avoid bias.
4. **Preserves:** The unified diff content itself, including context lines around changes.

Smith receives exactly two inputs:
- The sanitized unified diff
- The project conventions file (coding standards, style rules)

### Review Requirements

Smith must produce one of two outputs:

**Option A -- Issues Found (3+ required):**
Each issue must include:
- **Location:** Line reference within the diff
- **Severity:** `critical`, `major`, or `minor`
- **Category:** Logic error, convention violation, performance, readability, maintainability, error handling, etc.
- **Description:** What the issue is
- **Suggestion:** How to fix it

**Option B -- Clean Pass Justification:**
If Smith finds fewer than 3 issues, Smith must write a justification of >100 words explaining:
- Why the code is clean
- What specific qualities make it acceptable
- What was checked and found satisfactory

This prevents lazy "LGTM" reviews.

### Issue Severity Levels

| Severity | Definition | Action |
|----------|-----------|--------|
| critical | Blocks deployment. Data loss, security hole, crash. | Must fix before proceeding. |
| major | Should be fixed. Logic error, missing validation, poor error handling. | Creates remediation ticket. |
| minor | Nice to have. Style nit, naming suggestion, minor optimization. | Noted but does not block. |

### Double-Smith Protocol

If Smith finds 0 issues:
1. A second, independent Smith clone is spawned.
2. The second Smith receives the same sanitized diff but no knowledge of the first Smith's result.
3. If the second Smith also finds 0 issues: **pass** (the code is genuinely clean).
4. If the second Smith finds issues: those issues are used as the gate result.

This prevents false negatives from a single review pass.

### Output Format

`.matrix/gate-results/smith-review.json`:
```json
{
  "gate": "smith-review",
  "status": "pass" | "fail",
  "reviewer_count": 1 | 2,
  "issues": [
    {
      "id": "SMITH-001",
      "severity": "major",
      "category": "error-handling",
      "location": "diff line 42-45",
      "description": "Missing error handling for database query failure",
      "suggestion": "Wrap in try/catch and return appropriate error response"
    }
  ],
  "clean_pass_justification": null | "string (>100 words)",
  "summary": {
    "critical": 0,
    "major": 2,
    "minor": 1,
    "total": 3
  },
  "timestamp": "ISO-8601"
}
```

### Pass/Fail Criteria

- **Pass:** 0 critical issues AND (0 major issues OR all major issues have clear remediation path)
- **Fail:** Any critical issue OR 3+ major issues

---

## Gate 2: Trinity -- Security Audit

**Agent:** Trinity (sonnet)
**Purpose:** Identify security vulnerabilities before they reach production. Focuses on common web application security issues.

### Checks Performed

**OWASP Top 10 Coverage:**
1. **Injection** -- SQL injection, NoSQL injection, command injection, LDAP injection
2. **Broken Authentication** -- Weak password policies, missing MFA considerations, session management flaws
3. **Sensitive Data Exposure** -- Unencrypted data, missing HTTPS enforcement, verbose error messages
4. **XML External Entities (XXE)** -- If XML parsing is used
5. **Broken Access Control** -- Missing authorization checks, IDOR vulnerabilities, privilege escalation
6. **Security Misconfiguration** -- Default configs, unnecessary features enabled, missing headers
7. **Cross-Site Scripting (XSS)** -- Reflected, stored, DOM-based
8. **Insecure Deserialization** -- Untrusted data deserialization
9. **Using Components with Known Vulnerabilities** -- Outdated dependencies
10. **Insufficient Logging & Monitoring** -- Missing audit trails for security events

**Hardcoded Secrets Scan:**
Regex patterns for:
- API keys (various formats: `sk-`, `pk-`, `AKIA`, etc.)
- Passwords in strings (e.g., `password = "..."`, `passwd`, `secret`)
- Tokens (JWT, OAuth, bearer tokens in code)
- Connection strings with embedded credentials
- Private keys (RSA, EC, etc.)
- AWS, GCP, Azure credential patterns

**Injection Vulnerability Analysis:**
- SQL: String concatenation in queries, unsanitized parameters
- XSS: Unescaped user input rendered in HTML, `dangerouslySetInnerHTML`
- Command injection: `exec()`, `spawn()` with unsanitized input
- Path traversal: User input in file paths without sanitization

**Authentication and Authorization Review:**
- Auth middleware applied to protected routes
- Token validation on every request
- Role-based access control consistency
- Session invalidation on logout

### Severity Levels

| Severity | Definition | Gate Impact |
|----------|-----------|-------------|
| critical | Exploitable vulnerability, data breach risk. | Automatic gate failure. |
| high | Significant security weakness, should fix before deploy. | Gate failure if 2+ found. |
| medium | Security concern that should be tracked. | Noted, does not block. |
| low | Minor security observation. | Noted, does not block. |

### Output Format

`.matrix/gate-results/trinity-security.json`:
```json
{
  "gate": "trinity-security",
  "status": "pass" | "fail",
  "findings": [
    {
      "id": "SEC-001",
      "severity": "critical",
      "category": "injection",
      "subcategory": "sql-injection",
      "file": "src/api/users.ts",
      "line": 23,
      "description": "User input directly concatenated into SQL query",
      "evidence": "const query = `SELECT * FROM users WHERE id = ${req.params.id}`",
      "recommendation": "Use parameterized queries: db.query('SELECT * FROM users WHERE id = $1', [req.params.id])",
      "owasp_ref": "A1:2021-Injection"
    }
  ],
  "summary": {
    "critical": 1,
    "high": 0,
    "medium": 2,
    "low": 1,
    "total": 4
  },
  "secrets_found": false,
  "timestamp": "ISO-8601"
}
```

### Pass/Fail Criteria

- **Pass:** 0 critical findings AND fewer than 2 high findings AND no hardcoded secrets
- **Fail:** Any critical finding OR 2+ high findings OR any hardcoded secret detected

---

## Gate 3: Shannon -- Dynamic Security Testing

**Agent:** Shannon (sonnet)
**Purpose:** Actively probe the running application for exploitable vulnerabilities. While Trinity performs static analysis, Shannon attacks the live system to confirm or deny findings.

**Named after:** Claude Shannon, father of information theory — because every vulnerability is information leaking where it shouldn't.

### Testing Phases

1. **Reconnaissance** — Map all exposed endpoints, identify input vectors, catalog authentication mechanisms
2. **Authentication Testing** — Attempt auth bypass, token manipulation, session fixation, credential stuffing patterns
3. **Injection Testing** — SQL injection, NoSQL injection, command injection, LDAP injection, template injection against live endpoints
4. **Authorization Testing** — IDOR attempts, privilege escalation, horizontal access control bypass, missing function-level access control
5. **Business Logic Testing** — Race conditions, workflow bypass, parameter tampering, mass assignment

### Cross-Reference with Trinity

Shannon explicitly cross-references Trinity's static findings:
- **Confirmed:** Trinity found it statically, Shannon exploited it dynamically. High confidence — real vulnerability.
- **False Positive:** Trinity flagged it, but Shannon could not exploit it. The code path may be unreachable or properly mitigated.
- **New Finding:** Shannon found something Trinity missed. Dynamic-only vulnerability (e.g., race condition, timing attack).

### PoC Requirement

Every finding must include a **proof of concept** — a reproducible curl command or script that demonstrates the vulnerability. Findings without PoCs are classified as `unverified` and do not trigger gate failure.

### Severity Levels

| Severity | Definition | Gate Impact |
|----------|-----------|-------------|
| critical | Confirmed exploitable with PoC. Data breach, auth bypass, RCE. | Automatic gate failure. |
| high | Confirmed exploitable but limited blast radius. | Gate failure if 2+ found. |
| medium | Exploitable but requires specific conditions. | Noted, does not block. |
| low | Theoretical or requires insider access. | Noted, does not block. |

### Output Format

`.matrix/sentinels/shannon-pentest.json`:
```json
{
  "gate": "shannon-pentest",
  "status": "pass" | "fail",
  "app_started": true,
  "endpoints_tested": 15,
  "findings": [
    {
      "id": "SHAN-001",
      "severity": "critical",
      "category": "injection",
      "endpoint": "POST /api/users/search",
      "description": "SQL injection via unparameterized query in search filter",
      "poc": "curl -X POST http://localhost:3000/api/users/search -H 'Content-Type: application/json' -d '{\"filter\": \"' OR 1=1 --\"}'",
      "trinity_cross_ref": "SEC-003 (confirmed)",
      "remediation": "Use parameterized queries for all user-supplied search filters"
    }
  ],
  "trinity_cross_reference": {
    "confirmed": ["SEC-003"],
    "false_positives": ["SEC-005"],
    "not_tested": []
  },
  "summary": {
    "critical": 1,
    "high": 0,
    "medium": 2,
    "low": 1,
    "total": 4
  },
  "timestamp": "ISO-8601"
}
```

### Pass/Fail Criteria

- **Pass:** 0 critical findings AND fewer than 2 high findings (all with PoCs)
- **Fail:** Any critical finding with PoC OR 2+ high findings with PoCs

### Fallback Mode

If the application cannot be started (e.g., missing database, environment variables), Shannon falls back to **code-based analysis** — reviewing endpoint handlers, middleware chains, and request processing code for vulnerabilities that would be dynamically testable. Findings from fallback mode are marked as `static_fallback: true` and are treated with lower confidence.

---

## Gate 4: Switch + Mouse -- Test Coverage

**Agent (writing):** Switch (sonnet)
**Agent (running):** Mouse (haiku)
**Purpose:** Ensure comprehensive test coverage meets the project threshold (default 80%).

### Switch: Test Writing Phase

1. **Review existing tests:**
   - Identify what is already covered.
   - Map test files to source files.
   - Identify coverage gaps.

2. **Write missing tests:**
   - **Happy paths:** Normal expected usage of each function/endpoint.
   - **Error paths:** What happens when things go wrong (invalid input, network failure, missing data).
   - **Edge cases:** Empty inputs, null values, maximum lengths, concurrent access.
   - **Boundary conditions:** Off-by-one, pagination limits, rate limits, timeout boundaries.

3. **Test quality requirements:**
   - Each test must have a clear, descriptive name.
   - Tests must be deterministic (no reliance on external state or timing).
   - Tests must be independent (no shared mutable state between tests).
   - Mocks and stubs used appropriately (not over-mocked).

### Mouse: Test Execution Phase

1. **Run the full test suite:**
   - Execute all tests (existing + newly written by Switch).
   - Capture stdout, stderr, and exit code.
   - Parse test runner output for pass/fail counts.

2. **Parse coverage report:**
   - Extract line coverage, branch coverage, function coverage.
   - Identify files below the coverage threshold.
   - Calculate overall project coverage percentage.

3. **Report results:**
   - Total tests: passed, failed, skipped.
   - Coverage: overall percentage, per-file breakdown for files below threshold.
   - Failing test details: test name, error message, stack trace.

### Coverage Threshold

- **Default:** 80% line coverage (configurable in `.matrix/config.json`)
- **Per-file minimum:** No single file below 60% (to prevent coverage gaming by over-testing easy files)
- **Branch coverage:** Reported but not gating (informational)

### Output Format

`.matrix/gate-results/switch-tests.json`:
```json
{
  "gate": "switch-tests",
  "tests_written": 15,
  "test_files": [
    "src/__tests__/auth.test.ts",
    "src/__tests__/users.test.ts"
  ],
  "coverage_types": {
    "happy_path": 8,
    "error_path": 4,
    "edge_case": 2,
    "boundary": 1
  },
  "timestamp": "ISO-8601"
}
```

`.matrix/gate-results/mouse-coverage.json`:
```json
{
  "gate": "mouse-coverage",
  "status": "pass" | "fail",
  "test_results": {
    "total": 45,
    "passed": 43,
    "failed": 2,
    "skipped": 0
  },
  "coverage": {
    "overall": 84.2,
    "threshold": 80,
    "lines": 84.2,
    "branches": 71.5,
    "functions": 88.0,
    "statements": 83.9
  },
  "files_below_threshold": [
    {
      "file": "src/utils/crypto.ts",
      "coverage": 55.0
    }
  ],
  "failing_tests": [
    {
      "name": "should reject expired tokens",
      "file": "src/__tests__/auth.test.ts",
      "error": "Expected 401, received 200"
    }
  ],
  "timestamp": "ISO-8601"
}
```

### Pass/Fail Criteria

- **Pass:** 0 failing tests AND overall coverage >= threshold AND no file below 60%
- **Fail:** Any failing test OR overall coverage < threshold OR any file below 60%

---

## Remediation Flow

When any gate fails, the following remediation process is triggered:

### Step 1: Create Remediation Tickets

For each gate failure:
- Extract actionable items from the gate result JSON.
- Create remediation tickets in `.matrix/tickets/` with:
  - `priority: "critical"` for critical/high severity items
  - `priority: "high"` for major items
  - Full gate output attached as context in the ticket description
  - Reference to the original ticket that introduced the issue

### Step 2: Return to Phase 3

- Remediation tickets enter the Phase 3 (Jacking In) queue.
- Morpheus dispatches agents to fix the issues.
- Each fix follows the standard RARV cycle.
- Git checkpoint per fix: `fix(TICKET-{NNN}): {remediation description}`

### Step 3: Re-run Failed Gates

- After remediation, only the failed gates are re-run (not all three).
- Previously passed gates retain their pass status.
- New gate results overwrite the previous failure results.

### Step 4: Cycle Limit

- Maximum 3 remediation cycles per session.
- Each cycle includes: fix implementation + gate re-run.
- Cycle counter tracked in `session.json`.

### Step 5: Escalation (After 3 Failures)

If 3 remediation cycles are exhausted without all gates passing:

1. **Compile full report:**
   - All gate results from all cycles.
   - All remediation tickets and their outcomes.
   - Specific items that could not be resolved.

2. **Escalate to user:**
   - Present the report clearly.
   - Explain what was tried and why it failed.
   - Recommend specific manual interventions.
   - Ask the user whether to: retry with guidance, skip the failing gate, or abort the session.

---

## Gate Override Mechanism

The user can bypass a specific gate using `/neo gate override <gate>`. This is an escape hatch for situations where a gate is failing on a non-blocking issue or where the user has accepted the risk.

### Override Behavior

1. The override is recorded in `session.json` under `gate_overrides`:
   ```json
   {
     "gate_overrides": ["shannon"]
   }
   ```
2. When `quality-gate.sh` runs, it checks for overrides before executing each gate.
3. An overridden gate is marked as `overridden` (not `passed`) in the gate log.
4. A warning is logged in `.matrix/sentinels/gate-log.json`.
5. The override is recorded in episodic memory for future reference.

### Important

- Overrides should be rare. The system logs them prominently because skipping a quality gate is a conscious risk acceptance.
- Overridden gates are included in the session retrospective with a note.
- If multiple sessions override the same gate, the Trainman will flag this as a concerning pattern in cross-session analysis.
