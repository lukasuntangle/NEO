# PRD: TaskFlow — Simple Todo Application

## Overview
TaskFlow is a minimal todo application with user authentication, task management, and basic collaboration features. Built with Next.js, TypeScript, and SQLite.

## Goals
- Users can create an account, log in, and manage personal todo lists
- Tasks support title, description, due date, priority, and status
- Users can share lists with other users (read-only)
- Clean, accessible UI with keyboard shortcuts
- 80% test coverage minimum

## Tech Stack
- **Frontend:** Next.js 14 (App Router), React, TypeScript, Tailwind CSS
- **Backend:** Next.js API Routes, Zod validation
- **Database:** SQLite via better-sqlite3
- **Auth:** JWT-based (jose library)
- **Testing:** Vitest + React Testing Library + Playwright

## User Stories

### Authentication
1. As a user, I can sign up with email and password
2. As a user, I can log in with my credentials
3. As a user, I can log out
4. As a user, my session persists across page reloads (JWT in httpOnly cookie)

### Task Management
5. As a user, I can create a new task with title (required), description, due date, and priority (low/medium/high)
6. As a user, I can view all my tasks in a list, sorted by due date
7. As a user, I can mark a task as complete/incomplete (toggle)
8. As a user, I can edit a task's details
9. As a user, I can delete a task (with confirmation)
10. As a user, I can filter tasks by status (all/active/completed) and priority

### Lists
11. As a user, I can create named lists to organize tasks
12. As a user, I can move tasks between lists
13. As a user, I have a default "Inbox" list

### Sharing
14. As a user, I can share a list with another user by email (read-only)
15. As a user, I can view lists shared with me
16. As a user, I can revoke sharing access

### UI/UX
17. Keyboard shortcut: `n` to create new task
18. Keyboard shortcut: `j/k` to navigate tasks
19. Keyboard shortcut: `x` to toggle completion
20. Responsive design (mobile-first)
21. WCAG 2.1 AA accessible

## API Endpoints

### Auth
- `POST /api/auth/signup` — Create account
- `POST /api/auth/login` — Login, returns JWT
- `POST /api/auth/logout` — Clear session

### Tasks
- `GET /api/tasks?list={id}&status={status}&priority={priority}` — List tasks
- `POST /api/tasks` — Create task
- `PATCH /api/tasks/:id` — Update task
- `DELETE /api/tasks/:id` — Delete task

### Lists
- `GET /api/lists` — Get user's lists
- `POST /api/lists` — Create list
- `PATCH /api/lists/:id` — Update list
- `DELETE /api/lists/:id` — Delete list

### Sharing
- `POST /api/lists/:id/share` — Share list with user
- `DELETE /api/lists/:id/share/:userId` — Revoke access
- `GET /api/shared` — Get lists shared with me

## Database Schema

### users
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (UUID) | Primary key |
| email | TEXT | Unique, not null |
| password_hash | TEXT | bcrypt hash |
| created_at | TEXT | ISO 8601 |

### lists
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (UUID) | Primary key |
| user_id | TEXT | Foreign key → users |
| name | TEXT | Not null |
| is_default | INTEGER | Boolean, default 0 |
| created_at | TEXT | ISO 8601 |

### tasks
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (UUID) | Primary key |
| list_id | TEXT | Foreign key → lists |
| title | TEXT | Not null |
| description | TEXT | Nullable |
| due_date | TEXT | ISO 8601, nullable |
| priority | TEXT | low/medium/high |
| status | TEXT | active/completed |
| created_at | TEXT | ISO 8601 |
| updated_at | TEXT | ISO 8601 |

### list_shares
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (UUID) | Primary key |
| list_id | TEXT | Foreign key → lists |
| shared_with | TEXT | Foreign key → users |
| created_at | TEXT | ISO 8601 |

## Non-Functional Requirements
- Page load < 1s on 3G
- All inputs validated server-side with Zod
- No console.log in production code
- Conventional commits
- SQL injection prevention (parameterized queries)
- XSS prevention (React's built-in escaping + CSP headers)

## Out of Scope
- Real-time collaboration (future)
- File attachments (future)
- Mobile native app (future)
- OAuth / social login (future)
