from scipy.stats import norm
import numpy as np

from trading_bot.models.models import Rights


def black_scholes_delta(
    S: float, K: float, T: float, r: float, sigma: float, right: Rights
) -> float:
    """
    Calculate the delta of a European call or put option using the Black-Scholes model.

    Parameters:
    - S (float): Current stock price
    - K (float): Strike price
    - T (float): Time to expiration in years
    - r (float): Risk-free interest rate (annual)
    - sigma (float): Implied volatility (annual)
    - option_type (str): 'call' or 'put'

    Returns:
    - float: Delta of the option
    """
    if T <= 0:
        raise ValueError("Time to expiration (T) must be greater than zero.")

    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))

    if right == Rights.CALL:
        delta = norm.cdf(d1)
    elif right == Rights.PUT:
        delta = norm.cdf(d1) - 1
    else:
        raise ValueError("Option type must be 'call' or 'put'.")

    return delta
