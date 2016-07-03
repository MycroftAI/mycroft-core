apt-get install -y make python-pip python-dev libffi-dev wget mpg123
./install-libspotify.sh

wget -q -O - https://apt.mopidy.com/mopidy.gpg | apt-key add -
wget -q -O /etc/apt/sources.list.d/mopidy.list https://apt.mopidy.com/jessie.list
apt-get update
apt-get install mopidy mopidy-spotify mopidy-local-sqlite mopidy-gmusic
# These are installed using pip for debian compatibility
