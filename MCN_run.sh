AVAILABLE_SOLVERS=("Yasol_DD" "Yasol_Poly" "MCN" "EQuIPS")
AVAILABLE_TESTS=("public_repository" "rndgraph" "tree")

usage() {
    echo "Usage: $0 <probability> <test_name> <threads> <timelimit> <solver1> [solver2] ..."
    echo ""
    echo "Arguments:"
    echo "  probability Probability of keeping an instance in the test (0 <= p <= 1); to reduce runtime for a quick check"
    echo "  test_name  Name of the test set"
    echo "  threads    number of runs conducted in parallel"
    echo "  timelimit  the timelimit for each solver call in seconds"
    echo "  solver     One or more solvers to run"
    echo ""
    echo "Available tests:"
    for test in "${AVAILABLE_TESTS[@]}"; do
        echo "  $test"
    done
    echo ""
    echo "Available solvers:"
    for solver in "${AVAILABLE_SOLVERS[@]}"; do
        echo "  $solver"
    done
    echo ""
    echo "Examples:"
    echo "  $0 1.0 tree 20 1800 Yasol_DD Yasol_Poly"
    echo "  $0 0.5 rndgraph 50 180 Yasol_Poly MCN EQuIPS"
    echo "  $0 0.1 public_repository 2 60 Yasol_DD"
}

# Print error and exit
error() {
    echo "Error: $1" >&2
    echo "" >&2
    usage >&2
    exit 1
}

# Check minimum number of arguments
if (( $# < 5 )); then
    error "Not enough arguments."
fi

# Read parameters
p="$1"
test_name="$2"
threads="$3"
timelimit=$4
valid=false
for test in "${AVAILABLE_TESTS[@]}"; do
    if [[ "$test_name" == "$test" ]]; then
        valid=true
        break
    fi
done

if [[ "$valid" == false ]]; then
    error "Unknown test set '$test_name'."
fi

if ! [[ "$threads" =~ ^-?[0-9]+$ ]]; then
    error "Parameter 'threads'  must be an integer."
fi

if ! [[ "$timelimit" =~ ^-?[0-9]+$ ]]; then
    error "Parameter 'timelimit'  must be an integer."
fi
# Remove first two parameters
shift 4

# Remaining parameters are solver names
solvers=("$@")

# Validate probability
if ! awk -v p="$p" 'BEGIN {
    exit !(p ~ /^([0-9]+([.][0-9]*)?|[.][0-9]+)$/ &&
           p >= 0 && p <= 1)
}'; then
    error "Probability must be between 0 and 1."
fi

# Validate solver names
for solver in "${solvers[@]}"; do

    valid=false

    for available in "${AVAILABLE_SOLVERS[@]}"; do
        if [[ "$solver" == "$available" ]]; then
            valid=true
            break
        fi
    done

    if [[ "$valid" == false ]]; then
        error "Unknown solver '$solver'."
    fi
done

# All arguments are valid
echo "Experiment configuration:"
echo "  Probability: $p"
echo "  Test set:    $test_name"
echo "  Solvers:     ${solvers[*]}"
echo ""

MainFolder=$(pwd)
cd MCN

StarterFile="ParallelRuns_Main_${p}_${test_name}.txt"
rm -f $StarterFile
# Run experiments
for solver in "${solvers[@]}"; do
    echo "Preparing $solver on $test_name..."
case "$solver" in
        Yasol_DD)
            auxfile_Y_DD="ParallelRunsYasol_DD_Main_${p}_${test_name}.txt"
	    rm -f $auxfile_Y_DD
            ./StartYasolTest.sh Main_${p} DD $timelimit ${MainFolder}/Yasol/build/yasol "--isSimplyRestricted=1" ${p} ${test_name} ${auxfile_Y_DD}
            cat $auxfile_Y_DD >> $StarterFile
            ;;
        Yasol_Poly)
            auxfile_Y_P="ParallelRunsYasol_Poly_Main_${p}_${test_name}.txt"
            rm -f $auxfile_Y_P
            ./StartYasolTest.sh Main_${p} Poly $timelimit ${MainFolder}/Yasol/build/yasol "--isSimplyRestricted=1" ${p} ${test_name} ${auxfile_Y_P}
            cat $auxfile_Y_P >> $StarterFile
            ;;
        MCN)
            auxfile_MCN="ParallelRunsMCN_Main_${p}_${test_name}.txt"
            rm -f $auxfile_MCN
            ./StartMCNTest.sh Main_${p} $timelimit ${p} ${test_name} ${auxfile_MCN}
            cat $auxfile_MCN >> $StarterFile
            ;;
        EQuIPS)
            auxfile_E="ParallelRunsEQuIPS_Main_${p}_${test_name}.txt"
            rm -f $auxfile_E
            ./StartEQuIPSTest.sh Main_${p} Poly $timelimit ${MainFolder}/EQuIPS/build/EQuIPS ${p} ${test_name} ${auxfile_E}
            cat $auxfile_E >> $StarterFile
            ;;
   esac
done
cat $StarterFile | ./parallel -P$threads
mkdir -p "Tests/Main_${p}/eval/"

for solver in "${solvers[@]}"; do
    echo "Evaluating $solver on $test_name..."
case "$solver" in
        Yasol_DD)
            python3 evalYasol.py Main_${p} ${test_name} $timelimit
            ;;
        Yasol_Poly)
            python3 evalYasol.py Main_${p} ${test_name} $timelimit
            ;;
        MCN)
            python3 evalMCN.py Main_${p} ${test_name} $timelimit
            ;;
        EQuIPS)
            python3 evalEQuIPS.py Main_${p} ${test_name} $timelimit
            ;;
   esac
done

python3 evalAll.py Main_${p}
python3 summary.py Main_${p}

python3 performance_styled.py Main_${p} solver_updated.txt --methods ${test_name}

cp Tests/Main_${p}/eval/summary_solved.csv .
