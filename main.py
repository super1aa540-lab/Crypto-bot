import ccxt
import pandas as pd
import requests
import time
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

# ==================== CONFIGURATION (ပြင်ဆင်သတ်မှတ်ချက်) ====================
TOKEN = "8625385968:AAHpcmvOAhsNyEw8WcOaqciKk1XEOzBioc8"
CHAT_ID = "542783496" 
# =========================================================================

position_states = {}

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"OK - Crypto Bot Engine is Running 24/7")

def run_health_check_server():
    server_address = ('', 7860)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    print("🌍 Health Check Server running on port 7860...", flush=True)
    httpd.serve_forever()

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        if response.status_code == 200:
            print("✅ Telegram Message ပို့ဆောင်မှု အောင်မြင်ပါသည်။", flush=True)
            return True
        else:
            print(f"⚠️ Telegram Error Code: {response.status_code} - {response.text}", flush=True)
    except Exception as e:
        print(f"❌ Telegram ချိတ်ဆက်မှု မအောင်မြင်ပါ - {e}", flush=True)
    return False

def calculate_indicators(df):
    # EMA 9 နှင့် EMA 21 တွက်ချက်ခြင်း
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # RSI 14 တွက်ချက်ခြင်း
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def check_signals():
    exchange = ccxt.binance()
    symbols = ['BTC/USDT', 'XRP/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT']
    
    print("--- Crypto Signal Bot Engine Started 24/7 ---", flush=True)
    send_telegram_message("🚀 *Crypto Signal Bot Engine Started 24/7 (5 Coins)*")
    
    while True:
        for symbol in symbols:
            try:
                bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
                if not bars:
                    continue
                    
                df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df = calculate_indicators(df)
                
                last_row = df.iloc[-1]
                prev_row = df.iloc[-2]
                
                current_price = last_row['close']
                rsi = last_row['rsi']
                
                last_ema9 = last_row['ema9']
                last_ema21 = last_row['ema21']
                prev_ema9 = prev_row['ema9']
                prev_ema21 = prev_row['ema21']
                
                if symbol not in position_states:
                    position_states[symbol] = {'position': 'NONE', 'entry_price': 0.0}
                    
                state = position_states[symbol]
                signal = None
                
                # EMA Crossover Signal သတ်မှတ်ချက်
                if prev_ema9 <= prev_ema21 and last_ema9 > last_ema21:
                    signal = "🟢 LONG (BUY)"
                elif prev_ema9 >= prev_ema21 and last_ema9 < last_ema21:
                    signal = "🔴 SHORT (SELL)"
                    
                if signal:
                    current_pos = state['position']
                    entry_price = state['entry_price']
                    pnl_text = ""
                    
                    # Position ပြောင်းလဲသွားပါက အရင် Position ၏ အရှုံးအမြတ် (P&L) ကို 10x Leverage ဖြင့် တွက်ချက်ခြင်း
                    if (current_pos == "LONG" and "SHORT" in signal) or (current_pos == "SHORT" and "LONG" in signal):
                        if current_pos == "LONG":
                            base_pnl = (current_price - entry_price) / entry_price
                        else:
                            base_pnl = (entry_price - current_price) / entry_price
                            
                        lev_pnl = base_pnl * 10
                        
                        pnl_text = (
                            f"🔄 *Closed Previous {current_pos}:*\n"
                            f"📈 Entry Price: ${entry_price}\n"
                            f"📉 Exit Price: ${current_price}\n"
                            f"📊 P&L (Base): {base_pnl*100:+.2f}%\n"
                            f"🔥 P&L (10x Leverage): {lev_pnl*100:+.2f}%\n"
                        )
                    
                    state['position'] = "LONG" if "LONG" in signal else "SHORT"
                    state['entry_price'] = current_price
                    
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    msg = (
                        f"🚀 *NEW TRADING SIGNAL* 🚀\n\n"
                        f"🪙 *Pair:* {symbol}\n"
                        f"📈 *Action:* {signal}\n"
                        f"💰 *Current Price:* ${current_price}\n"
                        f"📉 *RSI (14):* {rsi:.2f}\n"
                        f"🔥 *Leverage:* 7x - 10x\n"
                        f"⏰ *Time:* {timestamp}\n"
                    )
                    
                    if pnl_text:
                        msg += f"\n---------------------------\n{pnl_text}"
                        
                    send_telegram_message(msg)
                    
            except Exception as e:
                print(f"Error checking signals for {symbol}: {e}", flush=True)
                
        time.sleep(60)

def main():
    web_thread = threading.Thread(target=run_health_check_server, daemon=True)
    web_thread.start()
    check_signals()

if __name__ == "__main__":
    main()
