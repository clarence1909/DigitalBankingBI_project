"""Month and timestamp helpers for the simulator.

All simulated times are Malaysia local time (MYT, UTC+8) held as naive
numpy datetime64[s]; the writers convert them to UTC for sources that store
UTC, exactly as the real systems would.
"""

import numpy as np
import pandas as pd

from src.config import DATA_END, FIRST_MONTH, LAST_MONTH, UTC_OFFSET_HOURS

MONTHS = pd.period_range(FIRST_MONTH, LAST_MONTH, freq="M")
N_MONTHS = len(MONTHS)
MONTH_LABELS = [str(m) for m in MONTHS]
MONTH_START = np.array([m.start_time.to_datetime64() for m in MONTHS], dtype="datetime64[s]")
MONTH_END_DATE = np.array([m.end_time.normalize().to_datetime64() for m in MONTHS], dtype="datetime64[D]")
DAYS_IN_MONTH = np.array([m.days_in_month for m in MONTHS])
END_TS = np.datetime64(DATA_END) + np.timedelta64(1, "D") - np.timedelta64(1, "s")

SECOND = np.timedelta64(1, "s")
MINUTE = np.timedelta64(60, "s")
HOUR = np.timedelta64(3600, "s")
DAY = np.timedelta64(86400, "s")

# Share of app activity by hour of day, Malaysia time (quiet overnight)
_HOUR_WEIGHTS = np.array([1, 0.6, 0.4, 0.3, 0.3, 0.5, 1.2, 2.2, 3, 3.2, 3.3, 3.5,
                          3.8, 3.6, 3.4, 3.4, 3.5, 3.7, 3.9, 4.2, 4.5, 4.4, 3.6, 2.2])
HOUR_P = _HOUR_WEIGHTS / _HOUR_WEIGHTS.sum()


def month_index(ts):
    """Month index (0 = Sep 2024) of MYT timestamps or dates."""
    ts = np.asarray(ts).astype("datetime64[M]")
    return (ts - np.datetime64(FIRST_MONTH, "M")).astype(int)


def random_times_in_month(rng, m, n, not_before=None, hours=None):
    """n random MYT timestamps in month m, optionally no earlier than not_before."""
    days = rng.integers(0, DAYS_IN_MONTH[m], size=n)
    if hours is None:
        hrs = rng.choice(24, size=n, p=HOUR_P)
    else:
        hrs = rng.integers(hours[0], hours[1], size=n)
    secs = rng.integers(0, 3600, size=n)
    ts = MONTH_START[m] + days * DAY + hrs * HOUR + secs * SECOND
    month_end = MONTH_START[m] + DAYS_IN_MONTH[m] * DAY - SECOND
    if not_before is not None:
        nb = np.minimum(np.asarray(not_before, dtype="datetime64[s]"), month_end)
        late = ts < nb
        if late.any():
            # Push early draws to a random point between not_before and month end
            span = (month_end - nb[late]).astype(int)
            span = np.maximum(span, 1)
            ts[late] = nb[late] + (rng.random(late.sum()) * span).astype(int) * SECOND
    # Everything generated for a month stays inside that month
    return np.minimum(ts, month_end)


def to_utc(ts_myt):
    return np.asarray(ts_myt, dtype="datetime64[s]") - UTC_OFFSET_HOURS * HOUR


def add_months(dates, months):
    """Add whole months to datetime64[D] dates, clipping the day to month end."""
    d = np.asarray(dates, dtype="datetime64[D]")
    months = np.asarray(months, dtype=np.int64)
    ym = d.astype("datetime64[M]")
    day = (d - ym.astype("datetime64[D]")).astype(np.int64)
    target = ym + months
    start = target.astype("datetime64[D]")
    days_in_target = ((target + 1).astype("datetime64[D]") - start).astype(np.int64)
    return start + np.minimum(day, days_in_target - 1)


def sen(amount_rm):
    """Ringgit to integer sen (all money is held in sen to keep sums exact)."""
    return np.round(np.asarray(amount_rm, dtype=float) * 100).astype(np.int64)
