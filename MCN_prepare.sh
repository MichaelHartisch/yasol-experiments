MainFolder=$(pwd)

cd MCN

mkdir Instances
mkdir Instances/raw
mkdir Instances/QIP_DD
mkdir Instances/QIP_Poly
mkdir Instances/raw/public_repository
mkdir Instances/raw/rndgraph
mkdir Instances/raw/tree
if [[ -d "Critical-Node-Problem/.git" ]]; then
    echo "Critical-Node-Problem repository already cloned. Skipping git clone."
elif [[ -d "Critical-Node-Problem" ]]; then
    echo "Critical-Node-Problem folder already exists. Skipping git clone. But make sure the correct version is available"
else
    echo "Cloning repository..."
    git clone https://github.com/mxmmargarida/Critical-Node-Problem || {
        echo "Error: Failed to clone repository." >&2
        exit 1
    }
fi
echo "extracting raw files"
cd Critical-Node-Problem/Instances
unrar x -inul "public repository.rar"
if [[ ! -d "public repository" ]]; then
    echo "Error: Directory 'public repository' does not exist." >&2
    exit 1
fi
echo "Copying files"
find "public repository" -type f -print0 | while IFS= read -r -d '' file; do
    cp "$file" ../../Instances/raw/public_repository || exit 1
done

unrar x -inul tables_MNC.rar
if [[ ! -d "tables_MNC" ]]; then
    echo "Error: Directory 'tables_MNC' does not exist." >&2
    exit 1
fi
find "tables_MNC" -type f -print0 | while IFS= read -r -d '' file; do
    filename=$(basename "$file")
    case "$filename" in
        tree*_0*)
            cp "$file" ../../Instances/raw/tree || exit 1
            ;;
        rnd*_0*)
            cp "$file" ../../Instances/raw/rndgraph || exit 1
            ;;
        *)
#            echo "Skipping $filename (unknown prefix)"
            ;;
    esac
done

echo "deleting not needed folders and files"
rm -r "public repository"
rm ../../Instances/raw/public_repository/*-intermediate
rm ../../Instances/raw/public_repository/soc-dolphins.mtx-5-5-5
rm ../../Instances/raw/public_repository/lap_25.mtx-3-3-3
rm ../../Instances/raw/public_repository/eco-mangwet.edges-5-5-5

cd ../..
echo "Creating QIP instances with decision-dependent uncertainty set."
python3 QIP_Generator.py DD
echo "Creating QIP instances with polyhedral uncertainty set."
python3 QIP_Generator.py Poly

echo "Preparations for MCN tests completed"
