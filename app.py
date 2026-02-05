import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import json
import os

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Gold Pro: Team Edition", page_icon="🏆", layout="wide")

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600&display=swap');
    html, body, [class*="css"]  { font-family: 'Kanit', sans-serif; }
    
    .footer { text-align: center; color: #94a3b8; font-size: 0.9rem; margin-top: 50px; border-top: 1px dashed #cbd5e1; padding-top: 20px; }
    
    /* Signal Box Styles */
    .signal-box { padding: 15px; border-radius: 10px; margin-bottom: 20px; text-align: center; font-weight: bold; font-size: 1.1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .buy-sig { background-color: #dcfce7; color: #166534; border: 1px solid #166534; }
    .sell-sig { background-color: #fee2e2; color: #991b1b; border: 1px solid #991b1b; }
    .wait-sig { background-color: #f3f4f6; color: #374151; border: 1px solid #6b7280; }
</style>
""", unsafe_allow_html=True)

st.title("🏆 Gold Pro: Trap Master V2.5")
st.markdown("**เครื่องมือวางแผนเทรดทองคำ (Grid Strategy + AI Analysis)**")
st.write("---")

# --- 2. ระบบจัดการข้อมูล (Local Database) ---
DB_FILE = 'gold_team_data.json'

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'accumulated_profit' not in data: data['accumulated_profit'] = 0.0
                if 'vault' not in data: data['vault'] = []
                if 'portfolio' not in data: 
                    data['portfolio'] = {str(i): {'status': 'EMPTY', 'entry_price': 0.0, 'grams': 0.0, 'date': None} for i in range(1, 6)}
                return data
        except: pass
    
    return {
        'portfolio': {str(i): {'status': 'EMPTY', 'entry_price': 0.0, 'grams': 0.0, 'date': None} for i in range(1, 6)},
        'vault': [],
        'accumulated_profit': 0.0
    }

def save_data(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

if 'gold_team_data' not in st.session_state:
    st.session_state.gold_team_data = load_data()

# --- 3. ฟังก์ชันคำนวณกราฟ (Technical Engine) ---
def calculate_indicators(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    return df

@st.cache_data(ttl=60) # Cache 1 นาที
def get_market_data():
    try:
        # FX
        fx = yf.Ticker("THB=X").history(period="1d")['Close'].iloc[-1]
        
        # Gold Data (1h interval for short-term trade)
        df = yf.download("GC=F", period="5d", interval="1h", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        if len(df) > 0:
            df = calculate_indicators(df)
            
        return float(fx), df
    except: return 34.50, None

# --- 4. Sidebar ตั้งค่า ---
st.sidebar.header("⚙️ ตั้งค่าราคา (Price Config)")
price_source = st.sidebar.radio("แหล่งที่มา:", ["🤖 Auto (Spot)", "✍️ Manual (ระบุเอง)"])

auto_fx, df_gold = get_market_data()
current_thb_baht = 0.0 
current_rsi = 0.0

if price_source == "🤖 Auto (Spot)":
    st.sidebar.caption("🔧 จูนราคาให้ตรงแอป")
    fx_rate = st.sidebar.number_input("USD/THB", value=auto_fx, format="%.2f")
    premium = st.sidebar.number_input("Premium (+)", value=100.0, step=10.0)
    
    if df_gold is not None:
        current_usd = float(df_gold['Close'].iloc[-1])
        current_thb_baht = round(((current_usd * fx_rate * 0.473) + premium) / 50) * 50
        current_rsi = df_gold['RSI'].iloc[-1]
        st.sidebar.success(f"ราคาตลาด: **{current_thb_baht:,.0f}**")
else:
    st.sidebar.caption("กรอกราคาซื้อขายจริงจากแอป")
    manual_price = st.sidebar.number_input("ราคาทอง (บาทละ)", value=40500, step=50)
    current_thb_baht = manual_price
    # ถ้า Manual ก็ยังพยายามดึง RSI มาโชว์ ถ้ามีข้อมูล
    if df_gold is not None:
        current_rsi = df_gold['RSI'].iloc[-1]

st.sidebar.markdown("---")
st.sidebar.header("📏 ตั้งค่าระยะ Grid")
gap_buy_1_2 = st.sidebar.number_input("ห่างไม้ 1->2 (บาท)", value=500, step=100)
gap_buy_2_3 = st.sidebar.number_input("ห่างไม้ 2->3 (บาท)", value=1000, step=100)
gap_profit = st.sidebar.number_input("กำไรขั้นต่ำ/ไม้ (บาท)", value=300, step=50)
spread_buffer = st.sidebar.number_input("เผื่อ Spread ขายคืน", value=50.0, step=10.0)
base_trade_size = st.sidebar.number_input("เงินต้นเริ่มแรก", value=10000, step=1000)

# --- 5. AI Analyst Logic ---
def analyze_market_condition(rsi, close, ema200):
    if rsi == 0: return "N/A", "wait-sig"
    
    msg = ""
    css_class = ""
    
    if rsi <= 30:
        msg = f"💎 OVERSOLD (RSI {rsi:.0f}): ราคาถูกมาก น่าเก็บไม้แรก!"
        css_class = "buy-sig"
    elif rsi <= 45 and close > ema200:
        msg = f"🛒 BUY DIP (RSI {rsi:.0f}): ย่อตัวในขาขึ้น น่าสะสม"
        css_class = "buy-sig"
    elif rsi >= 75:
        msg = f"🔥 OVERHEATED (RSI {rsi:.0f}): ราคาแพง ระวังแรงขาย!"
        css_class = "sell-sig"
    else:
        msg = f"⏳ WAIT (RSI {rsi:.0f}): ราคากลางๆ ไม่มีความได้เปรียบ"
        css_class = "wait-sig"
        
    return msg, css_class

# --- 6. Logic คำนวณพอร์ต ---
portfolio = st.session_state.gold_team_data['portfolio']
last_active_wood = 0
last_entry_price = 0

for i in range(1, 6):
    if portfolio[str(i)]['status'] == 'ACTIVE':
        last_active_wood = i
        last_entry_price = portfolio[str(i)]['entry_price']

next_wood = last_active_wood + 1
trap_price = 0
trap_reason = ""

if next_wood == 1:
    trap_price = current_thb_baht - 100
    trap_reason = "ราคาตลาด (หรือรอแนวรับ)"
elif next_wood <= 5:
    gap = gap_buy_1_2 if next_wood == 2 else (gap_buy_2_3 if next_wood == 3 else 1500)
    trap_price = last_entry_price - gap
    trap_reason = f"ระยะห่าง Grid {gap} บาท จากไม้ {last_active_wood}"

trap_price = round(trap_price / 50) * 50

# --- 7. Display Dashboard ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("โหมด", "Auto" if "Auto" in price_source else "Manual")
c2.metric("สถานะพอร์ต", f"{last_active_wood}/5 ไม้")
c3.metric("ราคาทองไทย", f"{current_thb_baht:,.0f} ฿")
current_capital = base_trade_size + st.session_state.gold_team_data.get('accumulated_profit', 0.0)
c4.metric("เงินทุน (ทบต้น)", f"{current_capital:,.0f} ฿")

# AI Signal Box
if df_gold is not None:
    last_c = df_gold['Close'].iloc[-1]
    ema_200 = df_gold['EMA200'].iloc[-1]
    ai_msg, ai_class = analyze_market_condition(current_rsi, last_c, ema_200)
    st.markdown(f'<div class="signal-box {ai_class}">🤖 AI ADVICE: {ai_msg}</div>', unsafe_allow_html=True)

# คำแนะนำ Trap
if next_wood <= 5:
    st.info(f"""
    📢 **แผนการรบสำหรับไม้ที่ {next_wood}**
    ให้ไปตั้งซื้อล่วงหน้า (Limit Order) ที่ราคา: **{trap_price:,.0f} บาท**
    *เงื่อนไข: {trap_reason}*
    """)
else:
    st.error("กระสุนหมดครบ 5 ไม้แล้ว! หยุดซื้อและรอขายอย่างเดียว")

st.write("---")

tab1, tab2, tab3 = st.tabs(["🔫 Sniper Board", "🧊 Vault", "📈 Chart"])

with tab1:
    st.subheader(f"🎯 เป้ากำไร: +{gap_profit} บาท/ไม้")
    for i in range(1, 6):
        key = str(i)
        wood = portfolio[key]
        
        with st.container(border=True):
            col_id, col_info, col_btn = st.columns([1, 3, 2])
            with col_id: st.markdown(f"### 🪵 #{i}")
            with col_info:
                if wood['status'] == 'EMPTY':
                    st.caption("ว่าง")
                    if i == next_wood:
                        st.markdown(f"📍 **รอตั้งรับที่:** `{trap_price:,.0f}`")
                else:
                    target_sell = wood['entry_price'] + gap_profit + spread_buffer
                    curr_profit = (current_thb_baht - spread_buffer - wood['entry_price']) * wood['grams']
                    color_pl = "green" if current_thb_baht >= target_sell else "red"
                    st.markdown(f"ทุน: **{wood['entry_price']:.0f}** | เป้าขาย: **{target_sell:,.0f}**")
                    st.markdown(f"สถานะ: :{color_pl}[{curr_profit:+.0f} ฿]")

            with col_btn:
                if wood['status'] == 'EMPTY':
                    prev_active = True if i == 1 else portfolio[str(i-1)]['status'] == 'ACTIVE'
                    if prev_active:
                        if st.button(f"🔴 ยิงไม้ {i}", key=f"buy_{i}", use_container_width=True):
                            st.session_state.gold_team_data['portfolio'][key] = {
                                'status': 'ACTIVE',
                                'entry_price': current_thb_baht,
                                'grams': current_capital / current_thb_baht,
                                'date': datetime.now().strftime("%Y-%m-%d %H:%M")
                            }
                            save_data(st.session_state.gold_team_data)
                            st.rerun()
                else:
                    target_sell = wood['entry_price'] + gap_profit + spread_buffer
                    btn_type = "primary" if current_thb_baht >= target_sell else "secondary"
                    if st.button(f"💰 ขายทำกำไร", key=f"sell_{i}", type=btn_type, use_container_width=True):
                        final_profit = (current_thb_baht - spread_buffer - wood['entry_price']) * wood['grams']
                        st.session_state.gold_team_data['vault'].append({
                            'wood': i, 'profit': final_profit, 'date': datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        st.session_state.gold_team_data['accumulated_profit'] += final_profit
                        st.session_state.gold_team_data['portfolio'][key] = {'status': 'EMPTY', 'entry_price': 0, 'grams': 0, 'date': None}
                        save_data(st.session_state.gold_team_data)
                        st.success(f"กำไร {final_profit:+.0f} บาท")
                        st.rerun()

with tab2:
    vault_data = st.session_state.gold_team_data.get('vault', [])
    if vault_data:
        st.dataframe(pd.DataFrame(vault_data), use_container_width=True)
        st.metric("กำไรสะสม", f"{sum(d['profit'] for d in vault_data):,.0f} ฿")
        if st.button("ล้างประวัติ"):
            st.session_state.gold_team_data['vault'] = []
            st.session_state.gold_team_data['accumulated_profit'] = 0
            save_data(st.session_state.gold_team_data)
            st.rerun()
    else: st.info("ยังไม่มีประวัติ")

with tab3:
    if df_gold is not None:
        st.subheader("📈 กราฟทองคำโลก (Spot USD)")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df_gold.index, open=df_gold['Open'], high=df_gold['High'],
                        low=df_gold['Low'], close=df_gold['Close'], name='Price'))
        fig.add_trace(go.Scatter(x=df_gold.index, y=df_gold['EMA50'], name='EMA 50 (ส้ม)', line=dict(color='orange', width=1)))
        fig.add_trace(go.Scatter(x=df_gold.index, y=df_gold['EMA200'], name='EMA 200 (ฟ้า)', line=dict(color='blue', width=2)))
        fig.update_layout(height=500, xaxis_rangeslider_visible=False, title="XAU/USD (1H)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("ไม่สามารถโหลดกราฟได้ (ลองเปลี่ยนเป็นโหมด Auto หรือรอสักครู่)")

st.markdown("<div class='footer'>🛠️ Engineered by <b>โบ้ 50</b> | Powered by Python & Streamlit</div>", unsafe_allow_html=True)
