# Technical Droid Design System

Use this reference when translating the skill into actual UI code.

## Tone

- Operational
- Precise
- Compact
- Calm under load

Avoid:

- glossy gradients as the primary visual identity
- glows, neon shadows, or decorative chrome
- oversized hero sections that waste space

## Typography

- Default to `font-mono`
- Use uppercase technical labels sparingly for structure, not everywhere
- Make values, identifiers, row counts, and section labels monospace

Recommended label treatment:

```text
text-base-content/60 text-xs font-mono uppercase tracking-[0.18em]
```

## Surfaces

- Prefer `rounded-sm`
- Prefer visible borders over shadows
- Keep surfaces flat or nearly flat
- Use subtle contrast between shell, panel, and active states

## Dense Layout Patterns

- Page shell:
  side nav + top header + main content
- Viewport fit:
  the page itself should fit within browser width at every supported breakpoint
  and must not rely on whole-page horizontal scrolling
- Section rhythm:
  `space-y-5` or `space-y-6`
- Dense dashboards:
  `grid gap-4 xl:grid-cols-12`
- Summary panels:
  small labels, one strong number, one short operational note

## Navigation

- Make active state obvious through border, background, or left rule
- Keep nav copy short
- Group items by workflow, not by arbitrary component type

## Data Views

- Show grain and scope early
- Keep filter state visible
- Highlight operational facts:
  counts, last update, scope, current selection
- Use sticky headers for wide tables when practical
- If a data view exceeds the viewport width, contain horizontal scrolling inside that panel only

## Accessibility

- Preserve visible focus styles
- Keep color contrast high
- Use ARIA labels for icon-only controls
- Never make critical state color-only
