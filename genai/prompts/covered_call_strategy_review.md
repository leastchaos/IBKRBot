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
* **Market Structure:** Characterize the stock's trend as **Uptrend, Range-Bound, or Downtrend**. This is a critical factor. Justify with key moving averages (e.g., 20EMA, 50SMA) and recent price action.
* **Key Price Levels:** Identify several significant **support and resistance** levels, noting whether they are derived from daily or weekly charts.
* **Implied Volatility (IV):** State the current Implied Volatility Rank (IVR). Classify it as High (>50), Moderate (25-50), or Low (<25).
* **Tactical Entry Signal:** Analyze the stock's current price to find a high-probability entry point. State one of the following:
    * **✅ Favorable Entry:** The stock is currently testing a major resistance level or is in a technically "overbought" condition (e.g., RSI > 70). This is the ideal time to sell a call.
    * **⚠️ Approaching Entry:** The stock is in an uptrend but still has room to run before hitting the next major resistance.
    * **❌ Unfavorable Entry:** The stock is in a downtrend, is oversold, or has just broken out above a key resistance level (we don't want to cap a new breakout).

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
    * **Exit Path (Overvalued Stock OR Price Has Met/Exceeded Target Price):** Prioritize generating a high premium and creating an attractive exit point. The goal is assignment. **Choose a strike at or just above the *current* resistance level that triggered our entry signal.**
* **Justification:** Explain exactly how the chosen path and strike align with your fundamental conclusion, the stock's position relative to its target price, and the current technical entry signal. For example: *"The stock is undervalued and hitting its first resistance at $222, providing a Favorable Entry. Per the Standard Path, we are selecting the $230 strike, which is the next major resistance level, to allow the healthy uptrend room to continue."*
* **Trade Metrics (Net of Commission):**
    * **Option Premium:** Current Bid/Ask spread and the Midpoint price.
    * **Net Premium Received:** `(Midpoint Price x Multiplier x Number of Contracts) - Commission`.
    * **Breaken Price:** `Cost_Basis - (Net Premium Received per Share)`.
    * **Return on Capital (RoC) (Annualized):** `(Net Premium per Share / Current Stock Price) * (365 / DTE)`.
    * **Return if Assigned:** `((Strike Price - Cost Basis) + Net Premium per Share) / Cost Basis`. (Label as "Mitigated Loss" if negative).
    * **Option Delta (Informational):** Provide the delta of the chosen option.

---
### **Part C: Synthesized Action Plan & Executive Summary**

This is the final step where you combine the results from Part A and Part B to generate a scannable dashboard of concrete actions. Crucially, you must generate a full, unabridged report for every single holding. Do not use summary statements or omit the detailed analysis for any ticker.

#### **1. Management Actions on Existing Positions**
| Ticker | P/L on Call | **Close Decision (Part A)** | **Open Decision (Part B)** | **FINAL ACTION** |
| :--- | :--- | :--- | :--- | :--- |
| **[Ticker]** | [e.g. 92% Profit] | [e.g. ✅ Close (Inefficient)] | [e.g. ✅ Prime Candidate] | **ROLL POSITION** |
| **[Ticker]** | [e.g. 65% Profit] | [e.g. ❌ Hold (Still efficient)] | *(N/A)* | **HOLD POSITION** |
| **[Ticker]** | [e.g. 85% Profit] | [e.g. ✅ Close (Inefficient)] | [e.g. ❌ No Action (Downtrend)] | **CLOSE CALL ONLY** |

#### **2. Recommendations for Uncovered Stocks**
| Ticker | **Open Decision (Part B)** | **FINAL ACTION** |
| :--- | :--- | :--- |
| **[Ticker]** | [e.g. ✅ Prime Candidate] | **SELL NEW CALL** |
| **[Ticker]** | [e.g. ❌ No Action (Low IV)] | **NO ACTION** |

#### **3. Executive Summary for Telegram**
Finally, provide a condensed plain-text summary of all actionable trades, under 4000 characters, in the following format:
//-- EXECUTIVE SUMMARY START --//
[Summarize all "Sell to Open", "Roll To", and "Close Position" actions in a clear, scannable text format here.]
//-- EXECUTIVE SUMMARY END --//

### **Final Instruction Check**

Before generating the response, verify that a complete, multi-part analysis (Part A or Part B) has been written for **every single stock position** provided in the input data. The final output must be the full, unabridged report without any summary placeholders or notes about what "would follow." Execute the full task for all tickers.