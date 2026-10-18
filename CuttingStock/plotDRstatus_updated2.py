#!/usr/bin/env python3
"""
plot_dr_status_by_parameter_ph_buckets.py

Create grouped stacked DR outcome plots by T and by I, including optimality,
quality buckets, and separated failure categories.

The script searches a directory for files matching

    evalDR*.csv

and treats each file as one DR variant. Files named like

    evalDR_p_h.csv

are labelled as DR(p,h), for example

    evalDR_1_2.csv -> DR(1,2)

Expected DR CSV columns:
    instance;T;B;I;p;h;status;time_sec;obj;scenarios;iterations;final_bound

The p column is optional because p and h are inferred from the filename if the
name follows evalDR_p_h.csv. The h column is also optional for labelling if the
filename follows this convention.

Expected exact multistage CSV columns:
    InstanceName;Solved;SolutionTime;SolutionValue

Every DR row whose exact multistage optimum is solved and finite is classified
as one of:

    optimal
    (0%, LOW%]
    (LOW%, HIGH%]
    > HIGH%
    no DR exists
    timeout

Thus, exact-infeasible instances and instances without known exact optimum are
excluded from the denominator.

Usage:
    python3 plot_dr_status_by_parameter_ph_buckets.py DR_RESULTS_DIR MS_OPTIMUM_CSV OUTPUT_PREFIX

Examples:
    python3 plot_dr_status_by_parameter_ph_buckets.py results/dr ms_optimum.csv dr_status
    python3 plot_dr_status_by_parameter_ph_buckets.py results/dr ms_optimum.csv dr_status --format svg
    python3 plot_dr_status_by_parameter_ph_buckets.py results/dr ms_optimum.csv dr_status --thresholds 5 20
    python3 plot_dr_status_by_parameter_ph_buckets.py results/dr ms_optimum.csv dr_status --y-mode count

Outputs:
    OUTPUT_PREFIX_by_T.pdf
    OUTPUT_PREFIX_by_I.pdf
    OUTPUT_PREFIX_by_T.summary.csv
    OUTPUT_PREFIX_by_I.summary.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt


def format_threshold(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def build_categories(low: float, high: float) -> List[str]:
    return [
        "optimal",
        f"(0%, {format_threshold(low)}%]",
        f"({format_threshold(low)}%, {format_threshold(high)}%]",
        f"> {format_threshold(high)}%",
        "no DR exists",
        "timeout",
    ]


def build_category_colors(low: float, high: float) -> Dict[str, str]:
    return {
        "optimal": "#1a9850",                                      # green
        f"(0%, {format_threshold(low)}%]": "#91cf60",              # light green
        f"({format_threshold(low)}%, {format_threshold(high)}%]": "#fee08b",  # yellow
        f"> {format_threshold(high)}%": "#fc8d59",                 # orange
        "no DR exists": "#8073ac",                                 # purple
        "timeout": "#d73027",                                      # red
    }


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


def load_exact_feasible_optima(path: Path) -> Tuple[Dict[str, float], Dict[str, int]]:
    """
    Return exact optima for instances that are solved, feasible, finite, and
    have positive objective value.
    """
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


def infer_dr_label(path: Path, rows: List[Dict[str, str]]) -> Tuple[str, Tuple[int, int, str]]:
    """
    Infer label and sorting key.

    Preferred filename format:
        evalDR_p_h.csv

    Example:
        evalDR_1_2.csv -> $\\mathrm{DR}(1,2)$
    """
    stem = path.stem

    match = re.match(r"^evalDR[_-](\d+)[_-](?:h)?(\d+)$", stem, re.IGNORECASE)
    if match:
        p = int(match.group(1))
        h = int(match.group(2))
        return rf"$\mathrm{{DR}}({p},{h})$", (p, h, stem)

    if stem.lower().startswith("evaldr"):
        numbers = re.findall(r"\d+", stem[6:])
        if len(numbers) >= 2:
            p = int(numbers[0])
            h = int(numbers[1])
            return rf"$\mathrm{{DR}}({p},{h})$", (p, h, stem)

    p_values = sorted({row.get("p", row.get("P", "")).strip() for row in rows
                       if row.get("p", row.get("P", "")).strip()})
    h_values = sorted({row.get("h", row.get("H", "")).strip() for row in rows
                       if row.get("h", row.get("H", "")).strip()})

    if len(p_values) == 1 and len(h_values) == 1:
        p = parse_int(p_values[0])
        h = parse_int(h_values[0])
        if p is not None and h is not None:
            return rf"$\mathrm{{DR}}({p},{h})$", (p, h, stem)

    if len(h_values) == 1:
        h = parse_int(h_values[0])
        if h is not None:
            return rf"$\mathrm{{DR}}(?,{h})$", (10**8, h, stem)

    return stem, (10**9, 10**9, stem)


def classify_row(
    row: Dict[str, str],
    optima: Dict[str, float],
    optimal_tol: float,
    low: float,
    high: float,
) -> Optional[str]:
    """
    Return a category for a DR row, or None if the instance is not comparable
    because the exact optimum is unavailable or infeasible.
    """
    instance = row.get("instance", row.get("InstanceName", "")).strip()
    if instance not in optima:
        return None

    status = row.get("status", row.get("STATUS", "")).strip().upper()

    if status == "FINISHED":
        obj = parse_float(row.get("obj", row.get("OBJ", "")))
        if obj is None or not math.isfinite(obj):
            return "other / missing"

        z_ms = optima[instance]
        deviation = (obj - z_ms) / z_ms * 100.0

        # Tiny positive/negative values are numerical noise around zero.
        if abs(deviation) <= optimal_tol:
            return "optimal"

        # A certified DR objective below the exact optimum normally indicates
        # numerical or output inconsistency. Keep it in the best category, but
        # it should be inspected separately if it occurs.
        if deviation < -optimal_tol:
            return "optimal"

        if deviation <= low:
            return f"(0%, {format_threshold(low)}%]"

        if deviation <= high:
            return f"({format_threshold(low)}%, {format_threshold(high)}%]"

        return f"> {format_threshold(high)}%"

    if status == "INFEASIBLE":
        return "no DR exists"

    if status == "TIMELIMIT":
        return "timeout"

    return "other / missing"


def collect_counts(
    rows: List[Dict[str, str]],
    parameter: str,
    optima: Dict[str, float],
    optimal_tol: float,
    low: float,
    high: float,
) -> Tuple[Dict[int, Dict[str, int]], Dict[str, int]]:
    """
    Returns:
        parameter_value -> category -> count,
        diagnostics
    """
    result: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    diagnostics = {
        "rows": len(rows),
        "included_rows": 0,
        "excluded_no_exact_optimum": 0,
        "missing_parameter": 0,
    }

    for row in rows:
        value = parse_int(row.get(parameter, ""))
        if value is None:
            diagnostics["missing_parameter"] += 1
            continue

        category = classify_row(
            row,
            optima=optima,
            optimal_tol=optimal_tol,
            low=low,
            high=high,
        )

        if category is None:
            diagnostics["excluded_no_exact_optimum"] += 1
            continue

        result[value][category] += 1
        diagnostics["included_rows"] += 1

    return result, diagnostics


def make_plot(
    all_variant_counts: List[
        Tuple[str, Tuple[int, int, str], str, Dict[int, Dict[str, int]], Dict[str, int]]
    ],
    parameter: str,
    output_path: Path,
    y_mode: str,
    title: Optional[str],
    low: float,
    high: float,
) -> None:
    category_order = build_categories(low, high)
    category_colors = build_category_colors(low, high)

    parameter_values = sorted({
        value
        for _, _, _, counts_by_value, _ in all_variant_counts
        for value in counts_by_value.keys()
    })

    if not parameter_values:
        raise SystemExit(f"No valid comparable {parameter} values found in DR CSV files.")

    all_variant_counts = sorted(all_variant_counts, key=lambda x: x[1])

    labels = [label for label, _, _, _, _ in all_variant_counts]
    num_variants = len(all_variant_counts)
    group_centers = list(range(len(parameter_values)))

    group_width = 0.82
    bar_width = group_width / max(num_variants, 1)

    fig_width = max(6.8, 0.9 * len(parameter_values) + 0.6 * num_variants)
    plt.figure(figsize=(fig_width, 4.5))

    summary_rows = []

    for variant_idx, (label, _sort_key, filename, counts_by_value, _diagnostics) in enumerate(all_variant_counts):
        offset = -group_width / 2 + bar_width / 2 + variant_idx * bar_width
        x_positions = [center + offset for center in group_centers]

        bottoms = [0.0 for _ in parameter_values]

        for category in category_order:
            values = []

            for value in parameter_values:
                counts = counts_by_value.get(value, {})
                total = sum(counts.values())
                count = counts.get(category, 0)

                if y_mode == "percentage":
                    values.append(100.0 * count / total if total > 0 else 0.0)
                else:
                    values.append(count)

            plt.bar(
                x_positions,
                values,
                width=bar_width * 0.92,
                bottom=bottoms,
                label=category if variant_idx == 0 else None,
                color=category_colors.get(category, "#bdbdbd"),
            )

            bottoms = [b + v for b, v in zip(bottoms, values)]

        for value in parameter_values:
            counts = counts_by_value.get(value, {})
            total = sum(counts.values())
            row = {
                "parameter": parameter,
                "parameter_value": value,
                "variant": label,
                "file": filename,
                "total": total,
            }
            for category in category_order:
                row[category] = counts.get(category, 0)
            summary_rows.append(row)

    if parameter == "T":
        tick_labels = [rf"$T={v}$" for v in parameter_values]
    elif parameter == "I":
        tick_labels = [rf"$I={v}$" for v in parameter_values]
    else:
        tick_labels = [str(v) for v in parameter_values]

    plt.xticks(group_centers, tick_labels)
    plt.xlabel("")

    if y_mode == "percentage":
        plt.ylabel("Instances (%)")
        plt.ylim(0, 100)
    else:
        plt.ylabel("Number of instances")
        max_total = 0
        for _, _, _, counts_by_value, _ in all_variant_counts:
            for counts in counts_by_value.values():
                max_total = max(max_total, sum(counts.values()))
        plt.ylim(0, max_total)

    if title:
        plt.title(title)

    plt.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0.0,
        frameon=False,
        title="Outcome",
    )

    if num_variants <= 6:
        ymin, ymax = plt.ylim()
        y_text = ymin - 0.08 * (ymax - ymin)
        for variant_idx, (label, _, _, _, _) in enumerate(all_variant_counts):
            offset = -group_width / 2 + bar_width / 2 + variant_idx * bar_width
            for center in group_centers:
                plt.text(
                    center + offset,
                    y_text,
                    label,
                    ha="center",
                    va="top",
                    rotation=90,
                    fontsize=8,
                    clip_on=False,
                )
        plt.subplots_adjust(bottom=0.25)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight")
    print(f"Wrote {output_path}")

    summary_path = output_path.with_suffix(".summary.csv")
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["parameter", "parameter_value", "variant", "file", "total", *category_order]
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)

    #print(f"Wrote {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create grouped stacked DR outcome plots by T and I, including deviation buckets."
    )
    parser.add_argument("dr_results_dir", type=Path, help="Directory containing evalDR*.csv files.")
    parser.add_argument("ms_optimum_csv", type=Path, help="CSV with exact multistage results.")
    parser.add_argument(
        "output_prefix",
        type=Path,
        help="Output prefix. The script creates <prefix>_by_T.<format> and <prefix>_by_I.<format>.",
    )
    parser.add_argument(
        "--format",
        choices=["pdf", "svg", "eps", "png"],
        default="pdf",
        help="Output format. Use pdf/svg/eps for vector graphics. Default: pdf.",
    )
    parser.add_argument(
        "--y-mode",
        choices=["percentage", "count"],
        default="percentage",
        help="Plot percentages or absolute counts. Default: percentage.",
    )
    parser.add_argument(
        "--optimal-tol",
        type=float,
        default=1e-8,
        help="Tolerance in percentage points for treating a deviation as zero. Default: 1e-8.",
    )
    parser.add_argument(
        "--thresholds",
        nargs=2,
        type=float,
        default=[10.0, 30.0],
        metavar=("LOW", "HIGH"),
        help="Deviation thresholds in percent. Default: 10 30.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional plot title used for both plots.",
    )

    args = parser.parse_args()

    low, high = args.thresholds
    if low < 0 or high <= low:
        raise SystemExit("Thresholds must satisfy 0 <= LOW < HIGH.")

    if not args.dr_results_dir.is_dir():
        raise SystemExit(f"DR results directory does not exist: {args.dr_results_dir}")

    if not args.ms_optimum_csv.is_file():
        raise SystemExit(f"Exact multistage CSV does not exist: {args.ms_optimum_csv}")

    dr_files = sorted(args.dr_results_dir.glob("evalDR*.csv"))
    if not dr_files:
        raise SystemExit(f"No evalDR*.csv files found in {args.dr_results_dir}")

    optima, exact_counts = load_exact_feasible_optima(args.ms_optimum_csv)

    if not optima:
        raise SystemExit("No exact-solved feasible instances found in the optimum CSV.")

    #print(f"Loaded {len(optima)} exact-solved feasible optima.")
    #print(f"Exact CSV counts: {exact_counts}")
    #print()

    variants_T = []
    variants_I = []

    for dr_file in dr_files:
        rows = read_csv_dicts(dr_file)
        label, sort_key = infer_dr_label(dr_file, rows)

        counts_T, diag_T = collect_counts(
            rows,
            "T",
            optima=optima,
            optimal_tol=args.optimal_tol,
            low=low,
            high=high,
        )
        counts_I, diag_I = collect_counts(
            rows,
            "I",
            optima=optima,
            optimal_tol=args.optimal_tol,
            low=low,
            high=high,
        )

        variants_T.append((label, sort_key, dr_file.name, counts_T, diag_T))
        variants_I.append((label, sort_key, dr_file.name, counts_I, diag_I))

        #print(f"{dr_file.name}: label={label}, rows={len(rows)}")
        #print(f"  included comparable rows: {diag_T['included_rows']}")
        #print(f"  excluded because exact optimum unavailable/infeasible: {diag_T['excluded_no_exact_optimum']}")
        #if diag_T["missing_parameter"]:
        #    print(f"  rows missing T: {diag_T['missing_parameter']}")
        #if diag_I["missing_parameter"]:
        #    print(f"  rows missing I: {diag_I['missing_parameter']}")
        #print()

    prefix = args.output_prefix
    out_T = prefix.with_name(prefix.name + f"_by_T.{args.format}")
    out_I = prefix.with_name(prefix.name + f"_by_I.{args.format}")

    make_plot(
        variants_T,
        parameter="T",
        output_path=out_T,
        y_mode=args.y_mode,
        title=args.title,
        low=low,
        high=high,
    )

    make_plot(
        variants_I,
        parameter="I",
        output_path=out_I,
        y_mode=args.y_mode,
        title=args.title,
        low=low,
        high=high,
    )


if __name__ == "__main__":
    main()
