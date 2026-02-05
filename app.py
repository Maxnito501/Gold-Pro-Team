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
</style>
""", unsafe_allow_html=True)

st.title("🏆 Gold Pro: Strategic Sniper V3.0")
st.markdown("**เครื่องมือวางแผนเทรดทองคำ: ระบบ Grid แบบก้าวหน้า (Progressive Grid)**")
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
        df = yf.download("GC=F", period="5d", interval="1h", progress=False)
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
st.sidebar.header("📏 ตั้งค่า Grid (ระยะห่าง)")
gap_1_2 = st.sidebar.number_input("ไม้ 1 -> 2 (บาท)", value=400, step=50)
gap_2_3 = st.sidebar.number_input("ไม้ 2 -> 3 (บาท)", value=600, step=50)
gap_3_4 = st.sidebar.number_input("ไม้ 3 -> 4 (บาท)", value=800, step=50)
gap_4_5 = st.sidebar.number_input("ไม้ 4 -> 5 (บาท)", value=1000, step=50)

st.sidebar.markdown("---")
gap_profit = st.sidebar.number_input("กำไรขั้นต่ำ/ไม้ (บาท)", value=300, step=50)
spread_buffer = st.sidebar.number_input("เผื่อ Spread ขายคืน", value=50.0, step=10.0)
base_trade_size = st.sidebar.number_input("เงินต้นเริ่มแรก", value=10000, step=1000)

# --- 5. AI Strategy Advisor (Smart Logic) ---
# Logic: หาไม้ถัดไปที่ต้องยิง หรือ ไม้ที่ควรขาย
portfolio = st.session_state.gold_team_data['portfolio']

# 1. เช็คสัญญาณขายก่อน (สำคัญสุด)
sell_signal = None
active_woods = []
for i in range(1, 6):
    wood = portfolio[str(i)]
    if wood['status'] == 'ACTIVE':
        active_woods.append(i)
        target = wood['entry_price'] + gap_profit + spread_buffer
        if current_thb_baht >= target:
            profit = (current_thb_baht - spread_buffer - wood['entry_price']) * wood['grams']
            sell_signal = f"💰 **SELL WOOD {i}!** (กำไร {profit:.0f} บาท) - ราคาถึงเป้าแล้ว"

# 2. ถ้าไม่มีขาย เช็คสัญญาณซื้อ
buy_signal = None
buy_price_target = 0
reason = ""

# หาไม้ล่าสุดที่ถืออยู่
last_wood_idx = max(active_woods) if active_woods else 0
next_wood_idx = last_active_wood + 1 if last_active_wood < 5 else 0

if sell_signal:
    ai_msg = sell_signal
    ai_class = "sell-sig"
elif next_wood_idx > 0:
    # คำนวณราคาเป้าหมายสำหรับไม้ถัดไป
    if next_wood_idx == 1:
        # ไม้ 1: ดู RSI หรือแนวรับ
        if current_rsi <= 45:
            buy_signal = f"🚀 **FIRE WOOD 1**: ราคาเหมาะสม (RSI {current_rsi:.0f})"
            ai_class = "buy-sig"
        else:
            buy_signal = f"⏳ **WAIT WOOD 1**: ราคายังไม่ย่อ (RSI {current_rsi:.0f})"
            ai_class = "wait-sig"
        buy_price_target = current_thb_baht # ราคาตลาดปัจจุบัน
    else:
        # ไม้ 2-5: ดูระยะห่างจากไม้ก่อนหน้า
        last_entry = portfolio[str(last_wood_idx)]['entry_price']
        
        if next_wood_idx == 2: gap = gap_1_2
        elif next_wood_idx == 3: gap = gap_2_3
        elif next_wood_idx == 4: gap = gap_3_4
        else: gap = gap_4_5
            
        buy_price_target = last_entry - gap
        
        if current_thb_baht <= buy_price_target:
             buy_signal = f"🛡️ **FIRE WOOD {next_wood_idx}**: ราคาลงมาตามแผน (ลดลง {gap} บาท)"
             ai_class = "buy-sig"
        else:
             buy_signal = f"⏳ **WAIT WOOD {next_wood_idx}**: รอราคา {buy_price_target:,.0f} (อีก {current_thb_baht - buy_price_target:.0f} บาท)"
             ai_class = "wait-sig"
    
    ai_msg = buy_signal
else:
    ai_msg = "🛑 **PORT FULL**: กระสุนหมดครบ 5 ไม้ (เข้าโหมดถือยาว)"
    ai_class = "sell-sig"

# --- 6. Display Dashboard ---
st.subheader("🧠 คำแนะนำจากระบบ")
st.markdown(f'<div class="sig-box {ai_class}">{ai_msg}</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("โหมด", "Auto" if "Auto" in price_source else "Manual")
c2.metric("สถานะพอร์ต", f"{last_active_wood}/5 ไม้")
c3.metric("ราคาทองไทย", f"{current_thb_baht:,.0f} ฿")
current_capital = base_trade_size + st.session_state.gold_team_data.get('accumulated_profit', 0.0)
c4.metric("เงินทุน (ทบต้น)", f"{current_capital:,.0f} ฿")

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
                    st.caption("สถานะ: ว่าง")
                    # โชว์เป้ารอซื้อเฉพาะไม้ถัดไป
                    if i == next_wood_idx and i > 1:
                         st.markdown(f"📍 **รอช้อนที่:** `{buy_price_target:,.0f}`")
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
                                'date': datetime.now().strftime("%Y-%m-%d")
                            }
                            save_data(st.session_state.gold_team_data)
                            st.rerun()
                else:
                    target_sell = wood['entry_price'] + gap_profit + spread_buffer
                    btn_type = "primary" if current_thb_baht >= target_sell else "secondary"
                    if st.button(f"💰 ขายทำกำไร", key=f"sell_{i}", type=btn_type, use_container_width=True):
                        final_profit = (current_thb_baht - spread_buffer - wood['entry_price']) * wood['grams']
                        st.session_state.gold_team_data['vault'].append({
                            'wood': i, 'profit': final_profit, 'date': datetime.now().strftime("%Y-%m-%d")
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
        fig.add_trace(go.Scatter(x=df_gold.index, y=df_gold['EMA50'], name='EMA 50', line=dict(color='orange', width=1)))
        fig.update_layout(height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("ไม่สามารถโหลดกราฟได้")

st.markdown("<div class='footer'>🛠️ Engineered by <b>โบ้ 50</b></div>", unsafe_allow_html=True)
