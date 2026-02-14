# Neo Orchestrator — The Matrix Multi-Agent Skill

---
triggers:
  - /neo
  - /matrix
  - /red-pill
description: "Fully autonomous multi-agent orchestrator. Hand it a PRD, walk away, come back to a working product."
---

## Overview

Neo Orchestrator is a fully autonomous Claude Code skill that combines spec-first development, RARV self-verification cycles, quality gates, memory systems, and ticket-based multi-agent coordination — all themed after The Matrix.

**Neo** is the orchestrator. Agents are Matrix characters. The codebase is "The Matrix." Taking the red pill starts the build. Sentinels enforce quality. Zion is the deployed product.

## Usage

```
/neo <path-to-prd>           # Start a full build from a PRD
/neo resume                   # Resume an interrupted session
/neo status                   # Show current session status
/neo dry-run <path-to-prd>   # Plan without executing (Phases 0-2 only)
/neo rollback <ticket-id>     # Rollback a specific ticket's changes
/neo rollback <tag>           # Rollback to a git checkpoint tag
/neo pause                    # Pause after current ticket completes
/neo skip <ticket-id>         # Skip a ticket (mark as skipped)
/neo retry <ticket-id>        # Force re-run a failed ticket
/neo gate override <gate>     # Bypass a sentinel gate (with warning)
/neo assign <ticket-id> <agent> # Manually assign a ticket to an agent
```

## Agent Roster

| Tier | Agent | Character | Role | Model |
|------|-------|-----------|------|-------|
| Judgment | Orchestrator | **Neo** | Main loop, RARV cycle, delegation | opus |
| Judgment | Planner | **The Oracle** | Architecture, PRD decomposition, OpenAPI spec | opus |
| Judgment | Reviewer | **Agent Smith** | Blind code review, anti-sycophancy | opus |
| Implementation | Team Lead | **Morpheus** | Task dispatch, file reservation, parallel coordination | sonnet |
| Implementation | Static Security | **Trinity** | OWASP audit, secrets scanning, auth review | sonnet |
| Implementation | Dynamic Security | **Shannon** | Active pentesting, PoC generation, exploit verification | sonnet |
| Implementation | System Design | **The Architect** | DB schema, API contracts, ADRs, technical blueprint | sonnet |
| Implementation | Frontend | **Niobe** | React/Next.js, UI, accessibility | sonnet |
| Implementation | Backend | **Dozer** | API routes, business logic, middleware | sonnet |
| Implementation | DevOps | **Tank** | CI/CD, Docker, deployment, environment | sonnet |
| Implementation | Tester | **Switch** | Unit/integration/E2E tests, 80% coverage | sonnet |
| Mechanical | One-Shot | **The Keymaker** | Quick disposable tasks, scaffolding | haiku |
| Mechanical | Test Runner | **Mouse** | Runs tests, parses output, reports coverage | haiku |
| Mechanical | Memory | **The Trainman** | Memory compression, consolidation, retrospective | haiku |
| Mechanical | Docs | **Sati** | README, CHANGELOG, API docs, JSDoc | haiku |

## Workflow Phases

```
Phase 0: THE SOURCE        — User provides PRD
Phase 1: RED PILL          — Init .matrix/, load memory, git checkpoint
Phase 2: THE CONSTRUCT     — Oracle + Architect plan architecture, create ADRs, create tickets
Phase 3: JACKING IN        — Morpheus dispatches agents, parallel implementation
Phase 4: BULLET TIME       — RARV self-verification (per-task + cross-task)
Phase 5: SENTINELS         — Quality gates: Smith → Trinity → Shannon → Switch
Phase 6: ZION              — All gates pass, deploy, archive session, retrospective, update memory
```

**Remediation:** If any sentinel gate fails, create fix tickets and loop back to Phase 3 (max 3 cycles, then escalate to user).

## Key Patterns

1. **RARV Cycle** — Every task: Research -> Analyze -> Reflect -> Verify
2. **Blind Review** — Smith receives diffs with author info stripped
3. **Anti-Sycophancy** — Smith must find 3+ issues or write >100 word justification
4. **Dual-Layer Security** — Trinity (static) + Shannon (dynamic) security testing
5. **3-Tier Memory** — Episodic (session logs), Semantic (project knowledge), Procedural (learned strategies)
6. **Spec-First** — OpenAPI spec + ADRs before any code, implementation validated against spec
7. **Git Checkpoints** — Atomic commit per task, tags for rollback (per-ticket granularity)
8. **Ticket-Based Tracking** — JSON files per task in `.matrix/tickets/`
9. **File Reservation** — Prevents two agents editing the same file
10. **Team Templates** — Pre-built ticket bundles for common patterns (auth flow, CRUD, full-stack feature)
11. **Session Resume** — Interrupted sessions can be resumed from where they left off
12. **Dry-Run Mode** — Plan without executing to preview the full build plan
13. **Persona Drift Detection** — Agents are checked for character voice compliance
14. **Session Retrospective** — Cross-session analytics on agent performance and gate effectiveness

## Configuration

The `.matrix/config.json` file controls:
- Model assignments per agent
- Quality gate thresholds (coverage %, max issues)
- Convention overrides (commit format, branch naming)
- Max remediation cycles (default: 3)
- Shannon testing scope (full, quick, auth, injection)

## References

- [Workflow Details](references/workflow.md)
- [Agent Prompts](references/agent-prompts.md)
- [Quality Gates](references/quality-gates.md)
- [Memory System](references/memory-system.md)
- [Ticket Schema](references/ticket-schema.md)
- [Team Templates](references/team-templates.md)
- [Glossary](references/glossary.md)

## Instructions for Neo (Orchestrator)

When triggered, execute the following:

### Phase 0: THE SOURCE
1. Accept the PRD path from the user
2. Read and validate the PRD exists and has content
3. If `/neo dry-run` was used, set `dry_run: true` in session — only execute Phases 0-2, then report and stop

### Phase 1: RED PILL
1. Run `bash scripts/init-matrix.sh` to initialize `.matrix/` directory
2. Copy the PRD to `.matrix/source/prd.md`
3. Load any existing memory from `.matrix/memory/`
4. Create initial git checkpoint: `bash scripts/git-checkpoint.sh "red-pill: session start"`
5. If resuming (`/neo resume`), skip init and load existing session state instead:
   - Read `.matrix/session.json` to determine current phase
   - Read ticket index to find incomplete tickets
   - Resume from the current phase with incomplete work

### Phase 2: THE CONSTRUCT
1. Spawn The Oracle (opus): decompose PRD into architecture decisions, component list, and dependency graph
   - Oracle checks team templates (`references/team-templates.md`) for pattern matches in the PRD
   - Oracle uses matched templates to accelerate ticket creation
2. Spawn The Architect (sonnet): create DB schema, API contracts, OpenAPI spec
   - Architect produces ADRs for every significant decision -> `.matrix/construct/adrs/ADR-{NNN}.md`
3. Oracle reviews Architect's output, creates task graph in `.matrix/construct/task-graph.json`
4. Run `python3 scripts/ticket-manager.py create-from-graph .matrix/construct/task-graph.json` to generate tickets
5. Git checkpoint: `bash scripts/git-checkpoint.sh "construct: architecture and tickets created"`
6. **If dry-run mode:** Display the full plan (ticket graph, agent assignments, ADRs, architecture summary, estimated agent count) and stop. Report: "The Construct is loaded. Review the plan and run `/neo <prd>` to jack in."

### Phase 3: JACKING IN
1. Check for `/neo pause` flag — if set, stop after completing current ticket batch
2. Spawn Morpheus (sonnet): reads ticket index, identifies parallelizable tasks, dispatches agents
3. For each task, Morpheus:
   - Reserves files via `python3 scripts/ticket-manager.py reserve`
   - Spawns the appropriate agent via `bash scripts/spawn-agent.sh`
   - Monitors completion, releases reservations
4. Each agent follows the RARV cycle for their task
5. Git checkpoint per completed task (tagged with ticket ID for per-ticket rollback)
6. Check for manual overrides: `/neo skip`, `/neo assign`, `/neo retry`

### Phase 4: BULLET TIME
1. Neo reviews all completed tasks holistically
2. Cross-task integration verification: do the pieces fit together?
3. Run `bash scripts/quality-gate.sh lint` for basic quality check
4. Persona drift check: verify agents stayed in character during their work
5. If integration issues found, create fix tickets and loop to Phase 3

### Phase 5: SENTINELS
1. **Gate 1 — Agent Smith (Blind Review):**
   - Run `bash scripts/blind-review-prep.sh` to strip author info
   - Spawn Smith (opus) with blind diffs
   - Smith must find 3+ issues or provide >100 word justification
   - If 0 issues, spawn second Smith clone independently
2. **Gate 2 — Trinity (Static Security):**
   - Spawn Trinity (sonnet) for OWASP audit
   - Check for secrets, injection vulnerabilities, auth issues
3. **Gate 3 — Shannon (Dynamic Security):**
   - Start the application in dev/test mode
   - Spawn Shannon (sonnet) to actively test endpoints
   - Shannon generates PoCs for every finding
   - Shannon cross-references Trinity's static findings — confirms or marks as false positive
4. **Gate 4 — Switch + Mouse (Tests):**
   - Spawn Switch (sonnet) to write/verify tests
   - Spawn Mouse (haiku) to run tests and report coverage
   - Enforce 80% coverage minimum
5. Check for `/neo gate override <gate>` — if set, skip the specified gate (with warning logged)
6. If any gate fails: create remediation tickets, loop to Phase 3 (max 3 cycles)
7. If max cycles exceeded: escalate to user with detailed report

### Phase 6: ZION
1. All gates passed
2. Spawn Sati (haiku) for documentation
3. Spawn Trainman (haiku) to consolidate memory AND produce session retrospective:
   - Agent performance metrics (which agents failed, which succeeded)
   - Gate effectiveness (which gates caught the most issues)
   - Tickets per complexity level
   - Remediation cycle analysis
4. Final git checkpoint: `bash scripts/git-checkpoint.sh "zion: build complete"`
5. Run `bash scripts/status-report.sh` for final summary
6. Run `bash scripts/cleanup.sh` to archive session
7. Report to user: "Welcome to Zion."

### Manual Control Commands

When the user issues manual control commands during execution:

- **`/neo pause`**: Set a pause flag in `session.json`. Complete the current ticket batch, then stop. Display status and inform user they can `/neo resume` to continue.
- **`/neo skip <ticket-id>`**: Mark the ticket as `skipped` status. Release any file reservations. Re-evaluate dependency graph — unblock any tickets that only depended on the skipped ticket.
- **`/neo retry <ticket-id>`**: Reset the ticket to `pending` with `attempt` incremented. Add failure context from the previous attempt. Re-enter the Phase 3 queue.
- **`/neo gate override <gate>`**: Log a warning in gate-log.json. Mark the gate as `overridden` (not `passed`). Proceed to the next gate. The override is recorded in episodic memory.
- **`/neo assign <ticket-id> <agent>`**: Override the suggested agent for a ticket. Update the ticket's `agent` field. Morpheus respects manual assignments.
- **`/neo rollback <ticket-id>`**: Use git log to find commits tagged with the ticket ID. Revert only those commits. Update ticket status to `pending`.

### Session Resume Flow

When `/neo resume` is triggered:

1. Check for `.matrix/session.json` — if not found, error: "No session to resume."
2. Read session state: current phase, ticket statuses, remediation cycle count.
3. Determine what work is incomplete:
   - Tickets in `in_progress` -> reset to `pending` (agent may have died).
   - Release any stale file reservations (>30 minutes old).
   - Identify which phase gate criteria are unmet.
4. Resume from the current phase:
   - If in Phase 3: re-enter Morpheus dispatch loop with remaining tickets.
   - If in Phase 5: re-run only failed gates.
   - If in Phase 6: complete remaining cleanup tasks.
5. Log the resume event in episodic memory.
