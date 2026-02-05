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

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600&display=swap');
    html, body, [class*="css"]  { font-family: 'Kanit', sans-serif; }
    .buy-sig { background-color: #dcfce7; color: #166534; border: 1px solid #166534; padding: 10px; border-radius: 5px; }
    .sell-sig { background-color: #fee2e2; color: #991b1b; border: 1px solid #991b1b; padding: 10px; border-radius: 5px; }
    .wait-sig { background-color: #f3f4f6; color: #374151; border: 1px solid #6b7280; padding: 10px; border-radius: 5px; }
    .footer { text-align: center; color: #94a3b8; font-size: 0.9rem; margin-top: 50px; border-top: 1px dashed #cbd5e1; padding-top: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("🏆 Gold Pro: Trap Master V2.8 (Auto Support/Resistance)")
st.markdown("**เครื่องมือวางแผนเทรดทองคำ: วิเคราะห์แนวรับ-ต้าน อัตโนมัติ**")
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

# --- 3. ฟังก์ชันคำนวณกราฟ & แนวรับต้าน ---
def calculate_indicators(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    return df

def find_support_resistance(df):
    # หาจุดต่ำสุด/สูงสุด ในรอบ 20 แท่งเทียนล่าสุด
    recent_low = df['Low'].tail(20).min()
    recent_high = df['High'].tail(20).max()
    return recent_low, recent_high

@st.cache_data(ttl=60)
def get_market_data():
    try:
        fx = yf.Ticker("THB=X").history(period="1d")['Close'].iloc[-1]
        # ดึงกราฟ 5 วัน รายชั่วโมง
        df = yf.download("GC=F", period="5d", interval="1h", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if len(df) > 0: df = calculate_indicators(df)
        return float(fx), df
    except: return 34.50, None

# --- 4. Sidebar ---
st.sidebar.header("⚙️ ตั้งค่าราคา")
price_source = st.sidebar.radio("แหล่งที่มา:", ["🤖 Auto (Spot)", "✍️ Manual (ระบุเอง)"])

auto_fx, df_gold = get_market_data()
current_thb_baht = 0.0 
current_rsi = 0.0
support_usd, resistance_usd = 0.0, 0.0

if price_source == "🤖 Auto (Spot)":
    st.sidebar.caption("🔧 จูนราคาให้ตรงแอป")
    fx_rate = st.sidebar.number_input("USD/THB", value=auto_fx, format="%.2f")
    premium = st.sidebar.number_input("Premium (+)", value=100.0, step=10.0)
    
    if df_gold is not None:
        current_usd = float(df_gold['Close'].iloc[-1])
        current_thb_baht = round(((current_usd * fx_rate * 0.473) + premium) / 50) * 50
        current_rsi = df_gold['RSI'].iloc[-1]
        support_usd, resistance_usd = find_support_resistance(df_gold)
        st.sidebar.success(f"ราคาตลาด: **{current_thb_baht:,.0f}**")
else:
    manual_price = st.sidebar.number_input("ราคาทอง (บาทละ)", value=40500, step=50)
    current_thb_baht = manual_price
    if df_gold is not None: 
        current_rsi = df_gold['RSI'].iloc[-1]
        support_usd, resistance_usd = find_support_resistance(df_gold)

st.sidebar.markdown("---")
gap_profit = st.sidebar.number_input("กำไรขั้นต่ำ/ไม้ (บาท)", value=300, step=50)
spread_buffer = st.sidebar.number_input("เผื่อ Spread ขายคืน", value=50.0, step=10.0)
base_trade_size = st.sidebar.number_input("เงินต้นเริ่มแรก", value=10000, step=1000)

# --- 5. AI Analysis ---
col_rsi, col_supp, col_res = st.columns(3)
col_rsi.metric("RSI ปัจจุบัน", f"{current_rsi:.1f}", 
               delta="โซนเข้าซื้อ" if current_rsi <= 45 else "โซนรอ/ขาย",
               delta_color="normal" if current_rsi <= 45 else "inverse")

if price_source == "🤖 Auto (Spot)":
    # แปลงแนวรับต้านเป็นเงินบาท
    supp_thb = round(((support_usd * fx_rate * 0.473) + premium) / 50) * 50
    res_thb = round(((resistance_usd * fx_rate * 0.473) + premium) / 50) * 50
    col_supp.metric("🟢 แนวรับ (จุดซื้อ)", f"{supp_thb:,.0f} ฿", f"Spot ${support_usd:.1f}")
    col_res.metric("🔴 แนวต้าน (จุดขาย)", f"{res_thb:,.0f} ฿", f"Spot ${resistance_usd:.1f}")
else:
    col_supp.metric("แนวรับ (USD)", f"${support_usd:.1f}")
    col_res.metric("แนวต้าน (USD)", f"${resistance_usd:.1f}")

# --- 6. Operations Tabs ---
st.write("---")
tab1, tab2, tab3 = st.tabs(["📈 กราฟเทคนิค (Entry)", "🔫 แผงควบคุม (Sniper)", "🧊 คลังสมบัติ"])

with tab1:
    if df_gold is not None:
        fig = go.Figure()
        
        # แท่งเทียน
        fig.add_trace(go.Candlestick(x=df_gold.index, open=df_gold['Open'], high=df_gold['High'],
                        low=df_gold['Low'], close=df_gold['Close'], name='Price'))
        
        # EMA
        fig.add_trace(go.Scatter(x=df_gold.index, y=df_gold['EMA50'], name='EMA 50', line=dict(color='orange', width=1)))
        fig.add_trace(go.Scatter(x=df_gold.index, y=df_gold['EMA200'], name='EMA 200', line=dict(color='blue', width=1)))
        
        # เส้นแนวรับ/ต้าน
        fig.add_hline(y=support_usd, line_dash="dot", line_color="green", annotation_text="แนวรับ (Support)")
        fig.add_hline(y=resistance_usd, line_dash="dot", line_color="red", annotation_text="แนวต้าน (Resistance)")
        
        fig.update_layout(height=500, xaxis_rangeslider_visible=False, title="XAU/USD (1H) + Auto Levels")
        st.plotly_chart(fig, use_container_width=True)
        
        st.info(f"""
        💡 **กลยุทธ์เข้าไม้ 1:**
        1. ดูที่ **RSI**: ถ้าต่ำกว่า **45** (ตอนนี้ {current_rsi:.1f}) -> เตรียมตัว
        2. ดูที่ **เส้นประสีเขียว (แนวรับ)**: ถ้าราคาลงมาแตะเส้นนี้แล้วไม่หลุด -> **กดซื้อได้เลย!**
        """)
    else:
        st.error("โหลดกราฟไม่ได้")

with tab2:
    st.subheader(f"🎯 เป้ากำไร: +{gap_profit} บ./ไม้")
    portfolio = st.session_state.gold_team_data['portfolio']
    current_capital = base_trade_size + st.session_state.gold_team_data.get('accumulated_profit', 0.0)
    
    for i in range(1, 6):
        key = str(i)
        wood = portfolio[key]
        with st.container(border=True):
            c1, c2, c3 = st.columns([1,3,2])
            with c1: st.markdown(f"### 🪵 #{i}")
            with c2:
                if wood['status'] == 'EMPTY': st.caption("สถานะ: ว่าง")
                else:
                    target_s = wood['entry_price'] + gap_profit + spread_buffer
                    curr_p = (current_thb_baht - spread_buffer - wood['entry_price']) * wood['grams']
                    col = "green" if current_thb_baht >= target_s else "red"
                    st.markdown(f"ทุน: **{wood['entry_price']:.0f}** | เป้า: **{target_s:,.0f}**")
                    st.markdown(f"สถานะ: :{col}[{curr_p:+.0f} ฿]")
            with c3:
                if wood['status'] == 'EMPTY':
                    prev = True if i==1 else portfolio[str(i-1)]['status']=='ACTIVE'
                    if prev:
                        if st.button(f"🔴 ซื้อ", key=f"b_{i}", use_container_width=True):
                            st.session_state.gold_team_data['portfolio'][key] = {
                                'status':'ACTIVE', 'entry_price':current_thb_baht, 
                                'grams': current_capital/current_thb_baht, 'date': datetime.now().strftime("%Y-%m-%d")
                            }
                            save_data(st.session_state.gold_team_data); st.rerun()
                else:
                    target_s = wood['entry_price'] + gap_profit + spread_buffer
                    btn_type = "primary" if current_thb_baht >= target_s else "secondary"
                    if st.button("💰 ขาย", key=f"s_{i}", type=btn_type, use_container_width=True):
                        prof = (current_thb_baht - spread_buffer - wood['entry_price']) * wood['grams']
                        st.session_state.gold_team_data['vault'].append({'wood':i, 'profit':prof, 'date':datetime.now().strftime("%Y-%m-%d")})
                        st.session_state.gold_team_data['accumulated_profit'] += prof
                        st.session_state.gold_team_data['portfolio'][key] = {'status':'EMPTY', 'entry_price':0, 'grams':0, 'date':None}
                        save_data(st.session_state.gold_team_data); st.success(f"กำไร {prof:.0f} บ."); st.rerun()

with tab3:
    vault = st.session_state.gold_team_data.get('vault', [])
    if vault:
        st.dataframe(pd.DataFrame(vault), use_container_width=True)
        st.metric("กำไรสะสม", f"{sum(d['profit'] for d in vault):,.0f} ฿")
        if st.button("ล้างประวัติ"):
            st.session_state.gold_team_data['vault'] = []; st.session_state.gold_team_data['accumulated_profit'] = 0
            save_data(st.session_state.gold_team_data); st.rerun()
    else: st.info("ยังไม่มีประวัติ")

st.markdown("<div class='footer'>🛠️ Engineered by <b>โบ้ 50</b></div>", unsafe_allow_html=True)
