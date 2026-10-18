#!/usr/bin/env python3
import argparse
import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt


DEFAULT_STYLES = [
    {
        "color": "#0072B2",   # blue
        "linestyle": "-",
        "marker": "o",
    },
    {
        "color": "#56B4E9",   # light blue
        "linestyle": "--",
        "marker": "s",
    },
    {
        "color": "#E69F00",   # orange
        "linestyle": "-.",
        "marker": "^",
    },
    {
        "color": "#CC79A7",   # purple
        "linestyle": ":",
        "marker": "D",
    },
    {
        "color": "#009E73",   # green
        "linestyle": "-",
        "marker": "v",
    },
    {
        "color": "#D55E00",   # vermillion
        "linestyle": "--",
        "marker": "P",
    },
]


def read_solver_map(path):
    """
    Read solver prefixes, display labels, and optional plotting styles from a
    semicolon-separated file.

    Backward-compatible minimal format:
        csv_prefix;display_label

    Extended format:
        csv_prefix;display_label;color;linestyle;marker

    Empty style fields are allowed. Empty lines and lines beginning with # are
    ignored.

    Examples:
        SolverA;Our method;#0072B2;-;o
        SolverB;Our method variant;#56B4E9;--;s
        SingleStage;Single-stage;#E69F00;-.;^
        TwoStage;Two-stage;#CC79A7;:;D

    The use of both color and line/marker style makes the plot easier to
    distinguish for colorblind readers and in grayscale print.
    """
    solvers = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split(";")]

            if len(parts) not in {2, 3, 4, 5}:
                raise ValueError(
                    f"{path}:{line_number}: expected "
                    "'csv_prefix;display_label' or "
                    "'csv_prefix;display_label;color;linestyle;marker'"
                )

            prefix = parts[0]
            label = parts[1]

            if not prefix:
                raise ValueError(
                    f"{path}:{line_number}: empty CSV prefix"
                )

            if not label:
                raise ValueError(
                    f"{path}:{line_number}: empty display label"
                )

            style = DEFAULT_STYLES[len(solvers) % len(DEFAULT_STYLES)].copy()

            if len(parts) >= 3 and parts[2]:
                style["color"] = parts[2]

            if len(parts) >= 4 and parts[3]:
                style["linestyle"] = parts[3]

            if len(parts) >= 5 and parts[4]:
                style["marker"] = parts[4]

            solvers.append(
                {
                    "prefix": prefix,
                    "label": label,
                    "color": style["color"],
                    "linestyle": style["linestyle"],
                   # "marker": style["marker"],
                }
            )

    if not solvers:
        raise ValueError(
            f"No solver definitions found in {path}"
        )

    return solvers


def read_solver_data(folder, solver_prefix):
    """
    Read all CSV files whose filenames start with solver_prefix.

    All instances with Solved == 1 are included, regardless of runtime.

    Returns:
        solved_times
        total_instances
        processed CSV files
        warnings
    """
    csv_files = sorted(
        p for p in folder.iterdir()
        if p.is_file()
        and p.suffix.lower() == ".csv"
        and p.name.startswith(solver_prefix)
        and "_analysis_" not in p.name
    )

    if not csv_files:
        raise RuntimeError(
            f"No CSV files starting with '{solver_prefix}' "
            f"found in {folder}"
        )

    solved_times = []
    total_instances = 0
    warnings = []

    seen_instances = set()

    required_columns = {
        "InstanceName",
        "Solved",
        "SolutionTime",
    }

    for csv_file in csv_files:
        with csv_file.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:
            reader = csv.DictReader(f, delimiter=";")

            if reader.fieldnames is None:
                warnings.append(
                    f"{csv_file.name}: file has no header"
                )
                continue

            missing = required_columns - set(reader.fieldnames)

            if missing:
                warnings.append(
                    f"{csv_file.name}: missing columns: "
                    + ", ".join(sorted(missing))
                )
                continue

            for line_number, row in enumerate(reader, start=2):
                instance = row["InstanceName"].strip()

                if not instance:
                    warnings.append(
                        f"{csv_file.name}:{line_number}: "
                        "empty InstanceName"
                    )
                    continue

                if instance in seen_instances:
                    warnings.append(
                        f"{solver_prefix}: instance '{instance}' "
                        "occurs more than once"
                    )

                seen_instances.add(instance)
                total_instances += 1

                try:
                    solved = int(row["Solved"])
                    solution_time = float(row["SolutionTime"])
                except (ValueError, TypeError):
                    warnings.append(
                        f"{csv_file.name}:{line_number}: "
                        "invalid Solved or SolutionTime value"
                    )
                    continue

                if solved == 1:
                    if solution_time < 0:
                        warnings.append(
                            f"{csv_file.name}:{line_number}: "
                            f"negative runtime for {instance}"
                        )
                        continue

                    solved_times.append(solution_time)

    solved_times.sort()

    return solved_times, total_instances, csv_files, warnings


def make_cactus_plot(
    solver_data,
    output_file,
    time_limit,
    percentage=True,
    log_x=True,
    y_max=None,
):
    fig, ax = plt.subplots(figsize=(7.2, 4.8))

    for solver in solver_data:
        times = solver["times"]
        total = solver["total"]
        label = solver["label"]

        if not times:
            print(
                f"WARNING: {label} solved no instances",
                file=sys.stderr,
            )
            continue

        if percentage:
            y = [
                100.0 * i / total
                for i in range(1, len(times) + 1)
            ]
        else:
            y = list(range(1, len(times) + 1))

        plot_times = list(times)
        plot_y = list(y)

        plot_times.append(time_limit)
        plot_y.append(plot_y[-1])
        # Do not place a marker at every solved instance if the curve is long.
        # marker_every = max(1, len(times) // 12)

        ax.step(
            plot_times,
            plot_y,
            where="post",
            label=label,
            linewidth=1.8,
            color=solver.get("color"),
            linestyle=solver.get("linestyle", "-"),
           # marker=solver.get("marker", None),
           # markersize=4.5,
           # markevery=marker_every,
        )

    all_positive_times = [
        t
        for solver in solver_data
        for t in solver["times"]
        if t > 0
    ]

    if not all_positive_times:
        print(
            "ERROR: no positive runtimes found.",
            file=sys.stderr,
        )
        return

    minimum_time = min(all_positive_times)
    maximum_time = max(all_positive_times)

    if log_x:
        ax.set_xscale("log")
        ax.set_xlim(
            max(minimum_time * 0.8, 1e-6),
            time_limit
            #maximum_time * 1.1,
        )
    else:
        ax.set_xlim(
            0,
            time_limit
            #maximum_time * 1.05,
        )

    #
    # Mark the nominal benchmark time limit.
    #
    if minimum_time <= time_limit <= maximum_time * 1.1:
        ax.axvline(
            180,
            linestyle="--",
            linewidth=1.0,
            color="black",
            alpha=0.7,
        )

    ax.set_xlabel("Runtime (seconds)")

    if percentage:
        ax.set_ylabel("Solved instances (%)")

        if y_max is not None:
            ax.set_ylim(0, y_max)
        else:
            max_percentage = max(
                100.0 * len(solver["times"]) / solver["total"]
                for solver in solver_data
                if solver["total"] > 0
            )

            ax.set_ylim(
                0,
                min(100.0, max_percentage * 1.15)
            )
    else:
        ax.set_ylabel("Number of instances solved")
        ax.set_ylim(bottom=0)

    ax.grid(
        True,
        which="both",
        linestyle=":",
        linewidth=0.6,
        alpha=0.7,
    )

    ax.legend(frameon=False)

    fig.tight_layout()

    fig.savefig(
        output_file,
        bbox_inches="tight",
    )

    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Create a cactus plot from solver-result CSV files."
        )
    )

    parser.add_argument(
        "folder",
        type=Path,
        help="Folder containing the CSV result files",
    )

    parser.add_argument(
        "solver_map",
        type=Path,
        help=(
            "Semicolon-separated file mapping CSV prefixes "
            "to display labels and optional styles"
        ),
    )

    parser.add_argument(
        "--time-limit",
        type=float,
        default=1800.0,
        help=(
            "Nominal time limit in seconds. "
            "Used only as a reference line in the plot "
            "(default: 180)"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Output figure. Extension determines format. "
            "Default: cactus_plot.pdf"
        ),
    )

    parser.add_argument(
        "--counts",
        action="store_true",
        help=(
            "Plot absolute numbers instead of percentages"
        ),
    )

    parser.add_argument(
        "--linear-x",
        action="store_true",
        help="Use a linear instead of logarithmic time axis",
    )

    parser.add_argument(
        "--y-max",
        type=float,
        default=None,
        help=(
            "Optional upper limit for the y-axis. "
            "For example: --y-max 35"
        ),
    )

    args = parser.parse_args()

    if not args.folder.is_dir():
        parser.error(
            f"{args.folder} does not exist or is not a directory"
        )

    if not args.solver_map.is_file():
        parser.error(
            f"{args.solver_map} does not exist or is not a file"
        )

    if args.output is None:
        output_file = args.folder / "cactus_plot.pdf"
    elif args.output.is_absolute():
        output_file = args.output
    else:
        output_file = args.folder / args.output

    try:
        solver_definitions = read_solver_map(
            args.solver_map
        )
    except ValueError as e:
        parser.error(str(e))

    solver_data = []
    all_warnings = []

    for solver in solver_definitions:
        prefix = solver["prefix"]
        label = solver["label"]

        try:
            times, total, files, warnings = read_solver_data(
                args.folder,
                prefix,
            )
        except RuntimeError as e:
            print(
                f"ERROR: {e}",
                file=sys.stderr,
            )
            return 1

        solver_data.append(
            {
                "prefix": prefix,
                "label": label,
                "times": times,
                "total": total,
                "color": solver["color"],
                "linestyle": solver["linestyle"],
                #"marker": solver["marker"],
            }
        )

        all_warnings.extend(warnings)

        solved_overall = len(times)

        within_limit = sum(
            1 for t in times
            if t <= args.time_limit
        )

        solved_percentage = (
            100.0 * solved_overall / total
            if total > 0
            else 0.0
        )

        within_percentage = (
            100.0 * within_limit / total
            if total > 0
            else 0.0
        )

        print(
            f"{label}: "
            f"{len(files)} CSV files, "
            f"{total} instances, "
            f"{solved_overall} solved overall "
            f"({solved_percentage:.1f}%), "
            f"{within_limit} within "
            f"{args.time_limit:g}s "
            f"({within_percentage:.1f}%)"
        )

    totals = {
        solver["total"]
        for solver in solver_data
    }

    if len(totals) > 1:
        print(
            "WARNING: the solvers do not contain the same "
            "number of instances.",
            file=sys.stderr,
        )

    make_cactus_plot(
        solver_data,
        output_file,
        args.time_limit,
        percentage=not args.counts,
        log_x=not args.linear_x,
        y_max=args.y_max,
    )

    print()
    print(f"Cactus plot written to: {output_file}")

    if all_warnings:
        warning_file = (
            args.folder / "cactus_plot_warnings.txt"
        )

        with warning_file.open(
            "w",
            encoding="utf-8"
        ) as f:
            for warning in all_warnings:
                f.write(warning + "\n")

        print(
            f"Warnings written to: {warning_file}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
