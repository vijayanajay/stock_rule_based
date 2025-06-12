
This document contains the canonical list of trading strategies and candlestick patterns to be implemented by the rule-based engine.

#### Candlestick Patterns (Custom Library)
1.  Doji
2.  Hammer / Hanging Man
3.  Inverted Hammer / Shooting Star
4.  Bullish Engulfing
5.  Bearish Engulfing
6.  Morning Star
7.  Evening Star
8.  Three White Soldiers
9.  Three Black Crows
10. Piercing Line
11. Dark Cloud Cover
12. Harami (Bullish/Bearish)

#### Trading Strategies (Defined via Rule Engine)
*Strategies will be composed of conditions using indicators from a library like `pandas-ta` and the custom candlestick patterns above.*

1.  **MA Crossover (Golden Cross):** BUY when 50-day SMA crosses above 200-day SMA. SELL when 50-day SMA crosses below.
2.  **RSI Oversold/Overbought:** BUY when RSI(14) crosses below 30. SELL when RSI(14) crosses above 70.
3.  **RSI Divergence (Bullish):** BUY on bullish divergence between price and RSI.
4.  **MACD Crossover (Bullish):** BUY when MACD line crosses above Signal line.
5.  **Bollinger Band Mean Reversion:** BUY when price touches lower Bollinger Band. SELL when price touches upper Bollinger Band.
6.  **Volume Spike Anomaly:** BUY on price increase with >2x average volume.
7.  **Hammer Confirmation:** BUY if a Hammer pattern is confirmed by a positive close on the next day.
8.  **Bullish Engulfing Confirmation:** BUY if a Bullish Engulfing pattern appears at a support level.
9.  **MA + RSI Combo:** BUY when price is above 200-day SMA and RSI(14) crosses below 40.
10. **Ichimoku Cloud Breakout (Bullish):** BUY when price breaks above the Kumo (cloud).