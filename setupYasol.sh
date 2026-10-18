echo "Download Yasol"

if [[ -d "Yasol/.git" ]]; then
    echo "Yasol repository already cloned. Skipping git clone."
elif [[ -d "Yasol" ]]; then
    echo "Yasol folder already exists. Skipping git clone. But make sure the correct Yasol version is available"
else
    echo "Cloning repository..."
#    git clone https://github.com/MichaelHartisch/Yasol.git || {
    git clone --depth 1 --branch v.4.6 https://github.com/MichaelHartisch/Yasol.git || {
        echo "Error: Failed to clone repository." >&2
        exit 1
    }
fi

if [[ -d "Yasol/build" ]]; then
    echo "Folder Yasol/build already exists. Do you want to reinstall Yasol? Type 'yes' or 'quit'."
    while true; do
        read -r -p "Enter your choice: " re_install
        case "$re_install" in
            yes)
                echo "Delete build folder and reinstall"
                rm -r Yasol/build
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
if [[ -d "Yasol" ]]; then
    cd "Yasol" || exit 1
else
    echo "Directory Yasol does not exist." >&2
    exit 1
fi

while true; do
    echo "Select option for Yasol Installation:"
    echo "  		cplex | compile with cplex"
    echo "		highs | compile with highs"
    echo "		coin  | compile with coinOR tools"
    echo ""
    read -r -p "Enter your choice: " lp_solver
    case "$lp_solver" in
        cplex|highs|coin)
            echo "Selected LP solver: $lp_solver"
            break
            ;;
        quit)
            echo "Installation cancelled."
            exit 0
            ;;
        *)
            echo "Invalid option. Please try again or type 'quit' to exit."
            echo ""
            ;;
    esac
done

echo "Install Yasol with ${lp_solver}"
./configure --${lp_solver}
cd build && make
echo "Finished installing Yasol"
echo "Let us run a quick test..."
ctest --output-on-failure
