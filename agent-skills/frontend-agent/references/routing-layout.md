# Routing And Layout

Use this reference when designing route structures or app shells for the target stack.

## Expected Router Shape

- `createHashRouter`
- App-level layout route
- `Outlet` for child views

Typical route set:

- `Dashboard`
- `Scans`
- `Networks`
- `Hosts`
- `Alerts`
- `Domains`
- `Summary`

## Layout Defaults

- Persistent left navigation
- Top header with page context and status indicators
- Main area split into:
  summary row,
  section panels,
  dense data views

## Recommended Component Boundaries

- `AppShell`
  overall navigation and frame
- `AppSidebar`
  route groups and current selection
- `AppHeader`
  page title, context, quick actions
- `PageSection`
  reusable section wrapper with title and metadata
- `DataPanel`
  compact bordered block for tables, logs, or metrics

## State Guidance

- Use route state for page context
- Use local component state for view-only interactions
- Lift state only when multiple siblings truly share behavior

## Review Heuristics

- Can a technician identify current scope within a few seconds?
- Are the primary next actions visible without hunting?
- Does the shell stay usable on a narrower desktop window?
- Is keyboard navigation obvious and intact?
