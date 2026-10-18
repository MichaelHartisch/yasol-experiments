from pathlib import Path
import csv
import sys


if len(sys.argv) != 2:
    raise ValueError("Usage: Summary.py testname")

testname = sys.argv[1]

folder = Path("Tests/" + testname + "/eval")
folder_home = Path(".")
if not folder.is_dir():
    raise ValueError(f"Folder does not exist: {folder}")



solved_summary = {}
time_summary = {}

all_solvers = set()

# Used for totals across all methods
total_solved = {}
total_runtimes = {}


path_m = Path("Instances")
path= Path(str(path_m))
for item in path.iterdir():
    method=item.name
    solved_file = folder / (method + "_solved.csv")
    times_file = folder / (method + "_times.csv")

    if not solved_file.is_file():
        print(f"Missing file: {solved_file}")
        continue

    if not times_file.is_file():
        print(f"Missing file: {times_file}")
        continue


    with solved_file.open(newline="") as f:
        reader = csv.DictReader(f, delimiter=";")

        solvers = [
            name for name in reader.fieldnames
            if name != "InstanceName"
        ]

        all_solvers.update(solvers)

        solved_counts = {
            solver: 0
            for solver in solvers
        }

        solved_instances = {
            solver: set()
            for solver in solvers
        }

        for solver in solvers:
            total_solved.setdefault(solver, 0)
            total_runtimes.setdefault(solver, [])

        for row in reader:
            instance = row["InstanceName"]

            for solver in solvers:
                if row[solver] != "" and int(row[solver]) == 1:
                    solved_counts[solver] += 1
                    solved_instances[solver].add(instance)

                    total_solved[solver] += 1

        solved_summary[method] = solved_counts


    runtimes = {
        solver: []
        for solver in solvers
    }

    with times_file.open(newline="") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            instance = row["InstanceName"]

            for solver in solvers:

                if instance not in solved_instances[solver]:
                    continue

                value = row[solver]

                if value != "":
                    runtime = float(value)

                    runtimes[solver].append(runtime)
                    total_runtimes[solver].append(runtime)


    time_summary[method] = {}

    for solver in solvers:

        if runtimes[solver]:
            time_summary[method][solver] = (
                sum(runtimes[solver]) / len(runtimes[solver])
            )
        else:
            time_summary[method][solver] = ""


all_solvers = sorted(all_solvers)


# --------------------------------------------------
# summary_solved.csv
# --------------------------------------------------

#with(folder / "summary_solved.csv").open("w", newline="") as f:
with (folder_home / "summary_solved.csv").open("w", newline="") as f:

    writer = csv.writer(f, delimiter=";")

    writer.writerow(["Method"] + all_solvers)

    path_m = Path("Instances")
    path= Path(str(path_m))
    for item in path.iterdir():
        method=item.name
        row = [method]

        for solver in all_solvers:
            row.append(
                solved_summary.get(method, {}).get(solver, "")
            )

        writer.writerow(row)

    # Total over all three methods
    row = ["Total"]

    for solver in all_solvers:
        row.append(total_solved.get(solver, 0))

    writer.writerow(row)


# --------------------------------------------------
# summary_times.csv
# --------------------------------------------------

#with (folder / "summary_times.csv").open("w", newline="") as f:
with (folder_home / "summary_times.csv").open("w", newline="") as f:

    writer = csv.writer(f, delimiter=";")

    writer.writerow(["Method"] + all_solvers)

    path_m = Path("Instances")
    path= Path(str(path_m))
    for item in path.iterdir():
        method=item.name
        row = [method]

        for solver in all_solvers:
            value = time_summary.get(method, {}).get(solver, "")

            if value != "":
                value = round(value, 3)

            row.append(value)

        writer.writerow(row)

    # Average runtime over all solved instances
    # from all three methods
    row = ["Total"]

    for solver in all_solvers:

        values = total_runtimes.get(solver, [])

        if values:
            average = sum(values) / len(values)
            row.append(round(average, 3))
        else:
            row.append("")

    writer.writerow(row)
