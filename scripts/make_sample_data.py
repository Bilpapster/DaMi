"""Generate the sample "database tables" in data/.

You do not need to run this script: the CSV files are already in the repository.
It is here so that you can see how the data was made, and use it as a starting
point when you create your own datasets.

    python scripts/make_sample_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
rng = np.random.default_rng(2026)


def blob(n, center, scale):
    return rng.normal(loc=center, scale=scale, size=(n, len(center)))


def customers() -> pd.DataFrame:
    """Customer segments: age (years) and annual income (EUR)."""
    parts = [
        blob(2500, [24, 18_000], [3, 4_000]),     # students and first jobs
        blob(1800, [31, 72_000], [3, 9_000]),     # young professionals
        blob(2700, [45, 42_000], [5, 7_000]),     # middle-income families
        blob(1500, [52, 125_000], [5, 14_000]),   # senior managers
        blob(1500, [70, 26_000], [4, 5_000]),     # retired
    ]
    data = np.vstack(parts)
    data = np.vstack([data, [[19, 950_000], [83, 610_000], [27, 480_000]]])  # a few very rich outliers
    df = pd.DataFrame(data, columns=["age", "annual_income_eur"])
    df["age"] = df["age"].clip(18, 90).round(0).astype(int)
    df["annual_income_eur"] = df["annual_income_eur"].clip(lower=6_000).round(-1)
    return df.sample(frac=1, random_state=1).reset_index(drop=True)


def products() -> pd.DataFrame:
    """Two interleaving half-moons (non-convex groups): price (EUR) and monthly sales (units)."""
    n = 2400
    t = rng.uniform(0, np.pi, n)
    moon_a = np.c_[np.cos(t), np.sin(t)]
    moon_b = np.c_[1 - np.cos(t), 0.5 - np.sin(t)]
    data = np.vstack([moon_a, moon_b]) + rng.normal(0, 0.06, size=(2 * n, 2))
    noise = rng.uniform([-1.2, -0.8], [2.2, 1.3], size=(200, 2))
    data = np.vstack([data, noise])
    df = pd.DataFrame(
        {
            "price_eur": (data[:, 0] + 1.5) * 120 + 5,
            "monthly_sales_units": (data[:, 1] + 1.0) * 700,
        }
    ).round(2)
    return df.sample(frac=1, random_state=2).reset_index(drop=True)


def marketing() -> pd.DataFrame:
    """Campaigns with NO real segments: one correlated cloud of reach and engagement."""
    n = 20_000
    reach = rng.lognormal(mean=10, sigma=0.6, size=n)
    engagement = np.clip(0.02 + 0.015 * np.log(reach / reach.mean()) + rng.normal(0, 0.01, n), 0.001, None)
    return pd.DataFrame({"reach_people": reach.round(0), "engagement_rate": engagement.round(4)})


def sensors() -> pd.DataFrame:
    """Factory press sensors: three operating states, plus a small 'sabotaged press' group and spikes."""
    parts = [
        blob(70_000, [22, 101], [1.2, 0.8]),     # idle
        blob(90_000, [61, 180], [2.5, 4.0]),     # normal production
        blob(39_400, [84, 238], [2.0, 5.0]),     # high load
        blob(180, [47, 262], [0.6, 1.0]),        # the sabotaged press: odd combination, tight group
    ]
    spikes = np.c_[rng.uniform(10, 110, 420), rng.uniform(80, 320, 420)]
    data = np.vstack(parts + [spikes])
    df = pd.DataFrame(data, columns=["temperature_c", "pressure_kpa"]).round(2)
    return df.sample(frac=1, random_state=3).reset_index(drop=True)


def transactions() -> pd.DataFrame:
    """Card transactions: amount (EUR) and transactions per day of the card. Hides a small fraud ring."""
    n = 500_000
    groups = [
        (0.55, 3.2, 0.5, 2.0, 0.6),   # everyday shopping: log-amount mean/sd, tx/day mean/sd
        (0.30, 4.6, 0.4, 0.8, 0.3),   # bigger monthly purchases
        (0.15, 5.6, 0.5, 6.0, 1.5),   # business cards
    ]
    rows = []
    for share, mu, sd, f_mu, f_sd in groups:
        k = int(n * share)
        amounts = rng.lognormal(mu, sd, k)
        freq = np.clip(rng.normal(f_mu, f_sd, k), 0.05, None)
        rows.append(np.c_[amounts, freq])
    data = np.vstack(rows)[: n - 40]
    ring = np.c_[rng.normal(4_850, 60, 40), rng.normal(34, 1.5, 40)]   # the fraud ring
    data = np.vstack([data, ring])
    df = pd.DataFrame(data, columns=["amount_eur", "tx_per_day"]).round(2)
    return df.sample(frac=1, random_state=4).reset_index(drop=True)


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    for name, make in {
        "customers": customers,
        "products": products,
        "marketing": marketing,
        "sensors": sensors,
        "transactions": transactions,
    }.items():
        df = make()
        df.to_csv(DATA_DIR / f"{name}.csv", index=False)
        print(f"{name:13s} {len(df):>7d} rows -> data/{name}.csv")


if __name__ == "__main__":
    main()
