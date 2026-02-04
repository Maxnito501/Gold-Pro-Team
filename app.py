import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Gold Pro: Team Edition", page_icon="🏆", layout="wide")

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600&display=swap');
    html, body, [class*="css"]  { font-family: 'Kanit', sans-serif; }
    
    .gold-box { background-color: #fffbeb; padding: 20px; border-radius: 10px; border: 1px solid #fcd34d; text-align: center; }
    .buy-sig { background-color: #dcfce7; color: #166534; padding: 10px; border-radius: 5px; border-left: 5px solid #166534; }
    .sell-sig { background-color: #fee2e2; color: #991b1b; padding: 10px; border-radius: 5px; border-left: 5px solid #991b1b; }
    .wait-sig { background-color: #f3f4f6; color: #374151; padding: 10px; border-radius: 5px; border-left: 5px solid #6b7280; }
    
    .footer {
        text-align: center;
        color: #94a3b8;
        font-size: 0.9rem;
        margin-top: 50px;
        padding-top: 20px;
        border-top: 1px dashed #cbd5e1;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏆 Gold Pro: ระบบวิเคราะห์ทองคำ (Team Edition)")
st.markdown("**เครื่องมือช่วยตัดสินใจสำหรับทีมงาน: เก็งกำไรระยะสั้น & ออมระยะยาว**")
st.write("---")

# --- 2. ฟังก์ชันคำนวณ ---
def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=60)
def get_market_data():
    try:
        # ดึงค่าเงินบาท และ ราคาทองโลก
        tickers = "THB=X GC=F"
        df = yf.download(tickers, period="6mo", interval="1d", progress=False)
        
        if isinstance(df.columns, pd.MultiIndex):
            df_close = df['Close']
        else:
            df_close = df['Close']
            
        fx = float(df_close['THB=X'].iloc[-1])
        
        # ข้อมูลทองคำทำกราฟ
        gold_df = yf.download("GC=F", period="6mo", interval="1d", progress=False)
        if isinstance(gold_df.columns, pd.MultiIndex): gold_df.columns = gold_df.columns.get_level_values(0)
        
        gold_df['RSI'] = calculate_rsi(gold_df)
        gold_df['EMA50'] = gold_df['Close'].ewm(span=50, adjust=False).mean()
        gold_df['EMA200'] = gold_df['Close'].ewm(span=200, adjust=False).mean()
        
        return fx, gold_df
    except:
        return 34.50, None

# --- 3. Sidebar ตั้งค่า ---
st.sidebar.header("⚙️ ตั้งค่าราคา (Calibration)")
auto_fx, df_gold = get_market_data()

fx_rate = st.sidebar.number_input("ค่าเงินบาท (USD/THB)", value=auto_fx, format="%.2f")
premium = st.sidebar.number_input("ส่วนต่างร้านทอง (Premium)", value=100.0, step=10.0, help="ปรับเพื่อให้ราคาตรงกับแอปเป๋าตัง/ฮั่วเซ่งเฮง")

# คำนวณราคาทองไทย
current_usd = df_gold['Close'].iloc[-1] if df_gold is not None else 0
current_thb = round(((current_usd * fx_rate * 0.473) + premium) / 50) * 50

# --- 4. Dashboard หลัก ---
c1, c2, c3 = st.columns(3)
c1.metric("🌍 Gold Spot (USD)", f"${current_usd:,.2f}")
c2.metric("🇹🇭 ทองคำแท่ง (บาท)", f"{current_thb:,.0f} ฿", help="ราคาขายออกโดยประมาณ")
rsi_val = df_gold['RSI'].iloc[-1] if df_gold is not None else 50
c3.metric("📊 RSI (Momentum)", f"{rsi_val:.1f}")

# --- 5. AI Strategy Advisor ---
st.subheader("🧠 คำแนะนำกลยุทธ์ (AI Strategy)")

if df_gold is not None:
    last_close = df_gold['Close'].iloc[-1]
    ema50 = df_gold['EMA50'].iloc[-1]
    ema200 = df_gold['EMA200'].iloc[-1]
    
    col_short, col_long = st.columns(2)
    
    # === กลยุทธ์เล่นสั้น (Sniper) ===
    with col_short:
        st.info("⚡ **สายเก็งกำไร (เล่นสั้น/รายวัน)**")
        signal_short = ""
        
        if rsi_val <= 30:
            signal_short = "🔫 **FIRE! (ซื้อสวน)**: ราคาลงลึกมาก (Oversold) ลุ้นเด้งสั้นๆ"
            st.markdown(f'<div class="buy-sig">{signal_short}</div>', unsafe_allow_html=True)
        elif rsi_val <= 45 and last_close > ema200:
            signal_short = "🟢 **BUY DIP (ย่อซื้อ)**: แนวโน้มยังขาขึ้น ราคาย่อตัวน่าสะสม"
            st.markdown(f'<div class="buy-sig">{signal_short}</div>', unsafe_allow_html=True)
        elif rsi_val >= 70:
            signal_short = "🔴 **SELL (ขายทำกำไร)**: ราคาแพงเกินไป ระวังย่อตัว"
            st.markdown(f'<div class="sell-sig">{signal_short}</div>', unsafe_allow_html=True)
        else:
            signal_short = "⏳ **WAIT (รอจังหวะ)**: ราคากลางๆ ไม่มีความได้เปรียบ"
            st.markdown(f'<div class="wait-sig">{signal_short}</div>', unsafe_allow_html=True)
            
        st.caption("*เป้าหมายกำไร: 200-500 บาท/บาททองคำ*")

    # === กลยุทธ์เล่นยาว (Investor) ===
    with col_long:
        st.success("🐢 **สายออมยาว (ถือข้ามปี/เกษียณ)**")
        signal_long = ""
        
        if last_close > ema200:
            signal_long = "🐂 **HOLD / RUN TREND**: ภาพใหญ่เป็นขาขึ้น ถือต่อไป"
            st.markdown(f'<div class="buy-sig">{signal_long}</div>', unsafe_allow_html=True)
            if last_close < ema50:
                st.caption("✨ *ราคาลงมาแตะแนวรับกลาง น่าเก็บเพิ่ม*")
        else:
            signal_long = "🐻 **CAUTION**: ราคาหลุดแนวรับสำคัญ ระยะยาวเริ่มเสียทรง"
            st.markdown(f'<div class="sell-sig">{signal_long}</div>', unsafe_allow_html=True)
            
        st.caption("*เป้าหมาย: สะสมความมั่งคั่ง ชนะเงินเฟ้อ*")

# --- 6. เครื่องคิดเลขทำมาหากิน ---
st.write("---")
with st.expander("🧮 เครื่องคิดเลขวางแผนเทรด (Profit Calculator)", expanded=True):
    c_cal1, c_cal2, c_cal3 = st.columns(3)
    with c_cal1:
        my_budget = st.number_input("เงินลงทุน (บาท)", value=10000, step=1000)
    with c_cal2:
        buy_price = st.number_input("ราคาซื้อ (ต้นทุน)", value=current_thb, step=50)
    with c_cal3:
        target_profit = st.number_input("อยากได้กำไรกี่บาท?", value=300, step=50)
        
    gold_amount = my_budget / buy_price
    spread = 100
    sell_price_target = buy_price + (target_profit / gold_amount) + spread
    sell_price_target = round(sell_price_target / 50) * 50
    
    st.markdown(f"""
    <div class="gold-box">
        <h4>🎯 เป้าหมายราคาขาย: <b>{sell_price_target:,}</b> บาท</h4>
        <small>คุณจะได้ทอง: {gold_amount:.4f} บาท | หัก Spread {spread} บาทแล้ว</small>
    </div>
    """, unsafe_allow_html=True)

# --- 7. กราฟเทคนิค ---
st.write("---")
st.subheader("📈 กราฟราคา Spot Gold")
if df_gold is not None:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_gold.index, open=df_gold['Open'], high=df_gold['High'],
                    low=df_gold['Low'], close=df_gold['Close'], name='Price'))
    fig.add_trace(go.Scatter(x=df_gold.index, y=df_gold['EMA50'], name='EMA 50 (ส้ม)', line=dict(color='orange', width=1)))
    fig.add_trace(go.Scatter(x=df_gold.index, y=df_gold['EMA200'], name='EMA 200 (ฟ้า)', line=dict(color='blue', width=2)))
    fig.update_layout(height=500, xaxis_rangeslider_visible=False, title="XAU/USD Daily Chart")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("ไม่สามารถโหลดกราฟได้")

# --- Footer (ลายเซ็นวิศวกร) ---
st.write("")
st.write("")
st.markdown("<div class='footer'>🛠️ Engineered by <b>โบ้ 50</b> | Powered by Python & Streamlit</div>", unsafe_allow_html=True)
