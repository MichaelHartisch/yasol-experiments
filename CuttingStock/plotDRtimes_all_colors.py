#!/usr/bin/env python3
"""
plot_dr_runtime_profile_styled.py

Create a runtime profile plot for decision-rule runs and the exact multistage
approach.

The script searches a directory for files matching

    evalDR*.csv

and adds one line per file. It also adds one line for the exact multistage
approach using the provided optimum CSV.

Decision-rule files are expected to be named like

    evalDR_p_h.csv

for example

    evalDR_1_3.csv

and are styled as follows:
    - color = p
    - line style = h

Thus, lines with the same p share a common color and are distinguished by
their line style according to h.

Expected DR CSV columns:
    instance;T;B;I;h;status;time_sec;obj;scenarios;iterations;final_bound

Expected exact multistage CSV columns:
    InstanceName;Solved;SolutionTime;SolutionValue

Default interpretation:
    - Exact approach: a run counts as solved if Solved == 1.
      This includes proven infeasibility if SolutionValue is "inf".
    - DR approach: a run counts as solved if status == FINISHED.
      TIMELIMIT and INFEASIBLE do not count as solved by default.
      Use --count-dr-infeasible if you want INFEASIBLE to count as a
      completed/certified DR outcome.

The denominator is the number of instances listed in the exact multistage CSV.
Thus, missing DR rows are treated as unsolved for that DR variant.

Usage:
    python3 plot_dr_runtime_profile_styled.py DR_RESULTS_DIR MS_OPTIMUM_CSV [OUTPUT_FILE]
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt


# Exact method style requested by the user.
EXACT_STYLE = {
    "color": "#0072B2",
    "linestyle": "-",
    "linewidth": 1.8,
}

# Base colors by p.
DR_BASE_COLORS = {
    1: "#E69F00",  # orange
    2: "#CC79A7",  # purple
    3: "#009E73",  # green
    4: "#D55E00",  # vermillion
    5: "#56B4E9",  # light blue
    6: "#999999",  # gray
}

# Line styles by h.
H_LINESTYLES = {
    1: "-",
    2: "--",
    3: "-.",
    4: ":",
    5: (0, (5, 1)),
    6: (0, (3, 1, 1, 1)),
}

FALLBACK_COLORS = [
    "#E69F00",
    "#CC79A7",
    "#009E73",
    "#D55E00",
    "#56B4E9",
    "#999999",
]


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


def infer_dr_parameters(path: Path, rows: List[Dict[str, str]]) -> Tuple[Optional[int], Optional[int]]:
    """
    Infer (p, h) from the filename evalDR_p_h.csv. Fall back to h from the data
    if necessary.
    """
    stem = path.stem
    match = re.search(r"_(\d+)_(\d+)$", stem)
    if match:
        return int(match.group(1)), int(match.group(2))

    h_values = sorted({
        parse_int(row.get("h", row.get("H", "")))
        for row in rows
        if parse_int(row.get("h", row.get("H", ""))) is not None
    })

    if len(h_values) == 1:
        return None, h_values[0]

    return None, None


def infer_dr_label(path: Path, rows: List[Dict[str, str]]) -> str:
    p, h = infer_dr_parameters(path, rows)
    if p is not None and h is not None:
        return rf"$\mathrm{{DR}}({p},{h})$"
    if h is not None:
        return rf"$\mathrm{{DR}}(?,{h})$"
    return path.stem


def infer_dr_style(path: Path, rows: List[Dict[str, str]]) -> Dict[str, object]:
    p, h = infer_dr_parameters(path, rows)

    if p is not None:
        color = DR_BASE_COLORS.get(p, FALLBACK_COLORS[(p - 1) % len(FALLBACK_COLORS)])
    else:
        color = "#666666"

    linestyle = H_LINESTYLES.get(h, "-")

    return {
        "color": color,
        "linestyle": linestyle,
        "linewidth": 1.5,
        "p": p,
        "h": h,
    }


def load_exact_times(
    path: Path,
    exclude_exact_infeasible: bool,
) -> Tuple[List[str], Dict[str, float], Dict[str, int]]:
    """
    Return:
      universe_instances, solved_times, counts

    The universe is all instances in the exact multistage CSV, except optionally
    proven-infeasible ones if --exclude-exact-infeasible is used.
    """
    rows = read_csv_dicts(path)

    universe: List[str] = []
    solved_times: Dict[str, float] = {}

    counts = {
        "rows": len(rows),
        "solved": 0,
        "unsolved": 0,
        "infeasible_exact": 0,
        "excluded_infeasible_exact": 0,
        "bad_time": 0,
    }

    for row in rows:
        instance = row.get("InstanceName", "").strip()
        if not instance:
            continue

        solved = parse_int(row.get("Solved", ""))
        sol_value = parse_float(row.get("SolutionValue", ""))
        sol_time = parse_float(row.get("SolutionTime", ""))

        is_exact_infeasible = sol_value is not None and math.isinf(sol_value)

        if exclude_exact_infeasible and is_exact_infeasible:
            counts["excluded_infeasible_exact"] += 1
            continue

        universe.append(instance)

        if is_exact_infeasible:
            counts["infeasible_exact"] += 1

        if solved == 1:
            if sol_time is not None and math.isfinite(sol_time) and sol_time >= 0:
                solved_times[instance] = sol_time
                counts["solved"] += 1
            else:
                counts["bad_time"] += 1
        else:
            counts["unsolved"] += 1

    return universe, solved_times, counts


def load_dr_times(
    path: Path,
    universe: Sequence[str],
    count_dr_infeasible: bool,
) -> Tuple[str, Dict[str, float], Dict[str, int], Dict[str, object]]:
    rows = read_csv_dicts(path)
    label = infer_dr_label(path, rows)
    style = infer_dr_style(path, rows)

    universe_set = set(universe)
    solved_times: Dict[str, float] = {}

    counts = {
        "rows": len(rows),
        "finished": 0,
        "infeasible": 0,
        "timelimit": 0,
        "unknown_status": 0,
        "outside_universe": 0,
        "bad_time": 0,
        "counted": 0,
    }

    solved_statuses = {"FINISHED"}
    if count_dr_infeasible:
        solved_statuses.add("INFEASIBLE")

    for row in rows:
        instance = row.get("instance", row.get("InstanceName", "")).strip()
        status = row.get("status", row.get("STATUS", "")).strip().upper()
        time_sec = parse_float(row.get("time_sec", row.get("TIME", "")))

        if status == "FINISHED":
            counts["finished"] += 1
        elif status == "INFEASIBLE":
            counts["infeasible"] += 1
        elif status == "TIMELIMIT":
            counts["timelimit"] += 1
        else:
            counts["unknown_status"] += 1

        if instance not in universe_set:
            counts["outside_universe"] += 1
            continue

        if status not in solved_statuses:
            continue

        if time_sec is None or not math.isfinite(time_sec) or time_sec < 0:
            counts["bad_time"] += 1
            continue

        solved_times[instance] = time_sec
        counts["counted"] += 1

    return label, solved_times, counts, style


def make_runtime_profile(
    times: Iterable[float],
    denominator: int,
    y_mode: str,
    max_time: Optional[float],
) -> Tuple[List[float], List[float]]:
    sorted_times = sorted(t for t in times if math.isfinite(t) and t >= 0)

    if max_time is None:
        right = max(sorted_times) if sorted_times else 1.0
    else:
        right = max_time

    xs = [0.0]
    ys = [0.0]

    count = 0
    for t in sorted_times:
        count += 1
        if t > right:
            continue

        y = count if y_mode == "count" else count / denominator * 100.0
        xs.append(t)
        ys.append(y)

    if xs[-1] < right:
        xs.append(right)
        ys.append(ys[-1])

    return xs, ys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a runtime profile plot for exact multistage and DR runs."
    )
    parser.add_argument("dr_results_dir", type=Path, help="Directory containing evalDR*.csv files.")
    parser.add_argument("ms_optimum_csv", type=Path, help="CSV with exact multistage results.")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=Path("dr_runtime_profile.pdf"),
        help="Output figure path, e.g. runtime_profile.pdf or runtime_profile.svg.",
    )
    parser.add_argument(
        "--y-mode",
        choices=["percentage", "count"],
        default="percentage",
        help="Plot percentage of instances or absolute count. Default: percentage.",
    )
    parser.add_argument(
        "--max-time",
        type=float,
        default=None,
        help="Maximum x-axis time in seconds. Default: maximum solved time among plotted methods.",
    )
    parser.add_argument(
        "--log-x",
        action="store_true",
        help="Use logarithmic x-axis. Times equal to zero are shifted to a small positive value.",
    )
    parser.add_argument(
        "--count-dr-infeasible",
        action="store_true",
        help="Count DR status INFEASIBLE as a completed/certified outcome in addition to FINISHED.",
    )
    parser.add_argument(
        "--exclude-exact-infeasible",
        action="store_true",
        help="Exclude exact instances with SolutionValue=inf from the denominator.",
    )
    parser.add_argument(
        "--exact-label",
        default="Yasol",
        help="Legend label for the exact multistage approach.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional plot title.",
    )
    parser.add_argument(
        "--legend-location",
        default="best",
        help="Legend location passed to matplotlib. Default: best.",
    )

    args = parser.parse_args()

    if not args.dr_results_dir.is_dir():
        raise SystemExit(f"DR results directory does not exist: {args.dr_results_dir}")

    if not args.ms_optimum_csv.is_file():
        raise SystemExit(f"Multistage optimum CSV does not exist: {args.ms_optimum_csv}")

    dr_files = sorted(args.dr_results_dir.glob("evalDR*.csv"))
    if not dr_files:
        raise SystemExit(f"No evalDR*.csv files found in {args.dr_results_dir}")

    universe, exact_times, exact_counts = load_exact_times(
        args.ms_optimum_csv,
        exclude_exact_infeasible=args.exclude_exact_infeasible,
    )
    denominator = len(universe)

    if denominator == 0:
        raise SystemExit("No instances available in the denominator.")

    all_plotted_times: List[float] = []

    dr_data = []
    for dr_file in dr_files:
        label, times, counts, style = load_dr_times(
            dr_file,
            universe,
            count_dr_infeasible=args.count_dr_infeasible,
        )
        dr_data.append((dr_file.name, label, times, counts, style))
        all_plotted_times.extend(times.values())

    all_plotted_times.extend(exact_times.values())

    # Stable order: by p, then by h, then by filename
    dr_data.sort(key=lambda item: (
        item[4].get("p") if item[4].get("p") is not None else 10**9,
        item[4].get("h") if item[4].get("h") is not None else 10**9,
        item[0]
    ))

    max_time = args.max_time
    if max_time is None and all_plotted_times:
        max_time = max(all_plotted_times)
    if max_time is None or max_time <= 0:
        max_time = 1.0

    #print(f"Denominator: {denominator} instances")
    print(f"Exact multistage solved: {len(exact_times)} / {denominator}")
    #print(f"Exact CSV counts: {exact_counts}")
    #print()

    plt.figure(figsize=(6.2, 4.0))

    summary_rows = []
    exact_xs, exact_ys = make_runtime_profile(
        exact_times.values(),
        denominator=denominator,
        y_mode=args.y_mode,
        max_time=max_time,
    )
    plt.step(
        exact_xs,
        exact_ys,
        where="post",
        label=args.exact_label,
        color=EXACT_STYLE["color"],
        linestyle=EXACT_STYLE["linestyle"],
        linewidth=EXACT_STYLE["linewidth"],
    )

    for filename, label, times, counts, style in dr_data:
        xs, ys = make_runtime_profile(
            times.values(),
            denominator=denominator,
            y_mode=args.y_mode,
            max_time=max_time,
        )
        plt.step(
            xs,
            ys,
            where="post",
            label=label,
            color=style["color"],
            linestyle=style["linestyle"],
            linewidth=style["linewidth"],
        )

        coverage = len(times) / denominator * 100.0
        summary_rows.append((
            filename,
            label,
            denominator,
            len(times),
            coverage,
            counts["finished"],
            counts["infeasible"],
            counts["timelimit"],
            counts["unknown_status"],
            style.get("p"),
            style.get("h"),
            style.get("color"),
            style.get("linestyle"),
        ))

        #print(f"{filename}:")
        #print(f"  label: {label}")
        #print(f"  style: p={style.get('p')}, h={style.get('h')}, color={style.get('color')}, linestyle={style.get('linestyle')}")
        #print(f"  counted as solved/completed: {len(times)} / {denominator} ({coverage:.2f}%)")
        #print(f"  statuses in file: FINISHED={counts['finished']}, "
        #      f"INFEASIBLE={counts['infeasible']}, TIMELIMIT={counts['timelimit']}, "
        #      f"UNKNOWN={counts['unknown_status']}")
        #if counts["outside_universe"]:
        #    print(f"  rows skipped because instance was not in exact CSV: {counts['outside_universe']}")
        #if counts["bad_time"]:
        #    print(f"  rows skipped because time was missing/nonfinite: {counts['bad_time']}")
        #print()

    summary_rows.append((
        "exact",
        args.exact_label,
        denominator,
        len(exact_times),
        len(exact_times) / denominator * 100.0,
        "",
        "",
        "",
        "",
        "",
        "",
        EXACT_STYLE["color"],
        EXACT_STYLE["linestyle"],
    ))

    plt.xlabel("Runtime (seconds)")
    if args.y_mode == "count":
        plt.ylabel("Solved instances")
        plt.ylim(bottom=0, top=denominator)
    else:
        plt.ylabel("Solved instances (%)")
        plt.ylim(0, 102)

    plt.xlim(left=0 if not args.log_x else None, right=max_time)

    if args.log_x:
        positive_times = [t for t in all_plotted_times if t > 0]
        left = min(positive_times) * 0.8 if positive_times else 1e-3
        plt.xscale("log")
        plt.xlim(left=left, right=max_time)

    if args.title:
        plt.title(args.title)

    plt.grid(True, linewidth=0.4, alpha=0.5)
    plt.legend(
        loc=args.legend_location,
        frameon=True,
        facecolor="white",
        edgecolor="black",
        framealpha=1.0,
    )
    plt.tight_layout()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(args.output)
    print(f"Wrote {args.output}")

    summary_path = args.output.with_suffix(".summary.csv")
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "file",
            "label",
            "denominator",
            "solved_or_completed",
            "coverage_percent",
            "finished",
            "infeasible",
            "timelimit",
            "unknown_status",
            "p",
            "h",
            "color",
            "linestyle",
        ])
        for row in summary_rows:
            writer.writerow(row)

    #print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
