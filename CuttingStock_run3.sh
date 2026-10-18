usage() {
    echo "Usage: $0 <probability> <threads> <timelimit> <P>"
    echo  
    echo "Where P is the number of pieces of the piecewise-linear functions used in the decision rule approach."
    echo
    echo "Examples:"
    echo "  $0 0.25 4 1800 1"
    echo "  $0 0.90 8 300 2"
    exit 1
}

if [[ $# -lt 4 ]]; then
    usage
fi

PROBABILITY="$1"
THREADS="$2"
TIMELIMIT="$3"
P="$4"

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
echo "Probability: $PROBABILITY"
echo "Creating $NUM_END_DIGITS instance(s) per T-B-I combination."
echo "Threads: $THREADS"
echo "Timelimit: $TIMELIMIT"

cd CuttingStock
#cd MultistageRobustCuttingStockProblem
cd MultistageCuttingStockProblem


OS="$(uname -s)"
CPU="$(uname -m)"

case "${OS}:${CPU}" in
    Linux:x86_64|Linux:amd64)
        CPLEX_ARCH="x86-64_linux"
        ;;
    Linux:aarch64|Linux:arm64)
        CPLEX_ARCH="arm64_linux"
        ;;
    Darwin:x86_64)
        CPLEX_ARCH="x86-64_osx"
        ;;
    Darwin:arm64)
        CPLEX_ARCH="arm64_osx"
        ;;
    *)
        echo "Unsupported system: OS=$OS, CPU=$CPU"
        exit 1
        ;;
esac

echo "Detected system: $OS ($CPU)"
echo "Expected CPLEX architecture: $CPLEX_ARCH"


echo "In order to run the decision rule approach, IBM ILOG CPLEX is required. Please provide the path to your main CPLEX installation directory!"
echo "This might look like this: /opt/ibm/ILOG/CPLEX_Studio2211"

while true; do
read -r -e -p ":" CPLEX_INPUT || exit 1

    # Allow paths beginning with ~/.
    if [[ "$CPLEX_INPUT" == "~/"* ]]; then
        CPLEX_INPUT="$HOME/${CPLEX_INPUT#\~/}"
    fi

    if [[ ! -d "$CPLEX_INPUT" ]]; then
        echo "Directory does not exist. Please try again."
        continue
    fi

    # Convert to an absolute path.
    CPLEX_ROOT="$(cd "$CPLEX_INPUT" && pwd -P)"

    # Check expected CPLEX Studio directory structure.
    if [[ ! -f "$CPLEX_ROOT/cplex/include/ilcplex/cplexx.h" ]]; then
        echo "CPLEX header cplexx.h not found."
        echo "Please provide the main CPLEX Studio directory."
        continue
    fi

    if [[ ! -f "$CPLEX_ROOT/concert/include/ilconcert/iloenv.h" ]]; then
        echo "Concert headers not found."
        echo "Please provide the main CPLEX Studio directory."
        continue
    fi
    break
done

CPLEX_LIB_DIR="$CPLEX_ROOT/cplex/lib/$CPLEX_ARCH/static_pic"
CONCERT_LIB_DIR="$CPLEX_ROOT/concert/lib/$CPLEX_ARCH/static_pic"

for lib in \
    "$CPLEX_LIB_DIR/libcplex.a" \
    "$CPLEX_LIB_DIR/libilocplex.a" \
    "$CONCERT_LIB_DIR/libconcert.a"
do
    if [[ ! -f "$lib" ]]; then
        echo "Required CPLEX library not found:"
        echo "  $lib"
        echo
        echo "The installation may not support $CPLEX_ARCH."
        exit 1
    fi
done
echo
echo "CPLEX installation verified."
echo "CPLEX_ROOT: $CPLEX_ROOT"
echo "CPLEX_ARCH: $CPLEX_ARCH"

cmake -S . -B build \
  -DBUILD_DECISION_RULE=ON \
  -DCPLEX_ROOT=$CPLEX_ROOT \
  -DCPLEX_ARCH=$CPLEX_ARCH
cmake --build build
echo "Decision-rule executable built successfully."

cd ..

MODEL_FLAGS=()
MODEL_FLAGS+=("--no-rc" "--no-ro-rc" "--no-ro" "--no-mip")

selected_count=0
echo "Generating model files "
RAW_DIR="instances/data"

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
testname="CuttingStock_type3_${PROBABILITY}_${TIMELIMIT}"
BUILD_DIR="MultistageCuttingStockProblem/build"

LOG_DIR_YASOL=Tests/${testname}/Yasol_QIP
mkdir -p $LOG_DIR_YASOL
INSTANCE_DIR=Tests/${testname}/instances
mkdir -p "${INSTANCE_DIR}/QLP"
export TESTBENCH_DIR="$(pwd)"

for history in {1..4}; do
    LOG_DIR=Tests/${testname}/DR_${P}_${history}
    mkdir -p $LOG_DIR
done
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
    for history in {1..4}; do
#        echo "Rawfile is " $raw_file
        LOG_DIR=Tests/${testname}/DR_${P}_${history}
        realname=${raw_file##*/}
#        echo "Realname is "$realname
        realname=${realname::-4}
        echo "$BUILD_DIR/RunDecisionRule $raw_file $P $history $TIMELIMIT > $LOG_DIR/${realname}_DR_${P}_${history}.log 2>&1"  >> $StarterFile
    done

    filename="$(basename "$raw_file")"
    stem_filename="${filename%.raw}"
    printf "\r[%d/%d | %.1f%%] Generating model files for %s" \
    "$created_count" "$total" "$percent" "$filename"
    "$BUILD_DIR"/GenerateModelFiles "$raw_file" "${MODEL_FLAGS[@]}"
    mv *.qlp ${INSTANCE_DIR}/QLP
    echo "../Yasol/build/yasol ${INSTANCE_DIR}/QLP/${stem_filename}.qlp --timeLimit=$TIMELIMIT --isSimplyRestricted=1 > $LOG_DIR_YASOL/${stem_filename}.log 2>&1" >> $StarterFile
done

echo "Run tests in parallel"
cat $StarterFile | ./parallel -P$THREADS

mkdir -p "Tests/${testname}/eval"
for history in {1..4}; do
    ./evalDR.sh Tests/${testname}/DR_${P}_${history} Tests/${testname}/eval/evalDR_${P}_${history}.csv
done
python3 evalYasol_QIP4check.py ${testname} $TIMELIMIT

python3 plotDRtimes_all_colors.py --exclude-exact-infeasible --log-x Tests/${testname}/eval/ Tests/${testname}/eval/Yasol_QIP_${testname}_.csv 
python3 plotDRstatus_updated2.py Tests/${testname}/eval/ Tests/${testname}/eval/Yasol_QIP_${testname}_.csv dist
echo "Done."
