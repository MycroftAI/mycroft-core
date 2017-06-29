sudo systemctl stop mycroft-speech-client
sudo systemctl stop mycroft-skills
sudo systemctl stop mycroft-messagebus
sudo systemctl start mycroft-messagebus
sudo systemctl start mycroft-skills
sudo systemctl start mycroft-speech-client
