
from decimal import Decimal

def tick_to_price(tick: int) -> Decimal:
        return Decimal("1.0001") ** tick

def tick_to_sqrt_price(tick: int) -> int:
    """Convert a tick to its corresponding square root price (P = sqrt(price))."""
    return 1.0001 ** (tick / 2)

def compute_token_amounts_from_liquidity(
    tick_lower: int, tick_upper: int, liquidity: Decimal, current_tick: int
) -> tuple[Decimal, Decimal]:
    sqrt_price = Decimal(tick_to_sqrt_price(current_tick))
    sqrt_price_lower = Decimal(tick_to_sqrt_price(tick_lower))
    sqrt_price_upper = Decimal(tick_to_sqrt_price(tick_upper))
    L = liquidity

    if current_tick <= tick_lower:
        amount0 = L * (1 / sqrt_price_lower - 1 / sqrt_price_upper)
        amount1 = Decimal(0)
    elif current_tick >= tick_upper:
        amount0 = Decimal(0)
        amount1 = L * (sqrt_price_upper - sqrt_price_lower)
    else:
        amount0 = L * (1 / sqrt_price - 1 / sqrt_price_upper)
        amount1 = L * (sqrt_price - sqrt_price_lower)

    return amount0, amount1


def compute_impermanent_loss(
    current_tick: int, entry_tick: int, min_tick: int, max_tick: int
) -> Decimal:
    k = Decimal(current_tick) / Decimal(entry_tick)
    k_min = Decimal(min_tick) / Decimal(entry_tick)
    k_max = Decimal(max_tick) / Decimal(entry_tick)

    il_base = (Decimal("2") * k.sqrt() / (Decimal("1") + k)) - Decimal("1")
    factor = Decimal("1") / (
        Decimal("1")
        - ((k_min.sqrt() + k * (Decimal("1") / k_max).sqrt()) / (Decimal("1") + k))
    )
    return il_base * factor * Decimal("100")


def compute_realized_il(
    entry_token0_ratio: Decimal,
    current_token0_ratio: Decimal,
    target_token0_ratio: Decimal,
    full_il: Decimal,
) -> Decimal:
    """
    Compute the realized impermanent loss as a fraction of full IL.
    The realization ratio is based on how much of the path from current to entry you correct.
    """
    if target_token0_ratio == current_token0_ratio:
        return Decimal("0")
    denominator = abs(entry_token0_ratio - current_token0_ratio)
    if denominator == 0:
        return Decimal("0")
    realization_fraction = abs(target_token0_ratio - current_token0_ratio) / denominator
    return realization_fraction * full_il * 100


def compute_liquidity_from_token0(amount0: Decimal, sqrtP: Decimal, sqrtB: Decimal) -> Decimal:
    return amount0 * sqrtP * sqrtB / (sqrtB - sqrtP)

def compute_token1_for_fixed_token0(
    amount0: Decimal,
    tick_lower: int,
    tick_upper: int,
    current_tick: int,
) -> tuple[Decimal, Decimal]:
    sqrtA = Decimal(tick_to_sqrt_price(tick_lower))
    sqrtB = Decimal(tick_to_sqrt_price(tick_upper))
    sqrtP = Decimal(tick_to_sqrt_price(current_tick))

    if current_tick <= tick_lower:
        liquidity = amount0 * sqrtA * sqrtB / (sqrtB - sqrtA)
        amount1 = Decimal(0)
    elif current_tick >= tick_upper:
        liquidity = Decimal(0)
        amount1 = Decimal(0)
    else:
        liquidity = amount0 * sqrtP * sqrtB / (sqrtB - sqrtP)
        amount1 = liquidity * (sqrtP - sqrtA)

    return liquidity, amount1

def sqrtPriceX96_to_price_adjusted(
    sqrtPriceX96: int,
    token0_decimals: int,
    token1_decimals: int,
) -> Decimal:
    """
    Converts sqrtPriceX96 to human-readable price of token1 in terms of token0,
    adjusting for decimals of both tokens.

    Parameters:
    - sqrtPriceX96 (Decimal): Q64.96 encoded square root price from Uniswap
    - token0_decimals (int): Number of decimals for token0 (base)
    - token1_decimals (int): Number of decimals for token1 (quote)

    Returns:
    - Decimal: Human-readable price of token1 per token0
    """
    Q96 = Decimal(2 ** 96)
    sqrt_price = sqrtPriceX96 / Q96
    price_raw = sqrt_price ** 2

    decimal_adjustment = Decimal(10 ** (token0_decimals - token1_decimals))
    price_adjusted = price_raw * decimal_adjustment

    return price_adjusted