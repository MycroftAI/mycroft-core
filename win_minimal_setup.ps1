echo "Creating virtual enviroment."
py -3.6 -m venv .venv
./venv-activate

echo "Installing dependencies"
pip3 install -r requirements\win-requirements.txt

echo "Installing mimic"

scripts/install-mimic-win.ps1