# Reproducing the Computational Experiments

This repository provides scripts to reproduce the computational study in our paper submitted to MPC and to run smaller experiments with selected solvers. The scripts prepare benchmark instances, execute solver runs, and generate summary tables and plots. Commands have to be from the repository root.

For full reproduction, use `probability=1`, `timelimit=1800`, and all specified solvers (preferably in the same versions). Reducing `probability` to some value within [0,1] reduces the number of used instances in the test by randomly choosing a subset of instances (selecting an instance with the specified probability). This is useful for quicker testing but may not reproduce the published numerical results excactly.

## Third-party software

This repository includes copies of GNU Parallel by Ole Tange and the Free Software Foundation, used to execute solver instances in parallel. GNU Parallel is distributed under the GNU General Public License. Its copyright notices and license terms are retained.
## 1. Install Yasol

Yasol needs an LP/MIP backend: CPLEX, HiGHS, or COIN-OR. We used **CPLEX 22.1.1**; results are most comparable when using that version.

Run the installation script and follow its instructions:

```bash
./setupYasol.sh
```

The script can also install HiGHS or COIN-OR automatically if selected.

## 2. Install optional comparison solvers

These installations are only necessary for experiments that include the respective solvers. To run only Yasol variants, skip this section.

### 2.1 EQuIPS

EQuIPS requires an installed and licensed Gurobi version. Then run:

```bash
./setupEQuIPS.sh
```

### 2.2 MCN solver (DAD)

The [Critical-Node-Problem repository](https://github.com/mxmmargarida/Critical-Node-Problem) is downloaded by `MCN_prepare.sh`.

Its `DAD.py` requires **Python 2.7** and **CPLEX Optimization Studio 12.9** (the last version compatible with Python 2.7). Install the matching CPLEX Python API, for example:

```bash
python2.7 -m pip install cplex==12.9.0.0
```

Alternatively, install the API from your CPLEX 12.9 installation directory. This is separate from the CPLEX 22.1.1 installation recommended for Yasol.

### 2.3 MibS

The following commands build MibS 1.2.2 with CPLEX. Set `CPLEX_ROOT` to the **main CPLEX Studio directory** (not its `cplex` subdirectory) and adapt the architecture-specific library path if necessary.

```bash
CPLEX_ROOT=/opt/ibm/ILOG/CPLEX_Studio2211

wget https://raw.githubusercontent.com/coin-or/coinbrew/master/coinbrew
chmod +x coinbrew
./coinbrew fetch MibS@1.2.2
./coinbrew build MibS \
    --prefix="$HOME/opt/mibs-cplex-122" \
    --with-cplex-incdir="$CPLEX_ROOT/cplex/include/ilcplex" \
    --with-cplex-lib="-L$CPLEX_ROOT/cplex/lib/x86-64_linux/static_pic -lcplex -ldl -lpthread -lm"
```

## Experiment parameters

Across the run scripts:

- `probability` (between 0 and 1) controls the fraction of instances considered. `1` includes all instances; smaller values select an approximately proportional subset.
- `threads` is the number of **solver runs in parallel**. Note that each solver call is restricted to only use a single thread.
- `timelimit` is the **time limit in seconds per solver run**.

The commands below use 48 parallel runs. Adjust this number to your machine. All runtime estimates are indicative and depend on hardware and solver setup.

## 3. MCN experiments (Section 4.1)

These experiments produce the results corresponding to **Figure 1** and **Table 1**.

**Required solvers:** Yasol for `Yasol_Poly` and `Yasol_DD`. The external `MCN` solver and EQuIPS are required only if included in the command; see Section 2 for their dependencies.

Prepare the environment and download the instances and external code:

```bash
./MCN_prepare.sh
```

Run experiments with:

```text
./MCN_run.sh <probability> <test_name> <threads> <timelimit> <solver1> [solver2 ...]
```

Valid `test_name` values are `tree`, `public_repository`, and `rndgraph`.

Suggested reduced experiment (approximately 10% of instances, five-minute limit per run):

```bash
./MCN_run.sh 0.1 tree              48 300 Yasol_Poly MCN EQuIPS Yasol_DD
./MCN_run.sh 0.1 public_repository 48 300 Yasol_Poly MCN EQuIPS Yasol_DD
./MCN_run.sh 0.1 rndgraph          48 300 Yasol_Poly MCN EQuIPS Yasol_DD
```

Indicative runtimes with 48 parallel runs: approximately 10 minutes (`tree`), 5 minutes (`public_repository`), and 30 minutes (`rndgraph`).

For the full original experiments:

```bash
./MCN_run.sh 1 tree              48 1800 Yasol_Poly MCN EQuIPS Yasol_DD
./MCN_run.sh 1 public_repository 48 1800 Yasol_Poly MCN EQuIPS Yasol_DD
./MCN_run.sh 1 rndgraph          48 1800 Yasol_Poly MCN EQuIPS Yasol_DD
```

Remove any solvers you do not wish to run from the arguments.

**Output:** `MCN/summary_solved.csv` corresponds to Table 1. The files `MCN/performance_profile_tree.pdf`, `MCN/performance_profile_public_repository.pdf`, and `MCN/performance_profile_rndgraph.pdf` correspond to Figure 1. See `MCN/Tests` for additional details.

## 4. Bilevel experiments (Section 4.2)

These experiments produce the results corresponding to **Figure 2** and **Table 2**.

**Required solvers:** Yasol for `Yasol_FA` and `Yasol_LA`. MibS and EQuIPS are optional and required only if selected.

Prepare the environment:

```bash
./Bilevel_prepare.sh
```

Run with:

```text
./Bilevel_run.sh <probability> <threads> <timelimit> <solver1> [solver2 ...]
```

Suggested reduced experiment (approximately 30% of instances; indicative runtime around 2.5 hours with 48 parallel runs):

```bash
./Bilevel_run.sh 0.3 48 300 Yasol_FA Yasol_LA MibS EQuIPS
```

**Output:** `Bilevel/cactusPlot.pdf` corresponds to Figure 2. The files `Bilevel/summary_solved.csv` and `Bilevel/summary_times.csv` provide summaries; `summary_solved.csv` corresponds to the information in Table 2. 

## 5. Cutting-stock experiments (Section 4.3)

These experiments cover **Table 4** and **Figures 3–5**.

### 5.1 Solver comparison (Table 4)

**Required solvers:** Only the solvers selected for this run: Yasol, EQuIPS (requires Gurobi), and/or CPLEX. The full MIP/LP expansion is generated only when CPLEX is selected.

Prepare the environment:

```bash
./CuttingStock_prepare.sh
```

Run:

```text
./CuttingStock_run1.sh <probability> <threads> <timelimit> <solver1> [solver2 ...]
```

Suggested reduced experiment (indicative runtime around 20 minutes with 48 parallel runs):

```bash
./CuttingStock_run1.sh 0.3 48 300 Yasol EQuIPS CPLEX
```

The script asks for your CPLEX installation path. You may omit EQuIPS or CPLEX from the solver list. The script generates the necessary QLP/LP model files; selecting CPLEX also generates the full MIP/LP expansion, which can require substantial disk space and preparation time.

**Output:** Summary results corresponding to Table 4.

### 5.2 Reduced-stage approximations (Figure 3)

**Required software:** Yasol and CPLEX; the script **requests** the CPLEX installation path.

```text
./CuttingStock_run2.sh <probability> <threads> <timelimit>
```

Suggested reduced experiment (indicative runtime around 30 minutes with 48 parallel runs):

```bash
./CuttingStock_run2.sh 0.5 48 600
```

**Output:** `CuttingStock/violinPlot.pdf`, corresponding to Figure 3. The distributions may differ when only a subset of instances is used.

### 5.3 Decision rules (Figures 4 and 5)

**Required software:** Yasol and CPLEX. The decision-rule executable uses CPLEX directly; the script requests the main CPLEX Studio installation directory, for example `/opt/ibm/ILOG/CPLEX_Studio2211`.

```text
./CuttingStock_run3.sh <probability> <threads> <timelimit> <P>
```

Here, `P` is the number of pieces in the piecewise-linear decision rules.

Suggested reduced experiment (indicative runtime around 30 minutes with 48 parallel runs):

```bash
./CuttingStock_run3.sh 0.5 48 300 1
```

**Output:** `CuttingStock/dr_runtime_profile.pdf` and `CuttingStock/dist_by_T.pdf`, corresponding to Figures 4 and 5, respectively.