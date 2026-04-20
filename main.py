import asyncio
from quotexapi.stable_api import Quotex
import requests

# --- إعدادات الحساب والربط ---
EMAIL = "afh3790@gmail.com"
PASSWORD = "a05383627597a"
TELEGRAM_TOKEN = "8609409467:AAHLg96BgPf2Vfny1xp__tvdPOBwvPjFvy4"
CHAT_ID = "8297189224"

# --- إعدادات التحدي ---
MAX_TRADES = 20        # التوقف بعد 20 صفقة
TRADE_AMOUNT = 10      # مبلغ كل صفقة
DURATION = 5           # المدة (5 دقائق)
ACCOUNT_TYPE = "PRACTICE"

trade_count = 0  # عداد الصفقات المنفذة

def send_msg(text):
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: requests.post(url, data=payload)
    except: pass

async def process_challenge(client, asset):
    global trade_count
    if trade_count >= MAX_TRADES: return

    # --- خوارزمية التحليل (السيولة + الأرقام المستديرة + الرفض) ---
    candles = await client.get_candles(asset, 50)
    if not candles: return

    c1 = candles[-1]
    price = c1['close']
    highs, lows = [c['high'] for c in candles[-30:-1]], [c['low'] for c in candles[-30:-1]]
    res, sup = max(highs), min(lows)
    
    # التحقق من الأسباب الثلاثة
    reasons = []
    action = None
    
    # منطق البيع (PUT)
    if price >= res: reasons.append("📍 سيولة")
    if abs(price - round(price, 2)) < 0.0008: reasons.append("🔢 رقم مستدير")
    if (c1['high'] - max(c1['close'], c1['open'])) > abs(c1['close'] - c1['open']): reasons.append("🕯️ رفض")
    if len(reasons) >= 3: action = "put"

    # منطق الشراء (CALL)
    if not action:
        reasons = []
        if price <= sup: reasons.append("📍 سيولة")
        if abs(price - round(price, 2)) < 0.0008: reasons.append("🔢 رقم مستدير")
        if (min(c1['close'], c1['open']) - c1['low']) > abs(c1['close'] - c1['open']): reasons.append("🕯️ رفض")
        if len(reasons) >= 3: action = "call"

    if action:
        trade_count += 1
        status, info = await client.buy(TRADE_AMOUNT, asset, action, DURATION)
        
        if status:
            order_id = info['id']
            send_msg(f"✅ **الصفقة رقم {trade_count} بدأت**\nالزوج: `{asset}` | النوع: {action.upper()}\nالسبب: {', '.join(reasons)}")
            
            # انتظار النتيجة (5 دقائق + 10 ثواني تأكيد)
            await asyncio.sleep((DURATION * 60) + 10)
            
            # فحص النتيجة
            win_status = client.check_win(order_id)
            result_text = "💰 ربح" if win_status > 0 else "❌ خسارة" if win_status < 0 else "🤝 تعادل"
            send_msg(f"📊 **نتيجة الصفقة {trade_count}:** {result_text}")
            
            # استراحة 5 دقائق قبل البحث عن الصفقة التالية
            if trade_count < MAX_TRADES:
                send_msg(f"⏳ استراحة 5 دقائق قبل الصفقة رقم {trade_count + 1}...")
                await asyncio.sleep(300)
            else:
                send_msg("🏆 **اكتمل تحدي الـ 20 صفقة بنجاح!**\nتم إيقاف البوت تلقائياً.")
                exit() # إنهاء البرنامج

async def main():
    client = Quotex(email=EMAIL, password=PASSWORD)
    check, reason = await client.connect()
    
    if check:
        client.change_balance(ACCOUNT_TYPE)
        send_msg(f"🏁 **بدأ تحدي الـ 20 صفقة**\nالحساب: تجريبي | المبلغ: ${TRADE_AMOUNT}")
        
        while trade_count < MAX_TRADES:
            try:
                profits = client.get_all_asset_profit()
                for asset, data in profits.items():
                    if "_otc" in asset and data['turbo'] >= 80:
                        await process_challenge(client, asset)
                        if trade_count >= MAX_TRADES: break
                await asyncio.sleep(20)
            except: await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
