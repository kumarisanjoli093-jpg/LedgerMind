# LedgerMind — Frontend Architecture & Design System

**Owner:** Person 1 (Branch: `frontend`)  
**Design Influences:**
* **Vantage Bank:** Luxury typography, deep forest green branding, warm cream surfaces, and refined editorial micro-borders.
* **Finovex:** Executive dashboard architecture, 4-column KPI metric cards, quick action toolbars, and structured data tables.
* **Pulse:** High-contrast analytics surface with smooth cubic bezier spline curves, glow points, and interactive risk exposure tooltips.
* **shadcn/ui:** Collapsible sidebar anatomy, nested navigation groups, status badge pills, and responsive layout.

---

## 🎨 Brand Design Tokens

The application strictly utilizes the chosen brand palette across all views:

| Token Name | Hex Code | Purpose & Semantic Usage |
| :--- | :--- | :--- |
| **Forest Green** | `#163D32` | Primary brand color, executive headers, primary CTA buttons, active state indicators. |
| **Warm Cream** | `#F5F0E8` | Canvas background, sub-card surfaces, warm editorial contrast against crisp white cards. |
| **Soft Pink** | `#E9BFC4` | Accent highlight, trend curves, badge pills, priority tags, and interactive chart glow. |
| **Charcoal** | `#252A27` | High-contrast typography, dark summary cards, table headers, and structural borders. |

---

## 🏗️ Architecture & Component Hierarchy

To ensure **100% zero-configuration compatibility** with the team's FastAPI backend (`main.py`), the frontend is structured cleanly within `templates/` and `static/`:

```
LedgerMind/
├── templates/
│   └── index.html          # Semantic HTML shell, shadcn sidebar, Finovex grid, and view tabs
├── static/
│   ├── style.css           # Custom CSS design system, typography, animations & responsive media queries
│   └── app.js              # State manager, API client, Pulse SVG chart generator & GST calculator
└── frontend/
    └── README.md           # This documentation
```

### Views & Capabilities

1. **Executive Overview (`#overview`)**:
   - Vantage Bank luxury welcome banner with persistent memory status.
   - 4 Finovex KPI cards: *Purchase Invoices*, *Vendors Tracked*, *Credit at Risk*, and *Open Exceptions*.
   - Quick operations bar: one-click CSV imports, GST calculation, sample downloads, and AI audit triggers.
   - Pulse Analytics: 6-month spline area curve graphing credit-at-risk exposure with hover tooltips.
   - Live Agent Activity Stream: real-time audit trail of reconciliation actions.
   - Priority Exceptions Table: immediate visibility into top ITC risk items.

2. **Reconciliation & Invoices (`#exceptions`)**:
   - Filing period filter and instant client-side search (by vendor, invoice number, or GSTIN).
   - Dual drag-and-drop dropzones for Purchase Register CSVs and GSTR-2B filing CSVs.
   - Interactive exception status tags: `High` priority, `Medium`, and `Match`.

3. **GST & Tax Engine (`#gstcalc`)**:
   - Interactive calculator hooked into `POST /api/gst/calculate`.
   - Real-time intra-state (CGST + SGST) vs inter-state (IGST) tax calculation based on supplier GSTIN state code and place of supply.
   - Dynamic line items with support for varying GST slabs (0%, 5%, 12%, 18%, 28%).

4. **Vendor Memory (`#vendors`)**:
   - Hindsight-powered memory bank tracking supplier filing compliance, late filing frequency, repeated GSTIN typos, and preferred communication channels.

5. **AI Action Drafts (`#actions`)**:
   - Groq-generated vendor follow-up notices with one-click clipboard copying and "Mark as Sent" status updates.

6. **Integrations (`#integrations`)**:
   - Live health checks for Hindsight memory bank, Groq LLM model, Band AI Desktop, and OpenClaw.

---

## 🔌 API Integration Contract

The frontend consumes the following existing backend endpoints:

* `GET /api/dashboard`: Overall statistics and 6-month risk trend data.
* `GET /api/issues`: Filterable reconciliation exception records.
* `GET /api/vendors`: Retained vendor behavior and compliance profiles.
* `GET /api/actions`: AI-formulated supplier communication drafts.
* `POST /api/run-agent`: Initiates autonomous reconciliation and draft formulation.
* `POST /api/actions/{id}/sent`: Updates action draft status.
* `POST /api/upload/{kind}`: Ingests `purchase` and `gstr2b` CSV files.
* `POST /api/gst/calculate`: Computes tax breakdown according to the IGST Act.
* `GET /api/integrations`: Verifies system service connectivity.
