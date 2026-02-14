# Ticket Schema and Lifecycle

Complete reference for the Neo Orchestrator ticket system, including format, status flow, indexing, and file reservations.

---

## Ticket Format

Each ticket is stored as an individual JSON file: `.matrix/tickets/TICKET-{NNN}.json`

Ticket IDs are zero-padded to 3 digits (e.g., `TICKET-001`, `TICKET-012`, `TICKET-100`).

### Full Schema

```json
{
  "id": "TICKET-001",
  "title": "Implement user authentication endpoint",
  "description": "Create POST /api/auth/login endpoint per OpenAPI spec. Accepts email and password, validates credentials against the database, and returns a signed JWT on success. Must handle invalid credentials, missing fields, and rate limiting.",
  "status": "pending",
  "priority": "high",
  "agent": "dozer",
  "model": "sonnet",
  "dependencies": ["TICKET-000"],
  "blocked_by": [],
  "blocks": ["TICKET-003", "TICKET-004"],
  "files": ["src/api/auth.ts", "src/middleware/auth.ts"],
  "acceptance_criteria": [
    "Endpoint accepts email + password",
    "Returns JWT on success",
    "Returns 401 on failure",
    "Input validated with Zod",
    "Rate limited to 5 attempts per minute per IP"
  ],
  "rarv": {
    "research": null,
    "analyze": null,
    "reflect": null,
    "verify": null
  },
  "context": null,
  "remediation_of": null,
  "attempt": 1,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z",
  "started_at": null,
  "completed_at": null,
  "git_checkpoint": null
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique ticket identifier, format `TICKET-{NNN}` |
| `title` | string | Short descriptive title (under 80 characters) |
| `description` | string | Detailed description of the work to be done |
| `status` | string | Current ticket status (see Status Flow below) |
| `priority` | string | Priority level: `critical`, `high`, `medium`, `low` |
| `agent` | string | Assigned agent name (e.g., `dozer`, `niobe`, `tank`) |
| `model` | string | Model tier for the agent: `opus`, `sonnet`, `haiku` |
| `dependencies` | string[] | Ticket IDs that must complete before this one starts |
| `blocked_by` | string[] | Ticket IDs currently blocking this ticket (computed) |
| `blocks` | string[] | Ticket IDs that depend on this ticket |
| `files` | string[] | Files this ticket will create or modify |
| `acceptance_criteria` | string[] | Specific criteria for the ticket to be considered done |
| `rarv` | object | RARV cycle notes filled in by the assigned agent |
| `context` | string/null | Additional context (e.g., gate failure details for remediation) |
| `remediation_of` | string/null | If this is a fix ticket, the original ticket ID |
| `attempt` | number | Attempt number (incremented on retry) |
| `created_at` | string | ISO-8601 timestamp of ticket creation |
| `updated_at` | string | ISO-8601 timestamp of last status change |
| `started_at` | string/null | ISO-8601 timestamp of when work began |
| `completed_at` | string/null | ISO-8601 timestamp of completion |
| `git_checkpoint` | string/null | Git commit hash for the completed work |

### RARV Fields

When an agent works on a ticket, it populates the `rarv` object:

```json
{
  "rarv": {
    "research": "Read existing auth patterns in the codebase. Found JWT utilities in src/lib/jwt.ts. Database user model in src/db/schema/users.ts.",
    "analyze": "Need to: 1) Create route handler, 2) Add Zod validation schema, 3) Query user by email, 4) Compare hashed password, 5) Sign and return JWT.",
    "reflect": "Considered session-based auth but JWT is specified in the architecture doc. Should use bcrypt for password comparison, not plain text.",
    "verify": "All 5 acceptance criteria met. Tested with valid credentials (200 + JWT), invalid password (401), missing fields (400), non-existent email (401)."
  }
}
```

---

## Status Flow

### Normal Flow

```
pending ──> in_progress ──> review ──> completed
```

1. **pending**: Ticket is created and waiting for an agent to pick it up.
2. **in_progress**: An agent has been assigned and is actively working on it.
3. **review**: Agent has completed the RARV cycle. Work is done but not yet validated by gates.
4. **completed**: Work has passed all quality gates.

### Failure/Retry Flow

```
pending ──> in_progress ──> failed ──> pending (retry)
```

1. **pending**: Original ticket.
2. **in_progress**: Agent starts working.
3. **failed**: Agent could not complete the work (error, timeout, RARV verification failed).
4. **pending**: Ticket re-enters the queue with `attempt` incremented and failure context added.

### Blocked Flow

```
(any status) ──> blocked
blocked ──> pending (when dependency resolves)
```

A ticket becomes `blocked` when one of its dependencies is not yet `completed`. The `blocked_by` field is dynamically computed based on which dependencies are still incomplete.

### Status Transition Rules

| From | To | Trigger |
|------|----|---------|
| `pending` | `in_progress` | Morpheus assigns an agent |
| `pending` | `blocked` | Dependency not met |
| `in_progress` | `review` | Agent completes RARV cycle |
| `in_progress` | `failed` | Agent encounters unrecoverable error |
| `review` | `completed` | All quality gates pass |
| `failed` | `pending` | Ticket re-queued for retry |
| `blocked` | `pending` | All dependencies now completed |

### Status Colors (for display)

| Status | Indicator |
|--------|-----------|
| `pending` | [WAIT] |
| `in_progress` | [WORK] |
| `review` | [REVW] |
| `completed` | [DONE] |
| `failed` | [FAIL] |
| `blocked` | [BLKD] |

---

## Ticket Index

The ticket index provides a quick overview of all tickets and their statuses.

**Location:** `.matrix/tickets/index.json`

### Schema

```json
{
  "total": 12,
  "by_status": {
    "pending": 5,
    "in_progress": 2,
    "review": 1,
    "completed": 4,
    "failed": 0,
    "blocked": 0
  },
  "by_priority": {
    "critical": 1,
    "high": 5,
    "medium": 4,
    "low": 2
  },
  "tickets": [
    "TICKET-001",
    "TICKET-002",
    "TICKET-003",
    "TICKET-004",
    "TICKET-005",
    "TICKET-006",
    "TICKET-007",
    "TICKET-008",
    "TICKET-009",
    "TICKET-010",
    "TICKET-011",
    "TICKET-012"
  ],
  "execution_order": [
    { "group": 1, "tickets": ["TICKET-001", "TICKET-002", "TICKET-005"] },
    { "group": 2, "tickets": ["TICKET-003", "TICKET-004", "TICKET-006"] },
    { "group": 3, "tickets": ["TICKET-007", "TICKET-008", "TICKET-009"] },
    { "group": 4, "tickets": ["TICKET-010", "TICKET-011", "TICKET-012"] }
  ],
  "last_updated": "2025-01-01T00:00:00Z"
}
```

### Index Maintenance

The index is updated by `ticket-manager.py` whenever:
- A new ticket is created.
- A ticket status changes.
- Tickets are re-prioritized or re-ordered.

The `execution_order` field reflects the parallelization plan from the task graph. Tickets within the same group can run simultaneously. Groups execute sequentially (group 2 waits for all of group 1 to complete).

---

## File Reservations

Prevents multiple agents from writing to the same file simultaneously.

**Location:** `.matrix/tickets/reservations.json`

### Schema

```json
{
  "reservations": {
    "src/api/auth.ts": {
      "ticket": "TICKET-001",
      "agent": "dozer",
      "reserved_at": "2025-01-01T10:00:00Z"
    },
    "src/components/Login.tsx": {
      "ticket": "TICKET-002",
      "agent": "niobe",
      "reserved_at": "2025-01-01T10:00:00Z"
    },
    "src/middleware/auth.ts": {
      "ticket": "TICKET-001",
      "agent": "dozer",
      "reserved_at": "2025-01-01T10:00:00Z"
    }
  }
}
```

### Reservation Rules

1. **Before an agent starts:** All files listed in the ticket's `files` array must be reserved for that ticket.
2. **If a file is already reserved:** The ticket cannot start. It either waits for the reservation to be released or is moved to the next batch.
3. **On ticket completion:** All reservations for that ticket are released immediately.
4. **On ticket failure:** Reservations are released so another agent (or retry) can claim them.
5. **Stale reservations:** If a reservation is older than 30 minutes without a corresponding `in_progress` ticket, it is considered stale and can be forcibly released.

### Read Access

File reservations only apply to **write** access. Any agent can **read** any file at any time, regardless of reservations. This allows agents to reference each other's work-in-progress for context.

---

## Priority Levels

| Priority | Definition | Examples | Scheduling Impact |
|----------|-----------|----------|-------------------|
| `critical` | Blocks other work or addresses security issues | Security vulnerability fix, shared type definitions needed by 5+ tickets | Scheduled first, interrupts current batch if needed |
| `high` | Core functionality that the product cannot ship without | Auth endpoints, primary CRUD operations, core business logic | Scheduled in early batches |
| `medium` | Important but not blocking other work | Secondary features, improved error messages, pagination | Scheduled after high-priority work |
| `low` | Nice-to-have, polish, documentation | Code comments, minor UI improvements, performance optimizations | Scheduled last, may be deferred |

### Priority Escalation

Tickets can be escalated in priority during a session:
- A `medium` ticket blocking 3+ other tickets may be escalated to `high`.
- A `low` ticket that a gate failure revealed as important may be escalated to `critical`.
- Escalation is logged in episodic memory.

---

## Remediation Tickets

When a quality gate fails, remediation tickets are created with special fields:

```json
{
  "id": "TICKET-013",
  "title": "Fix SQL injection in user query",
  "description": "Trinity security gate found SQL injection vulnerability in src/api/users.ts line 23. User input is directly concatenated into SQL query string.",
  "status": "pending",
  "priority": "critical",
  "agent": "dozer",
  "model": "sonnet",
  "dependencies": [],
  "blocked_by": [],
  "blocks": [],
  "files": ["src/api/users.ts"],
  "acceptance_criteria": [
    "All database queries use parameterized queries",
    "No string concatenation in SQL statements",
    "Trinity re-scan passes with 0 critical findings"
  ],
  "rarv": {
    "research": null,
    "analyze": null,
    "reflect": null,
    "verify": null
  },
  "context": "Gate failure: trinity-security. Finding SEC-001 (critical). Evidence: const query = `SELECT * FROM users WHERE id = ${req.params.id}`",
  "remediation_of": "TICKET-003",
  "attempt": 1,
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:00:00Z",
  "started_at": null,
  "completed_at": null,
  "git_checkpoint": null
}
```

Key differences from regular tickets:
- `remediation_of` references the original ticket that introduced the issue.
- `context` contains the gate failure details.
- `priority` is typically `critical` or `high` for gate failures.
- `acceptance_criteria` includes passing the specific gate check that failed.
