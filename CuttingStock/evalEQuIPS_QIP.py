import os
import csv
import sys
import math
from pathlib import Path
import argparse
parser = argparse.ArgumentParser()

if len(sys.argv) != 3:
    raise ValueError('Usage: evalEQuIPS.py testname timelimit')

testname = sys.argv[1]
timelimit = sys.argv[2]

folder = Path("Tests/"+testname+"/EQuIPS_QIP")

if not folder.is_dir():
    parser.error(f"Folder does not exist: {folder}")

path_eval = "Tests/"+testname+"/eval/"
path_out = "Tests/"+testname+"/eval/QIPvsRC/"
f = open(path_out+"EQuIPS_QIP_"+testname+"_.csv", 'w')

writer = csv.writer(f, delimiter = ";")
header = ['InstanceName', 'Solved', 'SolutionTime', 'SolutionValue']
writer.writerow(header)
FullData = list()

       
for file in folder.iterdir():
    if not file.is_file():
        continue
    text = file.read_text()
    #print(file.stem)
    solved = "Status: OPTIMAL" in text
    unsat = "Status: INFEASIBLE" in text
    #print(solved)
    time = timelimit
    objective = -1
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Time:"):
            value = line.split(":", 1)[1].strip()
            #print(value)
            if value != "Limit":
                time = float(value.replace("seconds", "").strip())
        elif line.startswith("Objective:"):
            value = line.split(":", 1)[1].strip()
            objective = float(value)
        if unsat:
            objective=math.inf
    #print([Path(file.stem).stem, int(solved or unsat), time, objective])
    FullData.append([Path(file.stem).stem.removesuffix("_new"), int(solved or unsat), time, objective])
def first(elem):
    return elem[0]
FullData.sort(key=first)
#print(FullData)
for line in FullData:
    writer.writerow(line)
