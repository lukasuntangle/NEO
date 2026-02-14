# Neo Orchestrator Workflow

Complete phase-by-phase reference for the Neo Orchestrator multi-agent system.

```
                         THE NEO ORCHESTRATOR WORKFLOW
  ============================================================================

   [USER]                                                          [CODEBASE]
     |                                                                 |
     |  PRD                                                            |
     v                                                                 |
  PHASE 0: THE SOURCE                                                  |
     |  Validate PRD, confirm with user                                |
     v                                                                 |
  PHASE 1: RED PILL                                                    |
     |  Init .matrix/, copy PRD, load memory, git checkpoint           |
     |  DNA fingerprint, blackboard init, cost tracking init           |
     v                                                                 |
  PHASE 2: THE CONSTRUCT                                               |
     |  Oracle decomposes -> Architect specs -> Task graph -> Tickets   |
     |  Speculative forks for competing architectures                  |
     v                                                                 |
  PHASE 3: JACKING IN  <---------------------------------------------+
     |  Morpheus dispatches agents via agent loop harness              |
     |  Each agent: reserve files -> RARV cycle -> release -> commit   |
     |  Continuous testing (Mouse), warm handoffs, blackboard comms    |
     |  Skill-based assignment, cost-aware model selection             |
     v                                                                 |
  PHASE 4: BULLET TIME                                                 |
     |  Neo reviews holistically: imports, APIs, types                 |
     |  Blackboard review for unresolved issues                        |
     |  Issues found? ----YES----> Create fix tickets ----+            |
     |       |                                            |            |
     |      NO                                            |            |
     |  Optional: Merovingian chaos test (/neo chaos-test)|            |
     v                                                    |            |
  PHASE 5: SENTINELS                                      |            |
     |  Gate 1: Smith (blind review)                      |            |
     |  Gate 2: Trinity (security)                        |            |
     |  Gate 3: Shannon (dynamic pentest)                 |            |
     |  Gate 4: Switch + Mouse (tests)                    |            |
     |  Gate results posted to blackboard                 |            |
     |  Any gate fails? ----YES----> Remediation tickets -+            |
     |       |                       (max 3 cycles, then escalate)     |
     |      NO (all pass)                                              |
     v                                                                 |
  PHASE 6: ZION                                                        |
     |  Docs generated, memory consolidated, session archived          |
     |  Final cost report, skill tracker updates                       |
     v                                                                 |
   [DONE] -- Status report to user                            [DEPLOYED]

  ============================================================================
```

---

## Phase 0: THE SOURCE

**Purpose:** Receive and validate the Product Requirements Document (PRD) before any work begins.

**Actors:** Neo (orchestrator), User

**Steps:**

1. **Receive PRD** -- The user provides the PRD either as a file path (e.g., `./docs/prd.md`) or inline text pasted directly into the prompt.

2. **Validate PRD exists and has content:**
   - If a path is given, verify the file exists and is non-empty.
   - If inline, confirm the text contains substantive requirements (not just a title or placeholder).
   - If validation fails, ask the user to provide a valid PRD.

3. **Confirm with user before proceeding:**
   - Display a summary of what Neo understood from the PRD.
   - Ask the user to confirm: "Take the red pill and begin? (yes/no)"
   - Only proceed to Phase 1 on explicit confirmation.

**Outputs:** Validated PRD content, user confirmation.

**Failure mode:** If the user declines (blue pill), the session ends gracefully with no changes.

---

## Phase 1: RED PILL

**Purpose:** Initialize the Matrix workspace, persist the PRD, load any existing memory, and create a clean starting checkpoint.

**Actors:** Neo

**Steps:**

1. **Run init-matrix.sh** to create the `.matrix/` directory structure:
   ```
   .matrix/
   ├── source/          # PRD and original requirements
   ├── construct/       # Architecture, specs, task graph
   ├── tickets/         # Individual ticket JSON files
   ├── memory/          # 3-tier memory system
   │   ├── episodic/
   │   ├── semantic/
   │   └── procedural/
   ├── gate-results/    # Quality gate outputs
   ├── logs/            # Session logs
   └── session.json     # Current session metadata
   ```

2. **Copy PRD** to `.matrix/source/prd.md` so it is preserved within the Matrix workspace.

3. **Load existing memory** from `.matrix/memory/` if it exists from previous sessions:
   - Load procedural memory first (most actionable).
   - Load semantic memory second (project context).
   - Load episodic memory last (recent history).
   - If no memory exists, this is a fresh project -- proceed with empty memory.

4. **Generate DNA fingerprint:**
   - Analyze the existing codebase for naming conventions, formatting patterns, and idioms.
   - Output: `.matrix/construct/dna-profile.json` -- used by all agents to match existing style.

5. **Initialize blackboard:**
   - Create `.matrix/blackboard.jsonl` as the shared append-only inter-agent communication log.
   - Post initial `SESSION_START` event with session metadata.

6. **Initialize cost tracking:**
   - Create `.matrix/costs.json` to track token usage and costs per agent and per phase.
   - Set budget limits from config if configured.

7. **Create initial git checkpoint:**
   - Stage all `.matrix/` initialization files.
   - Commit with message: `red-pill: session initialized`
   - Tag the commit: `red-pill-{timestamp}` (e.g., `red-pill-20250115-143022`)

8. **Initialize session.json:**
   ```json
   {
     "session_id": "uuid-v4",
     "started_at": "ISO-8601 timestamp",
     "phase": "red-pill",
     "prd_path": ".matrix/source/prd.md",
     "memory_loaded": true,
     "checkpoints": ["red-pill-{timestamp}"]
   }
   ```

**Outputs:** Initialized `.matrix/` directory, session.json, DNA profile, blackboard, cost ledger, git checkpoint with tag.

**Failure mode:** If `init-matrix.sh` fails, report the error and do not proceed.

---

## Phase 2: THE CONSTRUCT

**Purpose:** Decompose the PRD into architecture, technical specifications, and a dependency-aware task graph. This is the design phase -- no implementation code is written.

**Actors:** Oracle (opus), Architect (sonnet), ticket-manager.py

**Steps:**

1. **Spawn Oracle to decompose the PRD:**
   - Oracle reads `.matrix/source/prd.md` and any loaded memory.
   - Oracle checks team templates (`references/team-templates.md`) for pattern matches in the PRD and uses them to accelerate ticket creation.
   - Identifies: components, services, data models, external integrations.
   - Creates a dependency graph showing relationships between components.
   - Output: `.matrix/construct/architecture.md`
     - System overview
     - Component list with descriptions
     - Dependency graph (which components depend on which)
     - Technology decisions with rationale

2. **Spawn Architect to create technical specifications:**
   - Architect reads the Oracle's architecture document.
   - Architect creates ADRs for significant decisions -> `.matrix/construct/adrs/ADR-{NNN}.md`
   - Produces:
     - **Database schema** -> `.matrix/construct/schema.sql`
       - Table definitions, indexes, constraints, relationships
     - **OpenAPI specification** -> `.matrix/construct/openapi.yaml`
       - All endpoints, request/response schemas, auth requirements
     - **Technical blueprint** embedded in architecture.md updates
       - File structure, module boundaries, shared types

3. **Oracle reviews Architect's output:**
   - Cross-references specs against PRD for completeness.
   - Validates consistency between schema and API spec.
   - Creates the task graph -> `.matrix/construct/task-graph.json`:
     ```json
     {
       "tasks": [
         {
           "id": "TICKET-001",
           "title": "...",
           "dependencies": [],
           "parallel_group": 1,
           "estimated_complexity": "medium",
           "suggested_agent": "dozer",
           "suggested_model": "sonnet"
         }
       ],
       "parallel_groups": [
         { "group": 1, "tasks": ["TICKET-001", "TICKET-002"] },
         { "group": 2, "tasks": ["TICKET-003"], "depends_on_group": 1 }
       ]
     }
     ```

4. **ticket-manager.py creates tickets from the task graph:**
   - Generates individual `TICKET-{NNN}.json` files in `.matrix/tickets/`.
   - Creates/updates `.matrix/tickets/index.json`.
   - Sets initial status to `pending` for all tickets.
   - Populates `dependencies`, `blocks`, `blocked_by` fields.
   - **If dry-run mode was set**, display the full plan (ticket graph, agent assignments, ADRs, architecture summary, estimated agent count) and stop.

5. **Git checkpoint:**
   - Commit message: `construct: architecture and tickets created`
   - All `.matrix/construct/` and `.matrix/tickets/` files staged.

**Outputs:** architecture.md, schema.sql, openapi.yaml, task-graph.json, individual ticket files, ticket index.

**Failure mode:** If Oracle or Architect produce incomplete output, Neo requests a retry with specific feedback.

---

## Phase 3: JACKING IN

**Purpose:** Execute the implementation plan by dispatching agents to work on tickets in dependency-aware parallel batches.

**Actors:** Morpheus (team lead), various implementation agents (Dozer, Niobe, Tank, Keymaker, etc.)

**Steps:**

0. **Check for pause flag:**
   - Check for `/neo pause` flag — if set, stop after completing current ticket batch.

1. **Morpheus reads ticket index and builds execution plan:**
   - Load `.matrix/tickets/index.json` and all ticket files.
   - Check for manual overrides: `/neo skip`, `/neo assign`, `/neo retry`.
   - Identify tickets with no unmet dependencies (ready to execute).
   - Group ready tickets into parallelizable batches.
   - Assign agents based on ticket `suggested_agent` or override by complexity.

2. **Agent loop harness replaces one-shot spawning:**
   - Each agent runs in an iterative loop: execute, check results, receive feedback, re-execute if needed.
   - The harness manages retries, feedback injection, and convergence detection.
   - Continuous test watcher (Mouse) runs in the background, reporting regressions in real time.

3. **Skill-based agent assignment and cost-aware model selection:**
   - Morpheus assigns agents based on skill match (not just `suggested_agent`).
   - Model tier may be adjusted based on remaining budget tracked in `.matrix/costs.json`.

4. **For each parallelizable batch:**

   a. **Reserve files for each agent:**
      - Update `.matrix/tickets/reservations.json` with file locks.
      - If a file is already reserved, the ticket waits or is re-batched.
      - No two agents may write to the same file simultaneously.

   b. **Spawn agents with appropriate model tier:**
      - `bash scripts/spawn-agent.sh <agent-name> <model> "<task-description>"`
      - Agent receives: ticket JSON, relevant architecture docs, file reservations.
      - Agent has access only to its reserved files and read-only access to others.

   c. **Each agent follows the RARV cycle:**
      - **Research:** Read relevant existing code, specs, and memory.
      - **Analyze:** Plan the implementation approach.
      - **Reflect:** Self-review the plan before writing code.
      - **Verify:** After implementation, verify against acceptance criteria.

   d. **Warm handoffs between dependent tasks:**
      - When an agent completes work that another agent depends on, a structured handoff document is created.
      - The handoff includes decisions made, rationale, open questions, and context the next agent needs.
      - Handoffs are posted to the blackboard for traceability.

   e. **Blackboard communication throughout:**
      - Agents post status updates, warnings, and requests to `.matrix/blackboard.jsonl`.
      - Other agents and the orchestrator read the blackboard to coordinate.

   f. **On completion:**
      - Release file reservations in `reservations.json`.
      - Update ticket status to `review`.
      - Record RARV notes in the ticket's `rarv` field.
      - Git checkpoints are now tagged with ticket ID for per-ticket rollback capability.
      - Git checkpoint: `feat(TICKET-{NNN}): {ticket title}`

5. **Sequential tasks wait for dependencies:**
   - When a batch completes, Morpheus re-evaluates the ticket index.
   - Newly unblocked tickets enter the next batch.
   - Continue until all tickets are in `review` or `completed` status.

**Outputs:** Implemented code for all tickets, updated ticket statuses, git checkpoints per task.

**Failure mode:** If an agent fails a ticket, status is set to `failed`, and it re-enters the queue as `pending` with failure context attached.

---

## Phase 4: BULLET TIME

**Purpose:** Holistic integration review. Neo slows down to examine the full picture -- do all the pieces fit together?

**Actors:** Neo (orchestrator)

**Steps:**

1. **Cross-task integration check:**
   - Verify all imports resolve correctly across modules.
   - Confirm API contracts match between frontend and backend.
   - Validate type definitions are consistent across files.
   - Check that shared utilities are used consistently.
   - Ensure database schema matches ORM/query usage.

2. **Run linting and basic quality checks:**
   - Execute project linter (ESLint, Prettier, etc.) if configured.
   - Check for TypeScript compilation errors.
   - Identify any obvious code smells (duplicated logic, dead code).

3. **Persona drift check:**
   - Verify agents stayed in character during their work (spawn-agent.sh logs DRIFT_WARNING if markers are low).

4. **Blackboard review for unresolved issues:**
   - Scan `.matrix/blackboard.jsonl` for any unresolved warnings, agent requests, or anomalies posted during Phase 3.
   - Surface unresolved items as additional integration concerns.

5. **Optional Merovingian chaos test:**
   - If invoked via `/neo chaos-test`, spawn the Merovingian to adversarially test the orchestrator itself.
   - Tests rollback integrity, file reservation conflicts, ticket state machine transitions, agent failure handling, and pipeline integrity.
   - Output: structured chaos report posted to the blackboard.

6. **Decision point:**
   - **No issues found:** Proceed to Phase 5 (Sentinels).
   - **Issues found:** Create fix tickets with detailed descriptions of the integration problems. These tickets go back to Phase 3 for implementation. The fix tickets reference the original tickets that produced the issue.

**Outputs:** Integration report, optional fix tickets.

**Failure mode:** If integration issues are severe (fundamental architecture mismatch), escalate to user for guidance.

---

## Phase 5: SENTINELS

**Purpose:** Four independent quality gates must all pass before the code can reach Zion. Each gate is designed to catch different categories of problems.

**Actors:** Smith (opus), Trinity (sonnet), Shannon (sonnet), Switch (sonnet), Mouse (haiku)

**Gates:**

### Gate 1: Agent Smith -- Blind Code Review
- `blind-review-prep.sh` strips author info, commit messages, and file paths outside the diff.
- Smith receives only the unified diff content and the project conventions file.
- Must find 3+ issues OR write a >100 word justification for a clean pass.
- If Smith finds 0 issues, a second independent Smith clone is spawned.
- If both find 0 issues: pass (genuinely clean code).
- Output: `.matrix/gate-results/smith-review.json`

### Gate 2: Trinity -- Security Audit
- OWASP Top 10 check, hardcoded secrets scan, injection vulnerability analysis.
- Severity levels: critical, high, medium, low.
- Any critical finding = automatic gate failure.
- Output: `.matrix/gate-results/trinity-security.json`

### Gate 3: Shannon -- Dynamic Security Testing
- Shannon starts the application in dev/test mode.
- Actively probes running endpoints for vulnerabilities (SSRF, auth bypass, injection, IDOR).
- Generates PoC (proof of concept) for every finding.
- Cross-references Trinity's static findings — confirms real vulnerabilities and marks false positives.
- Output: `.matrix/sentinels/shannon-pentest.json`

### Gate 4: Switch + Mouse -- Test Coverage
- Switch writes missing tests.
- Mouse runs the full test suite and parses output.
- Coverage threshold: 80% minimum (configurable in config.json).
- Must cover: happy paths, error paths, edge cases, boundary conditions.
- Output: `.matrix/gate-results/switch-tests.json`, `.matrix/gate-results/mouse-coverage.json`

### Remediation Flow
- If any gate fails: create remediation tickets with gate output as context.
- Tickets re-enter Phase 3 (Jacking In) for implementation.
- Maximum 3 remediation cycles allowed.
- After remediation, only the failed gates are re-run (not all four).
- After 3 failures: escalate to user with full gate logs and a summary of unresolved issues.
- `/neo gate override <gate>` — allows bypassing a gate with a warning logged.

**Outputs:** Gate result JSON files, pass/fail determination, optional remediation tickets.

**Failure mode:** After 3 remediation cycles, the system stops and provides the user with a detailed report.

---

## Phase 6: ZION

**Purpose:** All quality gates have passed. Finalize the session: generate documentation, consolidate memory, archive everything.

**Actors:** Sati (haiku), Trainman (haiku), Neo

**Steps:**

1. **All gates passed** -- confirm final status.

2. **Sati generates documentation:**
   - README updates or creation.
   - API documentation from OpenAPI spec.
   - Inline code documentation where missing.
   - Architecture decision records (ADRs) for key decisions.

3. **Trainman consolidates memory:**
   - Compress episodic memory: extract key decisions and outcomes, discard verbose logs.
   - Update semantic memory: new knowledge about the project (tech stack, conventions, structure).
   - Update procedural memory: record which strategies worked, update confidence scores.
   - Produces a session retrospective with cross-session analytics (agent performance, gate effectiveness, remediation cycle analysis).

4. **Final git checkpoint:**
   - Commit message: `zion: all gates passed, session complete`
   - Tag: `zion-{timestamp}`

5. **Final cost report:**
   - Summarize total token usage and costs from `.matrix/costs.json`.
   - Break down by agent, by phase, and by model tier.
   - Include in the session retrospective and user-facing status report.

6. **Skill tracker updates:**
   - Record agent performance metrics (tickets completed, gate pass rates, remediation counts).
   - Update skill profiles so future sessions benefit from improved agent assignment.

7. **Session archived:**
   - Update `session.json` with `completed_at`, final phase, summary.
   - Move session log to `.matrix/memory/episodic/session-{id}.json`.

8. **Status report to user:**
   - Summary of what was built.
   - Number of tickets completed.
   - Gate results summary.
   - Any notes or recommendations for future work.
   - Links to key files created/modified.

**Outputs:** Documentation, consolidated memory, final cost report, skill tracker updates, final git tag, session archive, user-facing status report.

**Failure mode:** Phase 6 should not fail. If documentation generation fails, the session is still considered successful -- the code is done.

---

## Quick Reference: Phase Transitions

| From | To | Trigger |
|------|----|---------|
| Phase 0 | Phase 1 | User confirms (red pill) |
| Phase 0 | Exit | User declines (blue pill) |
| Phase 1 | Phase 2 | .matrix/ initialized successfully |
| Phase 2 | Phase 3 | All tickets created |
| Phase 3 | Phase 4 | All tickets in review/completed |
| Phase 4 | Phase 3 | Integration issues found (fix tickets) |
| Phase 4 | Phase 5 | No integration issues |
| Phase 5 | Phase 3 | Gate failure (remediation tickets, max 3x) |
| Phase 5 | Phase 6 | All gates pass |
| Phase 5 | Escalate | 3 remediation cycles exhausted |
| Phase 6 | Done | Session archived |
