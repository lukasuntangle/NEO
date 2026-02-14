# Memory System

The Neo Orchestrator uses a 3-tier memory system that persists knowledge across sessions, enabling the system to learn from past experience and improve over time.

---

## Tier 1: Episodic Memory

**Location:** `.matrix/memory/episodic/`
**Purpose:** Per-session logs capturing what happened, what was decided, and what the outcomes were.

### Storage

Each session produces a file: `session-{id}.json`

### Schema

```json
{
  "session_id": "uuid-v4",
  "started_at": "ISO-8601",
  "completed_at": "ISO-8601",
  "phase_reached": "zion",
  "prd_summary": "Brief description of what was built",
  "entries": [
    {
      "type": "decision",
      "timestamp": "ISO-8601",
      "content": "Chose PostgreSQL over MongoDB for relational data model",
      "context": "PRD requires complex joins between users, orders, and products",
      "outcome": "success"
    },
    {
      "type": "error",
      "timestamp": "ISO-8601",
      "content": "TypeScript compilation failed due to circular dependency",
      "context": "auth.ts imported from users.ts which imported from auth.ts",
      "outcome": "resolved",
      "resolution": "Extracted shared types into types/auth.ts"
    },
    {
      "type": "strategy",
      "timestamp": "ISO-8601",
      "content": "Parallelized frontend and backend implementation",
      "context": "API contract defined in OpenAPI spec, both sides could work independently",
      "outcome": "success"
    },
    {
      "type": "gate_result",
      "timestamp": "ISO-8601",
      "content": "Smith found 4 issues in auth module, 2 critical",
      "context": "Missing input validation on login endpoint, SQL injection risk",
      "outcome": "remediated",
      "resolution": "Added Zod validation and parameterized queries"
    }
  ],
  "summary": {
    "tickets_completed": 12,
    "remediation_cycles": 1,
    "total_agents_spawned": 18,
    "key_learnings": [
      "Auth module needed extra review attention",
      "Frontend/backend parallel execution worked well with shared types"
    ]
  }
}
```

### Entry Types

| Type | When Created | Contains |
|------|-------------|----------|
| `decision` | When a significant choice is made | What was chosen, why, and whether it worked |
| `error` | When an error occurs | What broke, context, and how it was resolved |
| `strategy` | When a strategy is applied | What approach was used and its outcome |
| `gate_result` | When a quality gate completes | Gate findings and remediation actions |
| `observation` | When something notable is observed | Patterns, anomalies, insights |

### Retention Policy

- **Last 5 sessions:** Kept in full detail (all entries preserved).
- **Older sessions:** Compressed by Trainman during consolidation.
- **Compression process:**
  1. Extract key decisions and their outcomes.
  2. Extract error patterns and resolutions.
  3. Extract strategy outcomes (success/failure).
  4. Discard verbose logs, intermediate steps, and redundant entries.
  5. Compressed sessions stored as `session-{id}-compressed.json`.

---

## Tier 2: Semantic Memory

**Location:** `.matrix/memory/semantic/`
**Purpose:** Accumulated knowledge about the project that grows over time.

### Storage

Single file: `project-knowledge.json`

### Schema

```json
{
  "project_name": "my-saas-app",
  "last_updated": "ISO-8601",
  "sessions_contributing": 5,

  "tech_stack": {
    "language": "TypeScript",
    "runtime": "Node.js 20",
    "framework": "Next.js 14",
    "database": "PostgreSQL 16",
    "orm": "Drizzle",
    "testing": "Vitest",
    "styling": "Tailwind CSS",
    "deployment": "Vercel",
    "package_manager": "npm"
  },

  "conventions": {
    "file_naming": "kebab-case for files, PascalCase for components",
    "import_style": "absolute imports via @/ alias",
    "error_handling": "Custom AppError class, centralized error middleware",
    "validation": "Zod schemas co-located with route handlers",
    "state_management": "React Server Components + minimal client state",
    "immutability": "Spread operator for all object updates, no mutation"
  },

  "structure": {
    "src/app/": "Next.js app router pages and layouts",
    "src/components/": "Shared React components",
    "src/lib/": "Utility functions and shared logic",
    "src/api/": "API route handlers",
    "src/db/": "Database schema, migrations, queries",
    "src/types/": "Shared TypeScript type definitions",
    "src/__tests__/": "Test files mirroring src/ structure"
  },

  "endpoints": [
    {
      "method": "POST",
      "path": "/api/auth/login",
      "description": "User login, returns JWT",
      "auth_required": false
    },
    {
      "method": "GET",
      "path": "/api/users/:id",
      "description": "Get user profile",
      "auth_required": true
    }
  ],

  "known_issues": [
    {
      "description": "Circular dependency risk between auth and user modules",
      "workaround": "Use shared types in src/types/ to break cycles",
      "discovered_in": "session-abc-123",
      "status": "mitigated"
    }
  ],

  "patterns": {
    "auth": "JWT with refresh tokens, stored in httpOnly cookies",
    "api_responses": "Consistent { data, error, meta } envelope",
    "pagination": "Cursor-based for lists, offset for admin views"
  }
}
```

### Update Rules

- Updated by Trainman at the end of every session.
- **Additive by default:** New knowledge is added, existing knowledge is preserved.
- **Overwrite on conflict:** If new information contradicts existing, the newer version wins (with a note in `known_issues`).
- **Endpoints are merged:** New endpoints added, existing endpoints updated if the spec changed.
- **Conventions are stable:** Only updated if the project explicitly changes its conventions.

---

## Tier 3: Procedural Memory

**Location:** `.matrix/memory/procedural/`
**Purpose:** Learned strategies with confidence scores, enabling the system to favor approaches that have worked in the past.

### Storage

Single file: `strategies.json`

### Schema

```json
{
  "last_updated": "ISO-8601",
  "strategies": [
    {
      "id": "strat-001",
      "description": "Parallel frontend/backend implementation with shared type definitions",
      "context": "When API contract is defined upfront (OpenAPI spec exists)",
      "preconditions": ["OpenAPI spec available", "Shared types directory exists"],
      "confidence": 0.85,
      "successes": 6,
      "failures": 1,
      "last_used": "ISO-8601",
      "notes": "Failed once when API spec was incomplete -- ensure spec is fully reviewed before parallelizing"
    },
    {
      "id": "strat-002",
      "description": "Extract shared types before implementing modules that depend on each other",
      "context": "When multiple modules reference the same data models",
      "preconditions": ["Dependency graph shows shared models"],
      "confidence": 0.92,
      "successes": 11,
      "failures": 1,
      "last_used": "ISO-8601",
      "notes": "Almost always effective. The one failure was due to a model that changed mid-implementation."
    },
    {
      "id": "strat-003",
      "description": "Run security gate before code review gate",
      "context": "When dealing with auth-heavy features",
      "preconditions": ["Feature involves authentication or authorization"],
      "confidence": 0.45,
      "successes": 3,
      "failures": 4,
      "last_used": "ISO-8601",
      "notes": "Mixed results. Security issues sometimes require architectural changes that invalidate the code review."
    }
  ],
  "archived": [
    {
      "id": "strat-old-001",
      "description": "Implement all database models before any API endpoints",
      "confidence": 0.22,
      "archived_reason": "Confidence dropped below 0.3 threshold",
      "archived_at": "ISO-8601"
    }
  ]
}
```

### Confidence Scoring

- **Formula:** `confidence = successes / (successes + failures)`
- **Minimum confidence:** 0.1 (never drops to zero, to allow recovery)
- **Maximum confidence:** 0.95 (never reaches 1.0, to prevent overconfidence)
- **New strategies start at:** 0.5 (neutral -- neither proven nor disproven)
- **Archive threshold:** Strategies below 0.3 confidence are moved to the `archived` array
- **Archived strategies** can be reinstated if conditions change (manually or by user request)

### Strategy Lifecycle

1. **Creation:** A new approach is tried during a session. Trainman records it with `confidence: 0.5, successes: 1, failures: 0` if it worked, or `confidence: 0.5, successes: 0, failures: 1` if it failed.
2. **Growth:** Each subsequent session where the strategy is used updates the counters.
3. **Maturity:** High-confidence strategies (>0.7) are prioritized by Oracle when planning.
4. **Decline:** Strategies that start failing drop in confidence.
5. **Archival:** Below 0.3 confidence, the strategy is archived with a reason.

### Strategy Selection

When Oracle is planning and multiple approaches are viable:
1. Filter strategies by matching `context` and `preconditions`.
2. Sort by confidence (highest first).
3. Prefer strategies with `confidence > 0.7`.
4. Avoid strategies with `confidence < 0.4` unless no alternatives exist.
5. If no strategies match, try a new approach (which becomes a new strategy entry).

---

## Memory Lifecycle

### 1. Session Start -- Load All Memory

When Phase 1 (Red Pill) initializes:

```
Load order (by priority):
  1. Procedural memory  (strategies.json)     -- Most actionable
  2. Semantic memory     (project-knowledge.json)  -- Project context
  3. Episodic memory     (last 5 session files)     -- Recent history
```

If context window is limited, truncate in reverse order (drop oldest episodic first, then semantic details, never drop procedural).

### 2. During Session -- Append to Episodic

Throughout the session, entries are appended to the current session's episodic log:
- Every significant decision is logged.
- Every error and its resolution is logged.
- Every strategy application and its outcome is logged.
- Every gate result is logged.

This happens in real-time as the session progresses.

### 3. Session End -- Trainman Consolidates

When Phase 6 (Zion) completes, Trainman performs consolidation:

**Episodic compression:**
- Current session is saved in full.
- If total sessions > 5, compress the 6th oldest:
  - Keep: decisions, error resolutions, strategy outcomes, gate results.
  - Discard: verbose logs, intermediate steps, redundant observations.
  - Save as `session-{id}-compressed.json`.

**Semantic update:**
- Scan current session for new knowledge:
  - New endpoints discovered -> add to endpoints list.
  - New conventions established -> add to conventions.
  - New issues discovered -> add to known_issues.
  - Tech stack changes -> update tech_stack.
  - File structure changes -> update structure.
- Merge into `project-knowledge.json`.

**Procedural update:**
- For each strategy used in the session:
  - If it succeeded: `successes += 1`, recalculate confidence.
  - If it failed: `failures += 1`, recalculate confidence.
  - Update `last_used` timestamp.
- For new strategies tried:
  - Create new entry with initial confidence of 0.5.
- Check for strategies below 0.3: archive them.

---

## Memory Loading Priority

When the context window is constrained and not all memory can be loaded, follow this priority order:

| Priority | Tier | Rationale |
|----------|------|-----------|
| 1 (highest) | Procedural | Most actionable -- directly influences planning decisions |
| 2 | Semantic | Project context -- essential for correct implementation |
| 3 (lowest) | Episodic | Historical -- useful but not critical for current work |

Within episodic memory, load most recent sessions first. Compressed sessions are smaller and can often fit when full sessions cannot.

### Context Budget Guidelines

- **Full context available:** Load everything.
- **75% budget:** Load all procedural + all semantic + last 3 episodic sessions.
- **50% budget:** Load all procedural + semantic (skip endpoints list) + last 1 episodic session (compressed).
- **25% budget:** Load all procedural + semantic tech_stack and conventions only.
- **Minimal:** Load procedural strategies with confidence > 0.7 only.
