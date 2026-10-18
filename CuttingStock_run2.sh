usage() {
    echo "Usage: $0 <probability> <threads> <timelimit> "
    echo
    echo "Examples:"
    echo "  $0 0.25 4 1800"
    echo "  $0 0.90 8 3600"
    exit 1
}

if [[ $# -lt 3 ]]; then
    usage
fi

PROBABILITY="$1"
THREADS="$2"
TIMELIMIT="$3"

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
echo "Probability: $PROBABILITY"
echo "Creating $NUM_END_DIGITS instance(s) per T-B-I combination."
echo "Threads: $THREADS"
echo "Timelimit: $TIMELIMIT"

RAW_DIR="instances/data"
BUILD_DIR="MultistageRobustCuttingStockProblem/build"

echo "Please provide the path to your CPLEX executable!"
read -r -e -p ":" THE_CPLEX_PATH
testname="CuttingStock_type2_${PROBABILITY}_${TIMELIMIT}"
rm -r Tests/$testname
echo "testname is $testname"

# GenerateModelFiles creates all supported files by default.
# Therefore, we disable everything that is not needed.
MODEL_FLAGS=()

# These are not needed for the solver set described here.
MODEL_FLAGS+=("--no-rc" "--no-ro-rc")

# ------------------------------------------------------------
# Select existing raw files by final seed digit and generate
# only the required model files.
# ------------------------------------------------------------

shopt -s nullglob

selected_count=0
echo "Generating model files "

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

LOG_DIR_RO=Tests/${testname}/Yasol_RO
LOG_DIR_MIP=Tests/${testname}/CPLEX_MIP
LOG_DIR_YASOL=Tests/${testname}/Yasol_QIP
mkdir -p $LOG_DIR_RO
mkdir -p $LOG_DIR_MIP
mkdir -p $LOG_DIR_YASOL
INSTANCE_DIR=Tests/${testname}/instances
mkdir -p "${INSTANCE_DIR}/RO"
mkdir -p "${INSTANCE_DIR}/MIP"
mkdir -p "${INSTANCE_DIR}/QLP"
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
    mv *RO.qlp ${INSTANCE_DIR}/RO
    mv *.qlp ${INSTANCE_DIR}/QLP
    mv *.lp ${INSTANCE_DIR}/MIP
    echo "../Yasol/build/yasol ${INSTANCE_DIR}/RO/${stem_filename}_RO.qlp --timeLimit=$TIMELIMIT --isSimplyRestricted=1 --outputFile=1> $LOG_DIR_RO/${stem_filename}.log 2>&1" >> $StarterFile
    echo "../Yasol/build/yasol ${INSTANCE_DIR}/QLP/${stem_filename}.qlp --timeLimit=$TIMELIMIT --isSimplyRestricted=1 > $LOG_DIR_YASOL/${stem_filename}.log 2>&1" >> $StarterFile
    echo $THE_CPLEX_PATH -c "read $(pwd)/${INSTANCE_DIR}/MIP/${stem_filename}_MIP.lp" \"set timelimit $TIMELIMIT\" \"set threads 1\" \"set logfile $(pwd)/$LOG_DIR_MIP/${stem_filename}.log\" \"optimize\" \"write $(pwd)/$LOG_DIR_MIP/${stem_filename}.sol\" \"quit\" "&> /dev/null"  >> $StarterFile
done
echo "Run tests in parallel"
cat $StarterFile | ./parallel -P$THREADS

mkdir -p "Tests/${testname}/eval"

echo "Reading found solutions and creating evaluation instances"
./CreateROCheck.sh $testname
./CreateMIPCheck.sh $testname
echo "Done creating evaluation instances"
CHECK_DIR=Tests/$testname/check

CheckStarter="StarterCheck_$testname.txt"
rm $CheckStarter
for filename in ${CHECK_DIR}/*.qlp; do
    realname=${filename##*/}
    echo "../Yasol/build/yasol $filename --timeLimit=$TIMELIMIT > ${CHECK_DIR}/$realname.log 2>&1" >> $CheckStarter
done

cat $CheckStarter| ./parallel -P$THREADS

python3 evalYasol_QIP4check.py $testname $TIMELIMIT
python3 evalYasol_check.py Tests/$testname/check/ $TIMELIMIT

python3 createViolin.py Tests/$testname/check/ Tests/$testname/eval/Yasol_QIP_${testname}_.csv violinPlot.pdf

echo "Done."
