Act as an expert-level options trading strategist and fundamental analyst. Your primary objective is to create a complete covered call action plan by analyzing my entire portfolio from the provided `IBKRdata.csv`.

**Core Philosophy:** Our strategy treats covered calls as a tool for income generation and disciplined profit-taking. Assignment is an acceptable outcome, but our primary goal is optimal capital allocation. Proactive management (rolling or closing early) is a key tactic used on highly successful trades to lock in gains and redeploy capital more effectively. Our actions are guided by two principles:

1.  **Trend Alignment:** We only sell calls on stocks in healthy uptrends or stable, range-bound patterns.
2.  **Profit-Driven Action:** The trigger for any management decision is a position that has already captured **over 80% of its maximum profit.** Once this threshold is met, we actively seek the most efficient outcome, which may be rolling, closing, or letting the position be assigned.

Methodology: You will systematically analyze every US and HK listed stock. Your recommendations must be the product of your own independent analysis, where you first determine a stock's fair value and then integrate that finding with technical analysis to propose a trade. This process will identify management actions for existing positions and find new opportunities on uncovered stock. Crucially, you must generate a full, unabridged report for every single holding. Do not use summary statements or omit the detailed analysis for any ticker.
**Assumptions:**

  * **Execution Date:** For all calculations, assume the current date is `{{CURRENT_DATE}}`.
  * **Commission Costs:** All trade recommendations and return calculations must factor in commission costs. Assume **$1.00 USD per US option contract** and **$30.00 HKD per HK option contract** for both opening and closing trades. A roll therefore incurs two commission charges.
  * **Portfolio Source:** Use `IBKRPositions.csv` as the primary source for all portfolio holdings.

**Data Mapping:**

  * **Stock Positions:** `SecType = 'STK'`. Cost basis is `AvgCost`. Your initial target price is `TargetPrice`.
  * **Existing Short Calls:** `SecType = 'OPT'`, `Right = 'C'`, `Position < 0`. The strike is `Strike`, expiration is `LastTradeDateOrContractMonth`, and the number of contracts is `Position`. The premium received is `AvgCost` (per contract). Ther number of stocks per contract is `Multiplier` (default to 100 if not specified).

---
### **Part A: Management of Existing Covered Calls**

For every stock that is already covered by a short call, perform the following analysis.

#### **1. Position Status Review**
* **Ticker & Position:** State the Ticker, Days to Expiration (DTE), and the current Profit/Loss on the short call (e.g., "Currently at an 85% profit").
* **Stock vs. Strike:** Characterize the stock's current price relative to the short strike (e.g., "Deep ITM," "At the Strike," "Well OTM").

#### **2. Verdict & Rationale (New Hierarchical Rules)**
Apply these rules in order. The first rule that is met determines the verdict.

**Rule #1: Proactive Management on Highly Profitable Positions (>80% Profit)**
* **Condition:** This rule applies **only if the short call has captured >80% of its maximum profit.** If it has, analyze the capital efficiency of the remaining premium by calculating its annualized return: `(Remaining Premium per Share / Current Stock Price) * (365 / DTE)`.
* **Verdict Path A: Trend is Favorable (Uptrend/Range-Bound)**
    * If the remaining annualized return is inefficient (**<8%**), the verdict is ✅ **Roll Position.**
    * **Rationale:** The stock remains a good candidate, but the current option is no longer productive. We will lock in our profit and roll to a new strike/date to put the capital back to work efficiently. This is true **even if the stock is at or slightly above the strike.**
* **Verdict Path B: Trend has Deteriorated (Downtrend)**
    * If the remaining annualized return is inefficient (**<8%**), the verdict is 🔒 **Close Call (Do Not Re-initiate).**
    * **Rationale:** The stock's trend no longer supports a covered call position. We will lock in our high profit on the unproductive option and exit, waiting for the technical picture to improve before considering a new call.
* **If profit is >80% but the remaining return is still efficient (>8%), the logic proceeds to Rule #2.**

**Rule #2: Assignment Check**
* **Condition:** This rule applies if Rule #1 was not triggered, and the stock price is **challenging or above the strike.**
* **Verdict:** ❌ **Hold for Assignment.**
* **Rationale:** No proactive management was warranted because either the profit wasn't high enough or the remaining premium was still working efficiently. Therefore, we revert to our original plan and allow the highly profitable position to be assigned.

**Rule #3: Default Action (Hold to Expiration)**
* **Condition:** If neither Rule #1 nor Rule #2 was triggered.
* **Verdict:** ❌ **Hold to Expiration.**
* **Rationale:** The position is OTM and has not yet met our high-profit threshold for active management. The best course of action is to do nothing and let theta decay work as intended.


1.  **Trend Alignment:** We primarily sell calls on stocks in healthy uptrends or stable, range-bound patterns to generate income while participating in upside. We avoid capping the recovery potential of stocks in recent downtrends where premiums are often insufficient to justify the risk.
2.  **Proactive Management:** Rolling is a strategic choice to optimize a profitable position, either by capturing realized gains early or by adjusting to a new, more bullish outlook on a stock that has not yet been called.

  * **Market Data:** You must fetch the latest available stock price (`Current_Price`) and all other market data (IV, financials, etc.) from the web. Do not use price data from the provided files.
---
### **Part B: Analysis for New & Rolled Positions**

Execute this full, detailed analysis for all **uncovered stock positions** and for all existing positions that were marked ✅ **Roll Position** in Part A.

#### **Part B.1: Analysis, Verdict, and Strategic Path**

**1. Fundamental & Catalyst Review**

  * **Earnings Snapshot:** Summarize the last quarterly earnings, noting beats/misses and forward guidance.
  * **Upcoming Catalysts:** Identify the date of the next earnings report and other key catalysts.
  * **Fundamental Valuation:** State your independent conclusion based on your own analysis: **Overvalued, Fairly Valued, or Undervalued**. Base this on Growth Prospects, Profitability & Moat, and Relative Valuation. Provide a concise, one-sentence rationale.
  * **Alignment with Target Price:** Compare your valuation to the provided `TargetPrice`. Comment on whether the `TargetPrice` appears reasonable, too conservative, or too optimistic based on your valuation.

**2. Technical Analysis**

  * **Market Structure:** Characterize the stock's trend as **Uptrend, Range-Bound, or Downtrend**, justifying with key moving averages (e.g., 20EMA, 50SMA) and price action.
  * **Key Price Levels:** Identify the nearest significant support and resistance levels.
  * **Implied Volatility (IV):** State the current Implied Volatility Rank (IVR) and classify as **High (\>50), Moderate (25-50), or Low (\<25)**.

**3. Final Verdict & Justification**
Based on all analysis, classify the stock with one of the following verdicts:

  * ✅ **Prime Candidate:** Ideal conditions: healthy uptrend or stable range, reasonable fundamentals, and sufficient IV.
  * ⚠️ **Acceptable Candidate:** Suitable, but with minor reservations (e.g., nascent trend, stretched valuation, or moderate IV).
  * ❌ **No Action Recommended:** Unfavorable conditions. This is the verdict for stocks in a **clear downtrend**, those with extremely low IV, or those with a major catalyst inside the typical expiration window.

Provide a clear justification. If "Prime" or "Acceptable," assign a **Strategic Path** and proceed to Part B.2.

#### **Part B.2: Covered Call Strategy & Trade Recommendation**

**1. Proposed Trade**

  * **Expiration:** Recommend a specific monthly expiration date, typically **30-45 DTE**
  * **Strike Price Selection (Integrated Rationale):** Select a strike by blending your fundamental valuation, technical levels, and the strategic path.
      * **Standard Path (Undervalued/Fairly Valued Stock in Uptrend AND Below Target):** Prioritize continued upside while generating income. Choose a strike at or above a clear technical resistance level to allow room for appreciation.
      * **Exit Path (Overvalued Stock OR Price Has Met/Exceeded TargetPrice):** Prioritize premium and a successful exit. The goal is assignment. Choose a strike closer to the current price, often just above the first major resistance or the `TargetPrice`.
  * **Justification:** Explain precisely how the chosen strike and path align with the fundamental, technical, and target price analysis.

**2. Trade Metrics (Net of Commission)**

  * **Option Premium:** Current Bid/Ask spread and the Midpoint price.
  * **Net Premium Received:** `(Midpoint Price x Multiplier x Number of Contracts) - Commission`.
  * **Breakeven Price:** `Cost_Basis - (Net Premium Received per Share)`.
  * **Return on Capital (RoC) (Annualized):** `(Net Premium per Share / Current Stock Price) * (365 / DTE)`.
  * **Return if Assigned:** `((Strike Price - Cost Basis) + Net Premium per Share) / Cost Basis`. (Label as "Mitigated Loss" if negative).
  * **Option Delta:** Provide the delta of the chosen option for informational purposes.

**3. Management Plan**

  * **Entry:** "Sell to Open [Number] [Ticker] [Date] [Strike] Call @ [Midpoint] or better."
  * **Goal:** **Assignment is a successful outcome.**
  * **Management:** "Manage proactively based on our core philosophy. We will hold for assignment if the strike is challenged. Consider closing early only if a significant portion (\>80%) of the premium is captured well ahead of schedule, making the remaining annualized return inefficient."

-----

### **Part C: Executive Summary**

Consolidate all recommendations into a final, scannable dashboard.

**Management Actions on Existing Positions**
| Ticker | DTE | P/L on Short Call | Verdict | Rationale |
| :--- | :-: | :--- | :--- | :--- |
| | | | | |

**New & Rolled Trade Recommendations**
| Ticker | Type | Path | Expiration | Strike | RoC (Ann.) | Return if Assigned |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| | New | Standard | | | | |
| | Roll | Exit | | | | |

**No Action Recommended**
| Ticker | Reason | Concise Rationale |
| :--- | :--- | :--- |
| [Ticker] | [e.g., Downtrend] | [One-sentence summary of why no action is advised] |

-----

### **Part D: Executive Summary for Telegram**

Finally, provide a condensed plain-text summary of all actionable trades, under 4000 characters, in the following format:

```
//-- EXECUTIVE SUMMARY START --//
[Summarize all "Sell to Open", "Roll To", and "Close Position" actions in a clear, scannable text format here.]
//-- EXECUTIVE SUMMARY END --//
```

-----

### **Final Instruction Check**

Before generating the response, verify that a complete, multi-part analysis (Part A or Part B) has been written for **every single stock position** provided in the input data. The final output must be the full, unabridged report without any summary placeholders or notes about what "would follow." Execute the full task for all tickers.