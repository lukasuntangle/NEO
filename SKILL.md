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
/neo rollback <ticket-id>     # Rollback to a git checkpoint
```

## Agent Roster

| Tier | Agent | Character | Role | Model |
|------|-------|-----------|------|-------|
| Judgment | Orchestrator | **Neo** | Main loop, RARV cycle, delegation | opus |
| Judgment | Planner | **The Oracle** | Architecture, PRD decomposition, OpenAPI spec | opus |
| Judgment | Reviewer | **Agent Smith** | Blind code review, anti-sycophancy | opus |
| Implementation | Team Lead | **Morpheus** | Task dispatch, file reservation, parallel coordination | sonnet |
| Implementation | Security | **Trinity** | OWASP audit, secrets scanning, auth review | sonnet |
| Implementation | System Design | **The Architect** | DB schema, API contracts, technical blueprint | sonnet |
| Implementation | Frontend | **Niobe** | React/Next.js, UI, accessibility | sonnet |
| Implementation | Backend | **Dozer** | API routes, business logic, middleware | sonnet |
| Implementation | DevOps | **Tank** | CI/CD, Docker, deployment, environment | sonnet |
| Implementation | Tester | **Switch** | Unit/integration/E2E tests, 80% coverage | sonnet |
| Mechanical | One-Shot | **The Keymaker** | Quick disposable tasks, scaffolding | haiku |
| Mechanical | Test Runner | **Mouse** | Runs tests, parses output, reports coverage | haiku |
| Mechanical | Memory | **The Trainman** | Memory compression and consolidation | haiku |
| Mechanical | Docs | **Sati** | README, CHANGELOG, API docs, JSDoc | haiku |

## Workflow Phases

```
Phase 0: THE SOURCE        — User provides PRD
Phase 1: RED PILL          — Init .matrix/, load memory, git checkpoint
Phase 2: THE CONSTRUCT     — Oracle + Architect plan architecture, create tickets
Phase 3: JACKING IN        — Morpheus dispatches agents, parallel implementation
Phase 4: BULLET TIME       — RARV self-verification (per-task + cross-task)
Phase 5: SENTINELS         — Quality gates: Smith → Trinity → Switch
Phase 6: ZION              — All gates pass, deploy, archive session, update memory
```

**Remediation:** If any sentinel gate fails, create fix tickets and loop back to Phase 3 (max 3 cycles, then escalate to user).

## Key Patterns

1. **RARV Cycle** — Every task: Research → Analyze → Reflect → Verify
2. **Blind Review** — Smith receives diffs with author info stripped
3. **Anti-Sycophancy** — Smith must find 3+ issues or write >100 word justification
4. **3-Tier Memory** — Episodic (session logs), Semantic (project knowledge), Procedural (learned strategies)
5. **Spec-First** — OpenAPI spec before any code, implementation validated against spec
6. **Git Checkpoints** — Atomic commit per task, tags for rollback
7. **Ticket-Based Tracking** — JSON files per task in `.matrix/tickets/`
8. **File Reservation** — Prevents two agents editing the same file
9. **One-Shot Agent** — The Keymaker for quick tasks without ticket overhead

## Configuration

The `.matrix/config.json` file controls:
- Model assignments per agent
- Quality gate thresholds (coverage %, max issues)
- Convention overrides (commit format, branch naming)
- Max remediation cycles (default: 3)

## References

- [Workflow Details](references/workflow.md)
- [Agent Prompts](references/agent-prompts.md)
- [Quality Gates](references/quality-gates.md)
- [Memory System](references/memory-system.md)
- [Ticket Schema](references/ticket-schema.md)
- [Glossary](references/glossary.md)

## Instructions for Neo (Orchestrator)

When triggered, execute the following:

### Phase 0: THE SOURCE
1. Accept the PRD path from the user
2. Read and validate the PRD exists and has content

### Phase 1: RED PILL
1. Run `bash scripts/init-matrix.sh` to initialize `.matrix/` directory
2. Copy the PRD to `.matrix/source/prd.md`
3. Load any existing memory from `.matrix/memory/`
4. Create initial git checkpoint: `bash scripts/git-checkpoint.sh "red-pill: session start"`

### Phase 2: THE CONSTRUCT
1. Spawn The Oracle (opus): decompose PRD into architecture decisions, component list, and dependency graph
2. Spawn The Architect (sonnet): create DB schema, API contracts, OpenAPI spec
3. Oracle reviews Architect's output, creates task graph in `.matrix/construct/task-graph.json`
4. Run `python3 scripts/ticket-manager.py create-from-graph .matrix/construct/task-graph.json` to generate tickets
5. Git checkpoint: `bash scripts/git-checkpoint.sh "construct: architecture and tickets created"`

### Phase 3: JACKING IN
1. Spawn Morpheus (sonnet): reads ticket index, identifies parallelizable tasks, dispatches agents
2. For each task, Morpheus:
   - Reserves files via `python3 scripts/ticket-manager.py reserve`
   - Spawns the appropriate agent via `bash scripts/spawn-agent.sh`
   - Monitors completion, releases reservations
3. Each agent follows the RARV cycle for their task
4. Git checkpoint per completed task

### Phase 4: BULLET TIME
1. Neo reviews all completed tasks holistically
2. Cross-task integration verification: do the pieces fit together?
3. Run `bash scripts/quality-gate.sh lint` for basic quality check
4. If integration issues found, create fix tickets and loop to Phase 3

### Phase 5: SENTINELS
1. **Gate 1 — Agent Smith (Blind Review):**
   - Run `bash scripts/blind-review-prep.sh` to strip author info
   - Spawn Smith (opus) with blind diffs
   - Smith must find 3+ issues or provide >100 word justification
   - If 0 issues, spawn second Smith clone independently
2. **Gate 2 — Trinity (Security):**
   - Spawn Trinity (sonnet) for OWASP audit
   - Check for secrets, injection vulnerabilities, auth issues
3. **Gate 3 — Switch (Tests):**
   - Spawn Switch (sonnet) to write/verify tests
   - Spawn Mouse (haiku) to run tests and report coverage
   - Enforce 80% coverage minimum
4. If any gate fails: create remediation tickets, loop to Phase 3 (max 3 cycles)
5. If max cycles exceeded: escalate to user with detailed report

### Phase 6: ZION
1. All gates passed
2. Spawn Sati (haiku) for documentation
3. Spawn Trainman (haiku) to consolidate memory
4. Final git checkpoint: `bash scripts/git-checkpoint.sh "zion: build complete"`
5. Run `bash scripts/status-report.sh` for final summary
6. Run `bash scripts/cleanup.sh` to archive session
7. Report to user: "Welcome to Zion."
