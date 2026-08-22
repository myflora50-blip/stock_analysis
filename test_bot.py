from tradingview_ta import TA_Handler, Interval

ASSETS = [
    {
        "name": "E7 Group (Abu Dhabi)",
        "symbol": "E7",
        "exchange": "ADX",
        "screener": "uae",
    },
    {
        "name": "Emaar Properties (Dubai)",
        "symbol": "EMAAR",
        "exchange": "DFM",
        "screener": "uae",
    },
    {
        "name": "Bitcoin (Crypto)",
        "symbol": "BTCUSDT",
        "exchange": "BINANCE",
        "screener": "crypto",
    },
]


def explain_reasons(indicators, summary):
  """Generates clear technical reasons for the Buy/Sell recommendation."""
  reasons = []

  rsi = indicators.get("RSI")
  macd = indicators.get("MACD.macd")
  macd_signal = indicators.get("MACD.signal")
  sma20 = indicators.get("SMA20")
  sma50 = indicators.get("SMA50")
  close = indicators.get("close")

  # 1. RSI Analysis
  if rsi:
    if rsi < 30:
      reasons.append(
          f"RSI is at {rsi:.2f} (Oversold zone - Strong bullish potential)"
      )
    elif rsi > 70:
      reasons.append(
          f"RSI is at {rsi:.2f} (Overbought zone - Potential reversal down)"
      )
    else:
      reasons.append(f"RSI is neutral at {rsi:.2f}")

  # 2. Moving Average Analysis
  if close and sma20 and sma50:
    if close > sma20 > sma50:
      reasons.append(
          f"Price ({close:.4f}) is above SMA20 ({sma20:.4f}) and SMA50"
          f" ({sma50:.4f}) -> Uptrend"
      )
    elif close < sma20 < sma50:
      reasons.append(
          f"Price ({close:.4f}) is below SMA20 ({sma20:.4f}) and SMA50"
          f" ({sma50:.4f}) -> Downtrend"
      )

  # 3. MACD Analysis
  if macd is not None and macd_signal is not None:
    if macd > macd_signal:
      reasons.append("MACD is above Signal Line (Bullish Momentum)")
    else:
      reasons.append("MACD is below Signal Line (Bearish Momentum)")

  # 4. Summary Breakdown
  reasons.append(
      f"Overall consensus out of 26 technical indicators: {summary['BUY']} Buy"
      f" vs {summary['SELL']} Sell"
  )

  return reasons


def check_markets():
  print("🔍 Scanning markets via TradingView...\n")

  for asset in ASSETS:
    try:
      handler = TA_Handler(
          symbol=asset["symbol"],
          exchange=asset["exchange"],
          screener=asset["screener"],
          #interval=Interval.INTERVAL_1_HOUR,
          # Change from 1 HOUR to 1 DAY
          interval = Interval.INTERVAL_1_DAY
      )

      analysis = handler.get_analysis()
      summary = analysis.summary
      indicators = analysis.indicators

      # Price Metrics
      open_price = indicators.get("open", 0.0)
      close_price = indicators.get("close", 0.0)
      price_change = (
          ((close_price - open_price) / open_price) * 100
          if open_price > 0
          else 0.0
      )
      change_sign = "+" if price_change >= 0 else ""

      print(f"📊 Asset: {asset['name']} ({asset['symbol']})")
      print(
          f"💵 Open: {open_price:.4f} | Close: {close_price:.4f} ("
          f"{change_sign}{price_change:.2f}%)"
      )
      print(f"💡 Recommendation: **{summary['RECOMMENDATION']}**")
      print("\n📌 Key Analysis Drivers:")

      reasons = explain_reasons(indicators, summary)
      for reason in reasons:
        print(f"  • {reason}")

      print("-" * 60)

    except Exception as e:
      print(f"❌ Error scanning {asset['name']}: {e}")
      print("-" * 60)


if __name__ == "__main__":
  check_markets()