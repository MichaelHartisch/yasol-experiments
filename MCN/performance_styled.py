#!/usr/bin/env python3
from pathlib import Path
import argparse
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


DEFAULT_METHODS = [
    "tree",
    "rndgraph",
    "public_repository",
]


def read_solver_map(path):
    """
    Read solver order, display labels, and plotting styles from a
    semicolon-separated file.

    Format:
        solver_column;display_label;color;linestyle

    The last two fields are optional:
        solver_column;display_label
        solver_column;display_label;color
        solver_column;display_label;color;linestyle

    The first field must match a solver column in the *_times.csv and
    *_solved.csv files. The second field is used verbatim as the legend label,
    so LaTeX/mathtext labels such as Solver$_b$ are supported.

    Example:
        Solver_a;Solver$_a$;#0072B2;-
        Solver_b;Solver$_b$;#56B4E9;--
        SingleStage;Single-stage;#E69F00;-.
        TwoStage;Two-stage;#CC79A7;:
    """
    solvers = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = [part.strip() for part in line.split(";")]

            if len(parts) not in {2, 3, 4}:
                raise ValueError(
                    f"{path}:{line_number}: expected "
                    "'solver_column;display_label[;color[;linestyle]]'"
                )

            solver = parts[0]
            label = parts[1]
            color = parts[2] if len(parts) >= 3 and parts[2] else None
            linestyle = parts[3] if len(parts) >= 4 and parts[3] else None

            if not solver:
                raise ValueError(f"{path}:{line_number}: empty solver column")
            if not label:
                raise ValueError(f"{path}:{line_number}: empty display label")

            solvers.append(
                {
                    "solver": solver,
                    "label": label,
                    "color": color,
                    "linestyle": linestyle,
                }
            )

    if not solvers:
        raise ValueError(f"No solver definitions found in {path}")

    return solvers


def parse_methods(value):
    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def get_solvers_for_method(times, solved, solver_definitions, method_name, strict):
    """
    Return solver definitions in exactly the order given by the solver-map file.

    A solver is used only if it appears as a column in both the times and solved
    files. In strict mode, missing solvers raise an error. Otherwise, they are
    skipped with a warning.
    """
    time_columns = set(times.columns)
    solved_columns = set(solved.columns)

    selected = []

    for solver_def in solver_definitions:
        solver = solver_def["solver"]

        if solver not in time_columns or solver not in solved_columns:
            message = (
                f"{method_name}: solver '{solver}' from solver map is missing "
                f"in {'times' if solver not in time_columns else 'solved'} file"
            )

            if strict:
                raise ValueError(message)

            print(f"WARNING: {message}; skipping.", file=sys.stderr)
            continue

        selected.append(solver_def)

    if not selected:
        raise ValueError(
            f"{method_name}: none of the solvers from the solver map were found "
            "in both input files."
        )

    return selected


def main():
    parser = argparse.ArgumentParser(
        description="Create performance profiles from *_times.csv and *_solved.csv files."
    )

    parser.add_argument(
        "testname",
        help="Test name. Data are read from Tests/<testname>/eval.",
    )

    parser.add_argument(
        "solver_map",
        type=Path,
        help=(
            "Semicolon-separated solver style file. "
            "Rows determine solver order, legend labels, colors, and line styles."
        ),
    )

    parser.add_argument(
        "--methods",
        default=",".join(DEFAULT_METHODS),
        help=(
            "Comma-separated list of method prefixes. "
            f"Default: {','.join(DEFAULT_METHODS)}"
        ),
    )

    parser.add_argument(
        "--strict-solvers",
        action="store_true",
        help=(
            "Require every solver from the solver map to appear in every "
            "*_times.csv and *_solved.csv file."
        ),
    )

    parser.add_argument(
        "--no-title",
        action="store_true",
        help="Do not add a title to the figures.",
    )

    parser.add_argument(
        "--output-format",
        default="pdf",
        choices=["pdf", "svg", "eps", "png"],
        help="Output format. Use pdf/svg/eps for vector graphics. Default: pdf.",
    )

    args = parser.parse_args()

    folder = Path("Tests") / args.testname / "eval"
    folder_home = Path(".") / args.testname / "eval"

    if not folder.is_dir():
        raise ValueError(f"Folder does not exist: {folder}")

    if not args.solver_map.is_file():
        raise ValueError(f"Solver map does not exist: {args.solver_map}")

    solver_definitions = read_solver_map(args.solver_map)
    methods = parse_methods(args.methods)

    for method in methods:
        times_file = folder / f"{method}_times.csv"
        solved_file = folder / f"{method}_solved.csv"

        if not times_file.is_file():
            print(f"Missing file: {times_file}")
            continue

        if not solved_file.is_file():
            print(f"Missing file: {solved_file}")
            continue

        print(f"Creating performance profile for {method}")

        # --------------------------------------------------
        # Read data
        # --------------------------------------------------

        times = pd.read_csv(times_file, sep=";")
        solved = pd.read_csv(solved_file, sep=";")

        if "InstanceName" not in times.columns:
            raise ValueError(f"{times_file.name}: missing InstanceName column")
        if "InstanceName" not in solved.columns:
            raise ValueError(f"{solved_file.name}: missing InstanceName column")

        # --------------------------------------------------
        # Check that both files contain the same instances
        # --------------------------------------------------

        if list(times["InstanceName"]) != list(solved["InstanceName"]):
            raise ValueError(
                f"Instance ordering differs between "
                f"{times_file.name} and {solved_file.name}"
            )

        selected_solvers = get_solvers_for_method(
            times=times,
            solved=solved,
            solver_definitions=solver_definitions,
            method_name=method,
            strict=args.strict_solvers,
        )

        solver_columns = [
            solver_def["solver"]
            for solver_def in selected_solvers
        ]

        # --------------------------------------------------
        # Mark unsolved instances with infinite runtime
        # --------------------------------------------------

        for solver in solver_columns:
            times.loc[
                solved[solver] != 1,
                solver
            ] = np.inf

        # --------------------------------------------------
        # Compute performance ratios
        #
        # ratio(instance, solver)
        #
        #     runtime of solver
        #     -----------------
        #     best runtime among plotted solvers
        #
        # --------------------------------------------------

        best_times = times[solver_columns].min(axis=1)

        ratios = times[solver_columns].div(
            best_times,
            axis=0
        )

        # --------------------------------------------------
        # Remove instances that no plotted solver solved
        # --------------------------------------------------

        valid_instances = np.isfinite(best_times)
        ratios = ratios.loc[valid_instances]

        number_of_instances = len(ratios)

        if number_of_instances == 0:
            print(
                f"  No instances solved by any plotted solver for {method}"
            )
            continue

        # --------------------------------------------------
        # Determine maximum finite performance ratio
        # --------------------------------------------------

        finite_ratios = ratios.to_numpy()
        finite_ratios = finite_ratios[np.isfinite(finite_ratios)]

        if len(finite_ratios) == 0:
            print(
                f"  No finite runtime ratios found for {method}"
            )
            continue

        max_ratio = max(1.0, finite_ratios.max())
        max_tau = max_ratio * 1.05

        # --------------------------------------------------
        # Build performance profile
        # --------------------------------------------------

        plt.figure(figsize=(7, 5))

        for solver_def in selected_solvers:
            solver = solver_def["solver"]
            solver_ratios = ratios[solver].to_numpy()

            finite_solver_ratios = solver_ratios[np.isfinite(solver_ratios)]

            taus = np.unique(
                np.concatenate(
                    (
                        np.array([1.0]),
                        finite_solver_ratios,
                        np.array([max_tau])
                    )
                )
            )

            profile = np.array([
                np.mean(solver_ratios <= tau)
                for tau in taus
            ])

            plt.step(
                taus,
                profile,
                where="post",
                label=solver_def["label"],
                color=solver_def["color"],
                linestyle=solver_def["linestyle"] or "-",
                linewidth=1.9,
            )

        # --------------------------------------------------
        # Figure formatting
        # --------------------------------------------------

        plt.xlabel("Performance ratio")
        plt.ylabel("Fraction of instances")

        if not args.no_title:
            plt.title(f"Performance profile: {method}")

        plt.xscale("log")
        plt.xlim(1, max_tau)
        plt.ylim(0, 1.05)

        plt.grid(
            True,
            linestyle=":",
            linewidth=0.7
        )

        plt.legend(frameon=True,facecolor="white",edgecolor="black",framealpha=1.0,)
        plt.tight_layout()

        # --------------------------------------------------
        # Save as vector PDF/SVG/EPS unless PNG is requested
        # --------------------------------------------------

        output_file = folder_home / f"performance_profile_{method}.{args.output_format}"

        plt.savefig(
            output_file,
            format=args.output_format,
            bbox_inches="tight"
        )

        plt.close()

        print(f"  Saved: {output_file}")


if __name__ == "__main__":
    sys.exit(main())
