OUTPUT_DIR="instances/data"
GENERATOR="MultistageRobustCuttingStockProblem/build/GenerateInstances"
numInstances=$1
mkdir -p "${OUTPUT_DIR}"

seed=0
count=0

for T in {5..12}; do
    B=$(( T / 2 ))

    for I in {2..5}; do
        for ((repetition=1; repetition<=numInstances; repetition++)); do
            "${GENERATOR}" "${T}" "${B}" "${I}" "${seed}" "${OUTPUT_DIR}"

            seed=$(( seed + 1 ))
            count=$(( count + 1 ))
        done
    done
done

echo "Generated ${count} raw instances in: ${OUTPUT_DIR}"
