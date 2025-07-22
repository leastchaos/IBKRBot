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
**6. Options Strategy Overlay:**
Based on the overarching investment thesis (Bullish, Neutral, or Bearish), propose a suitable options strategy. The analysis should consider the following options based on the market outlook:
For a "Bullish" Outlook (Extremely or Moderately Bullish):
Outright Stock Purchase: Consider this for a high-conviction "Buy" recommendation.
Long Call: If the outlook is extremely bullish and leveraged gains are desired. Provide a recommended strike and expiration with justification.
Cash-Secured Put: If the goal is to acquire the stock at a lower effective price. Provide a recommended strike and justification.
Bull Call Spread (Debit Spread): If the outlook is moderately bullish with a defined-risk profile. Provide recommended strikes and expiration.
Bull Put Spread (Credit Spread): If the outlook is moderately bullish or neutral and the goal is to generate income with a high probability. Provide recommended strikes and expiration.
Covered Call: If an investor already holds shares and the outlook is neutral to slightly bullish. Analyze if selling a covered call is appropriate. Provide a specific strike and expiration.
For a "Neutral" or "Sideways" Outlook:
Short Straddle or Short Strangle: Analyze if the stock's volatility is expected to remain low. Discuss the risk and reward profile. Provide recommended strikes and expiration.
Iron Condor: Analyze if a defined-risk, defined-reward strategy is suitable for a range-bound market. Provide recommended strikes and expiration.
For a "Bearish" Outlook:
If not holding the stock:
Long Put: Analyze buying a put option as a defined-risk way to profit from a decline. Provide a recommended strike and expiration.
Bear Call Spread (Credit Spread): Analyze selling a bear call spread as a defined-risk, high-probability strategy. Provide recommended strikes and expiration.
If holding the stock (Exit Strategies)
Outright Stock Sale: If the goal is to exit an existing position completely and immediately. Analyze whether this is the best course of action given the current price and risk/reward.
Protective Put: Analyze buying a put to protect against further downside. Recommend a specific strike that provides adequate protection.
Collar: Analyze creating a "collar" (selling a covered call to finance the purchase of a protective put) to define a clear exit range.
For all recommended strategies, provide a Timing Verdict (e.g., "Execute now," "Wait for a pullback," etc.), recommended strike(s) and expiration, and a clear justification based on the technical and fundamental analysis..
7. Risk Assessment:
Identify and explain the key risks to your investment thesis. These could include macroeconomic factors, competitive threats, regulatory changes, or company-specific execution risks.
8. Conclusion & Recommendation:
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
    * State if any news fundamentally challenges or **invalidates** the `Core Thesis Summary`. If the thesis is invalidated, the tactical recommendation should be to exit any existing position.

3.  **Short-Term Technical Assessment:**
    *   **Support/Resistance:** Identify the nearest key short-term support and resistance levels.
    *   **Momentum Indicators:** Analyze the daily Relative Strength Index (RSI) and MACD. Note any oversold/overbought conditions or crossovers.
    *   **Volume Analysis:** Is recent price movement accompanied by significant volume?

4.  **Market & Sector Context:**
    *   Briefly describe today's general market sentiment and the performance of the stock's specific sector.
**Part 3: Options Strategy Overlay**

* **If Holding and Recommendation is to "HOLD OFF":**
    * **Covered Call Analysis:** Evaluate selling a covered call for income. Provide a **Timing Verdict (Execute or Wait)** based on technicals, and if executing, recommend a specific strike and expiration.

* **If Holding and Recommendation is to "EXIT POSITION":**
    * **Protective Put Analysis:** Analyze if buying a near-term protective put is a prudent way to hedge downside risk while liquidating the position. Provide a **Timing Verdict**, and if executing, recommend a strike that offers the best protection versus cost.

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
**Options Overlay Suggestion:** (Provide the specific options recommendation from Part 3. State "N/A" if initiating a new position or if no options action is advised. Examples: "Now is an optimal time to sell the [Date] $[Strike] covered call." or "Consider buying the [Date] $[Strike] put to hedge while exiting the position.")
"""


PROMPT_BUY_RANGE_CHECK = "Based on the full report above, is the current stock price inside the 'BUY' range you identified? Please answer with only 'YES' or 'NO'."

PORTFOLIO_REVIEW_PROMPT = """You are to act as an expert financial analyst and portfolio strategist. Your analysis must be based on the latest publicly available information.

The attached file contains my current stock holdings. The file includes the ticker symbol, the number of shares I own, and my average cost basis. Please use this file only to identify the stocks I own and my position details. Disregard any other analytical data in the file, as it is likely outdated.

Your primary task is to conduct a thorough, stock-by-stock analysis of my portfolio. For each individual holding, you must evaluate the current market conditions, company fundamentals, technical indicators, and forward-looking catalysts to recommend one of the following four actions:

1. Sell (Set a Target Price):
This action is appropriate if the stock appears overvalued, has reached a significant technical resistance level, or if its fundamental outlook has weakened.

Required Output: Specify a concrete Target Sell Price. Justify this price with a rationale based on valuation metrics (e.g., P/E, P/S), technical analysis (e.g., RSI, Fibonacci levels, moving averages), and/or recent analyst price targets.

2. Sell a Covered Call:
This action is suitable for stocks you anticipate will trade sideways or experience only modest gains in the near term, allowing for income generation.

Required Output: Specify a Strike Price and an Expiration Date (typically 30-45 days from now). Justify your selection by explaining how it balances generating a reasonable premium against the risk of the shares being called away. Reference the stock's implied volatility (IV) in your reasoning.

3. Hold (Awaiting a Major Catalyst):
This action is for stocks with a significant, identifiable, near-term event that could lead to substantial price appreciation. Selling or writing a call would risk capping this potential upside.

Required Output: Clearly identify the specific upcoming Catalyst (e.g., an imminent earnings release with high expectations, a pending regulatory decision, a major product launch, or clinical trial results). Explain why this catalyst justifies avoiding any selling action at this time.

4. Hold (Neutral Stance):
This is the default action if none of the above are optimal. This could be because the stock is fairly valued and is a solid long-term holding, is currently in a consolidation phase without a clear direction, or if there is insufficient data to justify a more active strategy.

Required Output: Provide a concise rationale for why holding without a specific action is the most prudent strategy at this moment.

Output Format:
Please present your final analysis in two parts.

Part 1: Detailed Stock-by-Stock Analysis Present a structured, sequential analysis. For each stock in the portfolio, create a dedicated section. Repeat the following structure for every stock:
Ticker: [TICKER] - [Company Name]
Recommended Action: [e.g., Sell Covered Call]

Key Parameters: [e.g., Strike: $155.00, Expiration: [Date]]

Rationale & Analysis: [Provide your comprehensive summary here. This section should be detailed and explain the current financial data, market sentiment, technical levels, and any relevant news or upcoming events that support your recommendation. Since this is not in a table, feel free to be as descriptive as necessary.]

Part 2: Concluding Summary Table
After presenting the detailed analysis for all stocks, provide a final conclusion in the form of a summary table. This table should offer a quick, scannable overview of your recommendations.

Conclusion
Ticker	Recommended Action	Key Parameters	Concise Rationale
[Ticker]	[Action]	[Parameters]	[A one-sentence summary of your reasoning]
[Ticker]	[Action]	[Parameters]	[A one-sentence summary of your reasoning]
[Ticker]	[Action]	[Parameters]	[A one-sentence summary of your reasoning]"""

SHORT_DEEPDIVE_PROMPT = """You are the founder and portfolio manager of a specialist short-only fund, known for your extreme discipline and patience. Your fund's entire strategy is built on waiting for the "perfect pitch"—an opportunity where multiple, powerful bearish forces are converging simultaneously. You believe that most stocks are not shortable and that acting on marginal ideas is the quickest path to ruin. Your default answer is always "No."

Your task is to analyze the following stock through your rigorous investment framework and determine if it represents one of these rare, high-conviction opportunities.

//-- ANALYSIS PROTOCOL --//

Part 1: The Three Pillars of a High-Conviction Short

Before writing your report, you must first determine if you can build a compelling, interwoven narrative that convincingly addresses all three of the following pillars.

A Fundamentally Deteriorating Business: Is the company's core business model, competitive position, or financial health in a state of clear and likely irreversible decline? Go beyond slowing growth; look for evidence of structural decay.

An Untenable Valuation: Is the stock priced for a level of success, growth, or stability that is completely detached from the reality of its deteriorating business? The disconnect must be stark and obvious.

A Clear Catalyst for Re-pricing: Why will the market realize its mistake and re-price the stock lower in the foreseeable future (e.g., 6-18 months)? A catalyst is essential; without one, a cheap stock can get cheaper and an expensive stock can get more expensive. This could be an event (debt maturity, earnings miss) or a technical breakdown.

Part 2: Thesis Formulation & Recommendation

The Rule: You may only issue an "Initiate Short" recommendation if you can construct a powerful thesis that integrates all three pillars into a single, cohesive argument. The narrative must be compelling.

If the criteria are met: Proceed to build the full thesis below. Your thesis must be structured around the three pillars.

If any pillar is weak or absent: Your recommendation must be "Avoid." Write a brief memo explaining which pillar(s) are missing and why the stock, therefore, does not meet your high standards for a short position. Then, conclude the analysis.

//-- REQUIRED REPORT STRUCTURE (Only if an "Initiate Short" is recommended) --//

1. Executive Summary:

State the "Initiate Short" recommendation.

Concisely state that the thesis rests on the rare convergence of a deteriorating business, an untenable valuation, and a clear catalyst for re-pricing.

Summarize your price target.

2. The Short Thesis: A Convergence of Factors

Pillar 1: The Business is in Decline: Detail the evidence of fundamental decay.

Pillar 2: The Valuation is Untenable: Detail the valuation disconnect with specific multiples and comparisons.

Pillar 3: The Catalyst for Re-pricing: Clearly explain why the market's perception is likely to change.

3. Supporting Technical Analysis:

Analyze how the price chart confirms or supports the bearish narrative. Focus on key trends, levels, and momentum.

4. Options Strategy for a High-Conviction Short

Analyze potential options strategies to express this bearish view.

Primary Bearish Strategies (To enter a new position):

Buying Puts: Analyze buying put options as a defined-risk way to profit from a decline.

Bear Call Spread: Analyze selling a bear call spread as a high-probability, defined-risk strategy to profit if the stock stays below a certain price.

For each suggested strategy, you must provide:

Timing Verdict (Execute or Wait): Based on the technicals, is now an optimal time to enter the options trade?

Strike(s) and Expiration Selection: Provide specific recommendations.

Justification: Explain why the chosen strategy aligns with the thesis and catalyst timeline.

5. Risk Assessment (What Could Kill This Trade?):

Despite your conviction, identify the primary risks that could prove the thesis wrong (e.g., short squeeze, buyout offer, unexpected positive catalyst).

6. Conclusion & Recommendation:

Reiterate the "Initiate Short" call, the price target, and the price range for entry.

Your analysis should be based solely on publicly available information up to the present date.

The stock ticker to be analyzed is:"""

BUY_THE_DIP_DEEPDIVE_PROMPT = """I am an investor considering a contrarian position in a stock that has experienced a significant recent price drop. My goal is to determine if the drop is an overreaction to temporary news or a signal of a long-term, fundamental decline. Please conduct a multi-faceted deep research analysis on the company and provide a structured, objective report based on the following framework."

Phase 1: Fundamental Analysis (Quantitative & Qualitative)



Quantitative Analysis:

Financial Health: Analyze the most recent quarterly and annual reports (10-K and 10-Q). Report on the company's revenue and earnings growth trends over the last three to five years.

Balance Sheet: Scrutinize the balance sheet. Is the company's debt-to-equity ratio healthy compared to industry peers? Does it have sufficient cash on hand?

Profitability & Efficiency: Calculate and report on key ratios such as Return on Equity (ROE), Return on Assets (ROA), and Free Cash Flow (FCF). Are these metrics trending up or down?

Valuation: Compare the company's current valuation (e.g., P/E ratio, P/S ratio, EV/EBITDA) to its historical averages and the industry average.

Qualitative Analysis:

Business Model & Competitive Advantage ("Moat"): Describe the company's core business model. What is its competitive advantage? Is this "moat" (e.g., brand strength, network effects, patents, economies of scale) still intact, or is it eroding?

Management & Corporate Governance: Research the management team. What is their track record? Have there been any recent changes in leadership? Are there any reports of poor capital allocation (e.g., bad acquisitions, excessive executive compensation, poor-timed share buybacks)? Is insider buying or selling activity notable?

Phase 2: Event-Specific Analysis (The "Why")



Identify the Catalyst: Identify the specific event(s) that caused the recent price drop. Summarize the key news, an earnings miss, an analyst downgrade, or a legal issue.

Assess the Severity: Provide an objective evaluation of the severity of the news. Is it a one-time, temporary issue (e.g., supply chain disruption, a minor legal settlement) or a long-term, structural problem (e.g., a major competitor entering the market, a permanent decline in demand for their products)?

Market Reaction: Evaluate if the market's reaction seems rational or emotional. Compare the magnitude of the price drop to the actual financial impact of the news. For example, did the stock lose billions in market cap for a one-time charge of a few million?

Phase 3: Technical Analysis



Trend & Momentum Indicators: Analyze the stock's recent price action. Is it in a clear short-term or medium-term downtrend? Are key momentum indicators (e.g., RSI, MACD) showing oversold conditions or negative divergence?

Support & Resistance Levels: Identify key support and resistance levels on the chart. Where are the potential price floors and ceilings?

Moving Averages: Analyze the stock's position relative to key moving averages (e.g., 50-day, 200-day). Are they acting as support or resistance? Has the stock recently crossed a significant moving average?

Chart Patterns: Look for any relevant chart patterns (e.g., double bottom, rising wedge, head and shoulders) that might signal a potential reversal or continuation of the trend.

Phase 4: Red Flag Analysis (The "Value Trap" Test)



Revenue & Earnings Decline: Has the company been experiencing a sustained decline in revenue or earnings, even before the recent news?

High Debt & Unsustainable Dividends: Is the company carrying an excessive amount of debt, or is it paying a dividend that seems unsustainable given its cash flow?

Eroding Competitive Advantage: Are there clear signs that the company is losing market share to competitors or failing to innovate?

Management Issues: Are there any signs of aggressive accounting practices, poor capital allocation, or a management team that is "over-promising and under-delivering"?

Phase 5: Synthesis and Conclusion



Summary of Findings: Based on the above analysis, provide a clear, concise summary of the key arguments for and against investing in the company at its current price.

Final Recommendation & Strategy:

Categorize the company as:

A true value opportunity: The drop is an overreaction, and the fundamentals are sound.

A "falling knife" (too risky): The drop is a result of legitimate, ongoing issues.

A "value trap": The company is cheap for a reason, and there is no clear catalyst for a rebound.

Based on the preceding fundamental and technical analysis, propose and justify specific investment strategies for different risk appetites. For each strategy, recommend a specific entry point (e.g., current price, a specific support level) and provide explicit details for each leg (e.g., strike prices, expiration dates).

Use the following layout for the recommendations:

[Risk Profile]: [Title of Strategy]

Rationale: [Brief explanation of why this strategy is suitable for this risk profile and market condition.]

Recommended Action: [Clear, concise instructions on how to execute the strategy. Use bullet points for different options if applicable.]

Justification: [Connect the recommendation back to findings from the fundamental and technical analysis.]

Risk/Reward: [A brief summary of the potential outcomes.]

Justify the choice of each recommended strategy, explaining its risk/reward profile and why it fits the analysis's conclusion.

Justify the Conclusion: Explain the reasoning behind the final recommendation, citing specific data and insights from the previous phases.

Final Instructions:



Ensure the analysis is objective and data-driven.

Cite all sources used (e.g., company reports, reputable financial news outlets, analyst reports).

Avoid making emotional or subjective judgments.

Structure the final response using clear headings and bullet points for readability.

Ticker to be researched:
"""

BUY_THE_DIP_SCREENER_PROMPT = """Objective: "I need to generate a list of publicly traded companies that are potential candidates for a contrarian investment strategy. The goal is to identify stocks that have recently experienced a significant price drop but may be fundamentally sound and oversold."

Screening Criteria:

Financial Health:

Find companies with a positive Free Cash Flow (FCF) for the last four consecutive quarters.

Ensure the company has a current ratio (Current Assets / Current Liabilities) greater than 1.5.

The company's Debt-to-Equity (D/E) ratio should be below the industry average.

Recent Price Action (The "Drop"):

The stock price has dropped by at least 15% in the last 30 days.

The stock is currently trading at least 20% below its 52-week high.

Valuation & Growth:

The Forward P/E Ratio should be below its 5-year historical average.

Revenue growth (year-over-year) for the last reported quarter should be positive.

The stock's Price-to-Book (P/B) ratio should be below 3.

Technical Indicators (The "Oversold" Signal):

The Relative Strength Index (RSI) should be below 35.

The stock's price is currently below its 50-day and 200-day moving averages.

Market & Exclusions:

Exclude companies with a market capitalization below $2 billion (to focus on more established companies).

Exclude companies that have reported a significant and persistent decline in revenue or have recently been embroiled in a major corporate scandal.

Output Requirements:

Provide the results in a clear, formatted table.

For each company that meets the criteria, include the following data points in the table:

Ticker Symbol

Company Name

Industry

Recent Price Drop Percentage (30-day)

Current RSI

Forward P/E Ratio

Revenue Growth (YoY)

Do not provide any analysis or opinions on the companies. The purpose of this output is to generate a raw list of candidates for further deep-dive research.

Final Instruction: "Please run the screener based on the above criteria and provide the results."
"""
