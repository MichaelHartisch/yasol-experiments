
set -euo pipefail
usage() {
    echo "Usage: $0 <testname> <timelimit> <probability> <graph_type> <aux_file>"
    exit 1
}

if (( $# != 5 )); then
    usage
fi

testname="$1"
timelimit="$2"
probability="$3"
graph_type="$4"
aux_file="$5"
MainPath=$(pwd)
# Fixed seed for reproducibility and for use of same instances in all test
RANDOM=42
if ! [[ "$timelimit" =~ ^[0-9]+$ ]] ||
   ! (( 10#$timelimit > 0 )); then
    echo "Error: Timelimit must be a positive integer." >&2
    exit 1
fi

if ! awk -v p="$probability" 'BEGIN {
    exit !(p ~ /^([0-9]+(\.[0-9]*)?|\.[0-9]+)$/ &&
           p >= 0 && p <= 1)
}'; then
    echo "Error: Probability must be between 0 and 1." >&2
    exit 1
fi

input_directory="Instances/raw/$graph_type"
log_directory="${MainPath}/Tests/$testname/MCN/$graph_type"

if [[ ! -d "$input_directory" ]]; then
    echo "Error: Directory '$input_directory' does not exist." >&2
    exit 1
fi

mkdir -p "Tests/$testname/MCN/$graph_type"

# Clear/create auxiliary file
: > "$aux_file"

# Regex for Omega-Theta-Lambda
pattern='(^|[^0-9])([0-9]+)-([0-9]+)-([0-9]+)($|[^0-9])'

for file in "$input_directory"/*; do
    random=$RANDOM
# Test instance with probability approximately p
    if awk -v r="$random" -v p="$probability" \
        'BEGIN { exit !(r < p * 32768) }'; then

        [[ -f "$file" ]] || continue
        filename="${file##*/}"

        # Extract Omega, Theta, Lambda
        if [[ ! "$filename" =~ $pattern ]]; then
            echo "Skipping $filename: no Omega-Theta-Lambda parameters"
            continue
        fi

        Omega="${BASH_REMATCH[2]}"
        Theta="${BASH_REMATCH[3]}"
        Lambda="${BASH_REMATCH[4]}"

         V=""
        E=""

        while IFS= read -r line || [[ -n "$line" ]]; do
            if [[ "$line" == "A = "* ]]; then
                E="${line#A = }"
            elif [[ "$line" == "V = "* ]]; then
                V="${line#V = }"
            fi
        done < "$file"

        if [[ -z "$V" || -z "$E" ]]; then
            echo "Error: Missing V or E in $filename" >&2
            exit 1
        fi

    log_file="$log_directory/$filename.log"

    python_code="import DAD; print(DAD.Defend_Attack_Defend(${V},${E},${Omega},${Theta},${Lambda}))"

    printf 'PYTHONPATH="%s" OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 timeout %ss python2.7 -c %q > %q\n' \
        "${MainPath}/Critical-Node-Problem" "$timelimit" "$python_code" "$log_file" \
        >> "$aux_file"
    fi
done
