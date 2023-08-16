"""
Downscale annual or seasonal glacier mass balance observations.
"""
from __future__ import annotations
import datetime
from typing import Dict, Iterable, Tuple, Union

import numpy as np

Number = Union[float, int]


def evaluate_sine(
    x: Iterable[Number],
    a: Number = 1,
    b: Number = 1,
    c: Number = 0,
    d: Number = 0,
    mask: Tuple[Number, Number] | Iterable[Number] = None
) -> np.ndarray:
    """
    Evaluate sine function.

    The function is assumed to be of the form:

    f(x) = a sin(b(x - c)) + d

    Arguments:
        x: Values at which to evaluate the function.
        a: Amplitude.
        b: Period scaling (period = 2π/b).
        c: Phase shift (positive: right).
        d: Vertical shift (positive: up).
        mask: Interval outside of which the function is zero (min, max).

    Returns:
        Function values.

    Examples:
        >>> evaluate_sine([0, np.pi/2, np.pi, 3 * np.pi/2, 2 * np.pi]).round(12)
        array([ 0.,  1.,  0., -1., -0.])
        >>> evaluate_sine([0, np.pi/2, np.pi], a=2).round(12)
        array([0., 2., 0.])
        >>> evaluate_sine([0, np.pi/2, np.pi], d=1)
        array([1., 2., 1.])
        >>> evaluate_sine([0, np.pi/2, np.pi], d=1, mask=(0, np.pi/2))
        array([0., 0., 1.])
    """
    x = np.atleast_1d(x)
    f = a * np.sin(b * (x - c)) + d
    if mask is not None:
        f[(x >= min(*mask)) & (x <= max(*mask))] = 0
    return f


def integrate_sine(
    intervals: Iterable[Tuple[Number, Number]] | np.ndarray | pd.DataFrame,
    a: Number = 1,
    b: Number = 1,
    c: Number = 0,
    d: Number = 0,
    mask: Tuple[Number, Number] | Iterable[Number] = None
) -> np.ndarray:
    """
    Integrate sine function.

    The function is assumed to be of the form:

    f(x) = a sin(b(x - c)) + d

    The integral in the interval [i, j] is then:

    a(cos(b(i - c)) - cos(b(j - c))) / b + d(j - i)

    Arguments:
        intervals: Intervals to integrate over [(i1, j1), ..., (in, jn)].
        a: Amplitude.
        b: Period scaling (period = 2π/b).
        c: Phase shift (positive: right).
        d: Vertical shift (positive: up).
        mask: Interval outside of which the integral is zero (min, max).

    Returns:
        Integral for each interval.

    Examples:
        >>> integrate_sine([(0, np.pi), (np.pi, 2 * np.pi), (0, 2 * np.pi)])
        array([ 2., -2.,  0.])
        >>> integrate_sine([(0, np.pi), (np.pi, 2 * np.pi)], a=2)
        array([ 4., -4.])
        >>> integrate_sine([(0, np.pi), (np.pi, 2 * np.pi)], d=2/np.pi)
        array([4., 0.])
        >>> integrate_sine([(0, np.pi/2), (np.pi/2, np.pi)], mask=(0, np.pi/2))
        array([1., 0.])
    """
    intervals = np.atleast_2d(intervals)
    if mask is not None:
        # Restrict intervals to mask
        intervals = intervals.copy()
        xmin, xmax = min(*mask), max(*mask)
        intervals[intervals < xmin] = xmin
        intervals[intervals > xmax] = xmax
    i = intervals[:, 0]
    j = intervals[:, 1]
    return a * (np.cos(b * (i - c)) - np.cos(b * (j - c))) / b + d * (j - i)


def generate_seasonal_sine(
    balance: Number,
    interval: Tuple[Number, Number] | Iterable[Number] = (0, 0.5),
    annual_balance: Number = 0
) -> Dict[str, Number]:
    """
    Generate a sine function that estimates a mass balance season.

    Arguments:
        balance: Seasonal balance.
        interval: Seasonal interval, assuming the hydrological year is (0, 1).
        annual_balance: Annual balance applied uniformally over the year.

    Returns:
        Sine function parameters (see `evaluate_sine`, `integrate_sine`).

    Examples:
        >>> intervals = [(0, 0.75), (0.75, 1)]

        Summer and winter seasonal balances.

        >>> bw, bs = 4, -2
        >>> sine = generate_seasonal_sine(bw, interval=intervals[0])
        >>> integrate_sine(intervals[0], **sine)[0] == bw
        True
        >>> sine = generate_seasonal_sine(bs, interval=intervals[1])
        >>> integrate_sine(intervals[1], **sine)[0] == bs
        True

        Annual balance and balance amplitude with uniform annual balance.

        >>> ba, alpha = 2, 3
        >>> bwi, bsi = calculate_seasonal_balances(ba, alpha)
        >>> sine = generate_seasonal_sine(
        ...     bwi, interval=intervals[0], annual_balance=ba
        ... )
        >>> bw = integrate_sine(intervals[0], **sine)[0]
        >>> sine = generate_seasonal_sine(
        ...     bsi, interval=intervals[1], annual_balance=ba
        ... )
        >>> bs = integrate_sine(intervals[1], **sine)[0]
        >>> ba == bw + bs
        True
        >>> alpha == abs(bw - bs) / 2
        True
    """
    width = abs(min(*interval) - max(*interval))
    b = (2 * np.pi) / (2 * width)
    return {
        'a': (balance - annual_balance * width) * b / 2,
        'b': b,
        'c': min(*interval),
        'd': annual_balance
    }


def calculate_seasonal_balances(
    annual_balance: Number | np.ndarray | pd.Series,
    balance_amplitude: Number
) -> Tuple[Number | np.ndarray | pd.Series, Number | np.ndarray | pd.Series]:
    """
    Calculate seasonal balances from annual balance and amplitude.

    Returns:
        Winter and summer balances.
    """
    return (
        annual_balance / 2 + balance_amplitude,
        annual_balance / 2 - balance_amplitude
    )


def calculate_balance_amplitude(
    winter_balance: Number | np.ndarray | pd.Series,
    summer_balance: Number | np.ndarray | pd.Series
) -> Number | np.ndarray | pd.Series:
    """
    Calculate the mass-balance amplitude from seasonal balances.

    Mass-balance amplitude is defined as half the absolute value of the
    difference between the summer and winter balance.

    The term and definiton are based on
    Cogley et al. 2011 (https://unesdoc.unesco.org/ark:/48223/pf0000192525) and
    Braithwaite & Hughes 2020 (https://doi.org/10.3389/feart.2020.00302).

    Arguments:
        winter_balance: Winter mass balance.
        summer_balance: Summer mass balance.

    Returns:
        Mass-balance amplitude.

    Examples:
        >>> calculate_balance_amplitude(-4, 2)
        3.0
        >>> calculate_balance_amplitude(4, -2)
        3.0
    """
    return abs((winter_balance - summer_balance) / 2)


def downscale_annual_balance(
    annual_balance: Number,
    balance_amplitude: Number,
    winter_fraction: Number = 0.5,
    temporal_resolution: int = 365,
    uniform_annual_balance: bool = False
) -> np.ndarray:
    """
    Downscale annual mass balance over a full year.

    Winter and summer balances are each represented by their own sine function
    (see `generate_seasonal_sine`).

    Arguments:
        annual_balance: Annual mass balance.
        balance_amplitude: Mass-balance amplitude
            (see `calculate_balance_amplitude`).
        winter_fraction: Annual fraction of winter season.
        temporal_resolution: Temporal resolution of output,
            e.g. 12 (~monthly) or 365 (~daily).
        uniform_annual_balance: Whether annual balance should be applied
            uniformally over the year (True) rather than assume that all mass
            gain/loss occurs in winter/summer (False).

    Returns:
        Mass balance for each time interval.

    Examples:
        >>> balance_amplitude = 5
        >>> annual_balance = -3

        With winter and summer of equal length:

        >>> balances = downscale_annual_balance(
        ...     annual_balance, balance_amplitude, temporal_resolution=12
        ... )
        >>> np.isclose(annual_balance, balances.sum())
        True
        >>> np.isclose(
        ...     balance_amplitude,
        ...     abs(balances[:6].sum() - balances[6:].sum()) / 2
        ... )
        True

        With winter and summer of different lengths:

        >>> balances = downscale_annual_balance(
        ...     annual_balance, balance_amplitude, temporal_resolution=12,
        ...     winter_fraction=0.75
        ... )
        >>> np.isclose(annual_balance, balances.sum())
        True
        >>> np.isclose(
        ...     balance_amplitude,
        ...     abs(balances[:9].sum() - balances[9:].sum()) / 2
        ... )
        True

        And with uniform annual balance:

        >>> balances = downscale_annual_balance(
        ...     annual_balance, balance_amplitude, temporal_resolution=12,
        ...     winter_fraction=0.75, uniform_annual_balance=True
        ... )
        >>> np.isclose(annual_balance, balances.sum())
        True
        >>> np.isclose(
        ...     balance_amplitude,
        ...     abs(balances[:9].sum() - balances[9:].sum()) / 2
        ... )
        True
    """
    # Calculate seasonal balances from annual balance and balance amplitude
    winter_balance, summer_balance = calculate_seasonal_balances(
        annual_balance=annual_balance,
        balance_amplitude=balance_amplitude
    )
    if uniform_annual_balance:
        edges = np.linspace(0, 1, num=temporal_resolution + 1)
        intervals = np.column_stack((edges[:-1], edges[1:]))
        sine_w = generate_seasonal_sine(
            winter_balance,
            interval=[0, winter_fraction],
            annual_balance=annual_balance
        )
        sine_s = generate_seasonal_sine(
            summer_balance,
            interval=[winter_fraction, 1],
            annual_balance=annual_balance
        )
        balances = (
            integrate_sine(intervals, **sine_w, mask=[0, winter_fraction]) +
            integrate_sine(intervals, **sine_s, mask=[winter_fraction, 1])
        )
        return balances
    return downscale_seasonal_balances(
        winter_balance=winter_balance,
        summer_balance=summer_balance,
        winter_fraction=winter_fraction,
        temporal_resolution=temporal_resolution
    )


def downscale_seasonal_balances(
    winter_balance: Number,
    summer_balance: Number,
    winter_fraction: Number = 0.5,
    temporal_resolution: int = 365
) -> np.ndarray:
    """
    Downscale seasonal mass balances over a full year.

    Winter and summer balances are each represented by their own sine function
    (see `generate_seasonal_sine`).

    Arguments:
        winter_balance: Winter mass balance.
        summer_balance: Summer mass balance.
        winter_fraction: Annual fraction of winter season.
        temporal_resolution: Temporal resolution of output,
            e.g. 12 (~monthly) or 365 (~daily).

    Returns:
        Mass balance for each time interval.

    Examples:
        >>> winter_balance = 4
        >>> summer_balance = -3

        Single sample equals annual balance.

        >>> balances = downscale_seasonal_balances(
        ...     winter_balance=winter_balance, summer_balance=summer_balance,
        ...     winter_fraction=0.5, temporal_resolution=1
        ... )
        >>> np.isclose(balances[0], winter_balance + summer_balance)
        True

        Two samples with equal length season equal seasonal balances.

        >>> balances = downscale_seasonal_balances(
        ...     winter_balance=winter_balance, summer_balance=summer_balance,
        ...     winter_fraction=0.5, temporal_resolution=2
        ... )
        >>> np.isclose(balances[0], winter_balance)
        True
        >>> np.isclose(balances[1], summer_balance)
        True

        Samples with one spanning both seasons still sum to annual balance.

        >>> balances = downscale_seasonal_balances(
        ...     winter_balance=winter_balance, summer_balance=summer_balance,
        ...     winter_fraction=0.5, temporal_resolution=3
        ... )
        >>> np.isclose(balances.sum(), winter_balance + summer_balance)
        True
    """
    edges = np.linspace(0, 1, num=temporal_resolution + 1)
    intervals = np.column_stack((edges[:-1], edges[1:]))
    sine_w = generate_seasonal_sine(
        winter_balance, interval=[0, winter_fraction]
    )
    sine_s = generate_seasonal_sine(
        summer_balance, interval=[winter_fraction, 1]
    )
    balances = (
        integrate_sine(intervals, **sine_w, mask=[0, winter_fraction]) +
        integrate_sine(intervals, **sine_s, mask=[winter_fraction, 1])
    )
    return balances


def fill_balances(
    balances: Iterable[Tuple[Number, Number, Number]] | np.ndarray | pd.DataFrame,
    balance_amplitude: Number = None
) -> np.ndarray:
    """
    Fill missing winter, summer, or annual mass balances using each other.

    Arguments:
        balances: Series of winter, summer, and annual balance [(w, s, a), ...].
        balance_amplitude: Mean mass-balance amplitude. If not provided,
            it is computed from the seasonal balances in `balances`
            (see `calculate_balance_amplitude`).

    Returns:
        Array of filled winter, summer, and annual balances [(w, s, a), ...].

    Examples:
        >>> balances = [
        ...     (None, -4, -2),
        ...     (2, None, -2),
        ...     (2, -4, None),
        ...     (3, -3, 0),
        ...     (None, None, 0),
        ... ]
        >>> fill_balances(balances)
        array([[ 2., -4., -2.],
               [ 2., -4., -2.],
               [ 2., -4., -2.],
               [ 3., -3.,  0.],
               [ 3., -3.,  0.]])
        >>> fill_balances(balances[4:5], balance_amplitude=2)
        array([[ 2., -2.,  0.]])
    """
    # winter | summer | annual
    balances = np.array(balances, dtype=float)
    # Fill winter
    mask = np.isnan(balances[:, 0])
    balances[mask, 0] = balances[mask, 2] - balances[mask, 1]
    # Fill summer
    mask = np.isnan(balances[:, 1])
    balances[mask, 1] = balances[mask, 2] - balances[mask, 0]
    # Fill annual
    mask = np.isnan(balances[:, 2])
    balances[mask, 2] = balances[mask, 0] + balances[mask, 1]
    # Fill winter and summer
    mask = np.isnan(balances[:, 0]) & np.isnan(balances[:, 1])
    if mask.any():
        if balance_amplitude is None:
            if mask.all():
                raise ValueError(
                    'No seasonal balances from which to estimate balance amplitude.'
                    ' Please provide one.'
                )
            balance_amplitude = calculate_balance_amplitude(
                winter_balance=balances[~mask, 0],
                summer_balance=balances[~mask, 1]
            ).mean()
        balances[mask, 0], balances[mask, 1] = calculate_seasonal_balances(
            annual_balance=balances[mask, 2],
            balance_amplitude=balance_amplitude
        )
    return balances


def generate_annual_datetime_sequence(
    start: datetime.datetime,
    width: datetime.timedelta = datetime.timedelta(days=1),
    count: int = None
) -> np.ndarray:
    """
    Generate a regularly-spaced sequence of datetimes spanning one year.

    Arguments:
        start: Start of the year.
        width: Width of each interval.
        count: Number of intervals to divide year into.
            If provided, width is ignored.
            Since year length ranges from 365 to 366 days, width will
            vary from year to year.

    Raises:
        ValueError: If start is February 29.
        ValueError: If width does not divide year evenly.

    Returns:
        Sequence of datetimes for the egdes of the intervals
        (length `n + 1` for `n` intervals).

    Examples:
        >>> start = datetime.datetime(2023, 8, 15, 17, 30)

        A single interval for the whole year.

        >>> generate_annual_datetime_sequence(start, count=1)
        array([datetime.datetime(2023, 8, 15, 17, 30),
               datetime.datetime(2024, 8, 15, 17, 30)], dtype=object)

        Daily intervals two ways (2024 is a leap year).

        >>> a = generate_annual_datetime_sequence(start, count=366)
        >>> b = generate_annual_datetime_sequence(
        ...     start, width=datetime.timedelta(days=1)
        ... )
        >>> all(a == b)
        True
        >>> widths = a[1:] - a[:-1]
        >>> all(widths == datetime.timedelta(days=1))
        True
    """
    if start.month == 2 and start.day == 29:
        raise ValueError('Cannot start on a leap day (February 29)')
    end = start.replace(year=start.year + 1)
    delta = end - start
    if count is not None:
        width = delta / count
    else:
        count = delta / width
        if count != int(count):
            raise ValueError(
                f'Width ({width}) does not divide year evenly ({delta})'
            )
        count = int(count)
    return start + np.arange(count + 1) * width


def downscale_balance_series(
    years: Iterable[int],
    balances: Iterable[Tuple[Number, Number, Number]] | np.ndarray | pd.DataFrame,
    balance_amplitude: Number = None,
    winter_fraction: Number = 0.5,
    winter_start: Iterable[int] = (10, 1),
    interval_width: datetime.timedelta = datetime.timedelta(days=1),
    interval_count: int = None,
    uniform_annual_balance: bool = False
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Downscale seasonal or annual mass balances to daily resolution.

    See `downscale_seasonal_balances` and `downscale_annual_balance`
    for the two strategies used.

    Arguments:
        years: End year of each hydrological year.
        balances: Series of winter, summer, and annual balance [(w, s, a), ...].
        balance_amplitude: Mean mass-balance amplitude. If not provided,
            it is computed from the seasonal balances in `bwsa_df`
            (see `calculate_balance_amplitude`).
        winter_fraction: Annual fraction of winter season.
        winter_start: Start date of winter as a month, day, and optional
            hour, minute, second, ... (see arguments to `datetime.datetime`).
            The start year of winter is given by column Year in `bwsa_df` - 1.
        interval_width: Width of each interval.
        interval_count: Number of intervals to divide each year into.
            If provided, interval_width is ignored.
        uniform_annual_balance: Whether annual balance should be applied
            uniformally over the year (True) rather than assume that all mass
            gain/loss occurs in winter/summer (False).

    Returns:
        Tuple of datetimes (start of each interval) and balances.

    Raises:
        ValueError: If winter_start is February 29.
        ValueError: If interval_width does not divide year evenly.
    """
    balances = np.array(balances, dtype=float)
    if balance_amplitude is None:
        balance_amplitudes = calculate_balance_amplitude(
            winter_balance=balances[:, 0],
            summer_balance=balances[:, 1]
        )
        balance_amplitude = balance_amplitudes.mean()
    results = []
    for year, balance in zip(years, balances):
        # Create series of every date in the hydrological year
        edges = generate_annual_datetime_sequence(
            start=datetime.datetime(year - 1, *winter_start),
            width=interval_width,
            count=interval_count
        )
        dates = edges[:-1]
        n_dates = dates.size
        # Downscale to daily resolution
        if np.isnan(balance[0]) or np.isnan(balance[1]):
            # Use annual balance
            scaled_balances = downscale_annual_balance(
                annual_balance=balance[2],
                balance_amplitude=balance_amplitude,
                winter_fraction=winter_fraction,
                temporal_resolution=n_dates,
                uniform_annual_balance=uniform_annual_balance
            )
        else:
            # Use seasonal balances
            scaled_balances = downscale_seasonal_balances(
                winter_balance=balance[0],
                summer_balance=balance[1],
                winter_fraction=winter_fraction,
                temporal_resolution=n_dates
            )
        results.append((dates, scaled_balances))
    return (
        np.concatenate([r[0] for r in results]),
        np.concatenate([r[1] for r in results])
    )
