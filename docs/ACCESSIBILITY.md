# Accessibility

AniBench targets WCAG 2.2 Level AA for the browser explorer, documentation, and
release figures. This is a target and release gate, not a claim that a complete
independent accessibility audit has already passed.

## Browser explorer

- All functions must be available by keyboard with a visible focus indicator.
- Heading order, landmarks, form labels, table headers, and status messages must
  expose meaningful semantics to assistive technology.
- Controls must have accessible names that describe the action and current
  state. Instructions cannot depend only on position, shape, or color.
- Text and essential graphics must meet AA contrast. Focus indicators and
  component boundaries must remain visible in all supported themes.
- Zoom to 200 percent and narrow reflow must preserve content and operation
  without two-dimensional scrolling except for intrinsically tabular content.
- Validation errors must identify the field, explain the correction, and remain
  discoverable without color or sound.
- Motion must respect `prefers-reduced-motion`; AniBench must not require
  animation to interpret a result.

## Figures and tables

- Every score-bearing figure must have a nearby text summary stating the
  construct, unit or scale, comparison set, uncertainty, and evidence class.
- Color palettes must be distinguishable under common color-vision
  deficiencies. Red/green opposition alone cannot encode pass/fail.
- Lines, groups, and states need redundant labels, markers, patterns, or direct
  annotation.
- SVGs require useful titles/descriptions when embedded as content. Decorative
  images use empty alternative text.
- Data tables must have machine-readable headers and an equivalent downloadable
  data artifact where release rights permit.
- Raster figures are not the sole carrier of exact values.

## Documents and command-line output

- Markdown uses descriptive links, real lists, logical headings, and simple
  tables with explicit headers.
- Generated PDFs require tagged structure, reading-order inspection, embedded
  fonts, document language, title metadata, bookmarks for long documents, and
  alternative descriptions for informative figures.
- Command output uses text labels in addition to color and preserves useful
  errors when color is disabled.

## Release verification

- [ ] Keyboard-only pass over every explorer route and interactive control.
- [ ] Automated accessibility scan with zero unresolved critical or serious
  findings.
- [ ] Manual screen-reader pass over navigation, one score interpretation, one
  table, one error state, and one download flow.
- [ ] Contrast and color-vision simulation for every visualization palette.
- [ ] 200 percent zoom and narrow-viewport reflow pass.
- [ ] Reduced-motion pass.
- [ ] PDF reading order, tags, metadata, and figure alternatives inspected.
- [ ] Accessibility defects are recorded with version, route/artifact, severity,
  reproduction steps, and remediation owner.

The release record must name the tools, versions, operating system, browser,
assistive technology, artifacts tested, findings, and remaining exceptions.
Absence of a finding record is `not_tested`, not a pass.

