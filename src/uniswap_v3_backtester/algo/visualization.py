from matplotlib import pyplot as plt
from uniswap_v3_backtester.algo.backtester import BacktestResult


def plot_position_evolution(result: BacktestResult) -> None:
    # Unpack token balances
    timestamps, token0s, token1s = zip(*result.token_balance_series)
    token0s = [float(t) for t in token0s]
    token1s = [float(t) for t in token1s]

    # Extract ticks
    tick_times, ticks = zip(*result.swap_ticks)
    ticks = [float(t) for t in ticks]

    # Cumulative fee evolution
    fee_token0s = [float(f.token0) for f in result.fee_series.fees]
    fee_token1s = [float(f.token1) for f in result.fee_series.fees]
    fee_cum0 = [sum(fee_token0s[: i + 1]) for i in range(len(fee_token0s))]
    fee_cum1 = [sum(fee_token1s[: i + 1]) for i in range(len(fee_token1s))]

    # IL data
    il_timestamps = result.il_series.timestamps
    il_values = [float(v) for v in result.il_series.values]
    ril_timestamps = result.realized_il.timestamps
    ril_values = [float(v) for v in result.realized_il.values]

    # APR timeseries
    apr_dates = result.apr_series.dates
    apr_values = [float(a) for a in result.apr_series.aprs]  # annualized % view

    # Create figure
    fig, axs = plt.subplots(6, 1, figsize=(14, 16), sharex=True)

    # --- [0] Tick Evolution ---
    axs[0].plot(tick_times, ticks, label="Current Tick", color="black")
    axs[0].axhline(result.initial_tick_lower, color="red", linestyle="--", label="Tick Lower")
    axs[0].axhline(result.initial_tick_upper, color="green", linestyle="--", label="Tick Upper")
    axs[0].set_ylabel("Tick")
    axs[0].legend()
    axs[0].grid(True)

    # Shade active/inactive periods
    for t0, t1, active in zip(
        result.activity_series.timestamps[:-1],
        result.activity_series.timestamps[1:],
        result.activity_series.activity[:-1],
    ):
        color = "green" if active else "red"
        axs[0].axvspan(t0, t1, color=color, alpha=0.2)

    # --- [1] Token0 and Token1 Balances ---
    ax1 = axs[1]
    ln1 = ax1.plot(timestamps, token0s, label="Token0", color="blue")
    ax1.set_ylabel("Token0", color="blue")
    ax1.tick_params(axis="y", labelcolor="blue")
    ax1.grid(True)
    ax1b = ax1.twinx()
    ln2 = ax1b.plot(timestamps, token1s, label="Token1", color="orange")
    ax1b.set_ylabel("Token1", color="orange")
    ax1b.tick_params(axis="y", labelcolor="orange")
    lines = ln1 + ln2
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels, loc="upper left")

    # --- [2] APR Series ---
    axs[2].plot(apr_dates, apr_values, label="APR (annualized %)", color="purple")
    axs[2].set_ylabel("APR [%]")
    axs[2].legend()
    axs[2].grid(True)

    # --- [3] Cumulative Fees ---
    ax3 = axs[3]
    ln1 = ax3.plot(timestamps, fee_cum0, label="Cumulative Fees Token0", color="blue")
    ax3.set_ylabel("Fees Token0", color="blue")
    ax3.tick_params(axis="y", labelcolor="blue")
    ax3.grid(True)

    ax3b = ax3.twinx()
    ln2 = ax3b.plot(timestamps, fee_cum1, label="Cumulative Fees Token1", color="orange")
    ax3b.set_ylabel("Fees Token1", color="orange")
    ax3b.tick_params(axis="y", labelcolor="orange")

    lines = ln1 + ln2
    labels = [line.get_label() for line in lines]
    ax3.legend(lines, labels, loc="upper left")

    # --- [4] IL and Realized IL ---
    axs[4].plot(il_timestamps, il_values, label="Impermanent Loss", color="black")
    axs[4].plot(ril_timestamps, ril_values, label="Realized IL", color="red", linestyle="--")
    axs[4].set_ylabel("IL [%]")
    axs[4].legend()
    axs[4].grid(True)

    # --- [5] Placeholder for future additions (e.g., LP fees APR or compounding) ---
    axs[5].axis("off")  # reserved space

    plt.suptitle("Backtest Position Evolution")
    plt.tight_layout()
    plt.show()
