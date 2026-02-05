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
    
    .gold-box { background-color: #fffbeb; padding: 15px; border-radius: 10px; border: 1px solid #fcd34d; text-align: center; margin-bottom: 10px; }
    .target-box { background-color: #f0f9ff; padding: 10px; border-radius: 5px; border-left: 4px solid #0ea5e9; font-size: 0.9em; margin-top: 5px; }
    
    .buy-sig { background-color: #dcfce7; color: #166534; padding: 10px; border-radius: 5px; border-left: 5px solid #166534; font-weight: bold; }
    .sell-sig { background-color: #fee2e2; color: #991b1b; padding: 10px; border-radius: 5px; border-left: 5px solid #991b1b; font-weight: bold; }
    .wait-sig { background-color: #f3f4f6; color: #374151; padding: 10px; border-radius: 5px; border-left: 5px solid #6b7280; font-weight: bold; }
    
    .footer { text-align: center; color: #94a3b8; font-size: 0.9rem; margin-top: 50px; border-top: 1px dashed #cbd5e1; padding-top: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("🏆 Gold Pro: Strategic Sniper V3.5")
st.markdown("**เครื่องมือวางแผนเทรดทองคำ: ระบบ Grid + Trend Analysis**")
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
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean() # เพิ่ม EMA ระยะยาว
    return df

@st.cache_data(ttl=60)
def get_market_data():
    try:
        fx = yf.Ticker("THB=X").history(period="1d")['Close'].iloc[-1]
        # ดึง 3 เดือน เพื่อให้เห็นเทรนด์และคำนวณ EMA200 ได้
        df = yf.download("GC=F", period="3mo", interval="1h", progress=False)
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
trend_status = "N/A"

if price_source == "🤖 Auto (Spot)":
    st.sidebar.caption("🔧 จูนราคาให้ตรงแอป")
    fx_rate = st.sidebar.number_input("USD/THB", value=auto_fx, format="%.2f")
    premium = st.sidebar.number_input("Premium (+)", value=100.0, step=10.0)
    
    if df_gold is not None:
        current_usd = float(df_gold['Close'].iloc[-1])
        current_thb_baht = round(((current_usd * fx_rate * 0.473) + premium) / 50) * 50
        current_rsi = df_gold['RSI'].iloc[-1]
        
        # วิเคราะห์เทรนด์
        ema200 = df_gold['EMA200'].iloc[-1]
        if current_usd > ema200: trend_status = "🐂 ขาขึ้น (Uptrend)"
        else: trend_status = "🐻 ขาลง (Downtrend)"
            
        st.sidebar.success(f"ราคาตลาด: **{current_thb_baht:,.0f}**")
else:
    st.sidebar.caption("กรอกราคาซื้อขายจริงจากแอป")
    manual_price = st.sidebar.number_input("ราคาทอง (บาทละ)", value=40500, step=50)
    current_thb_baht = manual_price
    if df_gold is not None: 
        current_rsi = df_gold['RSI'].iloc[-1]

st.sidebar.markdown("---")
st.sidebar.header("📏 ตั้งค่าระยะ Grid")
gap_buy_1_2 = st.sidebar.number_input("ไม้ 1->2 (บาท)", value=500, step=100)
gap_buy_2_3 = st.sidebar.number_input("ไม้ 2->3 (บาท)", value=1000, step=100)
gap_3_4 = st.sidebar.number_input("ไม้ 3->4 (บาท)", value=800, step=50)
gap_4_5 = st.sidebar.number_input("ไม้ 4->5 (บาท)", value=1000, step=50)

st.sidebar.markdown("---")
gap_profit = st.sidebar.number_input("กำไรขั้นต่ำ/ไม้ (บาท)", value=300, step=50)
spread_buffer = st.sidebar.number_input("เผื่อ Spread ขายคืน", value=50.0, step=10.0)
base_trade_size = st.sidebar.number_input("เงินต้นเริ่มแรก", value=10000, step=1000)

# --- 5. AI Strategy Advisor ---
st.subheader("🧠 คำแนะนำกลยุทธ์ (AI Strategy)")

col_sniper, col_investor = st.columns(2)

with col_sniper:
    st.markdown("#### ⚡ Sniper (เล่นสั้น)")
    if current_rsi <= 30:
        st.markdown(f'<div class="buy-sig">💎 <b>FIRE!</b>: RSI {current_rsi:.0f} ต่ำมาก (ซื้อสวน)</div>', unsafe_allow_html=True)
    elif current_rsi <= 45:
        st.markdown(f'<div class="buy-sig">🛒 <b>BUY DIP</b>: RSI {current_rsi:.0f} ย่อตัวสวย</div>', unsafe_allow_html=True)
    elif current_rsi >= 75:
        st.markdown(f'<div class="sell-sig">💰 <b>SELL</b>: RSI {current_rsi:.0f} แพงแล้ว</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="wait-sig">⏳ <b>WAIT</b>: RSI {current_rsi:.0f} ราคากลางๆ</div>', unsafe_allow_html=True)

with col_investor:
    st.markdown("#### 🐢 Trend (เทรนด์หลัก)")
    st.markdown(f'<div class="wait-sig">{trend_status}</div>', unsafe_allow_html=True)

# --- 6. Logic คำนวณพอร์ต ---
portfolio = st.session_state.gold_team_data['portfolio']
current_capital = base_trade_size + st.session_state.gold_team_data.get('accumulated_profit', 0.0)

# คำนวณไม้ล่าสุดและไม้ถัดไป
last_active_wood = 0
last_entry_price = 0
for i in range(1, 6):
    if portfolio[str(i)]['status'] == 'ACTIVE':
        last_active_wood = i
        last_entry_price = portfolio[str(i)]['entry_price']

# --- 7. Display Dashboard ---
st.write("---")
c1, c2, c3, c4 = st.columns(4)
c1.metric("โหมด", "Auto" if "Auto" in price_source else "Manual")
c2.metric("สถานะพอร์ต", f"{last_active_wood}/5 ไม้")
c3.metric("ราคาทองไทย", f"{current_thb_baht:,.0f} ฿")
c4.metric("เงินทุน (ทบต้น)", f"{current_capital:,.0f} ฿")

tab1, tab2, tab3 = st.tabs(["🔫 Sniper Board", "🧊 Vault", "📈 Technical Chart"])

with tab1:
    st.subheader(f"🎯 เป้ากำไร: +{gap_profit} บาท/ไม้ (รวม Spread)")
    
    for i in range(1, 6):
        key = str(i)
        wood = portfolio[key]
        
        with st.container(border=True):
            col_id, col_info, col_btn = st.columns([1, 3, 2])
            with col_id: st.markdown(f"### 🪵 #{i}")
            
            # --- คำนวณเป้าหมาย (The Guide) ---
            guide_text = ""
            if wood['status'] == 'EMPTY':
                # คำนวณจุดรอซื้อ (Buy Target)
                if i == 1:
                    buy_target = "รอสัญญาณ RSI / แนวรับ"
                else:
                    # คำนวณ Gap จากไม้ก่อนหน้า
                    prev_wood_idx = i - 1
                    # ถ้าไม้ก่อนหน้า Active ถึงจะคำนวณได้
                    if portfolio[str(prev_wood_idx)]['status'] == 'ACTIVE':
                        prev_price = portfolio[str(prev_wood_idx)]['entry_price']
                        if i == 2: gap = gap_buy_1_2
                        elif i == 3: gap = gap_buy_2_3
                        elif i == 4: gap = gap_3_4
                        else: gap = gap_4_5
                        buy_target = f"{prev_price - gap:,.0f}"
                    else:
                        buy_target = "รอไม้ก่อนหน้า"
                
                guide_text = f"📉 **เป้าซื้อ:** {buy_target}"
                
            else:
                # คำนวณจุดรอขาย (Sell Target)
                target_sell = wood['entry_price'] + gap_profit + spread_buffer
                guide_text = f"🎯 **เป้าขาย:** {target_sell:,.0f}"

            with col_info:
                if wood['status'] == 'EMPTY':
                    st.caption("ว่าง (พร้อมยิง)")
                    st.markdown(f'<div class="target-box">{guide_text}</div>', unsafe_allow_html=True)
                else:
                    curr_profit = (current_thb_baht - spread_buffer - wood['entry_price']) * wood['grams']
                    color_pl = "green" if current_thb_baht >= target_sell else "red"
                    st.markdown(f"ทุน: **{wood['entry_price']:.0f}**")
                    st.markdown(f"สถานะ: :{color_pl}[{curr_profit:+.0f} ฿]")
                    st.markdown(f'<div class="target-box">{guide_text}</div>', unsafe_allow_html=True)

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
            st.session_state.gold_team_data['vault'] = []; st.session_state.gold_team_data['accumulated_profit'] = 0
            save_data(st.session_state.gold_team_data); st.rerun()
    else: st.info("ยังไม่มีประวัติ")

with tab3:
    if df_gold is not None:
        st.subheader("📈 กราฟเทคนิค (3 Months)")
        
        # หาแนวรับแนวต้าน (Support/Resistance) อัตโนมัติ
        recent_low = df_gold['Low'].tail(50).min()
        recent_high = df_gold['High'].tail(50).max()
        
        fig = go.Figure()
        
        # แท่งเทียน
        fig.add_trace(go.Candlestick(x=df_gold.index, open=df_gold['Open'], high=df_gold['High'],
                        low=df_gold['Low'], close=df_gold['Close'], name='Price'))
        
        # เส้นค่าเฉลี่ย
        fig.add_trace(go.Scatter(x=df_gold.index, y=df_gold['EMA50'], name='EMA 50 (ส้ม)', line=dict(color='orange', width=1)))
        fig.add_trace(go.Scatter(x=df_gold.index, y=df_gold['EMA200'], name='EMA 200 (ฟ้า)', line=dict(color='blue', width=2)))
        
        # เส้นแนวรับแนวต้าน
        fig.add_hline(y=recent_low, line_dash="dot", line_color="green", annotation_text="Support (แนวรับ)")
        fig.add_hline(y=recent_high, line_dash="dot", line_color="red", annotation_text="Resistance (แนวต้าน)")
        
        fig.update_layout(height=600, xaxis_rangeslider_visible=False, title="XAU/USD Trend Analysis")
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("💡 **Tips:** \n- เส้นสีฟ้า (EMA 200) บอกเทรนด์ระยะยาว \n- เส้นประสีเขียว คือแนวรับสำคัญ ถ้าหลุดเตรียมรับไม้ถัดไป")
    else:
        st.error("ไม่สามารถโหลดกราฟได้")

st.markdown("<div class='footer'>🛠️ Engineered by <b>โบ้ 50</b></div>", unsafe_allow_html=True)
