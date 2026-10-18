from pathlib import Path
import csv
import sys

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

folder = Path("Tests/"+testname+"/eval")

if not folder.is_dir():
    parser.error(f"Folder does not exist: {folder}")

path_m = Path("Tests/"+testname+"/Yasol_FA")
path= Path(str(path_m))
for item in path.iterdir():
    method=item.name
    input_files = sorted(folder.glob("*_"+str(method)+".csv"))

    solved_data = {}
    time_data = {}
    solvers = []

    for file in input_files:
        solver = file.name.removesuffix("_"+str(method)+".csv")
        solvers.append(solver)
       # print(solver)
       # print(file)
        with file.open(newline="") as f:
            reader = csv.DictReader(f, delimiter=";")

            for row in reader:
                instance = row["InstanceName"]

                if instance not in solved_data:
                    solved_data[instance] = {}

                if instance not in time_data:
                    time_data[instance] = {}

                solved_data[instance][solver] = row["Solved"]
                time_data[instance][solver] = row["SolutionTime"]
    write_summary(folder / str(method+"_solved.csv"), solved_data)
    write_summary(folder / str(method+"_times.csv"), time_data)

