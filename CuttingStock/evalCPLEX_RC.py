import os
import csv
import sys
import math
from pathlib import Path
import argparse
parser = argparse.ArgumentParser()

if len(sys.argv) != 3:
    raise ValueError('Usage: evalCPLEX.py testname timelimit')

testname = sys.argv[1]
timelimit = sys.argv[2]

folder = Path("Tests/"+testname+"/CPLEX_RC")

if not folder.is_dir():
    parser.error(f"Folder does not exist: {folder}")

path_eval = "Tests/"+testname+"/eval/"

path_out = "Tests/"+testname+"/eval/QIPvsRC/"
f = open(path_out+"CPLEX_RC_"+testname+"_.csv", 'w')
writer = csv.writer(f, delimiter = ";")
header = ['InstanceName', 'Solved', 'SolutionTime', 'SolutionValue']
writer.writerow(header)
FullData = list()

for file in folder.iterdir():
    if not file.is_file():
        continue
    if not file.name.endswith(".log"):
        continue
    text = file.read_text()
    #print(file.stem)
    solved = "MIP - Integer optimal solution" in text
    unsat = "MIP - Integer infeasible" in text
    #print(solved or unsat)
    time = timelimit
    objective = -1
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Solution time =") and (solved or unsat):
            value = (line.split("=")[1]).split()[0]

            #print(value)
            time = float(value)
        elif line.startswith("MIP - Integer optimal solution:"):
            value = (line.split("=")[1]).split()[0]
            objective = float(value)
    if unsat:
       objective=math.inf
    #print([Path(file.stem).stem, int(solved or unsat), time, objective])
    FullData.append([Path(file.stem).stem.removesuffix("_RC"), int(solved or unsat), time, objective])
def first(elem):
    return elem[0]
FullData.sort(key=first)
#print(FullData)
for line in FullData:
    writer.writerow(line)
