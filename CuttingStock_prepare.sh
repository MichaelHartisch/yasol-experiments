MainFolder=$(pwd)

cd CuttingStock

if [[ -d "MultistageRobustCuttingStockProblem/.git" ]]; then
    echo "MultistageRobustCuttingStockProblem repository already cloned. Skipping git clone."
elif [[ -d "MultistageRobustCuttingStockProblem" ]]; then
    echo "MultistageRobustCuttingStockProblem folder already exists. Skipping git clone. But make sure the correct version is available"
else
    echo "Cloning repository..."
    git clone https://github.com/MichaelHartisch/MultistageRobustCuttingStockProblem || {
        echo "Error: Failed to clone repository." >&2
        exit 1
    }
fi
cd MultistageRobustCuttingStockProblem
cmake -S . -B build
cmake --build build
cd ..
./create_raws.sh 10

echo "Preparations for MultistageRobustCuttingStockProblem tests completed"
