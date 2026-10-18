echo "Download EQuIPS"

if [[ -d "EQuIPS/.git" ]]; then
    echo "EQuIPS repository already cloned. Skipping git clone."
elif [[ -d "EQuIPS" ]]; then
    echo "EQuIPS folder already exists. Skipping git clone."
else
    echo "Cloning repository..."
    git clone https://github.com/MichaelHartisch/EQuIPS.git || {
        echo "Error: Failed to clone repository." >&2
        exit 1
    }
fi

if [[ -d "EQuIPS/build" ]]; then
    echo "Folder EQuIPS/build already exists. Do you want to reinstall EQuIPS? Type 'yes' or 'quit'."
    while true; do
        read -r -p "Enter your choice: " re_install
        case "$re_install" in
            yes)
                echo "Delete build folder and reinstall"
                rm -r EQuIPS/build
                break
                ;;
            quit)
                echo "(Re)Installation cancelled."
                exit 0
                ;;
            *)
                echo "Invalid option. Please try again or type 'quit' to exit."
                echo ""
                ;;
        esac
    done
fi
if [[ -d "EQuIPS" ]]; then
    cd "EQuIPS" || exit 1
else
    echo "Directory EQuIPS does not exist." >&2
    exit 1
fi

    echo "EQuIPS uses Gurobi as IP solver."
    if [[ -n "${GUROBI_HOME:-}" ]]; then
        echo "Your 'GUROBI_HOME' environment variable is set to ${GUROBI_HOME}."
    else
        echo "Make sure you have Gurobi installed with a respective license."
        echo "Make sure the 'GUROBI_HOME' environment variable is set to respective directory, e.g., /opt/gurobi1200/linux64/."
        echo "Try again as soon as you have taken care of that"
        exit 1
    fi

echo "Compile EQuIPS now!"
cmake -B build
cmake --build build
echo "Finished installing EQuIPS"
