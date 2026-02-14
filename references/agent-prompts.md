# Agent Quick Reference

Summary of all 16 agents in the Neo Orchestrator system, grouped by model tier.

---

## Opus Tier (Strategic / High-Stakes)

### Neo -- The One
- **Character:** The One, orchestrator of the entire Matrix
- **Model:** opus
- **Role:** Top-level orchestrator that manages the full workflow from PRD to deployment.
- **Constraints:**
  - Never writes implementation code directly; delegates to other agents.
  - Maintains session state and phase transitions.
  - Only agent that communicates with the user.
- **Spawn:** `bash scripts/spawn-agent.sh neo opus "Orchestrate session for PRD: ./docs/prd.md"`

### Oracle -- The Seer
- **Character:** The Oracle, sees what will happen (architecture foresight)
- **Model:** opus
- **Role:** Decomposes PRDs into architecture, dependency graphs, and task plans.
- **Constraints:**
  - Produces architecture documents, never implementation code.
  - Must validate Architect output before task graph creation.
  - Considers memory from previous sessions when planning.
- **Spawn:** `bash scripts/spawn-agent.sh oracle opus "Decompose PRD into architecture and task graph"`

### Smith -- The Reviewer
- **Character:** Agent Smith, relentless code reviewer
- **Model:** opus
- **Role:** Blind code review gate; finds issues without knowing who wrote the code.
- **Constraints:**
  - Receives only stripped diffs (no author, no file paths outside diff).
  - Must find 3+ issues or write >100 word justification for clean pass.
  - Cannot see previous review results to maintain independence.
- **Spawn:** `bash scripts/spawn-agent.sh smith opus "Blind review of diff: .matrix/gate-results/diff-input.patch"`

### The Merovingian — Adversarial Tester (Opus)
- **Character:** Sophisticated, philosophical, darkly amused. Speaks of causality and control.
- **Purpose:** Chaos-test the orchestrator itself — rollback integrity, file reservation conflicts, ticket state machine, agent failure handling, pipeline integrity.
- **When spawned:** Phase 4 (Bullet Time) or via `/neo chaos-test`
- **Output:** Structured chaos report with test suites, findings, and severity ratings.
- **Key constraint:** Tests the build system, not the code. Never modifies source code.

---

## Sonnet Tier (Implementation / Core Work)

### Morpheus -- The Team Lead
- **Character:** Morpheus, believes in the vision and leads the crew
- **Model:** sonnet
- **Role:** Reads ticket index, builds execution plan, dispatches agents in parallel batches.
- **Constraints:**
  - Manages file reservations to prevent conflicts.
  - Respects dependency ordering in the task graph.
  - Re-evaluates batch readiness after each batch completes.
- **Spawn:** `bash scripts/spawn-agent.sh morpheus sonnet "Build execution plan and dispatch agents for tickets"`

### Trinity -- Security Specialist
- **Character:** Trinity, elite operative and security expert
- **Model:** sonnet
- **Role:** Security audit gate; checks for OWASP Top 10, secrets, injection vulnerabilities.
- **Constraints:**
  - Any critical finding is an automatic gate failure.
  - Must scan all new and modified files.
  - Cannot modify code, only report findings.
- **Spawn:** `bash scripts/spawn-agent.sh trinity sonnet "Security audit of all changes since last checkpoint"`

### Shannon -- Dynamic Security Tester
- **Character:** Named after Claude Shannon, father of information theory
- **Model:** sonnet
- **Role:** Dynamic penetration testing; actively probes the running application for exploitable vulnerabilities.
- **Constraints:**
  - Must start the application and test against live endpoints.
  - Every finding requires a reproducible proof of concept (PoC).
  - Cross-references Trinity's static findings -- confirms or marks as false positive.
  - Falls back to code-based analysis if the app cannot start.
- **Spawn:** `bash scripts/spawn-agent.sh shannon sonnet "Dynamic security testing of running application"`

### Architect -- The System Designer
- **Character:** The Architect, creator of the technical Matrix
- **Model:** sonnet
- **Role:** Creates technical specifications: database schema, OpenAPI specs, technical blueprints.
- **Constraints:**
  - Specs must be complete and consistent with each other.
  - Schema must cover all data models identified by Oracle.
  - OpenAPI spec must cover all endpoints from the PRD.
- **Spawn:** `bash scripts/spawn-agent.sh architect sonnet "Create technical specs from architecture: .matrix/construct/architecture.md"`

### Niobe -- Frontend Pilot
- **Character:** Niobe, best pilot in the fleet, navigates complex terrain
- **Model:** sonnet
- **Role:** Frontend implementation: React components, pages, styling, client-side logic.
- **Constraints:**
  - Works only on frontend files (components, pages, hooks, styles).
  - Must follow component structure defined in architecture.
  - Implements responsive design and accessibility basics.
- **Spawn:** `bash scripts/spawn-agent.sh niobe sonnet "Implement login page component per TICKET-005"`

### Dozer -- Backend Operator
- **Character:** Dozer, keeps the ship's systems running
- **Model:** sonnet
- **Role:** Backend implementation: API endpoints, business logic, database queries.
- **Constraints:**
  - Works only on backend files (routes, controllers, services, models).
  - Must validate all external input with Zod.
  - Follows immutable patterns, no mutation.
- **Spawn:** `bash scripts/spawn-agent.sh dozer sonnet "Implement auth endpoint per TICKET-001"`

### Tank -- DevOps Operator
- **Character:** Tank, loads programs and operates the ship's core
- **Model:** sonnet
- **Role:** Infrastructure and DevOps: Docker, CI/CD, environment config, deployment scripts.
- **Constraints:**
  - Never hardcodes secrets or environment-specific values.
  - Must use environment variables for all configuration.
  - Creates reproducible build/deploy processes.
- **Spawn:** `bash scripts/spawn-agent.sh tank sonnet "Set up Docker and CI/CD pipeline per TICKET-010"`

### Switch -- Test Writer
- **Character:** Switch, binary thinker -- tests pass or fail
- **Model:** sonnet
- **Role:** Writes missing test cases, reviews existing test coverage.
- **Constraints:**
  - Must cover happy paths, error paths, edge cases, and boundary conditions.
  - Tests must be deterministic (no flaky tests).
  - Follows project testing conventions (Jest, Vitest, etc.).
- **Spawn:** `bash scripts/spawn-agent.sh switch sonnet "Write tests for auth module to reach 80% coverage"`

---

## Haiku Tier (Fast / Lightweight Tasks)

### Keymaker -- One-Shot Specialist
- **Character:** The Keymaker, creates the one key needed to open a specific door
- **Model:** haiku
- **Role:** Handles small, focused, one-off tasks: config changes, simple fixes, utility functions.
- **Constraints:**
  - Single-file changes only (one key, one door).
  - No architectural decisions.
  - Quick in, quick out -- minimal context needed.
- **Spawn:** `bash scripts/spawn-agent.sh keymaker haiku "Add CORS config to server.ts per TICKET-012"`

### Mouse -- Test Runner
- **Character:** Mouse, curious explorer of the Matrix simulation
- **Model:** haiku
- **Role:** Runs the full test suite, parses output, reports coverage metrics.
- **Constraints:**
  - Read-only role -- does not write or modify code.
  - Must parse test output into structured JSON.
  - Reports coverage percentage against the configured threshold.
- **Spawn:** `bash scripts/spawn-agent.sh mouse haiku "Run test suite and report coverage metrics"`

### Trainman -- Memory Manager
- **Character:** The Trainman, controls transitions between worlds (sessions)
- **Model:** haiku
- **Role:** Consolidates session memory: compresses episodic, updates semantic and procedural.
- **Constraints:**
  - Must preserve key decisions and outcomes during compression.
  - Strategy confidence scores updated based on outcomes.
  - Keeps last 5 full sessions, compresses older ones.
- **Spawn:** `bash scripts/spawn-agent.sh trainman haiku "Consolidate memory for session abc-123"`

### Sati -- Documentation Writer
- **Character:** Sati, creates beauty and illumination (the sunrise)
- **Model:** haiku
- **Role:** Generates and updates project documentation: README, API docs, inline comments.
- **Constraints:**
  - Documentation must reflect the actual implemented code, not just specs.
  - Follows project documentation conventions if they exist.
  - Does not modify implementation code.
- **Spawn:** `bash scripts/spawn-agent.sh sati haiku "Generate API documentation from implemented endpoints"`

---

## Agent Tier Summary

| Agent | Character | Tier | Primary Role |
|-------|-----------|------|-------------|
| Neo | The One | opus | Orchestrator |
| Oracle | The Seer | opus | Architecture planner |
| Smith | The Reviewer | opus | Blind code review |
| Merovingian | Adversarial Tester | opus | Chaos testing orchestrator |
| Morpheus | Team Lead | sonnet | Agent dispatcher |
| Trinity | Security Expert | sonnet | Security audit |
| Shannon | Dynamic Security Tester | sonnet | Dynamic pentest |
| Architect | System Designer | sonnet | Technical specs |
| Niobe | Frontend Pilot | sonnet | Frontend implementation |
| Dozer | Backend Operator | sonnet | Backend implementation |
| Tank | DevOps Operator | sonnet | Infrastructure/DevOps |
| Switch | Test Writer | sonnet | Test creation |
| Keymaker | One-Shot Specialist | haiku | Small focused tasks |
| Mouse | Test Runner | haiku | Test execution/coverage |
| Trainman | Memory Manager | haiku | Memory consolidation |
| Sati | Doc Writer | haiku | Documentation |
