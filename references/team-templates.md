# Team Templates: Construct Blueprints

*"I can only show you the door. You're the one that has to walk through it."*

These are pre-built ticket template bundles -- blueprints loaded into the Construct before jacking in. When the Oracle decomposes a PRD, she recognizes recurring architectural patterns and reaches for these blueprints rather than designing from scratch every time. Each blueprint is a proven dependency graph that maps cleanly onto the agent roster.

The Oracle matches PRD sections to templates using the **Recognition Triggers** listed in each blueprint. When a trigger matches, the Oracle instantiates the template, fills in the variables from PRD context, and wires the tickets into the larger task graph. Multiple templates can compose together -- a PRD that describes "a user management system with real-time notifications" would instantiate both `FULL_STACK_FEATURE` (for user CRUD) and `REALTIME_FEATURE` (for notifications), with cross-template dependencies handled by the Oracle.

---

## How to Read These Blueprints

Each template defines:

- **Recognition Triggers** -- PRD patterns that tell the Oracle to reach for this blueprint.
- **Variables** -- Placeholders filled from PRD context. Written as `{variable_name}`.
- **Ticket Table** -- The full ticket breakdown with agent, model tier, complexity, and dependencies.
- **Dependency Graph** -- ASCII visualization of execution order.
- **Filled Example** -- A concrete instantiation showing what the tickets look like after the Oracle fills in variables.

### Complexity Sizing

| Size | Definition | Typical Agent Time |
|------|-----------|-------------------|
| S | Single file, straightforward logic, minimal decisions | Fast -- one RARV cycle |
| M | 2-4 files, moderate logic, some design decisions | Standard -- full RARV with research |
| L | 5+ files, complex logic, architectural implications | Extended -- deep RARV, possible iteration |

---

## Template 1: FULL_STACK_FEATURE

**When the Oracle uses this:** Any feature that requires changes across the full stack -- database, API, and frontend. The PRD describes something users interact with through the UI that reads from or writes to persistent storage.

### Recognition Triggers

- PRD mentions a new page/screen AND data that must be stored
- PRD describes user-facing functionality with backend persistence
- Feature requires a new database table or significant schema change plus UI
- Keywords: "users can see/create/manage {thing}", "dashboard shows {data}", "page displays {information} from the database"

### Variables

| Variable | Source | Example |
|----------|--------|---------|
| `{feature_name}` | PRD section title or feature name | "Project Dashboard" |
| `{entity_name}` | Primary data entity | "project" |
| `{table_name}` | Database table (derived from entity) | "projects" |
| `{endpoint_base}` | API route prefix | "/api/projects" |
| `{component_name}` | Primary React component | "ProjectDashboard" |
| `{files_db}` | Database migration files | "src/db/migrations/add-projects.ts" |
| `{files_api}` | API route files | "src/api/projects.ts" |
| `{files_ui}` | Frontend component files | "src/components/ProjectDashboard.tsx" |
| `{files_test}` | Test files | "src/__tests__/projects.integration.test.ts" |

### Ticket Table

| # | Title | Agent | Model | Size | Dependencies | Files |
|---|-------|-------|-------|------|-------------|-------|
| 1 | Create `{table_name}` database schema and migration | Dozer | sonnet | M | None | `{files_db}` |
| 2 | Implement `{endpoint_base}` API endpoints | Dozer | sonnet | M | Ticket 1 | `{files_api}` |
| 3 | Build `{component_name}` frontend component(s) | Niobe | sonnet | M | Ticket 2 | `{files_ui}` |
| 4 | Write integration tests for `{feature_name}` | Switch | sonnet | M | Ticket 2, Ticket 3 | `{files_test}` |

### Dependency Graph

```
[1] DB Migration
      |
      v
[2] API Endpoints
      |
      v
[3] Frontend Components
      |
      v
[4] Integration Tests
```

Execution groups:
- Group 1: Ticket 1 (database must exist first)
- Group 2: Ticket 2 (API needs the schema)
- Group 3: Ticket 3 (frontend calls the API)
- Group 4: Ticket 4 (tests verify the full stack)

### Filled Example

PRD section: *"The application should display a project dashboard where users can see all their active projects, including project name, status, and last updated date."*

| # | ID | Title | Agent | Size |
|---|----|-------|-------|------|
| 1 | TICKET-005 | Create projects database schema and migration | Dozer | M |
| 2 | TICKET-006 | Implement /api/projects API endpoints (list, detail) | Dozer | M |
| 3 | TICKET-007 | Build ProjectDashboard frontend component | Niobe | M |
| 4 | TICKET-008 | Write integration tests for Project Dashboard | Switch | M |

```json
{
  "id": "TICKET-005",
  "title": "Create projects database schema and migration",
  "description": "Create the projects table with columns: id (uuid, PK), name (varchar, not null), status (enum: active/archived/draft), user_id (uuid, FK to users), created_at, updated_at. Write the migration file and Zod validation schema for the model.",
  "agent": "dozer",
  "model": "sonnet",
  "dependencies": [],
  "files": ["src/db/migrations/003-add-projects.ts", "src/db/schema/projects.ts"],
  "acceptance_criteria": [
    "Migration creates projects table with all specified columns",
    "Foreign key constraint to users table",
    "Zod schema validates project model",
    "Migration is reversible (down function exists)"
  ]
}
```

---

## Template 2: AUTHENTICATION_FLOW

**When the Oracle uses this:** Any PRD that requires user authentication -- signup, login, protected routes, session management. This is one of the most common blueprints and is almost always the first template instantiated, since most other features depend on knowing who the user is.

### Recognition Triggers

- PRD mentions user accounts, login, signup, or registration
- PRD references "authenticated users", "logged-in users", or "user sessions"
- Any feature that requires knowing the identity of the current user
- Keywords: "users must sign up", "login required", "protected routes", "authentication", "authorization", "JWT", "session"

### Variables

| Variable | Source | Example |
|----------|--------|---------|
| `{user_fields}` | Fields on the user model beyond email/password | "name, avatar_url, role" |
| `{auth_strategy}` | JWT, session-based, or OAuth | "JWT" |
| `{token_expiry}` | Token/session lifetime | "24h" |
| `{protected_routes}` | Routes requiring auth | "/api/projects/*, /api/settings/*" |
| `{password_rules}` | Password requirements from PRD | "min 8 chars, 1 uppercase, 1 number" |

### Ticket Table

| # | Title | Agent | Model | Size | Dependencies | Files |
|---|-------|-------|-------|------|-------------|-------|
| 1 | Create user model with password hashing | Dozer | sonnet | M | None | `src/db/schema/users.ts`, `src/db/migrations/001-users.ts` |
| 2 | Implement signup endpoint (POST /api/auth/signup) | Dozer | sonnet | M | Ticket 1 | `src/api/auth/signup.ts` |
| 3 | Implement login endpoint with {auth_strategy} (POST /api/auth/login) | Dozer | sonnet | M | Ticket 1 | `src/api/auth/login.ts`, `src/lib/jwt.ts` |
| 4 | Create auth middleware for protected routes | Dozer | sonnet | M | Ticket 3 | `src/middleware/auth.ts` |
| 5 | Implement logout and session invalidation | Dozer | sonnet | S | Ticket 3 | `src/api/auth/logout.ts` |
| 6 | Write auth integration tests | Switch | sonnet | L | Ticket 2, Ticket 3, Ticket 4, Ticket 5 | `src/__tests__/auth.integration.test.ts` |

### Dependency Graph

```
[1] User Model + Hashing
      |
      +--------+--------+
      |                  |
      v                  v
[2] Signup          [3] Login + JWT
                         |
                    +----+----+
                    |         |
                    v         v
               [4] Auth    [5] Logout
               Middleware
                    |         |
                    +----+----+
                         |
                         v
                 [6] Auth Tests
```

Execution groups:
- Group 1: Ticket 1 (user model is foundation)
- Group 2: Tickets 2, 3 (signup and login can be built in parallel)
- Group 3: Tickets 4, 5 (middleware and logout both depend on login/JWT)
- Group 4: Ticket 6 (tests verify everything)

### Filled Example

PRD section: *"Users register with email, password, and display name. They log in with email/password and receive a JWT valid for 7 days. All /api/ routes except /api/auth/* require authentication."*

| # | ID | Title | Agent | Size |
|---|----|-------|-------|------|
| 1 | TICKET-001 | Create user model with bcrypt password hashing | Dozer | M |
| 2 | TICKET-002 | Implement signup endpoint (POST /api/auth/signup) | Dozer | M |
| 3 | TICKET-003 | Implement login endpoint with JWT (POST /api/auth/login) | Dozer | M |
| 4 | TICKET-004 | Create auth middleware for /api/* routes | Dozer | M |
| 5 | TICKET-005 | Implement logout and JWT invalidation | Dozer | S |
| 6 | TICKET-006 | Write auth integration tests (signup, login, middleware, logout) | Switch | L |

```json
{
  "id": "TICKET-003",
  "title": "Implement login endpoint with JWT (POST /api/auth/login)",
  "description": "Create POST /api/auth/login endpoint. Accepts email and password, validates against the database using bcrypt comparison, and returns a signed JWT with 7-day expiry on success. JWT payload includes user id, email, and role. Must handle invalid credentials, missing fields, and rate limiting (5 attempts per minute per IP).",
  "agent": "dozer",
  "model": "sonnet",
  "dependencies": ["TICKET-001"],
  "files": ["src/api/auth/login.ts", "src/lib/jwt.ts"],
  "acceptance_criteria": [
    "Endpoint accepts email + password via POST body",
    "Returns signed JWT with 7-day expiry on valid credentials",
    "JWT payload contains user id, email, and role",
    "Returns 401 with generic message on invalid credentials",
    "Returns 400 on missing or malformed input",
    "Input validated with Zod",
    "Rate limited to 5 attempts per minute per IP"
  ]
}
```

---

## Template 3: CRUD_RESOURCE

**When the Oracle uses this:** Any entity in the PRD that requires full create-read-update-delete operations. This is the workhorse template -- most data-driven applications have multiple CRUD resources. The Oracle instantiates this template once per entity, then wires them together based on relationships (e.g., a project has many tasks, so the tasks CRUD depends on the projects CRUD).

### Recognition Triggers

- PRD describes an entity that users create, view, edit, and delete
- PRD uses CRUD-like language for a data object
- Entity has clear fields/attributes listed in the PRD
- Keywords: "manage {entities}", "add/edit/delete {entity}", "CRUD", "{entity} list with detail view", "users can create and update {entities}"

### Variables

| Variable | Source | Example |
|----------|--------|---------|
| `{entity_name}` | The resource being managed | "task" |
| `{entity_plural}` | Plural form for routes/collections | "tasks" |
| `{entity_fields}` | Fields from the PRD | "title, description, status, assignee_id, due_date" |
| `{endpoint_base}` | API route prefix | "/api/tasks" |
| `{parent_entity}` | Parent resource if nested | "project" |
| `{validation_rules}` | Business rules for the entity | "title required, due_date must be future" |
| `{ui_type}` | List/table/card layout preference | "table with detail modal" |

### Ticket Table

| # | Title | Agent | Model | Size | Dependencies | Files |
|---|-------|-------|-------|------|-------------|-------|
| 1 | Create `{entity_name}` database model and migration | Dozer | sonnet | M | None | `src/db/schema/{entity_plural}.ts`, `src/db/migrations/xxx-{entity_plural}.ts` |
| 2 | Implement create `{entity_name}` endpoint (POST `{endpoint_base}`) | Dozer | sonnet | M | Ticket 1 | `src/api/{entity_plural}/create.ts` |
| 3 | Implement read `{entity_name}` endpoints (GET `{endpoint_base}`, GET `{endpoint_base}/:id`) | Dozer | sonnet | M | Ticket 1 | `src/api/{entity_plural}/read.ts` |
| 4 | Implement update `{entity_name}` endpoint (PUT `{endpoint_base}/:id`) | Dozer | sonnet | S | Ticket 1 | `src/api/{entity_plural}/update.ts` |
| 5 | Implement delete `{entity_name}` endpoint (DELETE `{endpoint_base}/:id`) | Dozer | sonnet | S | Ticket 1 | `src/api/{entity_plural}/delete.ts` |
| 6 | Build `{entity_name}` CRUD UI (list + detail + forms) | Niobe | sonnet | L | Ticket 2, Ticket 3 | `src/components/{entity_plural}/*.tsx` |
| 7 | Write `{entity_name}` CRUD tests | Switch | sonnet | M | Ticket 2, Ticket 3, Ticket 4, Ticket 5 | `src/__tests__/{entity_plural}.test.ts` |

### Dependency Graph

```
        [1] DB Model + Migration
         |
    +----+----+----+----+
    |    |    |         |
    v    v    v         v
  [2] [3]  [4]       [5]
  Create Read Update  Delete
    |    |    |         |
    +--+-+    +----+----+
       |           |
       v           |
  [6] CRUD UI      |
       |           |
       +-----+-----+
             |
             v
       [7] CRUD Tests
```

Execution groups:
- Group 1: Ticket 1 (database model is foundation)
- Group 2: Tickets 2, 3, 4, 5 (all endpoints can be built in parallel once model exists)
- Group 3: Ticket 6 (UI needs at least create + read endpoints)
- Group 4: Ticket 7 (tests verify everything)

### Filled Example

PRD section: *"Users can manage tasks within a project. Each task has a title, description, status (todo/in-progress/done), optional assignee, and due date. Tasks are displayed in a table with inline status editing."*

| # | ID | Title | Agent | Size |
|---|----|-------|-------|------|
| 1 | TICKET-010 | Create task database model and migration | Dozer | M |
| 2 | TICKET-011 | Implement create task endpoint (POST /api/tasks) | Dozer | M |
| 3 | TICKET-012 | Implement read task endpoints (GET /api/tasks, GET /api/tasks/:id) | Dozer | M |
| 4 | TICKET-013 | Implement update task endpoint (PUT /api/tasks/:id) | Dozer | S |
| 5 | TICKET-014 | Implement delete task endpoint (DELETE /api/tasks/:id) | Dozer | S |
| 6 | TICKET-015 | Build task CRUD UI (table view with detail modal and forms) | Niobe | L |
| 7 | TICKET-016 | Write task CRUD tests | Switch | M |

```json
{
  "id": "TICKET-011",
  "title": "Implement create task endpoint (POST /api/tasks)",
  "description": "Create POST /api/tasks endpoint. Accepts title (required string), description (optional string), status (enum: todo/in-progress/done, defaults to todo), assignee_id (optional uuid, FK to users), due_date (optional ISO date, must be in the future if provided), and project_id (required uuid, FK to projects). Returns the created task with 201 status. Requires authentication.",
  "agent": "dozer",
  "model": "sonnet",
  "dependencies": ["TICKET-010"],
  "files": ["src/api/tasks/create.ts"],
  "acceptance_criteria": [
    "Endpoint accepts all task fields via POST body",
    "Title is required, returns 400 if missing",
    "Status defaults to 'todo' if not provided",
    "due_date must be a future date if provided",
    "project_id must reference an existing project",
    "Returns 201 with created task on success",
    "Input validated with Zod",
    "Requires valid JWT (auth middleware)"
  ]
}
```

---

## Template 4: REALTIME_FEATURE

**When the Oracle uses this:** Any feature that requires pushing data from server to client without polling -- live updates, collaborative editing, real-time notifications, chat, activity feeds, or any feature where the PRD says users should see changes "instantly" or "in real time."

### Recognition Triggers

- PRD describes live/real-time updates to the UI
- PRD mentions data that should appear without page refresh
- Features involving collaboration, live feeds, or instant notifications
- Keywords: "real-time", "live updates", "instant notifications", "WebSocket", "SSE", "collaborative", "live feed", "push notifications", "users see changes immediately"

### Variables

| Variable | Source | Example |
|----------|--------|---------|
| `{feature_name}` | The real-time feature | "Live Notifications" |
| `{transport}` | WebSocket or SSE (Oracle decides based on PRD) | "WebSocket" |
| `{event_types}` | Types of events to handle | "task.created, task.updated, comment.added" |
| `{channel_strategy}` | How connections are organized | "per-project room" |
| `{auth_required}` | Whether connections need authentication | true |

### Ticket Table

| # | Title | Agent | Model | Size | Dependencies | Files |
|---|-------|-------|-------|------|-------------|-------|
| 1 | Set up `{transport}` server infrastructure | Dozer | sonnet | M | None | `src/lib/websocket.ts`, `src/api/ws.ts` |
| 2 | Implement `{feature_name}` event handlers | Dozer | sonnet | M | Ticket 1 | `src/events/{feature_name_lower}.ts` |
| 3 | Build client-side `{transport}` connection and state management | Niobe | sonnet | M | Ticket 1 | `src/hooks/use-{feature_name_lower}.ts`, `src/lib/ws-client.ts` |
| 4 | Add reconnection logic with exponential backoff | Keymaker | haiku | S | Ticket 3 | `src/lib/ws-client.ts` |
| 5 | Write `{feature_name}` real-time tests | Switch | sonnet | M | Ticket 2, Ticket 3 | `src/__tests__/{feature_name_lower}.realtime.test.ts` |

### Dependency Graph

```
[1] Server Infrastructure
      |
      +--------+
      |        |
      v        v
[2] Event   [3] Client
Handlers    Connection
      |        |
      |        v
      |   [4] Reconnection
      |        |
      +---+----+
          |
          v
    [5] RT Tests
```

Execution groups:
- Group 1: Ticket 1 (server must exist first)
- Group 2: Tickets 2, 3 (handlers and client can be built in parallel)
- Group 3: Ticket 4 (reconnection augments the client)
- Group 4: Ticket 5 (tests verify the full real-time pipeline)

### Filled Example

PRD section: *"When a team member creates or updates a task, all other team members viewing the same project should see the change reflected immediately without refreshing. Use WebSocket connections scoped to the project."*

| # | ID | Title | Agent | Size |
|---|----|-------|-------|------|
| 1 | TICKET-020 | Set up WebSocket server with per-project rooms | Dozer | M |
| 2 | TICKET-021 | Implement task event handlers (task.created, task.updated, task.deleted) | Dozer | M |
| 3 | TICKET-022 | Build client-side WebSocket hook and state management | Niobe | M |
| 4 | TICKET-023 | Add WebSocket reconnection with exponential backoff | Keymaker | S |
| 5 | TICKET-024 | Write real-time task sync tests | Switch | M |

```json
{
  "id": "TICKET-020",
  "title": "Set up WebSocket server with per-project rooms",
  "description": "Initialize WebSocket server (ws library) alongside the existing HTTP server. Implement room-based connection management where each project ID maps to a room. Clients join a room by sending a 'join' message with project_id after connecting. Authentication is required -- validate JWT from the connection handshake query parameter. Track connected clients per room for targeted broadcasting. Handle connection cleanup on disconnect.",
  "agent": "dozer",
  "model": "sonnet",
  "dependencies": [],
  "files": ["src/lib/websocket.ts", "src/api/ws.ts"],
  "acceptance_criteria": [
    "WebSocket server starts alongside HTTP server",
    "Clients authenticate via JWT in connection handshake",
    "Clients can join project-scoped rooms",
    "Server tracks active connections per room",
    "Disconnected clients are cleaned up from rooms",
    "Invalid JWT rejects connection with 4001 close code"
  ]
}
```

---

## Template 5: API_INTEGRATION

**When the Oracle uses this:** Any PRD section that requires calling an external third-party API -- payment processing, email services, cloud storage, social auth providers, analytics, or any feature that depends on an external system the application does not control.

### Recognition Triggers

- PRD references an external service or third-party API
- Feature depends on data or functionality from outside the application
- PRD mentions specific services (Stripe, SendGrid, S3, OAuth providers, etc.)
- Keywords: "integrate with {service}", "use {provider} API", "send emails via", "process payments through", "fetch data from {external_source}", "third-party", "webhook"

### Variables

| Variable | Source | Example |
|----------|--------|---------|
| `{service_name}` | The external service | "Stripe" |
| `{service_name_lower}` | Lowercase for file names | "stripe" |
| `{api_operations}` | Operations needed from the API | "create charge, create customer, list invoices" |
| `{auth_method}` | How the API authenticates | "API key in header" |
| `{rate_limit}` | Known rate limits for the API | "100 req/sec" |
| `{webhook_events}` | Inbound webhook events to handle (if any) | "payment.succeeded, payment.failed" |
| `{env_vars}` | Required environment variables | "STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET" |

### Ticket Table

| # | Title | Agent | Model | Size | Dependencies | Files |
|---|-------|-------|-------|------|-------------|-------|
| 1 | Create `{service_name}` API client and wrapper | Dozer | sonnet | M | None | `src/lib/{service_name_lower}-client.ts` |
| 2 | Add error handling and retry logic for `{service_name}` | Dozer | sonnet | M | Ticket 1 | `src/lib/{service_name_lower}-client.ts` |
| 3 | Implement rate limiting for `{service_name}` calls | Keymaker | haiku | S | Ticket 1 | `src/lib/rate-limiter.ts` |
| 4 | Build `{service_name}` integration endpoints | Dozer | sonnet | M | Ticket 1, Ticket 2 | `src/api/{service_name_lower}/*.ts` |
| 5 | Write `{service_name}` mock tests | Switch | sonnet | M | Ticket 1, Ticket 4 | `src/__tests__/{service_name_lower}.test.ts`, `src/__tests__/mocks/{service_name_lower}.ts` |

### Dependency Graph

```
[1] API Client/Wrapper
      |
  +---+---+
  |       |
  v       v
[2]     [3]
Error   Rate
Handling Limiting
  |
  v
[4] Integration Endpoints
  |
  v
[5] Mock Tests
```

Execution groups:
- Group 1: Ticket 1 (client wrapper is the foundation)
- Group 2: Tickets 2, 3 (error handling and rate limiting are independent)
- Group 3: Ticket 4 (endpoints need the hardened client)
- Group 4: Ticket 5 (tests mock the external API)

### Filled Example

PRD section: *"The application processes payments through Stripe. Users can subscribe to a plan (monthly/yearly), update their payment method, and view invoice history. Handle payment.succeeded and payment.failed webhooks."*

| # | ID | Title | Agent | Size |
|---|----|-------|-------|------|
| 1 | TICKET-030 | Create Stripe API client wrapper | Dozer | M |
| 2 | TICKET-031 | Add error handling and retry logic for Stripe calls | Dozer | M |
| 3 | TICKET-032 | Implement rate limiting for Stripe API calls | Keymaker | S |
| 4 | TICKET-033 | Build Stripe integration endpoints (subscribe, update payment, invoices, webhooks) | Dozer | M |
| 5 | TICKET-034 | Write Stripe mock tests | Switch | M |

```json
{
  "id": "TICKET-030",
  "title": "Create Stripe API client wrapper",
  "description": "Build a typed wrapper around the Stripe Node SDK. Encapsulate customer creation, subscription management, payment method updates, and invoice listing behind a clean interface. Read STRIPE_SECRET_KEY from environment variables (never hardcode). Export Zod schemas for all Stripe-related request and response types used by the application. Include TypeScript types for webhook event payloads (payment.succeeded, payment.failed).",
  "agent": "dozer",
  "model": "sonnet",
  "dependencies": [],
  "files": ["src/lib/stripe-client.ts"],
  "acceptance_criteria": [
    "Wrapper initializes Stripe SDK with env var STRIPE_SECRET_KEY",
    "Exposes typed methods: createCustomer, createSubscription, updatePaymentMethod, listInvoices",
    "Zod schemas validate all request inputs",
    "TypeScript types cover webhook event payloads",
    "No secrets hardcoded anywhere",
    "Follows immutable patterns (no mutation of Stripe objects)"
  ]
}
```

---

## Template Composition

The Oracle frequently combines multiple templates for a single PRD. When composing templates, these rules govern cross-template dependencies:

### Composition Rules

1. **AUTHENTICATION_FLOW is almost always first.** If the PRD requires auth, the auth template is instantiated before any other template. Other templates' tickets that need authentication add a dependency on the auth middleware ticket (Template 2, Ticket 4).

2. **CRUD_RESOURCE can be instantiated multiple times.** One instance per entity. If entities have relationships (e.g., projects contain tasks), the child entity's model ticket depends on the parent entity's model ticket.

3. **FULL_STACK_FEATURE is for non-CRUD features.** Dashboards, analytics views, search pages -- things that read data but do not follow the standard CRUD pattern. If the feature also needs CRUD, use `CRUD_RESOURCE` instead.

4. **REALTIME_FEATURE augments other templates.** The real-time server ticket has no dependencies on other templates, but the event handler tickets typically depend on the CRUD endpoints they are reacting to.

5. **API_INTEGRATION is independent until the endpoint tickets.** The client wrapper and error handling are self-contained. The integration endpoints ticket depends on whichever application feature triggers the external call.

### Composition Example

PRD: *"A project management app where authenticated users manage projects and tasks. Task updates are shown in real time. Payments are processed through Stripe."*

The Oracle instantiates:

```
AUTHENTICATION_FLOW -----> auth tickets (TICKET-001 to TICKET-006)
CRUD_RESOURCE (project) -> project CRUD tickets (TICKET-007 to TICKET-013)
CRUD_RESOURCE (task) ----> task CRUD tickets (TICKET-014 to TICKET-020)
REALTIME_FEATURE --------> real-time tickets (TICKET-021 to TICKET-025)
API_INTEGRATION (Stripe)-> Stripe tickets (TICKET-026 to TICKET-030)
```

Cross-template dependencies the Oracle adds:
- TICKET-007 (project model) depends on TICKET-004 (auth middleware)
- TICKET-014 (task model) depends on TICKET-007 (project model, FK relationship)
- TICKET-021 (WS server) depends on TICKET-004 (auth middleware, for connection auth)
- TICKET-022 (task event handlers) depends on TICKET-014 (task endpoints to react to)
- TICKET-029 (Stripe endpoints) depends on TICKET-004 (auth middleware)

This produces an execution plan of approximately 8-10 groups, with maximum parallelism within each group.

---

## Notes for the Oracle

These blueprints are starting points, not rigid contracts. The Oracle should:

1. **Adjust ticket granularity** based on PRD complexity. A simple CRUD entity might collapse tickets 4 and 5 (update and delete) into a single ticket. A complex one might split ticket 6 (UI) into multiple tickets per view.

2. **Promote model tiers** when the PRD signals complexity. If the PRD describes an unusually complex authentication scheme (multi-factor, OAuth2 with PKCE, etc.), the Oracle should consider promoting auth tickets from sonnet to opus.

3. **Add tickets not in the template** when the PRD requires it. Templates cover common patterns, but if a feature needs something unique -- say, a PDF export endpoint or a background job -- the Oracle adds custom tickets alongside the template tickets.

4. **Skip tickets that are not needed.** If the PRD says "read-only dashboard" for an entity, the Oracle should not instantiate the full CRUD template. Use FULL_STACK_FEATURE instead, or instantiate CRUD_RESOURCE and drop the create/update/delete tickets.

5. **Consider memory.** If procedural memory contains a "Stripe integration" strategy from a previous session with high confidence, the Oracle should reference that strategy when filling in the API_INTEGRATION template for Stripe.

*"I told you I would find you. I am going to enjoy watching you build."*
