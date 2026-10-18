import csv
import argparse
from pathlib import Path
from collections import defaultdict

SOLVER_PREFIXES = ["Yasol", "EQuIPS", "CPLEX"]


def find_csv_files(folder):
    folder = Path(folder)

    if not folder.is_dir():
        raise ValueError(f"Not a valid directory: {folder}")

    pairs = []

    for solved_file in sorted(folder.glob("*_solved.csv")):
        prefix = solved_file.name[:-len("_solved.csv")]
        times_file = folder / f"{prefix}_times.csv"

        if times_file.is_file():
            pairs.append((solved_file, times_file))

    if not pairs:
        raise FileNotFoundError(
            f"No matching *_solved.csv and *_times.csv files found in {folder}"
        )

    if len(pairs) > 1:
        raise ValueError(
            "Multiple matching CSV pairs found:\n"
            + "\n".join(f"  {s.name} / {t.name}" for s, t in pairs)
            + "\nPlease keep only one matching pair in the folder."
        )

    return pairs[0]


def read_csv(filename):
    with open(filename, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        return {row["InstanceName"]: row for row in reader}


def extract_T(instance_name):
    # Example: binPacking_10_5_2_200 -> T = 10
    parts = instance_name.split("_")
    if len(parts) < 2:
        raise ValueError(f"Cannot extract T from instance name: {instance_name}")
    return int(parts[1])


def find_solver_columns(row):
    """
    Identify available solver columns based on prefixes.
    Missing solvers are allowed and simply skipped.
    Returns a dict like:
        {"Yasol": "Yasol_QIP_...", "CPLEX": "CPLEX_RC_..."}
    """
    columns = {}

    for solver in SOLVER_PREFIXES:
        matches = [col for col in row.keys() if col.strip().startswith(solver)]

        if len(matches) > 1:
            raise ValueError(
                f"Multiple columns found for solver '{solver}': {matches}"
            )

        if len(matches) == 1:
            columns[solver] = matches[0]

    return columns


def print_table(solved_file, runtime_file):
    solved_data = read_csv(solved_file)
    runtime_data = read_csv(runtime_file)

    if not solved_data or not runtime_data:
        raise ValueError("One or both CSV files are empty.")

    if set(solved_data.keys()) != set(runtime_data.keys()):
        missing_in_runtime = set(solved_data.keys()) - set(runtime_data.keys())
        missing_in_solved = set(runtime_data.keys()) - set(solved_data.keys())

        msg = ["The CSV files contain different instances."]
        if missing_in_runtime:
            msg.append(
                f"Missing in runtime file: {sorted(missing_in_runtime)[:5]}"
                + (" ..." if len(missing_in_runtime) > 5 else "")
            )
        if missing_in_solved:
            msg.append(
                f"Missing in solved file: {sorted(missing_in_solved)[:5]}"
                + (" ..." if len(missing_in_solved) > 5 else "")
            )

        raise ValueError("\n".join(msg))

    solved_columns = find_solver_columns(next(iter(solved_data.values())))
    runtime_columns = find_solver_columns(next(iter(runtime_data.values())))

    # Use only solvers that exist in BOTH files
    available_solvers = [
        solver for solver in SOLVER_PREFIXES
        if solver in solved_columns and solver in runtime_columns
    ]

    if not available_solvers:
        raise ValueError(
            "No common solver columns found in both CSV files.\n"
            f"Solved file columns found: {solved_columns}\n"
            f"Runtime file columns found: {runtime_columns}"
        )

    missing_solvers = [
        solver for solver in SOLVER_PREFIXES
        if solver not in available_solvers
    ]

    results = defaultdict(lambda: defaultdict(lambda: {"solved": 0, "time": 0.0}))

    for instance, solved_row in solved_data.items():
        T = extract_T(instance)
        runtime_row = runtime_data[instance]

        for solver in available_solvers:
            solved_col = solved_columns[solver]
            runtime_col = runtime_columns[solver]

            try:
                solved_value = solved_row[solved_col].strip()
                runtime_value = runtime_row[runtime_col].strip()

                solved = int(float(solved_value))
                runtime = float(runtime_value)
            except (ValueError, KeyError, TypeError, AttributeError) as e:
                raise ValueError(
                    f"Error processing instance '{instance}', solver '{solver}': {e}\n"
                    f"Solved value: {solved_row.get(solved_col)!r}\n"
                    f"Runtime value: {runtime_row.get(runtime_col)!r}"
                ) from e

            results[T][solver]["solved"] += solved
            results[T][solver]["time"] += runtime

    # Print info
    print(f"Using solved file: {solved_file.name}")
    print(f"Using times file:  {runtime_file.name}")
    print()

    print("Detected solvers:", ", ".join(available_solvers))
    if missing_solvers:
        print("Missing solvers:", ", ".join(missing_solvers))
    print()

    # Build dynamic table
    first_col_width = 4
    solver_col_width = 17

    header_parts = [f"{'T':>{first_col_width}}"]
    for solver in available_solvers:
        header_parts.append(f"{solver:^{solver_col_width}}")
    header = " | ".join(header_parts)

    subheader_parts = [f"{'':>{first_col_width}}"]
    for _ in available_solvers:
        subheader_parts.append(f"{'Solved':>6} {'Time [s]':>10}")
    subheader = " | ".join(subheader_parts)

    separator = "-" * max(len(header), len(subheader))

    print(separator)
    print(header)
    print(subheader)
    print(separator)

    for T in sorted(results):
        row_parts = [f"{T:>{first_col_width}}"]

        for solver in available_solvers:
            data = results[T][solver]
            row_parts.append(f"{data['solved']:>6} {data['time']:>10.1f}")

        print(" | ".join(row_parts))

    print(separator)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a solver comparison table from CSV files in a folder."
    )
    parser.add_argument(
        "folder",
        help="Folder containing *_solved.csv and *_times.csv"
    )

    args = parser.parse_args()

    solved_file, times_file = find_csv_files(args.folder)
    print_table(solved_file, times_file)


if __name__ == "__main__":
    main()
