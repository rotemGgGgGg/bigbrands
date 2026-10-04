# בוט טלגרם עם Claude

שולחים הודעה לבוט בטלגרם, הוא שואל את Claude ומחזיר תשובה.

## הגדרה (פעם אחת)
1. בטלגרם: פתח את @BotFather, שלח `/newbot`, ותעתיק את הטוקן.
2. צור מפתח API ב-https://console.anthropic.com (צריך להטעין קרדיט).
3. שים את `TelegramClaudeBot.exe` בתיקייה, העתק את `config.example.json` ל-`config.json` באותה תיקייה ומלא:
   - `telegram_bot_token` - הטוקן מ-BotFather
   - `anthropic_api_key` - המפתח מ-Anthropic
   - `allowed_user_ids` - ה-ID שלך בטלגרם, למשל `[123456789]`
4. הפעל את ה-exe ושלח לבוט הודעה.

**חשוב:** אם `allowed_user_ids` ריק, כל אחד שימצא את הבוט יכול לדבר איתו על חשבונך.
כדי לגלות את ה-ID שלך: שים בו מספר כלשהו, למשל `[1]`, ושלח לבוט הודעה. הוא יחזיר לך "Your user id is ...".

## שימוש
- כל הודעה מקבלת תשובה, והבוט זוכר את השיחה.
- `/reset` מתחיל שיחה חדשה.
- הבוט עובד רק כשהחלון פתוח.

## הורדת ה-exe
ב-GitHub: Actions → "Build Telegram bot .exe" → הריצה האחרונה → Artifacts → TelegramClaudeBot.
