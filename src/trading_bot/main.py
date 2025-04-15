import asyncio
from ib_async import IB, Contract, Order
from functools import partial

# Pure function to create an IB client
def create_ib_client(host='127.0.0.1', port=7497, client_id=1) -> IB:
    ib = IB()
    ib.connect(host, port, client_id)
    return ib

# Pure function to calculate position size
def calculate_position_size(current_price, fair_value, max_position, grid_step):
    price_diff = current_price - fair_value
    position_size = int(max_position * (1 - abs(price_diff) / fair_value))
    return max(1, min(position_size, max_position))  # Clamp between 1 and max_position

# Pure function to generate buy/sell prices
def generate_grid_prices(current_price, grid_step):
    return {
        'buy_price': current_price - grid_step,
        'sell_price': current_price + grid_step
    }

# Pure function to create orders
def create_order(action, quantity, price):
    order = Order()
    order.action = action
    order.orderType = 'LMT'
    order.totalQuantity = quantity
    order.lmtPrice = price
    return order


def get_limit_buy_price(ib: IB, )

def main():
    initial_position_size = 1
    max_position_per_level = 1
    grid_step = 10

    ib = create_ib_client()

    while True:

