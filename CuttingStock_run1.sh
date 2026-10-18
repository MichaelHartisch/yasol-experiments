AVAILABLE_SOLVERS=("Yasol" "EQuIPS" "CPLEX")

usage() {
    echo "Usage: $0 <probability> <threads> <timelimit> <solver1> [solver2] ..."
    echo
    echo "Available solvers:"
    printf "  %s\n" "${AVAILABLE_SOLVERS[@]}"
    echo
    echo "Examples:"
    echo "  $0 0.25 4 1800 Yasol EQuIPS"
    echo "  $0 0.90 8 3600 Yasol CPLEX"
    exit 1
}

contains_solver() {
    local solver="$1"
    shift
    local s
    for s in "$@"; do
        [[ "$s" == "$solver" ]] && return 0
    done
    return 1
}

is_available_solver() {
    local solver="$1"
    local s
    for s in "${AVAILABLE_SOLVERS[@]}"; do
        [[ "$s" == "$solver" ]] && return 0
    done
    return 1
}

if [[ $# -lt 4 ]]; then
    usage
fi

PROBABILITY="$1"
THREADS="$2"
TIMELIMIT="$3"
shift 3

SOLVERS=("$@")

for solver in "${SOLVERS[@]}"; do
    if ! is_available_solver "$solver"; then
        echo "Unknown solver: $solver"
        usage
    fi
done

cd CuttingStock

NUM_END_DIGITS=$(
python3 - <<EOF
import math
p = float("$PROBABILITY")
if p < 0 or p > 1:
    raise SystemExit("probability must be in [0,1]")
print(int(math.floor(10 * p + 1e-12)))
EOF
)

if [[ "$NUM_END_DIGITS" -eq 0 ]]; then
    echo "Probability $PROBABILITY selects no instances."
    exit 0
fi
echo "Selected solvers: ${SOLVERS[*]}"
echo "Probability: $PROBABILITY"
echo "Creating $NUM_END_DIGITS instance(s) per T-B-I combination."
echo "Threads: $THREADS"
echo "Timelimit: $TIMELIMIT"

RAW_DIR="instances/data"
BUILD_DIR="MultistageRobustCuttingStockProblem/build"

NEED_QLP=0
NEED_MIP=0

if contains_solver "Yasol" "${SOLVERS[@]}" || contains_solver "EQuIPS" "${SOLVERS[@]}"; then
    NEED_QLP=1
    rm -r "instances/QLP" 2>/dev/null
    mkdir -p "instances/QLP"
fi

if contains_solver "EQuIPS" "${SOLVERS[@]}"; then
    if [[ ! -d "EQuIPS" ]]; then
        echo "Error: 'EQuIPS not installed."
        exit 1        
    fi
fi
if contains_solver "CPLEX" "${SOLVERS[@]}"; then
    NEED_MIP=1
    rm -r "instances/RC"
    mkdir -p "instances/RC"
    echo "Please provide the path to your CPLEX executable!"
    read -r -e -p ":" THE_CPLEX_PATH
fi
testname="CuttingStock_type1_${PROBABILITY}_${TIMELIMIT}"
echo "testname is $testname"

if contains_solver "Yasol" "${SOLVERS[@]}"; then
    export LOG_DIR_YASOL=Tests/${testname}/Yasol_QIP
    mkdir -p $LOG_DIR_YASOL
fi

if contains_solver "EQuIPS" "${SOLVERS[@]}"; then
    export LOG_DIR_EQUIPS=Tests/${testname}/EQuIPS_QIP
    mkdir -p $LOG_DIR_EQUIPS
fi

if contains_solver "CPLEX" "${SOLVERS[@]}"; then
    export LOG_DIR_CPLEX=Tests/${testname}/CPLEX_RC
    mkdir -p $LOG_DIR_CPLEX
fi

# GenerateModelFiles creates all supported files by default.
# Therefore, we disable everything that is not needed.
MODEL_FLAGS=()

# These are not needed for the solver set described here.
MODEL_FLAGS+=("--no-ro" "--no-ro-rc" "--no-mip")

if [[ "$NEED_QLP" -eq 0 ]]; then
    MODEL_FLAGS+=("--no-qip")
fi

if [[ "$NEED_MIP" -eq 0 ]]; then
    MODEL_FLAGS+=("--no-rc")
fi

# ------------------------------------------------------------
# Select existing raw files by final seed digit and generate
# only the required model files.
# ------------------------------------------------------------

shopt -s nullglob

selected_count=0
echo "Generating model files "
if [[ "$NEED_MIP" -eq 1 ]]; then
echo "As you also run CPLEX, this might take a while; LP files of DEP will become large"
fi

for raw_file in "$RAW_DIR"/binPacking_*.raw; do
    filename="$(basename "$raw_file")"
    stem="${filename%.raw}"
    seed="${stem##*_}"

    if [[ ! "$seed" =~ ^[0-9]+$ ]]; then
        echo "Skipping file with nonnumeric seed: $filename"
        continue
    fi

    end_digit=$((seed % 10))

    if (( end_digit >= NUM_END_DIGITS )); then
        continue
    fi

    selected_files+=("$raw_file")
done

total=${#selected_files[@]}

if (( total == 0 )); then
    echo "No raw files selected."
    exit 0
fi

echo "Selected raw files: $total"
echo

created_count=0
StarterFile="ParallelRuns${testname}.txt"
rm $StarterFile
for raw_file in "${selected_files[@]}"; do
    created_count=$((created_count + 1))

    percent=$(
        python3 - <<EOF
print(f"{100.0 * $created_count / $total:.1f}")
EOF
    )

    filename="$(basename "$raw_file")"
    stem_filename="${filename%.raw}"
    printf "\r[%d/%d | %.1f%%] Generating model files for %s" \
    "$created_count" "$total" "$percent" "$filename"
    "$BUILD_DIR"/GenerateModelFiles "$raw_file" "${MODEL_FLAGS[@]}"
    if [[ "$NEED_QLP" -eq 1 ]]; then
        mv *.qlp instances/QLP
    fi
    if [[ -v LOG_DIR_YASOL ]]; then
        echo "../Yasol/build/yasol instances/QLP/${stem_filename}.qlp --timeLimit=$TIMELIMIT --isSimplyRestricted=1 > $LOG_DIR_YASOL/${stem_filename}.log 2>&1" >> $StarterFile
    fi
    if [[ -v LOG_DIR_EQUIPS ]]; then
        echo "../EQuIPS/build/EQuIPS instances/QLP/${stem_filename}.qlp $TIMELIMIT > $LOG_DIR_EQUIPS/${stem_filename}.log 2>&1" >> $StarterFile
    fi
    if [[ -v LOG_DIR_CPLEX ]]; then
       echo $THE_CPLEX_PATH -c "read $(pwd)/instances/RC/${stem_filename}_RC.lp" \"set timelimit $TIMELIMIT\" \"set threads 1\" \"set logfile $(pwd)/$LOG_DIR_CPLEX/${stem_filename}.log\" \"optimize\" \"write $(pwd)/$LOG_DIR_CPLEX/${stem_filename}.sol\" \"quit\" "&> /dev/null"  >> $StarterFile
    fi
    if [[ "$NEED_MIP" -eq 1 ]]; then
        mv *.lp instances/RC
    fi
done
echo "Run tests in parallel"
cat $StarterFile | ./parallel -P$THREADS

mkdir -p "Tests/${testname}/eval/QIPvsRC"
if [[ -v LOG_DIR_YASOL ]]; then
    python3 evalYasol_QIP.py $testname $TIMELIMIT
fi
if [[ -v LOG_DIR_EQUIPS ]]; then
    python3 evalEQuIPS_QIP.py $testname $TIMELIMIT
fi
if [[ -v LOG_DIR_CPLEX ]]; then
    python3 evalCPLEX_RC.py $testname $TIMELIMIT
fi
python3 evalAll_QIPvsRC.py $testname
python3 summary_QIPvsRC.py "Tests/${testname}/eval/QIPvsRC"
echo
echo "Done."
