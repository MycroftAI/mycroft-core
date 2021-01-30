echo "Creating virtual enviroment."
py -3.6 -m venv .venv
CALL .\venv-activate.bat

echo "Installing dependencies"
pip3 install -r requirements\win-requirements.txt

echo "Installing mimic"

python scripts\install-mimic-win.py

echo "Building precise"
git clone https://github.com/NoamDev/mycroft-precise.git precise-engine-build
cd precise-engine-build
git checkout 9c2eca94459a93dff24f36013d87b4923ee31c75
./build.bat
cd ..
python -c "import shutil;from os.path import expanduser;from glob import glob;precise_targz = glob('precise-engine-build/dist/precise-engine*.tar.gz')[0];shutil.unpack_archive(precise_targz',expanduser('~/.mycroft/precise'))"
