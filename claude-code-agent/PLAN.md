# PLAN.md - KAN-19: Sentry Error Analysis and Fix Plan

## Issue Summary

| Field | Value |
|-------|-------|
| **Jira Ticket** | KAN-19 |
| **Priority** | High |
| **Sentry Issue** | https://agents-system-poc.sentry.io/issues/7206894254/ |
| **Error Message** | `Error: [Test Error 0fafcb] Something went wrong at 2026-01-21T09:26:18.023Z` |
| **Error Location** | `/components/Header.tsx:26:17` in `onClick` handler |
| **Alert Source** | High priority issues notification from Sentry |
| **Analysis Date** | 2026-01-24 |

---

## Root Cause Analysis

### Key Finding: This is a TEST ERROR, Not a Production Bug

After comprehensive investigation, this error has been identified as an **intentional test error** from an external application, not a genuine bug in the claude-machine dashboard.

### Evidence Supporting Test Error Classification

| Evidence Type | Finding |
|---------------|---------|
| **Error Type Tag** | `error_type: test_error` |
| **Error Message Format** | `[Test Error {id}] Something went wrong at {timestamp}` - follows deliberate test pattern |
| **Console Breadcrumb** | `Test error button clicked! {errorId: "0fafcb", timestamp: "2026-01-21T09:26:18.023Z"}` |
| **UI Breadcrumb** | Button clicked: `button.text-[10px].bg-red-600/80.hover:bg-red-600.text-white.px-2.py-1.rounded.transition-colors` (red "test error" button) |
| **Context Data** | `{triggered_at: "2026-01-21T09:26:18.023Z", user_action: "clicked_error_button"}` |
| **Environment** | `development` (not production) |
| **Error Handling** | `handled: true` (error was caught properly, not an unhandled exception) |

### Source Application Identification

| Property | Value |
|----------|-------|
| **Repository** | `rom-orlovich/manga-creator` |
| **Stack** | React 19, Vite 6, TypeScript 5.8, TailwindCSS 4, Sentry |
| **Sentry SDK** | `sentry.javascript.react` v10.34.0 |
| **Relationship** | External application sharing same Sentry organization (`agents-system-poc`) |

### Code Verification in This Repository

The Header.tsx file in this repository (`/app/services/dashboard-v2/src/components/ui/Header.tsx`) is **DIFFERENT** from the one in manga-creator:

| Line | Content in This Repo | Notes |
|------|---------------------|-------|
| 26 | Empty line (blank) | Part of useEffect block, not onClick |
| 42 | `onClick={onToggleSidebar}` | Simple prop callback for mobile sidebar |
| 64 | `onClick={() => setIsDark(!isDark)}` | Simple state toggle for dark mode |

**Neither onClick handler in this codebase could produce the reported error message.**

---

## Affected Components

| Component | Status | Notes |
|-----------|--------|-------|
| `/components/Header.tsx` (manga-creator) | Error source | Contains test error button on line 26 |
| `/app/services/dashboard-v2/src/components/ui/Header.tsx` | **Not affected** | Different file, different project |
| Sentry Alert Integration | Working correctly | Successfully captured and routed error |
| Jira Integration | Working correctly | Auto-created ticket KAN-19 |
| Dashboard-v2 Sentry SDK | Not installed | No `@sentry/react` in package.json |

---

## Technical Details from Sentry

### Stack Trace (Application Frame)
```
File: /components/Header.tsx
Function: onClick
Line: 26, Column: 17
In App: true
```

### Full Call Stack
1. `dispatchDiscreteEvent` (react-dom_client.js:16765)
2. `dispatchEvent` (react-dom_client.js:16784)
3. `dispatchEventForPluginEventSystem` (react-dom_client.js:13763)
4. `batchedUpdates$1` (react-dom_client.js:2626)
5. `processDispatchQueue` (react-dom_client.js:13658)
6. `runWithFiberInDEV` (react-dom_client.js:997)
7. `executeDispatch` (react-dom_client.js:13622)
8. **`onClick` (Header.tsx:26:17)** <- Application code

### Event Metadata
| Key | Value |
|-----|-------|
| **Event ID** | `809f2a690db24c35b87b3a29d485c4b8` |
| **Error ID** | `0fafcb` |
| **Error Type** | `test_error` |
| **Environment** | `development` |
| **Handled** | `yes` |
| **Repository** | `rom-orlovich/manga-creator` |
| **Stack** | `frontend` |
| **Replay ID** | `e081815047d04a25afc20e664b1ccb64` |

### User Context
| Property | Value |
|----------|-------|
| **IP** | 199.203.224.200 |
| **Location** | Tel Aviv, Israel |
| **Browser** | Chrome 144.0.0 |
| **OS** | Mac OS X >=10.15.7 |

---

## Fix Strategy

### Recommended: Option A - No Code Fix Required

Since this is an intentional test error in a development environment from a different application:

1. **Resolve the Sentry issue** with reason: "Test Error - Working as intended"
2. **Update Jira ticket KAN-19** with analysis findings
3. **Close KAN-19** as "Not a Bug" or "Working as Intended"

### Alternative: Option B - Filter Test Errors (If Many Similar Issues Expected)

If test errors are frequently triggering alerts:

1. **Add Sentry inbound filter** to ignore errors with tag `error_type: test_error`
2. **Configure alert rules** to exclude `environment: development`
3. **Update Jira automation** to not auto-create tickets for test-tagged errors

### Alternative: Option C - Remove Test Button (In manga-creator repo)

If the test button should not exist:

1. Access the `rom-orlovich/manga-creator` repository
2. Remove the test error button from `/components/Header.tsx` (line 26)
3. Deploy the changes

---

## Files to Modify

### This Repository (`/app`)

**No changes required.** The dashboard-v2 Header.tsx is unrelated to this error.

### If Implementing Option B (Sentry Configuration)

| Location | Action |
|----------|--------|
| Sentry Dashboard > Settings > Inbound Data Filters | Add filter for `error_type:test_error` |
| Sentry Dashboard > Alerts > Alert Rules | Exclude `environment:development` |

### If Implementing Option C (manga-creator repo)

| File | Action |
|------|--------|
| `/components/Header.tsx` | Remove test error button (around line 26) |

---

## Testing Strategy

### For Option A (Close Ticket)
1. Verify Sentry issue is resolved with appropriate reason
2. Confirm Jira ticket KAN-19 is closed
3. No regression testing needed

### For Option B (Filter Test Errors)
1. Trigger a test error in development environment
2. Verify it does **not** create a Sentry alert
3. Verify it does **not** create a Jira ticket
4. Verify real production errors **still** trigger alerts

### For Option C (Remove Test Button)
1. Build and deploy manga-creator without test button
2. Verify Header component still functions correctly
3. Verify no test error button appears in UI
4. Verify Sentry integration still captures real errors

---

## Risks and Considerations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Filtering legitimate errors | Low | High | Use specific tag filter (`error_type:test_error`), not broad patterns |
| Test button useful for QA | Low | Medium | Create separate QA-only test page |
| Cross-repository confusion | Medium | Low | Document which Sentry projects map to which repos |
| Alert fatigue from test errors | Medium | Low | Implement Option B filtering if recurring |

---

## Complexity Assessment

| Factor | Rating | Justification |
|--------|--------|---------------|
| Investigation Complexity | **Low** | Clear evidence this is a test error |
| Code Changes Required | **None** | No changes needed in this repository |
| Testing Effort | **Low** | Simple verification |
| Risk Level | **Low** | No production impact |

**Overall Complexity: LOW**

**Estimated Effort:** 0.5 hours (ticket update and closure)

**Confidence Level:** 95%

---

## Estimated Impact

| Area | Impact Level | Notes |
|------|--------------|-------|
| **User Impact** | None | This is a test error from development |
| **System Impact** | None | Sentry/Jira integration working correctly |
| **Development Impact** | None | No code changes required |
| **Cost Impact** | Minimal | Time spent on investigation |

---

## Recommended Actions

### Immediate Actions
1. **Close KAN-19** with resolution "Test Error - No Fix Required"
2. **Add Jira comment** with investigation summary (see below)
3. **Resolve Sentry issue** as "Ignored - Test Event"

### Short-term Actions (Optional)
- Configure Sentry to filter `error_type:test_error` events from alerts
- Update Jira automation to skip test-tagged errors

### Long-term Actions (Optional)
- Consider adding proper Sentry SDK to dashboard-v2 for real error tracking
- Document Sentry organization structure (which repos belong to `agents-system-poc`)

---

## Suggested Jira Comment for KAN-19

```
**Investigation Complete**

This error was triggered intentionally by clicking a "Test Error" button in the Header component of an external application (manga-creator, rom-orlovich/manga-creator) that shares the same Sentry organization.

**Evidence:**
- Error type tag: `test_error`
- Console breadcrumb: "Test error button clicked!"
- Environment: `development`
- Error was handled (not an unhandled exception)

**Conclusion:**
This is working as intended - the test error button exists to verify Sentry integration is working correctly. The error does NOT originate from the claude-machine dashboard.

**Resolution:** Close as "Not a Bug" - no fix required.

**Recommendation:** Consider filtering `error_type:test_error` events from auto-creating Jira tickets.
```

---

## Appendix: Dashboard-v2 Header.tsx Analysis

### Current File Location
`/app/services/dashboard-v2/src/components/ui/Header.tsx`

### onClick Handlers in This File

**Line 40-47: Sidebar Toggle Button**
```typescript
<button
  type="button"
  onClick={onToggleSidebar}
  className="p-2 md:hidden hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors dark:text-gray-400"
  aria-label="Toggle Sidebar"
>
  {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
</button>
```

**Line 62-69: Theme Toggle Button**
```typescript
<button
  type="button"
  onClick={() => setIsDark(!isDark)}
  className="p-2 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors rounded-none border border-transparent hover:border-gray-200 dark:hover:border-slate-700 dark:text-gray-400"
  title="TOGGLE_PHASE_MODE"
>
  {isDark ? <Sun size={18} /> : <Moon size={18} />}
</button>
```

**Conclusion:** Both handlers are simple, synchronous operations. Neither could produce the reported error message `[Test Error 0fafcb] Something went wrong at {timestamp}`.

### Sentry SDK Status
- **Installed:** No
- **package.json:** No `@sentry/react` dependency
- **main.tsx:** No Sentry initialization

---

**Created:** 2026-01-24  
**Author:** Planning Agent (Claude Opus 4.5)  
**Status:** Ready for Review/Execution
