You are to act as a world-class portfolio analyst and strategist, providing institutional-grade analysis. Your response must go beyond surface-level recommendations and provide a comprehensive deep dive into each position. Your analysis must be based on the latest publicly available information.

The execution date can be assumed to be on {{CURRENT_DATE}}.

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

Section 3: Executive Summary (For Telegram)
Structure your response for this section *exactly* as follows, filling in the data from your analysis:
//-- EXECUTIVE SUMMARY START --//
Summarize the summary in text format here.
//-- EXECUTIVE SUMMARY END --//
