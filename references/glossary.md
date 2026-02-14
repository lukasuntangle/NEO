# Glossary: Matrix-to-Engineering Concept Map

*"The Matrix has you."*

Every developer knows the feeling: staring at a codebase so vast it feels like a simulated reality, wondering if there is a better way. The Neo Orchestrator is that better way. Taking the red pill means committing to autonomous development -- letting a coordinated team of AI agents decompose your requirements, architect the system, implement the code, review it blindly, audit it for security, test it to 80%+ coverage, and deliver a working product. You do not have to believe it will work. You just have to take the pill. The Matrix is the codebase. And Neo is going to rewrite it.

---

## Core Concepts

| Matrix Term | Engineering Concept | Details |
|-------------|-------------------|---------|
| **The Matrix** | The codebase / project | The entire software system being built or modified. Just as the Matrix is a constructed reality, the codebase is a constructed system of logic. |
| **The Source** | PRD / requirements document | The origin of truth. Everything flows from the PRD, just as everything in the Matrix flows from the Source. Phase 0 of the workflow. |
| **Red Pill** | Session initialization | Committing to the build. Once you take the red pill, the system initializes `.matrix/`, loads memory, and begins. There is no going back (gracefully). Phase 1. |
| **Blue Pill** | Abort / cancel session | Declining to proceed. The session ends, no changes are made, and you wake up in your bed believing whatever you want to believe. |
| **The Construct** | Architecture phase / design space | The white room where anything can be loaded. In the Construct phase, Oracle and Architect design the system before any code is written. Phase 2. |
| **Jacking In** | Starting implementation | Plugging into the Matrix to do real work. Agents are spawned, files are reserved, and code is written. Phase 3. |
| **Bullet Time** | RARV self-verification | Slowing down to see everything. Neo reviews the full codebase holistically -- checking imports, API contracts, type alignment. The moment where you stop and examine every angle. Phase 4. |
| **Sentinels** | Quality gates | The machines that hunt you down if your code is not clean. Three sentinel gates (Smith, Trinity, Switch+Mouse) must all pass before reaching Zion. Phase 5. |
| **Zion** | Successfully deployed product | The promised land. All gates passed, documentation generated, memory consolidated, session archived. The code is done. Phase 6. |

---

## Characters / Agents

| Matrix Term | Engineering Concept | Agent Details |
|-------------|-------------------|---------------|
| **The One (Neo)** | The orchestrator | Top-level coordinator. Manages phases, delegates work, communicates with the user. Opus tier. Never writes implementation code directly. |
| **Agents (Smith)** | Code reviewers / quality enforcers | In the Matrix, Agents enforce the system's rules. Here, Smith enforces code quality through blind review. Opus tier. |
| **The Oracle** | Architecture planner | Sees the future -- meaning she sees the design before it is built. Decomposes PRDs into architecture and task graphs. Opus tier. |
| **Morpheus** | Team lead / dispatcher | Believes in the vision and leads the crew. Reads the ticket index, builds execution plans, dispatches agents in parallel batches. Sonnet tier. |
| **Trinity** | Security specialist | The best at what she does. Runs OWASP audits, scans for secrets, checks for injection vulnerabilities. Sonnet tier. |
| **Shannon** | Dynamic security tester / pentester | Named after Claude Shannon, father of information theory. Actively probes running systems for exploitable vulnerabilities. Generates PoCs for every finding. Cross-references Trinity's static analysis. Sonnet tier. |
| **The Architect** | System designer | Creator of the technical Matrix. Produces database schemas, OpenAPI specs, and technical blueprints. Sonnet tier. |
| **Niobe** | Frontend pilot | Best pilot in the fleet. Navigates UI complexity -- React components, pages, client-side logic. Sonnet tier. |
| **Dozer** | Backend operator | Keeps the ship running. Implements API endpoints, business logic, database queries. Sonnet tier. |
| **Tank** | DevOps operator | Loads programs and environments. Handles Docker, CI/CD, infrastructure configuration. Sonnet tier. |
| **Switch** | Test specialist | Binary thinker -- things pass or they fail. Writes test cases covering happy paths, error paths, edge cases. Sonnet tier. |
| **The Keymaker** | One-shot specialist | Creates one specific key for one specific door. Handles small, focused, single-file tasks. Haiku tier. |
| **Mouse** | Test runner / explorer | Curious explorer of the simulation. Runs the full test suite, parses results, reports coverage metrics. Haiku tier. |
| **The Trainman** | Memory manager | Controls transitions between worlds (sessions). Compresses episodic memory, updates semantic and procedural knowledge. Haiku tier. |
| **Sati** | Documentation writer | Makes the sunrise -- illuminates the code for others to understand. Generates README, API docs, inline comments. Haiku tier. |

---

## Actions and Events

| Matrix Term | Engineering Concept | When It Happens |
|-------------|-------------------|----------------|
| **Unplugging** | Session cleanup / archival | End of Phase 6. The session is archived, memory is consolidated, the user is back in the real world with working code. |
| **Deja Vu** | Same error occurring twice | When the system detects that an error it already resolved has returned. Indicates a regression or incomplete fix. Triggers investigation. |
| **Glitch in the Matrix** | Recurring bug or suspicious pattern | A broader pattern -- not just a repeated error but a systemic issue that keeps surfacing in different forms. Warrants deep investigation. |
| **Free Your Mind** | Refactoring / breaking constraints | When the system (or user) decides to break free from the current structure. Major refactoring, rearchitecting, or abandoning an approach that is not working. |
| **There Is No Spoon** | Spec-first thinking | The abstraction is the reality. The OpenAPI spec, the type definitions, the interfaces -- these are the real system. Implementation is just making the spec manifest. |
| **Follow the White Rabbit** | Debugging / root cause tracing | Tracing an issue from symptom to root cause. Following imports, call stacks, data flows to find where something actually breaks. |
| **RARV** | Research, Analyze, Reflect, Verify | The four-step cycle every agent follows on every ticket. Research the context, Analyze the approach, Reflect before coding, Verify after coding. |
| **Dry Run** | Plan without executing | Running Phases 0-2 only to preview the full build plan without writing any implementation code. See what the Construct would look like before jacking in. |
| **Gate Override** | Bypassing a quality gate | Consciously accepting the risk of skipping a sentinel. Logged prominently and tracked in episodic memory. The override does not make the sentinel go away -- it makes you responsible for what it would have caught. |
| **Session Resume** | Resuming an interrupted session | When a session is interrupted (crash, timeout, manual pause), `/neo resume` picks up where it left off. Reads session.json, resets stale tickets, releases old reservations, and re-enters the current phase. |

---

## Locations and Structures

| Matrix Term | Engineering Concept | Mapping |
|-------------|-------------------|---------|
| **The Nebuchadnezzar** | The development environment | The ship from which agents operate. The local machine, the `.matrix/` directory, the tools and scripts. |
| **The Construct (place)** | `.matrix/construct/` directory | Where architecture documents, schemas, and specs are stored before implementation begins. |
| **ADR (Architecture Decision Record)** | `.matrix/construct/adrs/` directory | Where the Architect records every significant design decision. Each ADR captures what was decided, why, and what the consequences are. Numbered sequentially: ADR-001, ADR-002, etc. |
| **The Matrix (place)** | `src/` directory | The actual codebase where implementation lives. |
| **Zion (place)** | Production / deployed state | The final destination. Where code goes after passing all gates. |
| **The Trainman's Station** | `.matrix/memory/` directory | Between sessions, this is where knowledge persists. The transition point between one session and the next. |

---

## Quick Reference Card

```
PRD arrives           = The Source calls
Session starts        = Take the Red Pill
Design phase          = Enter the Construct
Implementation        = Jack In
Self-review           = Bullet Time
Quality gates         = Sentinels attack
All gates pass        = Reach Zion
Session ends          = Unplug
Same bug twice        = Deja Vu
Recurring pattern     = Glitch in the Matrix
Major refactor        = Free Your Mind
Spec-first approach   = There Is No Spoon
Debugging             = Follow the White Rabbit
Agent work cycle      = RARV
Plan only             = Dry Run
Skip a gate           = Gate Override
Continue session      = Resume (plug back in)
Design decisions      = ADRs
Active pentesting     = Shannon probes
Team blueprints       = Templates loaded
```
