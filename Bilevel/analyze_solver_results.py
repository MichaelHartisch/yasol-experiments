#!/usr/bin/env python3

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


DEFAULT_TOLERANCE = 1e-6
TIME_LIMIT = 180.0


def values_equal(a, b, tolerance):
    return math.isclose(a, b, rel_tol=tolerance, abs_tol=tolerance)


def build_reference_index(reference_dir):
    index = defaultdict(list)

    for path in reference_dir.rglob("*.res.json"):
        if path.is_file():
            index[path.name].append(path)

    return index


def load_reference_file(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def add_detail(
    details,
    csv_file,
    instance,
    category,
    solution_value,
    reference_value,
    solution_time,
    difficulty,
    note="",
):
    details.append(
        {
            "CsvFile": csv_file,
            "InstanceName": instance,
            "Category": category,
            "CsvValue": solution_value,
            "ReferenceValue": reference_value,
            "SolutionTime": solution_time,
            "Difficulty": difficulty,
            "Note": note,
        }
    )


def process_csv(
    csv_path,
    reference_index,
    tolerance,
    details,
    warnings,
):
    counters = {
        "IncorrectOptimal": 0,
        "HardSolvedQuickly": 0,
        "EasySolvedQuickly": 0,
        "EasyNotEasy": 0,
        "NewOptimal": 0,
    }

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")

        required_columns = {
            "InstanceName",
            "Solved",
            "SolutionTime",
            "SolutionValue",
        }

        if reader.fieldnames is None:
            raise ValueError(f"{csv_path}: CSV has no header")

        missing = required_columns - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"{csv_path}: missing CSV columns: "
                + ", ".join(sorted(missing))
            )

        for line_number, row in enumerate(reader, start=2):
            instance = row["InstanceName"].strip()

            if not instance:
                warnings.append(
                    f"{csv_path.name}:{line_number}: empty InstanceName"
                )
                continue

            try:
                solved = int(row["Solved"])
                solution_time = float(row["SolutionTime"])
                solution_value = float(row["SolutionValue"])
            except (ValueError, TypeError) as e:
                warnings.append(
                    f"{csv_path.name}:{line_number}: "
                    f"invalid numeric value for {instance}: {e}"
                )
                continue

            reference_filename = instance + ".res.json"
            matches = reference_index.get(reference_filename, [])

            if len(matches) == 0:
                warnings.append(
                    f"{csv_path.name}:{line_number}: "
                    f"no reference file found for {instance} "
                    f"(expected {reference_filename})"
                )
                continue

            if len(matches) > 1:
                locations = ", ".join(str(p) for p in matches)

                warnings.append(
                    f"{csv_path.name}:{line_number}: "
                    f"multiple reference files found for {instance}: "
                    f"{locations}"
                )
                continue

            reference_path = matches[0]

            try:
                reference = load_reference_file(reference_path)
            except (OSError, json.JSONDecodeError) as e:
                warnings.append(
                    f"{csv_path.name}:{line_number}: "
                    f"cannot read {reference_path}: {e}"
                )
                continue

            difficulty = reference.get("difficulty")
            reference_value = reference.get("objective_value")

            if difficulty is None:
                warnings.append(
                    f"{csv_path.name}:{line_number}: "
                    f"{reference_path} has no 'difficulty' field"
                )
                continue

            difficulty = str(difficulty).strip().lower()

            if reference_value is None:
                warnings.append(
                    f"{csv_path.name}:{line_number}: "
                    f"{reference_path} has no 'objective_value' field"
                )
                continue

            try:
                reference_value = float(reference_value)
            except (ValueError, TypeError):
                warnings.append(
                    f"{csv_path.name}:{line_number}: "
                    f"invalid objective_value in {reference_path}: "
                    f"{reference_value!r}"
                )
                continue

            #
            # 1. Claimed optimal solution disagrees with known optimum.
            #
            # "feasible" is excluded because its reference value is not
            # necessarily optimal.
            #
            if solved == 1 and difficulty != "feasible":
                if not values_equal(
                    solution_value,
                    reference_value,
                    tolerance,
                ):
                    counters["IncorrectOptimal"] += 1

                    add_detail(
                        details,
                        csv_path.name,
                        instance,
                        "incorrect_optimal",
                        solution_value,
                        reference_value,
                        solution_time,
                        difficulty,
                        (
                            "Solver claims optimality, but its objective "
                            "differs from the known optimum."
                        ),
                    )

                    #
                    # This is a critical correctness warning.
                    #
                    warnings.append(
                        f"CRITICAL: {csv_path.name}:{line_number}: "
                        f"{instance}: solver reports an optimal value of "
                        f"{solution_value}, but the known optimal value is "
                        f"{reference_value}"
                    )

            #
            # 2. Hard instance solved quickly.
            #
            if (
                solved == 1
                and difficulty == "hard"
                and solution_time <= TIME_LIMIT
            ):
                counters["HardSolvedQuickly"] += 1

                add_detail(
                    details,
                    csv_path.name,
                    instance,
                    "hard_solved_quickly",
                    solution_value,
                    reference_value,
                    solution_time,
                    difficulty,
                )

            #
            # 3. Easy instance solved quickly.
            #
            if (
                solved == 1
                and difficulty == "easy"
                and solution_time <= TIME_LIMIT
            ):
                counters["EasySolvedQuickly"] += 1

                add_detail(
                    details,
                    csv_path.name,
                    instance,
                    "easy_solved_quickly",
                    solution_value,
                    reference_value,
                    solution_time,
                    difficulty,
                )

            #
            # 4. Easy instance was not easy for this solver.
            #
            if difficulty == "easy" and (
                solved == 0 or solution_time > TIME_LIMIT
            ):
                counters["EasyNotEasy"] += 1

                reason = (
                    "not solved"
                    if solved == 0
                    else f"solution time exceeds {TIME_LIMIT:g}s"
                )

                add_detail(
                    details,
                    csv_path.name,
                    instance,
                    "easy_not_easy",
                    solution_value,
                    reference_value,
                    solution_time,
                    difficulty,
                    reason,
                )

            #
            # 5. Previously feasible instance now solved optimally.
            #
            if difficulty == "feasible" and solved == 1:

                if solution_value <= reference_value + tolerance:
                    counters["NewOptimal"] += 1

                    if values_equal(
                        solution_value,
                        reference_value,
                        tolerance,
                    ):
                        note = (
                            "Optimality proved for a previously only "
                            "feasible solution."
                        )
                    else:
                        note = (
                            "Optimality proved and the previous feasible "
                            "objective was improved."
                        )

                    add_detail(
                        details,
                        csv_path.name,
                        instance,
                        "new_optimal",
                        solution_value,
                        reference_value,
                        solution_time,
                        difficulty,
                        note,
                    )

                else:
                    add_detail(
                        details,
                        csv_path.name,
                        instance,
                        "feasible_value_inconsistency",
                        solution_value,
                        reference_value,
                        solution_time,
                        difficulty,
                        (
                            "Claimed optimum is worse than the previously "
                            "known feasible objective."
                        ),
                    )

                    #
                    # This is also a critical correctness warning.
                    #
                    warnings.append(
                        f"CRITICAL: {csv_path.name}:{line_number}: "
                        f"{instance}: solver reports an optimal value of "
                        f"{solution_value}, but a better feasible solution "
                        f"with value {reference_value} is already known"
                    )

    return counters


def write_summary(path, summaries):
    fieldnames = [
        "CsvFile",
        "IncorrectOptimal",
        "HardSolvedQuickly",
        "EasySolvedQuickly",
        "EasyNotEasy",
        "NewOptimal",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(summaries)


def write_details(path, details):
    fieldnames = [
        "CsvFile",
        "InstanceName",
        "Category",
        "CsvValue",
        "ReferenceValue",
        "SolutionTime",
        "Difficulty",
        "Note",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(details)


def write_warnings(path, warnings):
    with path.open("w", encoding="utf-8") as f:
        for warning in warnings:
            f.write(warning + "\n")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Compare solver CSV results against instance reference "
            "information stored in .res.json files."
        )
    )

    parser.add_argument(
        "csv_folder",
        type=Path,
        help="Folder containing the solver CSV files",
    )

    parser.add_argument(
        "reference_folder",
        type=Path,
        help=(
            "Folder whose directory tree contains the "
            "INSTANCE.res.json files"
        ),
    )

    parser.add_argument(
        "keyword",
        help=(
            "Only CSV filenames beginning with this keyword are processed. "
            "The keyword is also used as the solver name for output files."
        ),
    )

    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help=(
            "Tolerance for comparing objective values "
            f"(default: {DEFAULT_TOLERANCE})"
        ),
    )

    args = parser.parse_args()

    if not args.csv_folder.is_dir():
        parser.error(
            f"CSV folder does not exist or is not a directory: "
            f"{args.csv_folder}"
        )

    if not args.reference_folder.is_dir():
        parser.error(
            f"Reference folder does not exist or is not a directory: "
            f"{args.reference_folder}"
        )

    #
    # Output files are stored in the CSV input directory.
    #
    summary_path = (
        args.csv_folder
        / f"{args.keyword}_analysis_summary.csv"
    )

    details_path = (
        args.csv_folder
        / f"{args.keyword}_analysis_details.csv"
    )

    warnings_path = (
        args.csv_folder
        / f"{args.keyword}_analysis_warnings.txt"
    )

    print(
        f"Indexing reference files below "
        f"{args.reference_folder} ..."
    )

    reference_index = build_reference_index(
        args.reference_folder
    )

    reference_file_count = sum(
        len(paths) for paths in reference_index.values()
    )

    print(
        f"Found {reference_file_count} reference files "
        f"({len(reference_index)} unique filenames)."
    )

    #
    # Process only CSV files directly inside csv_folder whose
    # names begin with the solver keyword.
    #
    csv_files = sorted(
        p
        for p in args.csv_folder.iterdir()
        if p.is_file()
        and p.suffix.lower() == ".csv"
        and p.name.startswith(args.keyword)
        #
        # Do not accidentally process analysis files generated
        # by an earlier run.
        #
        and "_analysis_" not in p.name
    )

    if not csv_files:
        print(
            f"No CSV files beginning with {args.keyword!r} "
            f"found in {args.csv_folder}",
            file=sys.stderr,
        )
        return 1

    summaries = []
    details = []
    warnings = []

    for csv_path in csv_files:
        print(f"Processing {csv_path.name} ...")

        try:
            counters = process_csv(
                csv_path,
                reference_index,
                args.tolerance,
                details,
                warnings,
            )
        except (OSError, ValueError) as e:
            warnings.append(
                f"Could not process {csv_path}: {e}"
            )

            print(
                f"WARNING: could not process "
                f"{csv_path.name}: {e}",
                file=sys.stderr,
            )
            continue

        summaries.append(
            {
                "CsvFile": csv_path.name,
                **counters,
            }
        )

    write_summary(summary_path, summaries)
    write_details(details_path, details)
    write_warnings(warnings_path, warnings)

    print()
    print(f"Summary written to: {summary_path}")
    print(f"Details written to: {details_path}")
    print(f"Warnings written to: {warnings_path}")
    print(f"Warnings: {len(warnings)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
