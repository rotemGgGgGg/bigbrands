# TRADEBRIDGE — אפליקציית העתקת עסקאות (Windows)

השם TRADEBRIDGE זמני. כדי לשנות אותו: `BRAND` ב-`bridge/config.py`, ו-`<title>` + `#brand` ב-`bridge/static/index.html`.

## מה זה עושה
```
TradingView (האסטרטגיה = Leader)
   │  התראה עם JSON → כתובת ה-webhook
   ▼
TRADEBRIDGE  ── חוקי סיכון (שעות, מקסימום חוזים, הפסד יומי, דראודאון, יעד, חדשות, מתג עצירה)
   │  בקשה אחת לכל חשבון עוקב (Ratio, Micros only)
   ▼
PickMyTrade ──► Tradovate (חשבונות Lucid)
```
- **מצב בדיקה** כברירת מחדל: הכל רץ ונרשם, שום דבר לא נשלח. עוברים ל-LIVE מ-My Account.
- יציאות אף פעם לא נחסמות — רק כניסות חדשות.
- סגירה אוטומטית של כל חשבון בשעה שנקבעה לו (ברירת מחדל 15:55 ניו יורק).
- הפוזיציות וה-P&L **מוערכים** מהמחירים של TradingView. המספר האמיתי — בברוקר.

## הורדה
GitHub → Actions → **Build Windows app** → הריצה האחרונה הירוקה → Artifacts → `TRADEBRIDGE-windows` → חילוץ ZIP → `TRADEBRIDGE.exe`.
Windows יכול להציג "Windows protected your PC" (הקובץ לא חתום) → More info → Run anyway.
צריך WebView2 (מותקן כבר ב-Windows 10/11).

הנתונים נשמרים ב-`%APPDATA%\TRADEBRIDGE` (הגדרות, חשבונות, יומן, `app.log`).

## הגדרה ראשונה (4 שלבים — מופיע גם בכפתור Setup)
1. **Connections → Add connection** — שם, קבוצה, מספר חשבון, Ratio.
2. **הדבקת ה-JSON מ-PickMyTrade** — באלרט-בילדר של PickMyTrade מייצרים הודעה לחשבון, ומדביקים
   ב-"Open order JSON". במקום הערכים שמים `{{side}}` `{{qty}}` `{{symbol}}` `{{price}}` `{{time}}`.
   ב-"Close / flatten JSON" — ההודעה של PickMyTrade לסגירת פוזיציה (לבדוק מולם את הפורמט).
3. **TradingView** — Connections מציג את ה-JSON להודעת ההתראה (עם הסוד שלך). יוצרים התראה על האסטרטגיה,
   מסמנים Webhook URL ומדביקים את הכתובת הציבורית + `/webhook`.
4. **Go LIVE** ב-My Account — רק אחרי שאות בדיקה נראה נכון.

### כתובת ציבורית
TradingView שולח רק לכתובת אינטרנט (פורט 80/443). האפליקציה מאזינה ב-`http://127.0.0.1:8000`.
הכי פשוט: Cloudflare Tunnel —
```
cloudflared tunnel --url http://localhost:8000
```
מעתיקים את הכתובת `https://xxxx.trycloudflare.com` ל-My Account → Public address.
הכתובת הציבורית פותחת רק את `/webhook` (מוגן בסוד). הדשבורד דורש מפתח שרק חלון האפליקציה מכיר.

## פיתוח
```
pip install -r requirements-desktop.txt
python -m pytest -q tests        # בדיקות
python desktop.py                # האפליקציה
python desktop.py --selftest     # בדיקת הפעלה בלי חלון
```
בנייה מקומית ב-Windows:
```
pyinstaller --noconfirm --onefile --windowed --name TRADEBRIDGE --icon icon.ico --add-data "bridge/static;bridge/static" --collect-submodules uvicorn --collect-all webview desktop.py
```
