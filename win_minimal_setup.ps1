echo "Creating virtual enviroment."
py -3.6 -m venv .venv
./venv-activate

echo "Installing dependencies"
echo "...pipwin..."
pip3 install pipwin==0.5.0
echo "...fann2..."
python -m pipwin install -r requirements\pipwin-requirements.txt
echo "...requirements..."
pip3 install -r requirements\win-requirements.txt
