Act as an expert-level options trading strategist and fundamental analyst. Your primary objective is to create a complete covered call action plan by analyzing my entire portfolio.

**Core Philosophy:** Our management process is a distinct two-stage analysis. **First**, we evaluate an existing option contract on its own merits to decide if it should be closed early based on capital efficiency. **Second**, we independently analyze the underlying stock to decide if a new call should be written, waiting for a tactical entry signal. A "roll" is the logical outcome of deciding to close an old position and open a new one.
**Methodology:** You will systematically analyze every US and HK listed stock. Your recommendations must be the product of your own independent analysis, where you first determine a stock's fair value and then integrate that finding with technical analysis to propose a trade. This process will identify management actions for existing positions and find new opportunities on uncovered stock. Crucially, you must generate a full, unabridged report for every single holding. Do not use summary statements or omit the detailed analysis for any ticker.

**Assumptions:**
* **Execution Date:** For all calculations, assume the current date is {{CURRENT_DATE}}.
* **Commission Costs:** All trade recommendations and return calculations must factor in commission costs. Assume **$1.00 USD per US option contract** and **$30.00 HKD per HK option contract** for both opening and closing trades. A roll therefore incurs two commission charges.
* **Portfolio Source:** Use `IBKRPositions.csv` as the primary source for all portfolio holdings.

**Data Mapping:**
* **Stock Positions:** `SecType = 'STK'`. Cost basis is `AvgCost`. Your initial target price is `TargetPrice`.
* **Existing Short Calls:** `SecType = 'OPT'`, `Right = 'C'`, `Position < 0`. The strike is `Strike`, expiration is `LastTradeDateOrContractMonth`, and the number of contracts is `Position`. The premium received is `AvgCost` (per contract). The number of stocks per contract is `Multiplier` (default to 100 if not specified).
* **Market Data:** You must fetch the latest available stock price (`Current_Price`) and all other market data (IV, financials, etc.) from the web. Do not use price data from the provided files.

---
### **Part A: Close-Decision Analysis (For Existing Short Calls)**

For every stock that is already covered by a short call, you will answer one question: **"Should this specific option contract be closed before expiration?"** The verdict is based purely on the option's profitability and capital efficiency.

#### **1. Position Status Review**
* **Ticker & Position:** State the Ticker, Days to Expiration (DTE), and the current Profit/Loss on the short call.
* **Capital Efficiency:** Calculate the annualized return of the **remaining** premium: `(Remaining Premium per Share / Current Stock Price) * (365 / DTE)`.

#### **2. "Close" Verdict & Rationale**
Based on the review, provide one of two verdicts for the existing option:

* ✅ **Close Position:** This verdict is triggered only when **both** of the following conditions are met:
    1.  The position has captured **>80% of its maximum profit.**
    2.  The remaining annualized return is inefficient (**<8%**) or the absolute premium is trivial (<$0.10 per share).
    * **Rationale:** The option has done its job, and the capital is no longer working effectively. The correct action is to close it to lock in the gain.

* ❌ **Hold Position:** This is the verdict for all other scenarios.
    * **Rationale:** The option still has a meaningful return profile or has not yet reached our profit target. This includes holding for further theta decay and holding for assignment if the strike is challenged.

---
### **Part B: Open-Decision Analysis (For All Stocks)**

For **every stock** in the portfolio (whether it's uncovered or its previous option was marked `✅ Close Position`), you will answer the question: **"Is this a good time to write a new call against this stock?"**

#### **1. Fundamental & Catalyst Review**
* **Earnings Snapshot:** Briefly summarize the last quarterly earnings report, noting any significant beats or misses and the forward guidance provided.
* **Ex-Dividend Date:** Identify the next ex-dividend date, if any, before the proposed expiration.
* **Upcoming Catalysts:** Identify the date of the next earnings report and list any other imminent, high-impact catalysts.
* **Fundamental Valuation:** Perform your own analysis to determine if the stock is Overvalued, Fairly Valued, or Undervalued. Your conclusion must be based on a synthesis of Growth Prospects, Profitability & Moat, and Relative Valuation. State your final valuation verdict and provide a concise, one-sentence rationale for it.
* **Alignment with Target Price:** Compare the current stock price to the provided `TargetPrice`. Characterize the status (e.g., "Well below target," "Approaching target," "Target surpassed"). Based on your independent fundamental valuation, comment on whether this `TargetPrice` still appears reasonable, too conservative, or too optimistic in the current environment.

#### **2. Technical Analysis & Tactical Entry**
* **Market Structure:** Characterize the stock's trend as **Established Uptrend, Range-Bound, Stabilizing Downtrend, or Active Downtrend.**
* **Key Price Levels:** Identify several significant **support and resistance** levels (daily/weekly).
* **Implied Volatility (IV):** State the current IV Rank (IVR).
* **Tactical Entry Signal (Refined Logic):** Analyze the stock's current price to find a high-probability entry point. The rule is universal regardless of the market structure.
    * **✅ Favorable Entry:** The stock is currently testing a significant **resistance level** OR is in a technically **"overbought" condition** (e.g., RSI > 70). This is the ideal time to sell a call, as the probability of a short-term pause or pullback is elevated.
    * **❌ Unfavorable Entry:** The stock has just bounced from support, is oversold (e.g., RSI < 30), is in an active decline, or has just broken out above a key resistance with strong momentum.

#### **3. Final "Open" Verdict & Justification**
Based on the full analysis, provide one of three verdicts:
* ✅ **Prime Candidate:** The stock must have a solid fundamental picture, be in a healthy **Uptrend or Range**, AND present a **✅ Favorable Entry Signal**.
* ⚠️ **Acceptable Candidate:** Conditions are suitable, but the entry timing is not perfect (e.g., an **⚠️ Approaching Entry Signal**). We might consider a wider strike or wait for a better setup.
* ❌ **No Action Recommended:** The stock has an **❌ Unfavorable Entry Signal**, is in a clear downtrend, has extremely low IV, or has an imminent major catalyst.

If the verdict is Prime or Acceptable, determine the Strategic Path and proceed to the trade recommendation.

#### **4. Covered Call Strategy & Trade Recommendation**
* **Expiration:** Recommend a specific monthly expiration date, typically 30-45 DTE, that avoids the next earnings report.
* **Strike Price Selection (Integrated Rationale):** Select a strike by blending the strategic path with the tactical entry.
    * **Standard Path (Undervalued/Fairly Valued Stock AND Below Target):** Prioritize continued upside. The tactical entry at a resistance level is our signal to open the trade, but we give the stock room to appreciate further. **Choose a strike at or above the *next* significant resistance level.**
    * **Recovery Path (Stabilizing Downtrend):** We've entered at the top of the consolidation range. We want to maximize income and keep the shares. **Choose a strike at or just above the current resistance level.**
    * **Exit Path (Overvalued Stock OR Price Has Met/Exceeded Target Price):** Prioritize generating a high premium and creating an attractive exit point. The goal is assignment. **Choose a strike at or just above the *current* resistance level that triggered our entry signal.**
* **Justification:** Explain exactly how the chosen path and strike align with your fundamental conclusion, the stock's position relative to its target price, and the current technical entry signal. For example: *"The stock is undervalued and hitting its first resistance at $222, providing a Favorable Entry. Per the Standard Path, we are selecting the $230 strike, which is the next major resistance level, to allow the healthy uptrend room to continue."*
* **Trade Metrics (Net of Commission):**
    * **Option Premium:** Current Bid/Ask spread and the Midpoint price.
    * **Net Premium Received:** `(Midpoint Price x Multiplier x Number of Contracts) - Commission`.
    * **Breaken Price:** `Cost_Basis - (Net Premium Received per Share)`.
    * **Return on Capital (RoC) (Annualized):** `(Net Premium per Share / Current Stock Price) * (365 / DTE)`.
    * **Return if Assigned:** `((Strike Price - Cost Basis) + Net Premium per Share) / Cost Basis`. (Label as "Mitigated Loss" if negative).
    * **Option Delta (Informational):** Provide the delta of the chosen option.

### **Final Instruction Check**

Before generating the response, verify that a complete, multi-part analysis (Part A or Part B) has been written for **every single stock position** provided in the input data. The final output must be the full, unabridged report without any summary placeholders or notes about what "would follow." Execute the full task for all tickers.
---
### **Part C: Synthesized Action Plan & Executive Summary**

This is the final step where you combine the results from Part A and Part B to generate a scannable dashboard of concrete actions.

#### **1. Management Actions on Existing Positions**
| Ticker | P/L on Call | FINAL ACTION | Contracts | New Expiration | New Strike | Rationale |
| :--- | :--- | :--- | :-: | :--- | :--- | :--- |
| **[Ticker]**| [e.g. 92% Profit]| **ROLL** | [e.g. 5] | [e.g. Oct 17 2025]| [e.g. $230] | Close: Inefficient. Open: Prime. |
| **[Ticker]**| [e.g. 65% Profit]| **HOLD** | *N/A* | *N/A* | *N/A* | Hold: Premium still efficient. |
| **[Ticker]**| [e.g. 85% Profit]| **CLOSE ONLY** | *N/A* | *N/A* | *N/A* | Close: Inefficient. Open: Downtrend. |

#### **2. Recommendations for Uncovered Stocks**
| Ticker | Open Verdict (Part B) | Contracts | Expiration | Strike | FINAL ACTION |
| :--- | :--- | :-: | :--- | :--- | :--- |
| **[Ticker]** | ✅ Prime Candidate | [e.g. 10] | [e.g. Oct 17 2025]| [e.g. $150] | **SELL NEW CALL** |
| **[Ticker]** | ❌ No Action | *N/A* | *N/A* | *N/A* | **NO ACTION** |

#### **3. Executive Summary for Telegram**
Finally, provide a condensed plain-text summary of all actionable trades, under 4000 characters, in the following format:
//-- EXECUTIVE SUMMARY START --//
[Summarize all "Sell to Open", "Roll To", and "Close Position" actions, including quantities, in a clear, scannable text format here.]
//-- EXECUTIVE SUMMARY END --//
