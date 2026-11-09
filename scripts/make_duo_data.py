"""Generate the Step 5 table: factory sensors with real anomalies AND data-quality problems.

    python scripts/make_duo_data.py                         # the practice table in data/duo/
    python scripts/make_duo_data.py --seed 123 --out /tmp/x  # another table (instructors: a held-out one)

Writes <out>/factory_line.csv (what agents may look at) and <out>/factory_line.labels.csv
(row_id -> is_anomaly; only the evaluator reads it).
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

MACHINES = {"M1": (60, 190), "M2": (62, 196), "M3": (58, 186), "M4": (61, 193)}  # (temperature_c, pressure_kpa)


def make(seed: int, rows_per_machine: int = 5000) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    parts = []
    for machine, (t0, p0) in MACHINES.items():
        n = rows_per_machine
        load = np.clip(rng.normal(0.7, 0.06, n), 0.3, 1.0)                  # how hard the machine works
        pressure = p0 * (0.8 + 0.3 * load) + rng.normal(0, 3, n)
        power = 40 * load + 0.05 * pressure + rng.normal(0, 1.2, n)
        temperature = t0 + 18 * load + rng.normal(0, 1.5, n)
        vibration = 2.0 + 3.0 * load + rng.normal(0, 0.25, n)
        parts.append(pd.DataFrame({"machine": machine, "minute": np.arange(n), "temperature_c": temperature,
                                   "pressure_kpa": pressure, "vibration_mm_s": vibration, "power_kw": power}))
    df = pd.concat(parts, ignore_index=True)

    # Real anomalies (about 1%): what the detector should find.
    is_anomaly = np.zeros(len(df), dtype=bool)
    idx = rng.choice(len(df), int(0.01 * len(df)), replace=False)
    kinds = rng.integers(0, 3, len(idx))
    for i, kind in zip(idx, kinds):
        if kind == 0:   # pressure spike, temperature normal
            df.loc[i, "pressure_kpa"] *= rng.uniform(1.6, 2.0)
        elif kind == 1:  # vibration burst
            df.loc[i, "vibration_mm_s"] += rng.uniform(7.0, 10.0)
        else:            # power drop while pressure is high: a failing pump
            df.loc[i, "power_kw"] *= rng.uniform(0.2, 0.35)
    is_anomaly[idx] = True
    df.insert(0, "row_id", np.arange(len(df)))
    labels = pd.DataFrame({"row_id": df["row_id"], "is_anomaly": is_anomaly.astype(int)})

    # Data-quality problems (they are NOT anomalies; a good cleaning plan repairs them).
    m3 = df["machine"] == "M3"
    df.loc[m3, "temperature_c"] = df.loc[m3, "temperature_c"] * 9 / 5 + 32          # M3 logs Fahrenheit
    m2_window = (df["machine"] == "M2") & df["minute"].between(1500, 1559)
    df.loc[m2_window, "pressure_kpa"] /= 100                                        # M2 logged bar for a while
    m4_stuck = (df["machine"] == "M4") & df["minute"].between(3000, 3059)
    df.loc[m4_stuck, "vibration_mm_s"] = 0.0                                        # stuck vibration sensor
    swap = rng.choice(len(df), 60, replace=False)                                     # columns swapped at entry
    df.loc[swap, ["temperature_c", "pressure_kpa"]] = df.loc[swap, ["pressure_kpa", "temperature_c"]].to_numpy()
    missing = rng.choice(len(df), int(0.03 * len(df)), replace=False)               # missing values
    df.loc[missing, "power_kw"] = np.nan
    dupes = df.sample(frac=0.04, random_state=seed)                                  # duplicated rows
    df = pd.concat([df, dupes]).sample(frac=1, random_state=seed).reset_index(drop=True)

    df[["temperature_c", "pressure_kpa", "vibration_mm_s", "power_kw"]] = df[
        ["temperature_c", "pressure_kpa", "vibration_mm_s", "power_kw"]].round(2)
    return df, labels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "duo")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    df, labels = make(args.seed)
    df.to_csv(args.out / "factory_line.csv", index=False)
    labels.to_csv(args.out / "factory_line.labels.csv", index=False)
    print(f"{len(df)} rows ({labels.is_anomaly.sum()} real anomalies) -> {args.out}")


if __name__ == "__main__":
    main()
