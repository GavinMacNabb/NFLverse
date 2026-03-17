---
name: frontend-agent
description: Use this skill when designing, architecting, implementing, or reviewing user interfaces for Wails desktop applications with Go backends and React TypeScript frontends, especially MSP network discovery and customer onboarding tools. It helps with technician operational views, client presentation reports, Tailwind CSS v4 styling, React Aria Components, and nested React Router layouts.
---

# Frontend Agent

This skill is for UI work on a Wails desktop application that combines a Go backend with a React TypeScript frontend.

Default stack:

- React
- TypeScript
- Tailwind CSS v4
- React Aria Components
- React Router with `createHashRouter`
- Nested routes with an app layout and `Outlet`

Default product context:

- MSP network discovery
- Customer onboarding
- Technician operational views
- Client-facing presentation reports

Read bundled references as needed:

- For the Technical Droid design language and component defaults:
  `references/design-system.md`
- For layout, routing, and shell patterns:
  `references/routing-layout.md`
- For implementation scaffolds you can adapt directly:
  `assets/technical-droid-shell.tsx`
  `assets/technical-data-panel.tsx`

## Primary Goals

1. Translate UI requirements into semantic, accessible code.
2. Recommend maintainable component structure and state boundaries.
3. Apply responsive design patterns correctly.
4. Optimize for performance and maintainability.

## Technical Droid Style

Follow a precise, operational design language.

- Typography:
  Use `font-mono` for values, labels, technical indicators, and headers.
- Visual style:
  Prefer flat surfaces or restrained borders.
  Do not use glow effects or excessive neon shadows.
- Components:
  Use sharp or slightly rounded corners such as `rounded-sm`.
  Cards should rely on border treatment like `border-base-300` or `border-primary/30`.
  Avoid decorative shadow-heavy styling unless the existing product already uses it.
- Labeling:
  Standard label style is `text-base-content/60 text-xs font-mono`.
- Layout:
  Keep pages compact and information-dense while preserving readability.
  Prefer spacing systems such as `space-y-5` and `space-y-6`.
  Pages must fit within the browser width without causing whole-page horizontal overflow.
  If a data view is wider than the viewport, constrain overflow to the component itself.

## Implementation Rules

- Provide concrete code examples.
- Prefer semantic HTML with explicit accessibility support.
- Use React Aria Components for advanced interactive patterns where accessibility matters.
- Use React Router patterns consistent with nested Wails app navigation:
  `Outlet`, `useNavigate`, `useLocation`, and route-aware layouts.
- Keep examples aligned with pages such as:
  `Dashboard`, `Scans`, `Networks`, `Hosts`, `Alerts`, `Domains`, and `Summary`.
- Be specific about:
  component boundaries,
  utility classes,
  event handling,
  keyboard behavior,
  layout structure,
  and state ownership.
- Keep layouts viewport-safe:
  the overall page should fit within the browser width,
  and any horizontal scrolling should be isolated to bounded components such as tables.
- When reviewing existing UI code, focus on:
  usability,
  accessibility,
  performance,
  and maintainability.

## Default Architecture Guidance

Use these defaults unless the codebase clearly prefers something else:

- App shell:
  persistent side navigation, top header, nested page content via `Outlet`
- Navigation:
  use `useLocation()` for active-state rendering
- Composition:
  route container -> feature sections -> focused presentational components
- State:
  keep state local unless multiple siblings need coordinated behavior
- Data-heavy screens:
  prioritize sorting, filtering, keyboard access, and readable monospace values
  while keeping page-level overflow contained to the viewport

## Good Defaults

- Technical labels:
  `text-base-content/60 text-xs font-mono uppercase tracking-[0.18em]`
- Dense card shell:
  `rounded-sm border border-base-300 bg-base-100`
- Page rhythm:
  `space-y-5`
- Data layouts:
  `grid gap-4 xl:grid-cols-12`
- Header blocks:
  keep title, operational description, and status indicators together

## Using Bundled Resources

- Use the references for concrete design constraints before proposing new UI structure.
- Use the assets as implementation scaffolds, not as immutable templates.
- Preserve existing product patterns when the codebase already has a stronger local convention.

## Review Checklist

For frontend reviews, check:

- Is the page hierarchy obvious?
- Are primary actions clear?
- Is the information density high but still scannable?
- Does the page fit within the browser width without global horizontal scrolling?
- Are keyboard and screen-reader paths covered?
- Are component responsibilities clear?
- Does the implementation follow router and layout conventions?
- Does the styling stay within the Technical Droid direction?

## Clarifying Questions

If key constraints are missing, ask concise questions before proposing design or implementation:

- Which platform matters most: macOS, Windows, or Linux?
- Is this a new page, a redesign, or a refactor?
- Should it follow an existing component system or start fresh?
- Is the priority technician workflow speed, client presentation quality, or both?

Ask only what is necessary to avoid guessing.
