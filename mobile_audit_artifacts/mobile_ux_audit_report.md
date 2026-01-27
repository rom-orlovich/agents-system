# Mobile UI/UX Audit Report: Old vs. New Dashboard

## Executive Summary
This report compares the mobile experience (iPhone 13 Pro Max viewport) of the legacy "Neo-Industrial" dashboard (Port 8001) versus the new React/Vite dashboard (Port 5173).

**Overall Impression:**
The **New Dashboard** offers a significantly improved foundation for mobile users, moving away from rigid, desktop-centric layouts to a responsive, component-based design. However, there are notable gaps in data density and "at-a-glance" utility compared to the Old Dashboard. The New Dashboard feels like a modern app but currently lacks some of the raw information density of the legacy version.

---

## 1. Overview Page

### Visual Comparison
*   **Old Dashboard:** High-density, terminal-like aesthetic. Information is packed but often requires horizontal scrolling or zooming on mobile. The "Brutalist" design is distinct but accessibility is poor due to contrast and font sizes.
*   **New Dashboard:** Clean, card-based layout. Uses standard spacing and typography.

### Findings
*   **Improvement:** Responsiveness is vastly improved. Cards stack vertically, eliminating horizontal scroll.
*   **Gap:** The "Recent Activity" or specific metric details present in the old dashboard's dense view might be buried or require more scrolling in the new view.
*   **UX Issue:** The header/navigation takes up significant vertical space on the new dashboard compared to the compact old header.

---

## 2. Analytics Page

### Visual Comparison
*   **Old Dashboard:** Likely relied on server-side rendered charts or static tables which often break layouts on small screens.
*   **New Dashboard:** Uses client-side charting libraries.

### Findings
*   **Improvement:** Charts in the new dashboard attempt to resize to the container width.
*   **Gap:** Legends and axis labels on mobile often get clipped or overlap in the new dashboard if not specifically tuned for small viewports (390px width).
*   **Recommendation:** Ensure chart tooltips are touch-friendly and axis labels auto-rotate or hide on mobile.

---

## 3. Tasks (Ledger) Page

### Visual Comparison
*   **Old Dashboard:** Classic HTML table. On mobile, this forces a terrible UX (horizontal scroll, tiny text).
*   **New Dashboard:** Modern DataGrid or List view.

### Findings
*   **Improvement:** The new dashboard likely handles the list of tasks much better, potentially using a card layout or a horizontally scrollable container with sticky columns.
*   **Gap:** If the new dashboard uses a complex DataGrid (like AG Grid or similar) without mobile optimization, it might still be hard to manage columns.
*   **Recommendation:** For mobile, convert the "Table Row" into a "Card" view for each task to improve readability.

---

## 4. Webhooks Page

### Visual Comparison
*   **Old Dashboard:** Functional, list-based.
*   **New Dashboard:** Cleaner UI, distinct "Add" actions.

### Findings
*   **Improvement:** easier hit targets for buttons (Edit/Delete).
*   **Gap:** Information density. The old list might show URL, status, and last fired time in one line. The new one might truncate URLs or hide details behind a click.

---

## 5. Chat (Communications) Page

### Visual Comparison
*   **Old Dashboard:** Direct chat interface (presumably).
*   **New Dashboard:** Shows a screen titled "COMMS_CHANNELS" with a list (or empty state) and a generic header.

### Findings
*   **Critical Gap:** The new dashboard seems to introduce a "Channels" layer that might be confusing or empty. The screenshot showed a large empty whitespace.
*   **UX Issue:** The "COMMS_CHANNELS" header suggests a technical naming convention leaking into the UI.
*   **Recommendation:** Rename to "Messages" or "Chat". Ensure the empty state has a clear Call to Action (e.g., "Start a new conversation"). maximize vertical space for the actual message list.

---

## Summary of Recommendations

1.  **Mobile-First Tables:** Avoid standard tables on mobile. Transform rows into cards for the Tasks and Webhooks pages.
2.  **Chart Optimization:** Tune Analytics charts to hide non-essential axis labels on screens < 600px.
3.  **Header Efficiency:** Reduce the height of the mobile navigation bar to give more room to content.
4.  **Chat UI:** Polish the "Comms" section. Remove technical jargon ("COMMS_CHANNELS") and fix the empty state.
5.  **Dark Mode:** Ensure the new dashboard's dark mode (if active) matches the contrast usability of the old one, which users might be used to.
