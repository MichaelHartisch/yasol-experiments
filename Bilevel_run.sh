AVAILABLE_SOLVERS=("Yasol_FA" "Yasol_LA" "MibS" "EQuIPS")

usage() {
    echo "Usage: $0 <probability> <threads> <timelimit> <solver1> [solver2] ..."
    echo ""
    echo "Arguments:"
    echo "  probability Probability of keeping an instance in the test (0 <= p <= 1); to reduce runtime for a quick check"
    echo "  threads    number of runs conducted in parallel"
    echo "  timelimit  the timelimit for each solver call in seconds"
    echo "  solver     One or more solvers to run"
    echo ""
    echo "Available solvers:"
    for solver in "${AVAILABLE_SOLVERS[@]}"; do
        echo "  $solver"
    done
    echo ""
    echo "Examples:"
    echo "  $0 1.0 20 1800 Yasol_FA Yasol_LA"
    echo "  $0 0.5 50 180 Yasol_LA Yasol_FA MCN EQuIPS"
    echo "  $0 0.1 2 60 Yasol_LA"
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
threads="$2"
timelimit=$3

if ! [[ "$threads" =~ ^-?[0-9]+$ ]]; then
    error "Parameter 'threads'  must be an integer."
fi

if ! [[ "$timelimit" =~ ^-?[0-9]+$ ]]; then
    error "Parameter 'timelimit'  must be an integer."
fi
# Remove first two parameters
shift 3

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
OneYasol=false
for solver in "${solvers[@]}"; do

    valid=false

    for available in "${AVAILABLE_SOLVERS[@]}"; do
        if [[ "$solver" == "EQuIPS" ]]; then
            if [[ ! -d "EQuIPS" ]]; then
                valid=false
                echo "Error: '$solver' not installed."
                exit 1
                break
            fi
        fi
        if [[ "$solver" == "Yasol_LA" ]]; then
            OneYasol=true
        fi
        if [[ "$solver" == "Yasol_FA" ]]; then
            OneYasol=true
        fi
        if [[ "$solver" == "$available" ]]; then
            valid=true
            if [[ "$solver" == "MibS" ]]; then
                echo "Please provide the path to your mibs executable!"
		echo "Note that we assume it is compiled with cplex."
                read -r -e -p ":" MibS_PATH
            fi
            break
        fi
    done

    if [[ "$valid" == false ]]; then
        error "Unknown solver '$solver'."
    fi
done

    if [[ "$OneYasol" == false ]]; then
         "Either Yasol_LA or Yasol_FA should be tested."
         exit 1
    fi

# All arguments are valid
echo "Experiment configuration:"
echo "  Probability: $p"
echo "  Solvers:     ${solvers[*]}"
echo ""

MainFolder=$(pwd)
cd Bilevel

StarterFile="ParallelRunsBilevel_Main_${p}.txt"
rm -f $StarterFile
# Run experiments
for solver in "${solvers[@]}"; do
    echo "Preparing $solver on bilevel instances..."
case "$solver" in
        Yasol_FA)
            auxfile_Y_FA="ParallelRunsYasol_FA_Main_${p}.txt"
	    rm -f $auxfile_Y_FA
            ./StartYasolTest.sh Main_${p} "FA" $timelimit ${MainFolder}/Yasol/build/yasol "--isSimplyRestricted=1" ${p} ${auxfile_Y_FA}
            cat $auxfile_Y_FA >> $StarterFile
            ;;
        Yasol_LA)
            auxfile_Y_LA="ParallelRunsYasol_LA_Main_${p}.txt"
            rm -f $auxfile_Y_LA
            ./StartYasolTest.sh Main_${p} "LA" $timelimit ${MainFolder}/Yasol/build/yasol "--isSimplyRestricted=1" ${p} ${auxfile_Y_LA}
            cat $auxfile_Y_LA >> $StarterFile
            ;;
        MibS)
            auxfile_MibS="ParallelRunsMibS_Main_${p}"
            rm -f $auxfile_MibS
            ./StartMibSTest.sh Main_${p} $timelimit $MibS_PATH ${p} ${auxfile_MibS}
            cat $auxfile_MibS >> $StarterFile
            ;;
        EQuIPS)
            auxfile_E="ParallelRunsEQuIPS_Main_${p}.txt"
            rm -f $auxfile_E
            ./StartEQuIPSTest.sh Main_${p} $timelimit ${MainFolder}/EQuIPS/build/EQuIPS ${p} ${auxfile_E}
            cat $auxfile_E >> $StarterFile
            ;;
   esac
done
cat $StarterFile | ./parallel -P$threads

mkdir -p "Tests/Main_${p}/eval/"

for solver in "${solvers[@]}"; do
    echo "Evaluating $solver on bilevel instances..."
case "$solver" in
        Yasol_FA)
            python3 evalYasol.py Main_${p} FA $timelimit
            ;;
        Yasol_LA)
            python3 evalYasol.py Main_${p} LA $timelimit
            ;;
        MibS)
            python3 evalMibS.py Main_${p} ${test_name} $timelimit
            ;;
        EQuIPS)
            python3 evalEQuIPS.py Main_${p} ${test_name} $timelimit
            ;;
   esac
done

python3 evalAll.py Main_${p}
python3 summary.py Main_${p}

python3 makePlot_updated.py Tests/Main_${p}/eval/ solver_updated.txt --output $(pwd)/cactus_plot.pdf --time-limit $timelimit
