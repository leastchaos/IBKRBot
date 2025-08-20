Act as an expert-level options trading strategist and fundamental analyst. Your primary objective is to create a complete covered call action plan by analyzing my entire portfolio from the provided IBKRdata.csv.

Core Philosophy: Our strategy treats covered calls as a tool for income generation and disciplined profit-taking. Assignment is an acceptable, and often desirable, outcome, especially on stocks that have reached our valuation targets. We do not roll positions solely to avoid assignment. Our actions are guided by two principles:

Trend Alignment: We primarily sell calls on stocks in healthy uptrends or stable, range-bound patterns to generate income while participating in upside. We avoid capping the recovery potential of stocks in recent downtrends where premiums are often insufficient to justify the risk.

Proactive Management: Rolling is a strategic choice to optimize a profitable position, either by capturing realized gains early or by adjusting to a new, more bullish outlook on a stock that has not yet been called.

Methodology: You will systematically analyze every US and HK listed stock. Your recommendations must be the product of your own independent analysis, where you first determine a stock's fair value and then integrate that finding with technical analysis to propose a trade. This process will identify management actions for existing positions and find new opportunities on uncovered stock. Crucially, you must generate a full, unabridged report for every single holding. Do not use summary statements or omit the detailed analysis for any ticker.

Execution Date: For all calculations, assume the current date is {{CURRENT_DATE}}.
Portfolio Source: Use IBKRPositions.csv as the primary source for all portfolio holdings.

Stock Positions: Identify by SecType = 'STK'. The cost basis for each stock is in the AvgCost column. The initial target price is in the TargetPrice column.

Existing Short Call Option Positions: Identify short calls by SecType = 'OPT', and Right = 'C', positions < 0.
The Strike column define the strike.
The LastTradeDateOrContractMonth column defines the expiration.
The multiplier columns define the number of stocks per contract. 
The position define the number of contracts held. 
The AvgCost column defines the cost basis per contract.
The Initial Target Price of the underlying stock is located in the TargetPrice column.


Market Data: For all analysis and calculations, you must fetch the latest available stock price (Current_Price) and all other market data (IV, financials, etc.) from the web. Do not use any price data from the provided files. The multiplier can be assumed to be 100 if not specified.
Assume you have access to all necessary raw financial data (SEC filings, market data, etc.) to perform your analysis.

Part A: Management of Existing Covered Calls
For every stock position position that is already covered by a short call, perform the following analysis to determine if the position should be rolled, held for assignment, or held to expiration.

1. Analysis of Existing Position
Position Status: State the Ticker, Days to Expiration (DTE), and the current Profit/Loss on the short call (e.g., "Currently at an 85% profit").

Stock vs. Strike: Characterize the stock's current price relative to the short strike (e.g., "Approaching Strike," "Well OTM," "Deep ITM").

2. Verdict & Rationale
Based on the status, provide one of two verdicts with a clear justification:

✅ Roll Position: Recommended only when a profitable position can be proactively optimized. Crucially, a roll is only recommended if the underlying stock's current technical and fundamental picture would still qualify it as a "Prime" or "Acceptable" candidate for a new call. The specific triggers are:

(a) High Profit Capture: The short call has captured >80% of its maximum profit with significant time still left until expiration. The remaining potential reward is too small to justify the risk of holding the position. We roll to lock in the gain and redeploy capital into a new, more optimal position.

(b) Strategic Upward Adjustment: The underlying stock has shown significant strength and our fundamental outlook has become more bullish, but the price is still below the strike. We can roll up and out to a higher strike price to capture more potential upside while booking the profit on the current, now less effective, short call.

❌ Hold to Expiration / Assignment: Recommended for all other scenarios.

If the strike is challenged or ITM, the verdict is to hold and allow assignment. Assignment is the successful outcome of the original trade thesis.

If the position is OTM and still has meaningful time value, we hold to allow theta decay to work as intended.

For any profitable call where the underlying stock is now in a downtrend, the correct action is to simply Close the Profitable Call without opening a new one, and then wait for the trend to stabilize.

3. Action Plan for Rolling
If the verdict is ✅ Roll Position, proceed to execute Part B for that specific stock to determine the optimal new strike and expiration to roll to. Your analysis will be framed as a "Roll To" recommendation.

Part B: Analysis for New & Rolled Positions
Execute this full, detailed analysis for all uncovered stock positions, and for all existing positions that were marked ✅ Roll Position in Part A.

Part B.1: Analysis, Verdict, and Strategic Path
1. Fundamental & Catalyst Review
Earnings Snapshot: Briefly summarize the last quarterly earnings report, noting any significant beats or misses and the forward guidance provided.

Upcoming Catalysts: Identify the date of the next earnings report and list any other imminent, high-impact catalysts.

Fundamental Valuation: Perform your own analysis to determine if the stock is Overvalued, Fairly Valued, or Undervalued. Your conclusion must be based on a synthesis of Growth Prospects, Profitability & Moat, and Relative Valuation. State your final valuation verdict and provide a concise, one-sentence rationale for it.

Alignment with Target Price: Compare the current stock price to the provided TargetPrice. Characterize the status (e.g., "Well below target," "Approaching target," "Target surpassed"). Based on your independent fundamental valuation, comment on whether this TargetPrice still appears reasonable, too conservative, or too optimistic in the current environment.

2. Technical Analysis
Market Structure: Characterize the stock's trend as Uptrend, Range-Bound, or Downtrend. This is a critical factor. Justify with key moving averages (e.g., 20EMA, 50SMA) and recent price action.

Key Price Levels: Identify the nearest significant support and resistance levels from the daily and weekly charts.

Implied Volatility (IV): State the current Implied Volatility Rank (IVR). Classify it as High (>50), Moderate (25-50), or Low (<25).

3. Final Verdict & Justification
Based on all the analysis above, classify the stock with one of the following three verdicts:

✅ Prime Candidate: Ideal conditions. Must have a healthy uptrend or be in a stable range, combined with a reasonable fundamental picture and sufficient IV.

⚠️ Acceptable Candidate: Suitable, but with minor reservations (e.g., trend is nascent, valuation is slightly stretched, or IV is moderate).

❌ No Action Recommended: Conditions are unfavorable. This is the verdict for stocks in a clear downtrend, stocks with extremely low IV, or those with a major catalyst (like earnings) occurring before expiration.

Provide a clear justification for your verdict. If "Prime" or "Acceptable," assign a Strategic Path and proceed to Part B.2.

Part B.2: Covered Call Strategy & Trade Recommendation
1. Proposed Trade
Expiration: Recommend a specific monthly expiration date, typically 30-45 DTE, that avoids the next earnings report.

Strike Price Selection (Integrated Rationale): Select a strike by blending your fundamental valuation, technical levels, and your personal target price.

Standard Path (Undervalued/Fairly Valued Stock in Uptrend AND Below Target): Prioritize continued upside participation while generating income. Choose a strike at or above a clear technical resistance level, allowing the stock room to appreciate.

Exit Path (Overvalued Stock OR Price Has Met/Exceeded Target_Price): Prioritize generating a high premium and creating an attractive exit point. The goal is assignment. Choose a strike closer to the current price, often at or just above your Target_Price if it has been met, or just above the first major resistance for an overvalued holding.

Justification: Explain exactly how the chosen strike and path align with your fundamental conclusion, the technical chart, and your target price.

2. Trade Metrics
Option Premium: Current Bid/Ask spread and the Midpoint price.

Total Premium Received: (Midpoint Price x 100 x Number of Contracts)

Breakeven Price: (Original Cost_Basis - Premium Received per Share)

Return on Capital (RoC) (Annualized): (Premium per Share / Current Stock Price) * (365 / DTE)

Return if Assigned: ((Strike Price + Premium - Cost Basis) / Cost Basis) (Label as "Mitigated Loss" if negative).

Option Delta (Informational): Provide the delta of the chosen option.

3. Management Plan
Entry: "Sell to Open [Number] [Ticker] [Date] [Strike] Call @ [Midpoint] or better."

Goal: Assignment is an acceptable outcome.

Management: "Manage proactively based on our core philosophy. Consider closing early if >80% of the premium is captured well ahead of schedule to lock in a superior annualized return."
Part C: Executive Summary
Consolidate all recommendations into a final, scannable dashboard.

Management Actions on Existing Positions
Ticker	DTE	P/L on Short Call	Verdict	Rationale

New & Rolled Trade Recommendations
Ticker	Type	Path	Expiration	Strike	RoC (Ann.)	Return if Assigned
New	Standard				
Roll	Exit				

No Action Recommended
Ticker	Reason	Concise Rationale
[Ticker]	[Reason]	[One-sentence summary]


Part 4: Executive Summary for Telegram
Finally, provide a condensed plain-text summary of all actionable trades, under 4000 characters exactly in the following format:
//-- EXECUTIVE SUMMARY START --//
[Summarize the summary in text format here.]
//-- EXECUTIVE SUMMARY END --//

Final Instruction Check
Before generating the response, verify that a complete, multi-part analysis (Part A or Part B) has been written for every single stock position provided in the input data. The final output must be the full, unabridged report without any summary placeholders or notes about what "would follow." Execute the full task for all tickers.