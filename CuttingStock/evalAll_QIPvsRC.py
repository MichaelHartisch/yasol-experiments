from pathlib import Path
import csv
import sys
import argparse

parser = argparse.ArgumentParser()
def write_summary(filename, data):
    with filename.open("w", newline="") as f:
        writer = csv.writer(f, delimiter=";")

        # header
        writer.writerow(["InstanceName"] + solvers)

        # rows
        for instance in sorted(data):
            row = [instance]

            for solver in solvers:
                row.append(data[instance].get(solver, ""))

            writer.writerow(row)

if len(sys.argv) != 2:
    raise ValueError('Usage: evalAll.py testname')

testname = sys.argv[1]

folder = Path("Tests/"+testname+"/eval/QIPvsRC")

if not folder.is_dir():
    parser.error(f"Folder does not exist: {folder}")

input_files = sorted(folder.glob("*.csv"))

solved_data = {}
time_data = {}
solvers = []

for file in input_files:
    print(file.name)
    solver = file.name.removesuffix("_.csv")
    if file.name.endswith("times.csv") or file.name.endswith("solved.csv"):
        continue
    solvers.append(solver)
    with file.open(newline="") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            instance = row["InstanceName"]

            if instance not in solved_data:
                solved_data[instance] = {}

            if instance not in time_data:
                time_data[instance] = {}
#            print(row)
            solved_data[instance][solver] = row["Solved"]
            time_data[instance][solver] = row["SolutionTime"]
    write_summary(folder / str("QIPvsRC_solved.csv"), solved_data)
    write_summary(folder / str("QIPvsRC_times.csv"), time_data)

