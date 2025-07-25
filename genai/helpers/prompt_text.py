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

PORTFOLIO_REVIEW_PROMPT = """You are to act as a world-class portfolio analyst and strategist, providing institutional-grade analysis. Your response must go beyond surface-level recommendations and provide a comprehensive deep dive into each position. Your analysis must be based on the latest publicly available information.

The attached file contains my current stock and options positions.

Your primary task is to conduct a multi-layered analysis by first parsing and grouping the entire portfolio into four distinct categories in the following order of precedence:

Covered Call Positions

Option Spread Positions

Stock-Only Holdings

Single-Leg Options Positions

You will provide a detailed analysis for each position, followed by a consolidated executive summary containing all summary tables at the end of your response.

Analysis Frameworks by Category
Framework for Stocks (Used in Part 1 & 3)
For each stock (whether standalone or part of a covered call), your detailed analysis must follow this structure:

Recommendation & Key Parameters: State the recommended action and the specific parameters (e.g., Target Price, New Strike/Exp).

Rationale & Analysis (Deep Dive Structure):

Fundamental Deep Dive:

Valuation: What is its current P/E, P/S, or EV/EBITDA? How does this compare to its direct industry peers and its own 5-year historical average? Is it currently looking cheap, fair, or expensive?

Financial Health: Briefly assess its balance sheet. Mention Debt-to-Equity ratio, current cash position, and recent Free Cash Flow (FCF) trends. Is the company financially sound?

Growth & Profitability: What are the recent trends in Revenue and EPS growth (YoY/QoQ)? Are profit margins (Gross, Operating) expanding or contracting?

Technical Picture:

Trend & Key Levels: Is the stock in a clear uptrend, downtrend, or consolidation? Where are the critical short-term support and resistance levels (provide specific prices)? Is it trading above or below its key 50-day and 200-day moving averages?

Momentum & Volume: What is the current RSI reading and what does it suggest (e.g., overbought, oversold, neutral, divergence)? Is there any notable recent trading volume activity?

Forward Outlook & Strategic Narrative:

Bull Case: What are the 2-3 primary catalysts or long-term drivers that would push the stock higher? (e.g., new product cycle, market share gains, margin expansion).

Bear Case: What are the 2-3 primary risks or headwinds facing the company? (e.g., intense competition, macroeconomic sensitivity, regulatory threats).

Upcoming Catalysts: Note the next scheduled earnings report date or any other significant corporate events.

Framework for Options (Used in Part 1, 2 & 4)
For each option strategy (covered calls, spreads, or single legs), your detailed analysis must follow this structure:

Recommendation & Key Parameters: State the recommended action and the specific parameters (e.g., New Strike/Exp).

Rationale & Analysis (Deep Dive Structure):

The Greeks (Position DNA) & Interpretation:

Delta: What is the position's net delta? What is its current share-equivalent exposure?

Theta: What is the daily time decay? Is this decay helping (short premium) or hurting (long premium) the position?

Vega: How sensitive is the position to changes in volatility? Is a spike or crush in IV a major risk or benefit?

Gamma: Is there significant gamma risk (i.e., will delta change rapidly if the stock moves toward a short strike)?

Volatility Analysis:

Implied Volatility (IV): What is the current IV of the options?

IV Rank/Percentile: What is the IV Rank or Percentile? (e.g., "IV Rank is 75," meaning current IV is in the top 25% of its 1-year range). What does this imply for the strategy (i.e., is premium rich or cheap)?

Scenario & Risk Analysis:

Profit/Loss Profile: What are the breakeven price(s), maximum profit potential, and maximum risk for this position?

Probabilistic Outlook: What is the approximate Probability of Profit (PoP)? Is the trade positioned for a high-probability outcome or a low-probability, high-reward event?

Primary Risk: What is the single biggest threat to this position right now? (e.g., "A sharp move beyond the short strike," "An imminent IV crush after the upcoming earnings report," or "Accelerating time decay.")

Output Format
Please present your response in two main sections:

Section 1: Detailed Deep-Dive Analysis
Present the full, detailed analysis for each position, broken down into the four categories below.

Part 1: Covered Call Positions
(For each, recommend: Roll the Call, Hold, Allow Assignment, or Close Entire Position. Apply the relevant Stock and Option analysis frameworks.)

Part 2: Option Spread Positions
(For each, recommend: Hold, Close, Roll, or Let Expire. Apply the Option analysis framework.)

Part 3: Stock-Only Holdings
(For each, recommend from the full range of actions: Sell, Sell a Covered Call, Hold (Catalyst), Add to Position, or Hold (Neutral). Apply the Stock analysis framework.)

Part 4: Single-Leg Options Positions
(For each, recommend: Close, Roll, Hold, or Let Expire. Apply the Option analysis framework.)

Section 2: Executive Summary
After presenting all the detailed analyses, provide this concluding section that consolidates all summary tables for a quick overview.

Covered Call Summary
| Strategy | Recommended Action | New Parameters | Concise Rationale |
| :--- | :--- | :--- | :--- |
| Covered Call on Ticker | [Action] | [New Strike/Exp] | [One-sentence summary] |

Option Spread Summary
| Strategy | Recommended Action | Key Parameters | Concise Rationale |
| :--- | :--- | :--- | :--- |
| [Full Spread Desc.] | [Action] | [Parameters] | [One-sentence summary] |

Stock-Only Summary
| Ticker | Recommended Action | Key Parameters | Concise Rationale |
| :--- | :--- | :--- | :--- |
| [Ticker] | [Action] | [Parameters] | [One-sentence summary] |

Single-Leg Options Summary
| Position | Recommended Action | New Parameters | Concise Rationale |
| :--- | :--- | :--- | :--- |
| [Full Position Desc.] | [Action] | [New Strike/Exp] | [One-sentence summary] |
"""

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

BUY_THE_DIP_DEEPDIVE_PROMPT = """Objective: To analyze a stock after a significant price drop, differentiating between a temporary overreaction (a bounce opportunity) and a fundamental decline (a value trap), with a heightened sensitivity to short-term market dynamics.

Phase 1: Situational Triage & Sentiment Analysis (The "Why" and "Who Thinks What")
This phase is prioritized to quickly assess if the sell-off is likely emotional and exhausted.

Catalyst Identification:

Precisely identify the news/event(s) that triggered the drop (e.g., earnings miss, guidance cut, litigation, regulatory action, competitive threat).

Source and summarize the primary documents (press releases, SEC filings) and reputable news coverage.

Impact Quantification (The Overreaction Test):

Attempt to quantify the direct financial impact of the negative news. For example:

Earnings Miss: How much did it miss by in EPS and revenue? What is the dollar value of the revised annual guidance?

Litigation/Fine: What is the estimated or actual financial liability?

Compare this quantifiable impact to the loss in market capitalization. Has the market wiped out billions in value for a problem that costs millions? State the ratio clearly.

Market Sentiment & Positioning Analysis:

Short Interest: What is the current short interest as a percentage of the float? Has it spiked recently? High short interest can fuel a "short squeeze" on any good news.

Options Market Activity: Analyze the put/call ratio. Is it unusually high, suggesting extreme pessimism (a contrarian indicator)? Look at the implied volatility (IV Rank/Percentile). Is it elevated, making options selling strategies more attractive?

Analyst Revisions: Track the trend of analyst ratings and price targets since the news. Are analysts universally downgrading, or are some defending the stock, creating a "battleground"? Note the range of price targets.

Phase 2: Fundamental Health Check (The "Will it Survive?" Test)
This is a streamlined analysis focused on solvency and stability, not perfection.

Liquidity & Balance Sheet Strength:

Cash Position: How much cash and short-term investments are on hand?

Burn Rate: Based on the most recent quarter's Free Cash Flow (FCF), what is the company's cash burn or generation rate? How many quarters of liquidity does it have if the crisis persists?

Debt: What is the debt-to-equity ratio and Net Debt/EBITDA? Are there any major debt covenants at risk of being breached? When are the major debt maturities?

Core Profitability & Valuation:

Profitability Check: Is the company still profitable on an operating basis (EBIT) despite the recent issues? Is it still generating positive free cash flow?

Valuation Snapshot: How do the current valuation multiples (P/E, P/S, EV/EBITDA) compare to their 5-year historical lows and the industry average? Is it cheap on a historical basis?

Qualitative Resilience:

Business Model & Moat: In one or two sentences, what is the core business? Is the competitive advantage (moat) temporarily impaired (e.g., a factory shutdown) or permanently breached (e.g., a competitor's superior product)?

Management & Insider Activity: Did management provide a clear, confident plan during their conference call? Critically, has there been any insider buying following the price drop? Insider buys are a powerful signal.

Phase 3: Technical Analysis (The "When & Where" of Entry)
This phase focuses on identifying potential entry points and reversal signals.

Price Action & Key Levels:

Identify major long-term support levels (e.g., multi-year lows, prior consolidation zones). Has the stock reached one of these levels?

Map out key resistance levels on the upside (e.g., the bottom of the gap down, key moving averages).

Momentum & Reversal Indicators:

Oversold Condition: Is the daily and weekly Relative Strength Index (RSI) in oversold territory (typically below 30)?

Divergence: Is there any bullish divergence forming (e.g., the price making a new low while the RSI makes a higher low)? This can signal weakening downward momentum.

Volume Profile: Was the sell-off on exceptionally high volume? Is volume diminishing as the price stabilizes, suggesting seller exhaustion?

Confirmation Signals to Watch For:

What specific technical event would signal a potential bottom is in? (e.g., A reclamation of the 5-day moving average, a "hammer" candlestick pattern on high volume, a break of the immediate downtrend line).

Phase 4: Synthesis & Strategic Execution
This final phase integrates all findings into actionable, risk-managed strategies.

Summary of Findings:

The Bull Case (Opportunity): Summarize the arguments for a rebound (e.g., "Massive market cap loss dwarfs the quantifiable financial impact, RSI is deeply oversold at a multi-year support level, and insider buying has been reported.")

The Bear Case (Risk): Summarize the arguments against investing (e.g., "The company has high debt, the guidance cut implies a structural problem, and the competitive moat appears to be eroding.")

Final Recommendation & Strategy:

Categorize the situation as:

Speculative Rebound Play: High-risk, but the overreaction appears extreme. The trade is primarily based on sentiment and technicals.

Contrarian Value Opportunity: The sell-off is significant, but the company's fundamentals and moat appear resilient enough to recover over the long term.

Falling Knife / Value Trap: The negative catalyst reveals deep, unresolved fundamental problems. Avoid.

Tiered Strategy Recommendations:

[Aggressive Risk Profile]: Tactical Rebound Trade

Rationale: To capitalize on a potential sharp, short-term bounce driven by extreme oversold conditions and high short interest. This is a high-risk, high-reward approach.

Recommended Action:

Option 1 (Stock): Buy a small, initial position at the current price, with a tight stop-loss below the recent low.

Option 2 (Options): Buy short-dated (30-60 days) at-the-money or slightly out-of-the-money call options.

Justification: This strategy is justified if Phase 1 shows a massive overreaction and Phase 3 shows extreme oversold technicals (RSI < 25) at a major support level.

Risk/Reward: High potential reward if a bounce occurs quickly. High risk of total loss on options or being stopped out on the stock if the downtrend continues.

[Moderate Risk Profile]: Defined-Risk Entry

Rationale: To gain bullish exposure while defining maximum loss and potentially entering the stock at a lower price. Balances the desire to participate with prudent risk management.

Recommended Action:

Option 1 (Cash-Secured Put): Sell a short-dated (30-45 days) out-of-the-money put option at a strike price corresponding to a major support level.

Option 2 (Bull Call Spread): Buy a call option and simultaneously sell a higher-strike call option to finance the purchase and cap both risk and reward.

Justification: This strategy is ideal when the analysis suggests a likely bottom but you want confirmation or a better price. Elevated implied volatility (from Phase 1) makes selling options premium attractive.

Risk/Reward: Moderate, defined reward. The risk is either owning the stock at a lower price (for puts) or losing the net debit paid (for spreads).

[Conservative Risk Profile]: Staggered Accumulation

Rationale: For the long-term investor who believes in the fundamental recovery but acknowledges that timing the exact bottom is impossible.

Recommended Action:

Initiate a small (e.g., 1/4 of full position size) purchase at the current price.

Plan subsequent purchases at pre-defined lower support levels or after a technical confirmation signal (e.g., reclaiming the 50-day moving average).

Justification: This approach is justified if the conclusion is "Contrarian Value," where the long-term fundamentals (Phase 2) are deemed solid despite the current crisis. It prioritizes achieving a good average cost over timing the bottom.

Risk/Reward: Lower immediate risk by not deploying all capital at once. The main risk is "catching a falling knife" if the fundamental thesis is wrong, but the damage is averaged down."""


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
