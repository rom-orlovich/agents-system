# Integration Plan: Local Claude Usage Tracker

## Problem Statement
הפרויקט כרגע משתמש ב-OAuth API (`core/oauth_usage.py`) כדי לקבל נתוני שימוש של Claude Code. אבל ה-API הזה:
1. דורש credentials תקפים
2. עלול להיכשל אם ה-endpoint משתנה
3. לא תמיד זמין

הפתרון המוצע: להוסיף מעקב מקומי שקורא ישירות מקבצי `messages.jsonl` של Claude Code במחשב המקומי.

## User Review Required

> [!IMPORTANT]
> **Architecture Decision Required**
> 
> יש לבחור אחת מהאסטרטגיות הבאות:
> 
> **Option 1: Dual Source (Recommended)**
> - OAuth API = Primary source (מדויק יותר, כולל כל המכשירים)
> - Local Files = Fallback source (כאשר OAuth נכשל)
> - יתרונות: אמינות גבוהה, תמיד יש מקור נתונים
> - חסרונות: מורכבות בשילוב
> 
> **Option 2: Local Only**
> - רק קריאה מקבצים מקומיים
> - יתרונות: פשוט, ללא תלות ב-API
> - חסרונות: רק נתונים מהמכשיר הנוכחי
> 
> **Option 3: User Choice**
> - המשתמש בוחר באיזה מקור להשתמש דרך settings
> - יתרונות: גמישות מקסימלית
> - חסרונות: מורכבות UI

> [!WARNING]
> **Breaking Changes**
> - שינוי ב-API response structure של `/api/usage` (הוספת `source` field)
> - Dashboard צריך לטפל בשני מקורות נתונים

## Proposed Changes

### Core Module

#### [NEW] [local_usage_tracker.py](file:///Users/romo/projects/agents-prod/claude-code-agent/core/local_usage_tracker.py)

מודול חדש שמטפל בקריאת נתוני שימוש מקבצים מקומיים:

**Classes:**
- `LocalUsageData` - Pydantic model לנתוני שימוש מקומיים
- `ProjectUsage` - נתוני שימוש לפרויקט בודד
- `MessageTokens` - פירוט טוקנים להודעה

**Functions:**
- `find_claude_projects()` - מחפש את כל הפרויקטים של Claude Code
- `read_messages_jsonl(file_path)` - קורא קובץ messages.jsonl
- `parse_message_tokens(message)` - מחלץ נתוני טוקנים מהודעה
- `get_local_usage()` - פונקציה ראשית לקבלת נתוני שימוש מקומיים
- `calculate_usage_percentage(used, limit)` - חישוב אחוזי שימוש

---

#### [MODIFY] [oauth_usage.py](file:///Users/romo/projects/agents-prod/claude-code-agent/core/oauth_usage.py)

הוספת פונקציה משולבת שמנסה OAuth ואז fallback ל-local:

**New Function:**
```python
async def get_usage_data(prefer_local: bool = False) -> UsageResponse:
    """
    Get usage data from best available source.
    
    Args:
        prefer_local: If True, try local first, then OAuth
                     If False, try OAuth first, then local
    
    Returns:
        UsageResponse with source indicator
    """
```

**New Model:**
```python
class UsageResponse(BaseModel):
    """Unified usage response from any source."""
    session: Optional[SessionUsage]
    weekly: Optional[WeeklyUsage]
    source: Literal["oauth", "local", "none"]
    error: Optional[str]
    timestamp: datetime
```

---

### API Layer

#### [NEW] [api/routes/usage.py](file:///Users/romo/projects/agents-prod/claude-code-agent/api/routes/usage.py)

API endpoints חדשים למעקב שימוש:

**Endpoints:**
- `GET /api/usage` - קבלת נתוני שימוש (auto-detect source)
- `GET /api/usage/oauth` - בפירוש OAuth בלבד
- `GET /api/usage/local` - בפירוש local בלבד
- `GET /api/usage/alerts` - קבלת התראות שימוש
- `POST /api/usage/alerts/settings` - הגדרת thresholds להתראות

---

### Database

#### [NEW] [core/database/usage_tracking.py](file:///Users/romo/projects/agents-prod/claude-code-agent/core/database/usage_tracking.py)

טבלאות למעקב אחרי שימוש והתראות:

**Tables:**
- `usage_snapshots` - snapshots של שימוש לאורך זמן
- `usage_alerts` - התראות שנשלחו
- `usage_settings` - הגדרות משתמש (thresholds, preferred source)

---

### Dashboard Integration

#### [MODIFY] [services/dashboard-v2/src/hooks/useOAuthUsage.ts](file:///Users/romo/projects/agents-prod/claude-code-agent/services/dashboard-v2/src/hooks/useOAuthUsage.ts)

שינוי שם ל-`useUsageData.ts` ותמיכה בשני מקורות:

**Changes:**
- Rename to `useUsageData`
- Add `source` field to response type
- Add visual indicator for data source (OAuth vs Local)
- Add error handling for both sources

---

#### [MODIFY] [services/dashboard-v2/src/components/ui/UsageLimits.tsx](file:///Users/romo/projects/agents-prod/claude-code-agent/services/dashboard-v2/src/components/ui/UsageLimits.tsx)

הוספת תצוגה לנתוני שימוש מקומיים:

**Changes:**
- Show data source badge (OAuth/Local)
- Add project breakdown for local data
- Add alert settings UI
- Show warning when approaching 75%/90%

---

### Monitoring & Alerts

#### [NEW] [core/usage_alerts.py](file:///Users/romo/projects/agents-prod/claude-code-agent/core/usage_alerts.py)

מערכת התראות:

**Functions:**
- `check_usage_thresholds(usage_data)` - בדיקת thresholds
- `send_usage_alert(level, percentage, tokens)` - שליחת התראה
- `get_alert_settings(user_id)` - קבלת הגדרות התראות
- `update_alert_settings(user_id, settings)` - עדכון הגדרות

**Alert Levels:**
- `info` - 50% usage
- `warning` - 75% usage
- `critical` - 90% usage

---

### Configuration

#### [MODIFY] [core/config.py](file:///Users/romo/projects/agents-prod/claude-code-agent/core/config.py)

הוספת הגדרות למעקב מקומי:

**New Settings:**
```python
# Local usage tracking
CLAUDE_PROJECTS_DIRS: List[Path] = [
    Path.home() / '.config' / 'claude' / 'projects',
    Path.home() / '.claude' / 'projects'
]
USAGE_TRACKING_ENABLED: bool = True
USAGE_PREFERRED_SOURCE: Literal["oauth", "local", "auto"] = "auto"
USAGE_ALERT_THRESHOLDS: Dict[str, int] = {
    "info": 50,
    "warning": 75,
    "critical": 90
}
```

## Verification Plan

### Automated Tests

**TDD Lifecycle for local usage tracking:**

```bash
# [RED] Write tests
pytest tests/unit/test_local_usage_tracker.py -v (expect failures)

# [GREEN] Implement functionality
pytest tests/unit/test_local_usage_tracker.py -v (expect passes)

# [REFACTOR] Improve code
pytest tests/unit/test_local_usage_tracker.py -v (still passes)
```

**Test Files:**
1. `tests/unit/test_local_usage_tracker.py` - יחידה למודול מקומי
2. `tests/unit/test_usage_alerts.py` - יחידה להתראות
3. `tests/integration/test_usage_api.py` - אינטגרציה ל-API endpoints
4. `tests/integration/test_usage_fallback.py` - בדיקת fallback OAuth→Local

**Test Scenarios:**
- ✅ קריאת קבצי messages.jsonl תקינים
- ✅ טיפול בקבצים פגומים/ריקים
- ✅ חישוב נכון של טוקנים
- ✅ fallback מ-OAuth ל-Local
- ✅ שליחת התראות בזמן הנכון
- ✅ אי-שליחת התראות כפולות

### Manual Verification

1. **Dashboard Testing:**
   - וידוא שהנתונים מוצגים נכון
   - בדיקת source indicator
   - בדיקת project breakdown

2. **Alert Testing:**
   - סימולציה של שימוש גבוה
   - וידוא שהתראות נשלחות ב-75% ו-90%
   - בדיקה שאין התראות כפולות

3. **API Testing:**
   ```bash
   # Test OAuth endpoint
   curl http://localhost:8000/api/usage/oauth
   
   # Test local endpoint
   curl http://localhost:8000/api/usage/local
   
   # Test auto-detect
   curl http://localhost:8000/api/usage
   ```

4. **Performance Testing:**
   - בדיקת זמן טעינה עם הרבה פרויקטים
   - בדיקת זיכרון עם קבצי messages גדולים
