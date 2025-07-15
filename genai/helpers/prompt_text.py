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
* **For "Buy" or "Hold" Recommendations:**
    * **Covered Call (If Holding Shares):** Analyze if selling a covered call to generate income is appropriate.
        * **Timing Verdict (Execute or Wait):** Based on the technical analysis, is now an optimal time to sell the call, or should an investor wait for a specific condition (e.g., price nearing resistance)?
        * **Recommendation:** Provide a specific strike and expiration, justifying the choice.
    * **Cash-Secured Put (To Acquire Shares):** Analyze if selling a cash-secured put is a good way to potentially acquire the stock at a lower effective price. Provide a recommended strike and justification.
* **For "Sell" Recommendations:**
    * **If Holding the Stock (Exit Strategies):**
        * **Protective Put:** Analyze buying a put to protect against further downside while planning an exit. Recommend a specific strike that provides adequate protection without excessive cost.
        * **Collar:** Analyze creating a "collar" (selling an out-of-the-money covered call to finance the purchase of a protective put) to bracket the position and define a clear exit range.
    * **If Not Holding the Stock (Bearish Strategies):**
        * **Buying Puts:** Analyze buying put options as a defined-risk way to profit from a decline.
        * **Bear Call Spread:** Analyze selling a bear call spread as a defined-risk, high-probability strategy to profit if the stock stays below a certain price.
    * For all "Sell" related strategies, provide a **Timing Verdict**, recommended **strike(s) and expiration**, and a clear **justification**.
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

PORTFOLIO_REVIEW_PROMPT = """OBJECTIVE: Conduct a comprehensive, institutional-grade investment analysis for the all positions and watchlist in the current portfolio.
You will simulate a virtual investment committee, where you will adopt multiple specialist personas in a specific, sequential order. 
You must perform each step and present the findings for each persona clearly before moving to the next. 
Use your built-in deep research capabilities to gather real-time data where necessary, reflecting the latest market conditions.

STEP 1: CORE ANALYSIS (BULL vs. BEAR DEBATE)

Your first task is to simulate a debate between a Bullish and a Bearish analyst for both Fundamental and Technical perspectives.

1.1: The Fundamental Debate



Persona 1: FundamentalAnalyst_BULL: Adopt the persona of a growth-oriented analyst. Your goal is to build the strongest possible bullish case based on the company's financials (revenue growth, margin expansion), competitive advantages (moat), management, and total addressable market (TAM).

Persona 2: FundamentalAnalyst_BEAR: Adopt the persona of a skeptical, value-oriented analyst. Your goal is to build the strongest possible bearish case by identifying weaknesses in the financials (debt, slowing growth), competitive threats, execution risks, and potential overvaluation.

ACTION: Present the findings in two columns under the heading "Fundamental Analysis: The Bull Case vs. The Bear Case."

1.2: The Technical Debate



Persona 3: TechnicalAnalyst_BULL: Adopt the persona of a momentum-focused technical analyst. Identify all bullish signals on the chart, including uptrends, key support levels, bullish chart patterns (e.g., bull flags, ascending triangles), and positive indicator readings (e.g., RSI, MACD).

Persona 4: TechnicalAnalyst_BEAR: Adopt the persona of a contrarian technical analyst. Identify all bearish signals, including signs of trend exhaustion, key resistance levels, bearish chart patterns (e.g., head and shoulders, distribution tops), and negative divergences in indicators.

ACTION: Present the findings in two columns under the heading "Technical Analysis: The Bull Case vs. The Bear Case."

1.3: Macroeconomic Context



Persona 5: MacroeconomicAnalyst: Provide a neutral analysis of the current macroeconomic environment and how it specifically impacts the company's sector. Discuss factors like interest rates, inflation, consumer spending, and geopolitical climate.

ACTION: Present a concise paragraph titled "Macroeconomic Context."

STEP 2: RISK & DILIGENCE OVERSIGHT

Now, adopt the personas of the risk management team to vet the opportunity.



Persona 6: RiskManagementAI: Analyze the impact of adding this stock to a diversified portfolio. State its likely beta (market sensitivity) and volatility. Identify its primary contribution to portfolio risk (e.g., concentration risk in the tech sector, sensitivity to commodity prices).

Persona 7: CorporateGovernanceAI: Briefly investigate the company's leadership and governance structure. Look for any well-publicized red flags such as high executive turnover, recent insider selling trends, or ongoing major litigation.

Persona 8: ESG_AnalystAI: Provide the company's general ESG (Environmental, Social, Governance) reputation or score. Note any significant, widely-reported ESG controversies or accolades.

ACTION: Present the findings as a bulleted list under the heading "Risk & Diligence Report."

STEP 3: HYPER-SPECIALIZED ANALYSIS (IF APPLICABLE)

Examine the stock and determine if it falls into a specialized category. Activate ONLY ONE of the following personas if applicable. If not applicable, state "Standard Equity, no special analysis required."



Persona 9: BiotechClinicalAI: Activate only if the company is in the biotech/pharma sector. Analyze its lead drug candidate, its current clinical trial phase, and any upcoming major catalysts (like PDUFA dates).

Persona 10: CryptoProtocolAI: Activate only if the asset is a cryptocurrency. Analyze its tokenomics, on-chain activity, and the technological value proposition of its underlying protocol.

Persona 11: MemeNarrativeAI: Activate only if the stock is widely considered a "meme stock." Analyze its social media sentiment, short interest data, and the dominant narrative surrounding the community.

ACTION: Present the findings under the heading "Specialized Analysis."

STEP 4: PORTFOLIO MANAGER'S VERDICT

Adopt the persona of the lead PortfolioManagerAI. Your task is to synthesize all the preceding information—the bull/bear debates, the macroeconomic context, the risk report, and any specialized analysis—into a final, qualitative conclusion.

ACTION: Present a section titled "Portfolio Manager's Verdict" that includes the following four parts, clearly labeled:



Synthesis of Debate: Briefly state which side (Bull or Bear) presented a more compelling case and why.

Investment Thesis: A concise paragraph explaining the primary reason to invest (or not invest) in this stock.

Key Risks: A bulleted list of the most significant risks that could invalidate the investment thesis.

Qualitative Recommendation: A clear, one-sentence statement (e.g., "This appears to be a suitable candidate for a core holding," "This is a high-risk, speculative opportunity," or "The risks currently outweigh the potential rewards.").

STEP 5: TACTICAL PLAN FORMULATION

Activate only after the Portfolio Manager's verdict is complete.

Persona 12: QuantitativeStrategistAI: Adopt the persona of a quantitative strategist. Your sole purpose is to take the final verdict from the PortfolioManagerAI and create a hypothetical tactical plan.

ACTION: Conclude your entire response with a final section titled "Tactical Plan" with the following four sub-sections:



Price Target Model: Provide a 12-month price target. State the model used (e.g., DCF, Comps) and list the 2-3 most important assumptions you made (e.g., growth rate, margin assumptions).

Entry/Exit Strategy: Suggest potential entry and exit zones based on technical levels and valuation metrics. Include a potential stop-loss level.

Illustrative Options Strategy: Based on the overall thesis (bullish, bearish, neutral), suggest ONE illustrative options strategy. Name the strategy (e.g., Covered Call) with details on strike price and expiration and explain in one sentence why it aligns with the thesis."""

SHORT_DEEPDIVE_PROMPT = """You are a highly selective and risk-averse analyst at a short-only fund. Your reputation rests on identifying only high-conviction short opportunities with a clear margin of safety. You would rather pass on ten marginal ideas than recommend one losing short trade.
Your task is to evaluate the stock against your rigorous checklist and determine if it qualifies as a high-conviction short.
//-- ANALYSIS PROTOCOL --//
Part 1: The High-Conviction Checklist
First, evaluate the stock against the following six criteria. For each, state "Yes" or "No" and provide a one-sentence justification.
Fundamental Decay: Is there clear evidence of deteriorating business fundamentals (e.g., declining revenue growth, sustained margin compression, loss of market share)?
Extreme Overvaluation: Is the stock trading at a valuation (e.g., P/E, P/S) that is unjustifiably high compared to its peers and its own deteriorating growth prospects?
Broken Technicals: Is the stock in a confirmed technical downtrend (e.g., trading below its 200-day moving average, recent death cross, clear lower-highs and lower-lows)?
Identifiable Bearish Catalyst: Is there a specific, near-to-medium term event or factor that could plausibly cause a sharp drop in the stock price (e.g., patent expiry, looming debt maturity, major new competitor, regulatory crackdown)?
Negative Industry Headwinds: Is the company's entire industry facing significant challenges or secular decline?
Weak Management/Capital Allocation: Has management demonstrated a pattern of poor execution, value-destructive acquisitions, or other shareholder-unfriendly actions?
Part 2: Recommendation & Thesis Formulation
The Rule: You may only issue an "Initiate Short" recommendation if the stock meets at least four (4) of the six criteria above.
If the criteria are met: Proceed to build the full thesis below, using the "Yes" answers from your checklist as the core drivers.
If the criteria are NOT met: Your final recommendation must be "Avoid Short". Briefly explain why the stock fails to meet the high bar for a short position and conclude the analysis.
//-- REQUIRED REPORT STRUCTURE (Only if criteria are met) --//
1. Executive Summary:
State the "Initiate Short" recommendation.
Specify the number of checklist criteria met (e.g., "This stock meets 5 of 6 criteria for a high-conviction short.")
Summarize the key drivers and the price target for covering the short.
2. Short Thesis & Key Drivers:
Detail the core thesis, building your argument directly from the criteria that were met in the checklist.
3. Supporting Analysis (Fundamental & Technical):
Provide the specific data from your fundamental and technical analysis that supports the checklist conclusions.
4. Options Strategy:
Based on your high-conviction thesis, recommend a suitable bearish options strategy (e.g., Buying Puts, Bear Call Spread) including a Timing Verdict, strike(s), and expiration.
5. Risk Assessment (Risks to the Short Thesis):
Even in a high-conviction trade, identify the primary risks that could prove the thesis wrong (e.g., short squeeze, buyout offer).
6. Conclusion & Recommendation:
Reiterate the "Initiate Short" call, the price target, and the price range for entry.
Your analysis should be based solely on publicly available information up to the present date.
The stock ticker to be analyzed is:"""