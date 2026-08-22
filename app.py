import json
import os
import time
from tradingview_ta import TA_Handler, Interval
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="UAE & Global Trading Scanner",
    page_icon="📈",
    layout="wide",
)

DATA_FILE = "watchlist.json"

DEFAULT_WATCHLIST = [
    {"name": "E7 Group", "symbol": "E7", "exchange": "ADX", "screener": "uae"},
    {
        "name": "Emaar Properties",
        "symbol": "EMAAR",
        "exchange": "DFM",
        "screener": "uae",
    },
    {
        "name": "ADNOC Distribution",
        "symbol": "ADNOCDIST",
        "exchange": "ADX",
        "screener": "uae",
    },
    {
        "name": "Bitcoin",
        "symbol": "BTCUSDT",
        "exchange": "BINANCE",
        "screener": "crypto",
    },
]


def load_watchlist():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r") as f:
        return json.load(f)
    except Exception:
      return DEFAULT_WATCHLIST
  return DEFAULT_WATCHLIST


def save_watchlist(data):
  with open(DATA_FILE, "w") as f:
    json.dump(data, f, indent=4)


if "watchlist" not in st.session_state:
  st.session_state.watchlist = load_watchlist()

TIMEFRAMES = {
    "15 Minutes": Interval.INTERVAL_15_MINUTES,
    "1 Hour": Interval.INTERVAL_1_HOUR,
    "4 Hours": Interval.INTERVAL_4_HOURS,
    "1 Day": Interval.INTERVAL_1_DAY,
    "1 Week": Interval.INTERVAL_1_WEEK,
}

# ---------------- SIDEBAR CONTROLS ----------------
st.sidebar.title("⚙️ Trading Strategy & Controls")

# Strategy Selection Toggle
strategy_mode = st.sidebar.radio(
    "Select Trading Strategy Mode",
    options=[
        "🇦🇪 UAE Bank Mode (Buy Only / Spot)",
        "🌐 Derivatives / Crypto (Long & Short)",
    ],
    help=(
        "UAE Bank Mode is tailored for spot stock apps (ADX/DFM) where you"
        " cannot short sell."
    ),
)

selected_interval_label = st.sidebar.selectbox(
    "Select Scanning Timeframe", list(TIMEFRAMES.keys()), index=3
)
selected_interval = TIMEFRAMES[selected_interval_label]

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Force Refresh Signals"):
  st.cache_data.clear()
  st.rerun()

st.sidebar.subheader("➕ Add Custom Asset")
with st.sidebar.form("add_asset_form", clear_on_submit=True):
  new_name = st.text_input("Asset Name", placeholder="e.g., ADNOC Gas")
  new_symbol = st.text_input("Ticker Symbol", placeholder="e.g., ADNOCGAS")
  new_exchange = st.selectbox(
      "Exchange", ["ADX", "DFM", "BINANCE", "NASDAQ", "NYSE"]
  )
  new_screener = st.selectbox(
      "Screener Category", ["uae", "crypto", "america"]
  )

  submitted = st.form_submit_button("Save Asset")
  if submitted and new_name and new_symbol:
    new_item = {
        "name": new_name,
        "symbol": new_symbol.upper(),
        "exchange": new_exchange,
        "screener": new_screener,
    }
    st.session_state.watchlist.append(new_item)
    save_watchlist(st.session_state.watchlist)
    st.cache_data.clear()
    st.sidebar.success(f"Saved {new_name}!")
    st.rerun()


# ---------------- FETCH & ANALYSIS LOGIC ----------------
@st.cache_data(ttl=300)
def fetch_analysis(symbol, exchange, screener, interval):
  time.sleep(0.4)
  handler = TA_Handler(
      symbol=symbol, exchange=exchange, screener=screener, interval=interval
  )
  analysis = handler.get_analysis()
  return analysis.summary, analysis.indicators


def calculate_trade_levels(indicators, summary, is_uae_mode):
  close_price = indicators.get("close", 0.0)
  rsi = indicators.get("RSI", 50.0)
  macd = indicators.get("MACD.macd", 0.0)
  macd_sig = indicators.get("MACD.signal", 0.0)
  ema20 = indicators.get("EMA20", close_price)
  rec = summary.get("RECOMMENDATION", "NEUTRAL")

  pivot_s1 = indicators.get("Pivot.M.Classic.S1", close_price * 0.98)
  pivot_r1 = indicators.get("Pivot.M.Classic.R1", close_price * 1.02)

  reasons = []

  # --- BUY SIGNAL LOGIC ---
  if "BUY" in rec:
    sl_price = max(pivot_s1, close_price * 0.98)
    risk = close_price - sl_price
    tp_price = close_price + (risk * 2.0)  # 1:2 Risk to Reward Target

    if rsi < 45:
      reasons.append(f"RSI is low at **{rsi:.2f}** (Room for growth).")
    if macd > macd_sig:
      reasons.append("MACD shows strong **Bullish Momentum**.")
    if close_price >= ema20:
      reasons.append(
          f"Price ({close_price:.4f}) is trading **above EMA20** ({ema20:.4f})."
      )
    reasons.append(
        f"Indicator Consensus: **{summary['BUY']} out of 26 indicators** vote"
        " BUY."
    )

    return {
        "action": "BUY",
        "action_label": "🟢 BUY (Enter Trade)",
        "entry": close_price,
        "tp": tp_price,
        "sl": sl_price,
        "reasons": reasons,
    }

  # --- SELL / SHORT SIGNAL LOGIC ---
  elif "SELL" in rec:
    if is_uae_mode:
      # UAE Bank Mode: Filter out short entries and present as exit guidance
      reasons.append(
          "Market trend is weak. **Do not place new buy orders** for this"
          " stock."
      )
      if close_price < ema20:
          reasons.append(f"Price is below EMA20 ({ema20:.4f}).")
      if rsi > 55:
          reasons.append(f"RSI is high at {rsi:.2f} (Overbought/Falling).")
      reasons.append(
          f"Consensus: **{summary['SELL']} out of 26 indicators** vote SELL."
      )

      return {
          "action": "EXIT_ONLY",
          "action_label": "🔴 SELL / DO NOT BUY",
          "entry": close_price,
          "tp": None,
          "sl": None,
          "reasons": reasons,
      }
    else:
      # Derivatives / Crypto Mode: Active Short Position
      sl_price = min(pivot_r1, close_price * 1.02)
      risk = sl_price - close_price
      tp_price = max(0.0001, close_price - (risk * 2.0))

      if rsi > 55:
          reasons.append(f"RSI is at **{rsi:.2f}** (Overbought/Fading).")
      if macd < macd_sig:
          reasons.append("MACD shows **Bearish Momentum**.")
      reasons.append(
          f"Consensus: **{summary['SELL']} out of 26 indicators** vote SELL."
      )

      return {
          "action": "SHORT",
          "action_label": "🔴 SHORT (Sell First)",
          "entry": close_price,
          "tp": tp_price,
          "sl": sl_price,
          "reasons": reasons,
      }

  # --- NEUTRAL LOGIC ---
  else:
    reasons.append(
        "Market is currently consolidating. Wait for a clear breakout before"
        " entering."
    )
    return {
        "action": "NEUTRAL",
        "action_label": "⚪ NEUTRAL / WAIT",
        "entry": close_price,
        "tp": None,
        "sl": None,
        "reasons": reasons,
    }


# ---------------- DASHBOARD UI ----------------
st.title("📈 Market Analysis & Trade Signal Scanner")
is_uae = "UAE Bank" in strategy_mode

if is_uae:
  st.info(
      "🇦🇪 **UAE Bank Mode Active:** Screened for spot stock buying on ADX/DFM."
      " Short sell signals are converted into 'DO NOT BUY' warnings."
  )
else:
  st.warning(
      "🌐 **Derivatives Mode Active:** Showing both Buy (Long) and Sell (Short)"
      " targets for margin/crypto trading."
  )

st.caption(f"Timeframe: **{selected_interval_label}** | Refreshes every 5 mins")

for index, asset in enumerate(st.session_state.watchlist):
  with st.expander(
      f"📌 **{asset['name']}** ({asset['symbol']} - {asset['exchange']})",
      expanded=True,
  ):
    try:
      summary, indicators = fetch_analysis(
          asset["symbol"],
          asset["exchange"],
          asset["screener"],
          selected_interval,
      )
      trade = calculate_trade_levels(indicators, summary, is_uae_mode=is_uae)

      col1, col2, col3, col4 = st.columns([1.2, 1.2, 1, 1])

      close_p = indicators.get("close", 0.0)
      open_p = indicators.get("open", 0.0)
      change = (
          ((close_p - open_p) / open_p) * 100 if open_p and open_p > 0 else 0.0
      )

      col1.metric("Current Price", f"{close_p:.4f}", f"{change:+.2f}%")
      col2.markdown(f"**Signal:** {trade['action_label']}")

      if trade["action"] == "BUY":
        col2.write(f"Buy Target Entry: **{trade['entry']:.4f}**")
        col3.markdown(f"🟢 **Take Profit (Sell At):** `{trade['tp']:.4f}`")
        col4.markdown(f"🔴 **Stop Loss (Exit At):** `{trade['sl']:.4f}`")
      elif trade["action"] == "SHORT":
        col2.write(f"Short Target Entry: **{trade['entry']:.4f}**")
        col3.markdown(f"🟢 **Take Profit (Buy Back At):** `{trade['tp']:.4f}`")
        col4.markdown(f"🔴 **Stop Loss (Exit At):** `{trade['sl']:.4f}`")
      else:
        col3.write("🟢 **Take Profit:** N/A")
        col4.write("🔴 **Stop Loss:** N/A")

      st.markdown("---")
      st.markdown("### 💡 **Signal Breakdown:**")
      for reason in trade["reasons"]:
        st.write(f"- {reason}")

    except Exception as e:
      st.error(f"Error scanning {asset['symbol']}: {e}")

    if st.button(f"🗑️ Remove Asset", key=f"remove_{index}"):
      st.session_state.watchlist.pop(index)
      save_watchlist(st.session_state.watchlist)
      st.cache_data.clear()
      st.rerun()