#!/usr/bin/env python3
"""
plot_reduced_stage_deviation_violins.py

Create a violin plot with embedded box plots for reduced-stage approaches
(e.g., 1-stage and 2-stage) after evaluation in the true multistage setting.

The script searches a directory for files matching

    eval*.csv

Each such file becomes one violin. The method label is extracted from the file
name by removing the leading "eval" and the ".csv" suffix. For example:

    eval1stage.csv      -> 1stage
    evalTwoStage.csv    -> TwoStage
    evalRO.csv          -> RO

Expected CSV structure for both reduced-stage files and the optimum file:

    InstanceName;Solved;SolutionTime;SolutionValue
    binPacking_10_5_2_200;1;6.72404;46.0

The deviation is computed as

    (evaluated_value - multistage_optimum) / multistage_optimum * 100.

Only instances with a solved, finite, positive multistage optimum are used as
reference instances. For each reduced-stage method, only rows with Solved=1 and
finite SolutionValue are included in the violin.

Usage:
    python3 plot_reduced_stage_deviation_violins.py EVAL_DIR OPTIMUM_CSV OUTPUT_FILE

Examples:
    python3 plot_reduced_stage_deviation_violins.py results/reduced exact.csv reduced_quality.pdf
    python3 plot_reduced_stage_deviation_violins.py results/reduced exact.csv reduced_quality.svg
    python3 plot_reduced_stage_deviation_violins.py results/reduced exact.csv reduced_quality.pdf --points

Outputs:
    OUTPUT_FILE
    OUTPUT_FILE.summary.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np


def clean_header(name: str) -> str:
    return name.strip().strip("\\").strip()


def sniff_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        return dialect.delimiter
    except csv.Error:
        return ";" if sample.count(";") >= sample.count(",") else ","


def read_csv_dicts(path: Path) -> List[Dict[str, str]]:
    delimiter = sniff_delimiter(path)

    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        if reader.fieldnames is None:
            return []

        original_fields = reader.fieldnames
        cleaned_fields = [clean_header(h) for h in original_fields]

        rows: List[Dict[str, str]] = []
        for raw in reader:
            row: Dict[str, str] = {}
            for old, new in zip(original_fields, cleaned_fields):
                value = raw.get(old, "")
                row[new] = value.strip() if value is not None else ""
            rows.append(row)

        return rows


def parse_float(value: str) -> Optional[float]:
    value = value.strip().replace(",", ".")
    if value == "":
        return None

    lower = value.lower()
    if lower in {"inf", "+inf", "infinity", "+infinity"}:
        return math.inf
    if lower in {"-inf", "-infinity"}:
        return -math.inf

    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value: str) -> Optional[int]:
    value = value.strip()
    if value == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def method_label_from_path(path: Path) -> str:
    stem = path.stem
    if stem.lower().startswith("eval"):
        label = stem[4:]
    else:
        label = stem

    label = label.strip("_- ")
    return label if label else stem


def natural_sort_key(text: str):
    parts = re.split(r"(\d+)", text)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def load_optima(path: Path) -> Tuple[Dict[str, float], Dict[str, int]]:
    rows = read_csv_dicts(path)

    optima: Dict[str, float] = {}
    counts = {
        "rows": len(rows),
        "included": 0,
        "unsolved": 0,
        "infeasible_or_nonfinite": 0,
        "nonpositive": 0,
        "missing_name": 0,
    }

    for row in rows:
        instance = row.get("InstanceName", "").strip()
        solved = parse_int(row.get("Solved", ""))
        value = parse_float(row.get("SolutionValue", ""))

        if not instance:
            counts["missing_name"] += 1
            continue

        if solved != 1:
            counts["unsolved"] += 1
            continue

        if value is None or not math.isfinite(value):
            counts["infeasible_or_nonfinite"] += 1
            continue

        if value <= 0:
            counts["nonpositive"] += 1
            continue

        optima[instance] = value
        counts["included"] += 1

    return optima, counts


def load_method_deviations(path: Path, optima: Dict[str, float]) -> Tuple[List[float], Dict[str, int]]:
    rows = read_csv_dicts(path)

    deviations: List[float] = []
    counts = {
        "rows": len(rows),
        "included": 0,
        "unsolved": 0,
        "missing_exact_optimum": 0,
        "nonfinite_value": 0,
        "missing_name": 0,
        "negative_deviation": 0,
    }

    for row in rows:
        instance = row.get("InstanceName", "").strip()
        solved = parse_int(row.get("Solved", ""))
        value = parse_float(row.get("SolutionValue", ""))

        if not instance:
            counts["missing_name"] += 1
            continue

        if instance not in optima:
            counts["missing_exact_optimum"] += 1
            continue

        if solved != 1:
            counts["unsolved"] += 1
            continue

        if value is None or not math.isfinite(value):
            counts["nonfinite_value"] += 1
            continue

        optimum = optima[instance]
        deviation = (value - optimum) / optimum * 100.0

        if deviation < 0:
            counts["negative_deviation"] += 1
            if abs(deviation) < 1e-8:
                deviation = 0.0

        deviations.append(deviation)
        counts["included"] += 1

    return deviations, counts


def percentile(values: List[float], q: float) -> Optional[float]:
    if not values:
        return None
    return float(np.percentile(np.array(values, dtype=float), q))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create violin + box plots of deviation from the multistage optimum."
    )
    parser.add_argument("eval_dir", type=Path, help="Directory containing eval*.csv files.")
    parser.add_argument("optimum_csv", type=Path, help="CSV containing exact multistage optima.")
    parser.add_argument(
        "output",
        type=Path,
        help="Output figure path, e.g. reduced_quality.pdf or reduced_quality.svg.",
    )
    parser.add_argument(
        "--points",
        action="store_true",
        help="Overlay individual instance deviations as jittered points.",
    )
    parser.add_argument(
        "--max-y",
        type=float,
        default=None,
        help="Optional upper limit for the y-axis in percent.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional plot title.",
    )

    args = parser.parse_args()

    if not args.eval_dir.is_dir():
        raise SystemExit(f"Evaluation directory does not exist: {args.eval_dir}")

    if not args.optimum_csv.is_file():
        raise SystemExit(f"Optimum CSV does not exist: {args.optimum_csv}")

    eval_files = sorted(
        [p for p in args.eval_dir.glob("eval*.csv") if p.resolve() != args.optimum_csv.resolve()],
        key=lambda p: natural_sort_key(method_label_from_path(p)),
    )

    if not eval_files:
        raise SystemExit(f"No eval*.csv files found in {args.eval_dir}")

    optima, optimum_counts = load_optima(args.optimum_csv)
    if not optima:
        raise SystemExit("No solved finite positive optima found in the optimum CSV.")

    labels: List[str] = []
    data: List[List[float]] = []
    summaries = []

    #print(f"Loaded {len(optima)} solved finite positive multistage optima.")
    #print(f"Optimum CSV counts: {optimum_counts}")
    #print()

    for path in eval_files:
        label = method_label_from_path(path)
        deviations, counts = load_method_deviations(path, optima)

        if not deviations:
            print(f"Warning: {path.name} has no comparable solved finite values and will be skipped.")
            continue

        labels.append(label)
        data.append(deviations)

        summary = {
            "file": path.name,
            "method": label,
            "n": len(deviations),
            "mean": float(np.mean(deviations)),
            "median": float(np.median(deviations)),
            "q1": percentile(deviations, 25),
            "q3": percentile(deviations, 75),
            "min": min(deviations),
            "max": max(deviations),
            "within_0_percent": sum(1 for x in deviations if abs(x) <= 1e-8),
            "within_10_percent": sum(1 for x in deviations if x <= 10.0),
            "within_30_percent": sum(1 for x in deviations if x <= 30.0),
            **counts,
        }
        summaries.append(summary)

#        print(f"{path.name}: label={label}")
#        print(f"  comparable solved values: {len(deviations)}")
#        print(f"  median deviation: {summary['median']:.4g}%")
#        print(f"  mean deviation: {summary['mean']:.4g}%")
#        print(f"  min/max deviation: {summary['min']:.4g}% / {summary['max']:.4g}%")
#        print(f"  skipped rows: unsolved={counts['unsolved']}, "
#              f"missing exact optimum={counts['missing_exact_optimum']}, "
#              f"nonfinite value={counts['nonfinite_value']}")
#        if counts["negative_deviation"]:
#            print(f"  warning: {counts['negative_deviation']} negative deviations observed")
#        print()

    if not data:
        raise SystemExit("No comparable data available for plotting.")

    positions = np.arange(1, len(data) + 1)

    fig_width = max(5.5, 1.0 * len(data) + 3.0)
    plt.figure(figsize=(fig_width, 4.3))
    ax = plt.gca()

    violin = ax.violinplot(
        data,
        positions=positions,
        showmeans=False,
        showmedians=False,
        showextrema=False,
    )

    for body in violin["bodies"]:
        body.set_alpha(0.6)

    ax.boxplot(
        data,
        positions=positions,
        widths=0.18,
        showfliers=False,
        patch_artist=False,
    )

    if args.points:
        rng = np.random.default_rng(12345)
        for pos, values in zip(positions, data):
            jitter = rng.uniform(-0.06, 0.06, size=len(values))
            ax.scatter(
                np.full(len(values), pos) + jitter,
                values,
                s=8,
                alpha=0.45,
                linewidths=0,
            )

    ax.axhline(0, linewidth=0.8, linestyle="--")
    ax.set_xticks(positions)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Deviation from multistage optimum (%)")

    if args.max_y is not None:
        ax.set_ylim(top=args.max_y)

    if args.title:
        ax.set_title(args.title)

    ax.grid(True, axis="y", linewidth=0.4, alpha=0.5)

    plt.tight_layout()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(args.output)
    print(f"Wrote {args.output}")

    summary_path = args.output.with_suffix(".summary.csv")
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "file",
            "method",
            "n",
            "mean",
            "median",
            "q1",
            "q3",
            "min",
            "max",
            "within_0_percent",
            "within_10_percent",
            "within_30_percent",
            "rows",
            "included",
            "unsolved",
            "missing_exact_optimum",
            "nonfinite_value",
            "missing_name",
            "negative_deviation",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for row in summaries:
            writer.writerow(row)

    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
