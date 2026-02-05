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
    
    .gold-box { background-color: #fffbeb; padding: 20px; border-radius: 10px; border: 1px solid #fcd34d; text-align: center; }
    
    /* กล่องสัญญาณ */
    .sig-box { padding: 15px; border-radius: 8px; margin-bottom: 10px; text-align: center; font-weight: bold; font-size: 1.1rem; }
    
    .buy-sig { background-color: #dcfce7; color: #166534; border: 1px solid #166534; }
    .sell-sig { background-color: #fee2e2; color: #991b1b; border: 1px solid #991b1b; }
    .wait-sig { background-color: #f3f4f6; color: #374151; border: 1px solid #6b7280; }
    
    .footer { text-align: center; color: #94a3b8; font-size: 0.9rem; margin-top: 50px; border-top: 1px dashed #cbd5e1; padding-top: 20px; }
    
    /* Animation สำหรับ Fire Alert */
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7); }
        70% { transform: scale(1.02); box-shadow: 0 0 0 10px rgba(220, 38, 38, 0); }
        100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
    }
    .fire-alert {
        background-color: #fee2e2; 
        color: #991b1b; 
        border: 2px solid #b91c1c; 
        padding: 20px; 
        border-radius: 10px; 
        text-align: center;
        font-weight: bold;
        font-size: 1.5rem;
        animation: pulse 2s infinite;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏆 Gold Pro: Trap Master V2.9 (Auto Alert)")
st.markdown("**เครื่องมือวางแผนเทรดทองคำ: แจ้งเตือนเมื่อราคาเข้าเกณฑ์**")
st.write("---")

# --- 2. ระบบจัดการข้อมูล ---
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

# --- 3. ฟังก์ชันคำนวณกราฟ ---
def calculate_indicators(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    return df

@st.cache_data(ttl=60)
def get_market_data():
    try:
        fx = yf.Ticker("THB=X").history(period="1d")['Close'].iloc[-1]
        df = yf.download("GC=F", period="6mo", interval="1h", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if len(df) > 0: df = calculate_indicators(df)
        return float(fx), df
    except: return 34.50, None

# --- 4. Sidebar ตั้งค่า ---
st.sidebar.header("⚙️ ตั้งค่าราคา")
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
    if df_gold is not None: current_rsi = df_gold['RSI'].iloc[-1]

st.sidebar.markdown("---")
st.sidebar.header("📏 ตั้งค่าระยะ Grid")
gap_buy_1_2 = st.sidebar.number_input("ห่างไม้ 1->2 (บาท)", value=500, step=100)
gap_buy_2_3 = st.sidebar.number_input("ห่างไม้ 2->3 (บาท)", value=1000, step=100)
gap_3_4 = st.sidebar.number_input("ไม้ 3 -> 4 (บาท)", value=800, step=50)
gap_4_5 = st.sidebar.number_input("ไม้ 4 -> 5 (บาท)", value=1000, step=50)

st.sidebar.markdown("---")
gap_profit = st.sidebar.number_input("กำไรขั้นต่ำ/ไม้ (บาท)", value=300, step=50)
spread_buffer = st.sidebar.number_input("เผื่อ Spread ขายคืน", value=50.0, step=10.0)
base_trade_size = st.sidebar.number_input("เงินต้นเริ่มแรก", value=10000, step=1000)

# --- 5. AI Strategy Advisor (Dual Mode) ---
st.subheader("🧠 คำแนะนำกลยุทธ์ (AI Strategy)")

if df_gold is not None:
    last_close = df_gold['Close'].iloc[-1]
    ema200 = df_gold['EMA200'].iloc[-1]
    
    col_sniper, col_investor = st.columns(2)
    
    # === กลยุทธ์ 1: Sniper ===
    with col_sniper:
        st.markdown("#### ⚡ สายเก็งกำไร")
        if current_rsi <= 30:
            st.markdown(f'<div class="buy-sig">💎 <b>FIRE!</b>: RSI {current_rsi:.0f} ต่ำมาก ซื้อเลย!</div>', unsafe_allow_html=True)
        elif current_rsi <= 45 and last_close > ema200:
            st.markdown(f'<div class="buy-sig">🛒 <b>BUY DIP</b>: RSI {current_rsi:.0f} ย่อตัวสวย</div>', unsafe_allow_html=True)
        elif current_rsi >= 75:
            st.markdown(f'<div class="sell-sig">💰 <b>SELL</b>: RSI {current_rsi:.0f} แพงแล้ว</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="wait-sig">⏳ <b>WAIT</b>: RSI {current_rsi:.0f} กลางๆ</div>', unsafe_allow_html=True)

    # === กลยุทธ์ 2: Investor ===
    with col_investor:
        st.markdown("#### 🐢 สายออมยาว")
        if last_close > ema200:
            st.markdown('<div class="hold-sig">🐂 <b>HOLD</b>: เทรนด์ขาขึ้น</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="sell-sig">🐻 <b>CAUTION</b>: หลุดเทรนด์</div>', unsafe_allow_html=True)

# --- 6. Logic คำนวณพอร์ต & แจ้งเตือน ---
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
alert_trigger = False

# คำนวณราคาดักซื้อ
if next_wood == 1:
    # ไม้ 1: ถ้า RSI <= 45 ให้ถือว่าเป็นจังหวะเข้า
    trap_price = current_thb_baht # ราคาปัจจุบัน
    trap_reason = "RSI เข้าเกณฑ์ / ราคาตลาด"
    if current_rsi <= 45: alert_trigger = True
elif next_wood <= 5:
    gap = gap_buy_1_2 if next_wood == 2 else (gap_buy_2_3 if next_wood == 3 else (gap_3_4 if next_wood == 4 else gap_4_5))
    trap_price = last_entry_price - gap
    trap_reason = f"ระยะห่าง Grid {gap} บาท จากไม้ {last_active_wood}"
    
    # ถ้าหลุดลงมาถึงราคาเป้าหมาย -> แจ้งเตือน!
    if current_thb_baht <= trap_price:
        alert_trigger = True

# ปัดเศษราคาเป้าหมาย (ถ้ายังไม่ถึง)
if not alert_trigger and next_wood > 1:
    trap_price = round(trap_price / 50) * 50

# --- 7. Display Dashboard ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("โหมด", "Auto" if "Auto" in price_source else "Manual")
c2.metric("สถานะพอร์ต", f"{last_active_wood}/5 ไม้")
c3.metric("ราคาทองไทย", f"{current_thb_baht:,.0f} ฿")
current_capital = base_trade_size + st.session_state.gold_team_data.get('accumulated_profit', 0.0)
c4.metric("เงินทุน (ทบต้น)", f"{current_capital:,.0f} ฿")

# กล่องแจ้งเตือน (Highlight)
if next_wood <= 5:
    if alert_trigger:
        # กรณีถึงเป้าแล้ว: ขึ้นตัวแดงใหญ่ๆ กระพริบๆ
        st.markdown(f"""
        <div class="fire-alert">
            🚨 FIRE WOOD {next_wood} NOW! 🚨<br>
            ราคา {current_thb_baht:,.0f} ถึงจุดนัดพบแล้ว ({trap_price:,.0f})<br>
            <small>กดปุ่มยิงด้านล่างเดี๋ยวนี้!</small>
        </div>
        """, unsafe_allow_html=True)
    else:
        # กรณียังไม่ถึงเป้า: แจ้งให้ตั้งรอ
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
                    if i == next_wood and alert_trigger:
                         st.markdown(f"🔥 **ยิงเลย! ที่:** `{current_thb_baht:,.0f}`")
                    elif i == next_wood:
                         st.markdown(f"📍 **รอช้อนที่:** `{trap_price:,.0f}`")
                else:
                    target_sell = wood['entry_price'] + gap_profit + spread_buffer
                    curr_profit = (current_thb_baht - spread_buffer - wood['entry_price']) * wood['grams']
                    color_pl = "green" if current_thb_baht >= target_sell else "red"
                    st.markdown(f"ทุน: **{wood['entry_price']:.0f}** | เป้า: **{target_sell:,.0f}**")
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
        st.subheader("📈 กราฟทองคำโลก")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df_gold.index, open=df_gold['Open'], high=df_gold['High'],
                        low=df_gold['Low'], close=df_gold['Close'], name='Price'))
        fig.add_trace(go.Scatter(x=df_gold.index, y=df_gold['EMA50'], name='EMA 50 (ส้ม)', line=dict(color='orange', width=1)))
        fig.update_layout(height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("ไม่สามารถโหลดกราฟได้")

st.markdown("<div class='footer'>🛠️ Engineered by <b>โบ้ 50</b></div>", unsafe_allow_html=True)

