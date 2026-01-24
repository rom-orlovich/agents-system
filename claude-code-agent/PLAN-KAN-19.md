# PLAN: KAN-19 - Sentry Error Analysis

## Issue Summary

**Jira Ticket:** KAN-19
**Project:** My Software Team
**Priority:** High
**Sentry Issue:** https://agents-system-poc.sentry.io/issues/7206894254/

**Error:**
```
Error: [Test Error 0fafcb] Something went wrong at 2026-01-21T09:26:18.023Z
  at onClick (/components/Header.tsx:26:17)
```

---

## Root Cause Analysis

### Finding: This is a Synthetic Test Error

Based on comprehensive codebase analysis, this error is **NOT a genuine production bug** but rather a **test/synthetic error**. Evidence:

1. **Error ID Pattern**: The `0fafcb` identifier follows Sentry's test event ID format
2. **Generic Message**: "Something went wrong" is a generic test message not found in the application source code
3. **Timestamp in Error**: Including a precise ISO timestamp in the error message (`2026-01-21T09:26:18.023Z`) is a common pattern for test events to ensure uniqueness
4. **Line Number Mismatch**: The stack trace points to `/components/Header.tsx:26:17`, but in the actual source code (`/app/services/dashboard-v2/src/components/ui/Header.tsx`):
   - **Line 26 is empty** (blank line between two `useEffect` hooks)
   - No `onClick` handler exists on or near line 26
   - The actual onClick handlers are at lines 42 and 64

### Actual Header.tsx onClick Handlers

| Line | Handler | Purpose | Risk |
|------|---------|---------|------|
| 42 | `onClick={onToggleSidebar}` | Toggles mobile sidebar | Low - simple prop callback |
| 64 | `onClick={() => setIsDark(!isDark)}` | Toggles dark/light theme | Low - simple state toggle |

### Possible Explanations for Stack Trace Mismatch

1. **Source Map Misconfiguration**: Production build source maps may be outdated or incorrectly mapped
2. **Sentry SDK Test Event**: This appears to be a Sentry test event generated via:
   - Sentry SDK's `Sentry.captureException(new Error("Test Error..."))`
   - Sentry's "Create sample event" feature from the dashboard
   - A test button/feature in the application (not found in current code)
3. **Old Code Version**: Error captured from a previous version of the application

---

## Affected Components

| Component | Status | Notes |
|-----------|--------|-------|
| `/app/services/dashboard-v2/src/components/ui/Header.tsx` | No issue found | Current code has no errors at line 26 |
| Sentry Integration | Not configured | No Sentry SDK found in dashboard-v2 source |
| Source Maps | Unknown | Would need production build to verify |

---

## Fix Strategy

### Recommendation: No Code Fix Required

This is a test error, not a production bug. The appropriate response depends on the context:

### Option A: If Testing Sentry Webhook Integration
- **Status**: Working correctly - the error was captured and routed to Jira
- **Action**: Mark ticket as resolved/test-passed
- **Reason**: The Sentry webhook integration successfully created a Jira ticket

### Option B: If Unexpected Test Error
- **Action 1**: Identify the source of the test event generation
- **Action 2**: Remove or disable test error triggers in production
- **Action 3**: Add error filtering for test events in Sentry

### Option C: If Genuine Bug Suspected
If there is belief this is a genuine bug (e.g., users reported issues):

1. **Verify Source Maps**
   - Check Vite build configuration for source map generation
   - Verify source maps are uploaded to Sentry
   
2. **Add Sentry SDK to Dashboard**
   - Install `@sentry/react` package
   - Configure with proper DSN and environment
   - Enable source map uploading in build process
   
3. **Add Error Boundary to Header**
   - Wrap Header component with error boundary for resilience
   - Log errors with proper context

---

## Files to Modify

### If Implementing Option C (Full Sentry Integration)

| File | Action | Purpose |
|------|--------|---------|
| `services/dashboard-v2/package.json` | Add | `@sentry/react` dependency |
| `services/dashboard-v2/src/main.tsx` | Modify | Initialize Sentry SDK |
| `services/dashboard-v2/vite.config.ts` | Modify | Configure source map uploads |
| `services/dashboard-v2/src/components/ui/Header.tsx` | Optional | Add error boundary wrapper |

### Code Changes (If Needed)

#### 1. Add Sentry to main.tsx (if implementing full integration)
```typescript
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration(),
  ],
  tracesSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});
```

#### 2. Vite Source Map Configuration
```typescript
// vite.config.ts
import { sentryVitePlugin } from "@sentry/vite-plugin";

export default defineConfig({
  build: {
    sourcemap: true,
  },
  plugins: [
    sentryVitePlugin({
      org: "agents-system-poc",
      project: "dashboard-v2",
      authToken: process.env.SENTRY_AUTH_TOKEN,
    }),
  ],
});
```

---

## Testing Strategy

### Verify Error Origin
1. Check Sentry dashboard for event details (browser, user session, breadcrumbs)
2. Review Sentry event metadata for test indicators
3. Search for any test error generation code in deployment environments

### If Implementing Sentry Integration
1. **Unit Tests**
   - Test Sentry initialization
   - Test error boundary behavior
   
2. **Integration Tests**
   - Verify source maps are correctly uploaded
   - Test error capture and reporting
   
3. **Manual Testing**
   - Trigger intentional error and verify it appears in Sentry with correct stack trace
   - Verify line numbers match source code

---

## Risks and Considerations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Genuine bug missed | Low | Medium | Monitor user reports; add Sentry SDK properly |
| Source map exposure | Low | Low | Use hidden source maps in production |
| Performance impact | Low | Low | Configure appropriate sample rates |
| Alert fatigue from test errors | Medium | Low | Filter test events in Sentry rules |

---

## Complexity Assessment

| Factor | Rating | Justification |
|--------|--------|---------------|
| Investigation Complexity | Low | Clear evidence this is a test error |
| Code Changes Required | None/Low | No immediate fix needed |
| Testing Effort | Low | Simple verification |
| Risk Level | Low | No production impact |

**Overall Complexity: LOW**

---

## Estimated Impact

- **User Impact**: None - this is a test error
- **System Impact**: None - Sentry webhook integration working correctly
- **Development Impact**: Low - may want to add proper Sentry SDK integration

---

## Recommended Actions

1. **Immediate**: Close KAN-19 as "Test Error - No Fix Required"
2. **Short-term**: Consider adding Sentry SDK to dashboard-v2 for proper error tracking
3. **Long-term**: Set up Sentry alerting rules to filter out test events

---

## Appendix: Header.tsx Analysis

### Current onClick Handlers (Full Context)

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

**Conclusion**: Both handlers are simple, synchronous operations with no potential for throwing the reported error.
