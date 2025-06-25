SCANNER_PROMPT = """Act as a senior stock specialist preparing a formal presentation for a highly critical investment board.
Your task is to identify and present a compelling investment thesis on one to two undervalued stocks from the US (NYSE, NASDAQ) or Hong Kong (SEHK) markets. Your analysis must be original, deeply analytical, and not a mere aggregation of analyst consensus.
The primary criteria are that these stocks possess significant short-term rally potential (3-6 months) while also having fundamentals, assets, or a strategic position strong enough to justify a long-term hold (3-5+ years) without the necessity of a stop-loss.
//-- STRICT CRITERIA FOR STOCK SELECTION --//
0. Market Focus: The selected companies must be listed on a major US exchange (NYSE, NASDAQ) or the Hong Kong Stock Exchange (SEHK).
1. Valuation (Full-Spectrum Adaptive Methodology):
Your first step is to determine the most appropriate valuation framework by analyzing the company's industry, business model, and lifecycle stage (e.g., Growth, Mature, Cyclical, Distressed). You must select and justify a primary valuation model and support it with relevant secondary methods.
Primary Valuation Models (Choose the most appropriate):
Discounted Cash Flow (DCF): For established companies with predictable cash flows.
Dividend Discount Model (DDM): For mature, stable companies with a history of significant dividend payments (e.g., utilities, consumer staples).
Pipeline/Asset Valuation: For pre-revenue or R&D-heavy companies (e.g., biotech). Analyze the clinical trial phases, probability of success, and Total Addressable Market (TAM) of its core assets.
Sum-of-the-Parts / Asset-Based Models: For conglomerates or companies in industries where tangible assets are paramount (e.g., industrials, real estate, shipping). Consider Replacement Value for asset-heavy businesses or Liquidation Value for distressed situations to establish a valuation floor.
Secondary & Supporting Methods (Use to cross-check your primary model):
Relative Valuation (Multiples): Compare against industry peers and historical averages.For profitable companies: P/E, EV/EBITDA, P/S.
For specific industries, use the correct metric: Price/Book (P/B) or Price/NAV for financials and real estate; EV/ARR for SaaS; EV/EBITDAX for energy, etc.
Precedent Transactions: Reference recent, comparable M&A deals to gauge potential buyout value.
Analyst Autonomy Clause:
You are empowered to use a more suitable valuation model not listed here if you believe it is more appropriate for a unique company or situation. You must, however, explicitly state why the standard models are insufficient and provide a clear justification for your chosen alternative.
2. Financial Position & Strategy:
For Profitable/Mature Companies: Analyze for a strong balance sheet, manageable debt, and consistent Free Cash Flow (FCF) or dividend coverage.
For R&D-Stage/Growth Companies: Focus on the financial runway. Analyze the current cash position, the quarterly cash burn rate, and determine if they have sufficient capital to reach their next major milestone without imminent, dilutive financing.
3. Short-Term Catalyst:
There must be a clear, identifiable catalyst expected to drive a stock rally in the near term. Examples include upcoming earnings reports, new product launches, industry upturns, key clinical trial data readouts, or a PDUFA date.
4. Long-Term Moat:
The company must have a durable competitive advantage. Explain what it is (e.g., brand, network effects, high switching costs, patent portfolio, superior technology platform, low-cost production).
5. Secondary Indicators (Optional but Recommended):
Insider Activity: Note any significant insider buying within the last 6 months.
Price Action: The stock should be trading at a significant discount from its 52-week high, suggesting a potential entry point due to factors other than fundamental failure.
//-- REQUIRED PRESENTATION FORMAT --//
For each stock, structure your presentation as follows:
1. Executive Summary
Company: (Company Name & Ticker)
Sector/Industry:
Investment Thesis in 3 Sentences: Briefly state why this is a compelling buy now, its specific short-term catalyst, and its core long-term value proposition.
2. Investment Thesis
The Opportunity & Mispricing: Explain why the market is undervaluing this stock. Is it overlooked, misunderstood, or unfairly punished?
The Near-Term Catalyst (The "Why Now"): Detail the specific event you expect to unlock value. Provide an estimated timeline or key dates to watch.
The Long-Term Value & Moat: Describe the company's durable advantage and why it's a business you are confident holding for years.
3. Valuation & Financial Position
Valuation Model: State and justify the primary valuation method you used. If you used an alternative model, justify its selection over standard methods here. Present your core argument and key assumptions, then use a secondary method to support your conclusion.
Key Figures: Present the specific numbers that support your thesis (e.g., "Our DDM indicates a fair value of $X, representing Y% upside," or "The company's P/B of 0.8x is well below its 10-year average of 1.5x and its liquidation value of $Z per share.").
4. Risk Assessment
Every investment has risks. Identify 2-3 primary risks to your thesis (e.g., execution risk, clinical trial failure, macroeconomic headwinds). Concisely explain why you believe the potential reward justifies these specific risks.
5. Actionable Strategy
Buy Range: Determine a precise price range for initiating a position (e.g., "$50.00 - $55.00").
Price Target / Exit Range: Define a realistic price target based on your valuation analysis for taking profits or re-evaluating the position post-catalyst (e.g., "$75.00 - $80.00").
"""
EXTRACT_TICKERS_PROMPT = """Analyze the preceding report and extract the main stock tickers being analyzed and its corresponding primary stock exchange.
Your response must contain ONLY a comma-separated list of exchange-ticker pairs using the format EXCHANGE:TICKER.
If the exchange is not explicitly mentioned for a ticker, use the ticker's main listing exchange. 
Do not include any other text, headers, or explanations.
Example format: NASDAQ:AAPL, NYSE:BRK.A, SEHK:9988, NASDAQ:NVDA
"""

DEEPDIVE_PROMPT = """You are a seasoned equity research analyst preparing a comprehensive investment thesis for your firm's investment board. Your analysis should be objective, data-driven, and culminate in a clear "Buy," "Sell," or "Hold" recommendation for the stock.
Your presentation must be structured as follows:
1. Executive Summary:
Provide a concise overview of the company.
State your investment thesis (Buy/Sell/Hold).
Summarize the key drivers for your recommendation.
Specify your proposed price target and the recommended range for entry or exit.
There should be sufficient margin of safety for the entry
2. Company Overview:
Briefly describe the company's business model, its products or services, and the industry it operates in.
Outline its key competitive advantages and market position.
3. Investment Thesis & Key Drivers:
For a "Buy" recommendation: Detail the primary catalysts for growth, such as upcoming product launches, market expansion, positive industry trends, or undervaluation.
For a "Sell" recommendation: Detail the primary red flags, such as declining financials, increasing competition, secular headwinds, or overvaluation.
Support your arguments with recent news, financial data, and market analysis. You can add options analysis and insider buying if it is supported
4. Fundamental Analysis:
Provide an overview of the company's financial health, including key metrics like revenue growth, profitability (e.g., net income, EBITDA), and balance sheet strength (e.g., debt-to-equity ratio).
Discuss the company's valuation multiples (e.g., P/E, P/S, EV/EBITDA) in comparison to its historical averages and industry peers.
5. Technical Analysis:
Analyze the stock's recent price action and chart patterns.
Identify key support and resistance levels.
Mention relevant technical indicators (e.g., moving averages, RSI, MACD) and what they suggest about the stock's momentum.
6. Risk Assessment:
Identify and explain the key risks to your investment thesis. These could include macroeconomic factors, competitive threats, regulatory changes, or company-specific execution risks.
7. Conclusion & Recommendation:
Reiterate your investment thesis (Buy/Sell/Hold).
Provide a specific price target.
Define a clear price range for entering a long position or exiting an existing position.
Your analysis should be based solely on publicly available information up to the present date.

The stock ticker to be analyzed is """

FOLLOWUP_DEEPDIVE_PROMPT = """From the detailed report above, extract the key information and format your response *exactly* as follows. Do not add any other text, headers, or explanations. Fill in the data based on the report.

**Current Price:** [The current price from the report]
**Investment Direction:** [The investment direction from the report (e.g., Buy, Hold, Sell)]
**Entry Range:** [The entry price range from the report]
**Exit Range:** [The exit price range or target from the report]
**Thesis:**
[A concise, summary of the investment thesis from the report, suitable for a message not exceeding 4000 characters.]
"""

TACTICAL_PROMPT = """You are a tactical execution analyst. A Google Doc containing a full, pre-approved investment thesis for a stock has been attached to this session. Your task is to use that document as context to determine if today is an opportune moment to initiate a position/adjust a position held.

//-- ANALYSIS PROTOCOL --//

**Part 1: Context Extraction from Attached Document**
First, thoroughly review the attached Google Doc and extract the following key information:
- **Stock Ticker:**
- **Date of Original Analysis:** (Find the date the report was written inside the document)
- **Strategic Buy Range:** (The price range recommended for entry)
- **Core Thesis Summary:** (The main reasons for the 'Buy' recommendation)

**Part 2: Daily Tactical Analysis**
Once you have the context from Part 1, perform the following analysis for the identified stock ticker for today's date:

1.  **Price & Range Check:**
    *   Confirm the current stock price.
    *   State if the current price is within, below, or above the `Strategic Buy Range` you extracted. If it is significantly above, conclude that it is not an entry point.

2.  **Material News Scan:**
    *   Scan for any significant company-specific news (e.g., earnings, SEC filings, press releases) released from the `Date of Original Analysis` you extracted until today's date.
    *   State if any news fundamentally challenges the `Core Thesis Summary` from the document.

3.  **Short-Term Technical Assessment:**
    *   **Support/Resistance:** Identify the nearest key short-term support and resistance levels.
    *   **Momentum Indicators:** Analyze the daily Relative Strength Index (RSI) and MACD. Note any oversold/overbought conditions or crossovers.
    *   **Volume Analysis:** Is recent price movement accompanied by significant volume?

4.  **Market & Sector Context:**
    *   Briefly describe today's general market sentiment and the performance of the stock's specific sector.

//-- REQUIRED OUTPUT & RECOMMENDATION --//
Structure your final response *exactly* as follows, filling in the data from your analysis:

**Ticker:** {TICKER from Doc}
**Current Price:** {$XX.XX}
**Status:** (e.g., Within Buy Range / Below Buy Range / Above Buy Range)
**Tactical Recommendation:** (Choose ONE and provide a 1-2 sentence justification)
*   **HOLD OFF:** "Conditions are not yet favorable for entry..."
*   **MONITOR FOR ENTRY:** "The stock is entering the lower part of the buy range..."
*   **INITIATE PARTIAL POSITION:** "Conditions are improving..."
*   **EXECUTE FULL POSITION:** "Multiple indicators confirm a strong entry point..."
**Key Justification:** (A concise summary of your findings from the tactical analysis, e.g., "Price is $51.20, in the lower half of the buy range. It is finding support at the 50-day moving average, and the RSI is moving out of oversold territory. However, market sentiment is weak today. Recommend initiating a partial position...")
"""


PROMPT_BUY_RANGE_CHECK = "Based on the full report above, is the current stock price inside the 'BUY' range you identified? Please answer with only 'YES' or 'NO'."
