MainFolder=$(pwd)

cd Bilevel
echo "I will now download and unzip the interdiction.tar.gz from the BOBILib."
if [[ -f  interdiction.tar.gz ]]; then
    echo "Zipped interdiction instances already exist."
else
    wget "https://gitlab.uni-trier.de/nlopt/bobilib-data/-/raw/master/downloads/instances/interdiction.tar.gz"
fi

if [[ -d interdiction ]]; then
    echo "'interdiction' directory already exists. I will not unpack 'interdiction.tar.gz' again."
else
    tar -xzf interdiction.tar.gz
fi
rm -r Instances 2>/dev/null
mkdir -p Instances

echo "I will now copy the instances into a new directory structure"
SOURCE=$(realpath interdiction)
DEST=$(realpath Instances)

# Find directories that contain no subdirectories
find "$SOURCE" -type d -links 2 -print0 |
while IFS= read -r -d '' dir; do
    dirname=$(basename "$dir")
    mkdir -p Instances/$dirname/MibS
    mkdir -p Instances/$dirname/QLP_FA
    mkdir -p Instances/$dirname/QLP_LA
    cp -a "$dir/." "Instances/$dirname/MibS"
done

echo "I now remove instances that are not used in the test."
rm -r Instances/clique
rm -r Instances/generalized
rm -r Instances/or

rm Instances/inter-assig/MibS/2AP05-1.*
rm Instances/inter-assig/MibS/2AP05-13.*
rm Instances/inter-assig/MibS/2AP05-14.*
rm Instances/inter-assig/MibS/2AP05-23.*
rm Instances/inter-assig/MibS/2AP05-24.*

rm -r interdiction

echo "unpack 'mps.gz' files"
find "Instances" -type f -name "*.gz" -print0 |
while IFS= read -r -d '' file; do
    gunzip "$file"
done

echo "Download and compile instance converter"

if [[ -d mibs2qlp ]]; then
    echo "already installed"
else
    git clone https://github.com/MichaelHartisch/mibs2qlp 
fi
if [[ ! -d build ]]; then
    cd mibs2qlp
    cmake -B build
    cd build
    make
    cd ../..
fi

echo "Create qlp files from mps/aux files."
# Recursively find all .mps files
find "Instances" -type f -name "*.mps" | while read -r mpsfile; do
    folder_path=$(dirname "$(dirname "$mpsfile")")
    base="${mpsfile%.mps}"
    instance=$(basename "$mpsfile")
    instance="${instance%.mps}"
    auxfile="${base}.aux"
    qlpfile="${folder_path}/QLP_FA/${instance}.qlp"

    # Check whether matching .aux file exists
    if [[ -f "$auxfile" ]]; then
        mibs2qlp/build/mibs2qlp "$mpsfile" "$auxfile" "${qlpfile}"
    else
        echo "Skipping $mpsfile (missing $auxfile)"
    fi
    if [[ $(basename "$folder_path") == "kp" ]];then
        sed -i 's/<= +inf/<= 1/g' "$qlpfile" 
    fi
    qlpfile_LA="${folder_path}/QLP_LA/${instance}.qlp"
    python3 transformer.py $qlpfile ${qlpfile_LA}
done


