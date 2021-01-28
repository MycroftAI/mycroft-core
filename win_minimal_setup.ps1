echo "Creating virtual enviroment."
py -3.6 -m venv .venv
./venv-activate

echo "Installing dependencies"
pip3 install -r requirements\win-requirements.txt

echo "Installing mimic"

scripts/install-mimic-win.ps1

echo "Building precise"
git clone https://github.com/NoamDev/mycroft-precise.git precise-engine-build
cd precise-engine-build
git checkout 9c2eca94459a93dff24f36013d87b4923ee31c75
./build.bat
cd ..
$precise_gz = (Get-ChildItem precise-engine-build/dist/precise-engine*.tar.gz).toString()
py -c "import shutil; from os.path import expanduser; shutil.unpack_archive('$precise_gz',expanduser('~/.mycroft/precise'))"
