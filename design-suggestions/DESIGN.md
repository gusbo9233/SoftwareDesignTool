# Design System Specification: The Engineering Editorial

## 1. Overview & Creative North Star: "The Technical Architect"
This design system rejects the "toy-like" roundness of modern SaaS in favor of a high-density, professional environment inspired by IDEs and architectural blueprints. Our Creative North Star is **"The Technical Architect"**—a philosophy that treats software design as a rigorous discipline. 

The aesthetic moves beyond "clean" into "precise." We break the standard web template by utilizing asymmetric layouts, varying content densities, and a sophisticated layering system that favors tonal depth over structural lines. It is designed to feel like a high-end instrument: efficient, low-friction, and unapologetically technical.

---

## 2. Colors & Surface Philosophy

### The "No-Line" Rule
Traditional 1px borders are strictly prohibited for sectioning. They create visual noise and "box in" the user. Instead, define boundaries through background shifts. A sidebar uses `surface-container-low`, the main canvas uses `surface`, and inspector panels use `surface-container-high`. This creates a seamless flow of information.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical, stacked layers.
- **Base Layer:** `surface` (#f8f9fa) — The primary workspace.
- **Recessed Areas:** `surface-container` (#eaeff1) — Used for inactive panels.
- **Elevated Interactive Elements:** `surface-container-lowest` (#ffffff) — Used for active cards or editable document areas to provide "pop" against the background.

### The "Glass & Gradient" Rule
To prevent the UI from feeling "flat" or "dead," use semi-transparent `surface-variant` with a `backdrop-blur` (12px–20px) for floating overlays, such as command palettes or context menus. 
- **CTA Soul:** Primary actions (`primary` #005db5) should use a subtle linear gradient transitioning into `primary-dim` (#0052a0) at a 135-degree angle. This adds a "machined" metallic depth to buttons that flat colors cannot achieve.

---

## 3. Typography: Structural Clarity

The typography system is split between **Inter** (Proportional) for administrative UI and **Space Grotesk** (Monospaced lean) for data and technical labels.

- **Display & Headlines:** Use `display-md` and `headline-sm` with tight letter-spacing (-0.02em). These should feel authoritative and editorial, often placed with intentional asymmetry (e.g., flush-left headers with wide-right margins).
- **The Data Layer:** `label-md` using **Space Grotesk** is the workhorse for metadata, timestamps, and status tags. This creates the "coding editor" feel, signaling to the user that this information is technical and precise.
- **Body:** `body-md` (Inter) is reserved for documentation and requirements, optimized for long-form readability with a generous 1.5 line-height.

---

## 4. Elevation & Depth: Tonal Layering

We convey hierarchy through **Tonal Layering** rather than drop shadows or lines.

- **The Layering Principle:** To lift a component, don't reach for a shadow; reach for a lighter surface token. Place a `surface-container-lowest` card on top of a `surface-container-low` section. The contrast is enough to define the object without cluttering the viewport.
- **Ambient Shadows:** Only for floating modals. Use the `on-surface` color (#2b3437) at 4% opacity with a 32px blur and 16px Y-offset. It should feel like a soft glow, not a dark stain.
- **The "Ghost Border" Fallback:** If a divider is mandatory for accessibility in high-density tables, use `outline-variant` (#abb3b7) at **15% opacity**. It should be felt, not seen.

---

## 5. Components

### Buttons: The Precision Triggers
- **Primary:** Gradient from `primary` to `primary-dim`. `sm` (2px) corner radius. No border.
- **Secondary:** Surface-tinted. Use `secondary-container` text on `surface` background.
- **States:** Hover states should not lighten; they should increase the "inner glow" via a 1px inset `primary-fixed-dim` shadow.

### Cards: Content Containers
Forbid divider lines. Use `surface-container-low` for the card body and `surface-container-lowest` for the "header" area of the card. This internal tonal shift creates natural organization.

### Tables: Data Grids
- **Header:** `label-sm` (Space Grotesk) in `on-surface-variant`.
- **Row Separation:** No horizontal lines. Use a subtle `surface-container-highest` background fill on hover to highlight the active row.
- **Density:** High. Cell padding should be `0.5rem` vertical to maximize data visibility.

### Sidebar Navigation
Use a "Deep Dock" approach. The sidebar uses `surface-dim` (#d1dce0) to ground the application. Active items are indicated by a `primary` vertical bar (2px wide) and a shift to `surface-bright`.

### Custom Component: The "Document Tag"
For different document types (Diagrams, Requirements, Code), use muted tertiary tokens:
- **Diagrams:** `tertiary-container` text on `tertiary-fixed-dim`.
- **Requirements:** `secondary-container` text on `secondary-fixed-dim`.

---

## 6. Do’s and Don’ts

### Do:
- **Do** embrace "White Space as Logic." Use spacing to group related technical requirements rather than boxes.
- **Do** use `Space Grotesk` for any value that can be measured (numbers, dates, file sizes).
- **Do** use the `sm` (0.125rem) or `md` (0.375rem) corner radius for a sharp, "engineered" look.

### Don't:
- **Don't** use `xl` (0.75rem) or `full` rounded corners; they are too "consumer-grade" for this system.
- **Don't** use 100% black text. Always use `on-surface` (#2b3437) to maintain a soft, ink-on-paper editorial feel.
- **Don't** use standard "drop shadows" on cards. Rely on the surface color tokens for separation.
- **Don't** use icons without labels in the primary navigation. This tool values precision over "guessing" what a glyph means.