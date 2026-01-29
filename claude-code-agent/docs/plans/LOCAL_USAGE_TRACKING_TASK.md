# Task: Integrate Local Claude Usage Tracker

## Context
המשתמש רוצה לשלב סקריפט שקורא את נתוני השימוש של Claude Code ישירות מקבצים מקומיים (`~/.config/claude/projects/*/messages.jsonl`) כפתרון משלים ל-OAuth API הקיים.

## Goals
- [ ] הוסף מודול לקריאת נתוני שימוש מקבצים מקומיים של Claude Code
- [ ] שלב עם המערכת הקיימת `oauth_usage.py`
- [ ] צור API endpoint חדש לקבלת נתוני שימוש מקומיים
- [ ] הוסף תמיכה ב-dashboard להצגת נתוני שימוש מקומיים
- [ ] צור מערכת התראות כאשר השימוש מגיע ל-75%/90%
- [ ] הוסף בדיקות TDD

## Components to Create/Modify
- [ ] `core/local_usage_tracker.py` - מודול חדש לקריאת קבצים מקומיים
- [ ] `api/routes/usage.py` - endpoint חדש
- [ ] `core/oauth_usage.py` - שילוב עם מעקב מקומי
- [ ] Dashboard integration
- [ ] Tests

## Architecture Decision
צריך להחליט:
1. האם לשלב את שני המקורות (OAuth + Local) או להשאיר נפרדים?
2. איזה מקור יהיה primary?
3. איך לטפל במקרים שבהם יש סתירה בין המקורות?
