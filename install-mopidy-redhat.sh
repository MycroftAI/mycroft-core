
yum install -y make python-pip python-devel libffi-dev wget

cd /usr/src
wget http://sourceforge.net/projects/mpg123/files/mpg123/1.23.4/mpg123-1.23.4.tar.bz2/download
mv download mpg123-1.23.4.tar.bz2
tar -xjvf mpg123-1.23.4.tar.bz2
cd mpg123-1.23.4
./configure && make && make install

./install-libspotify.sh

#This is the most sketchy way in the world to possibly install mopidy. Turn out RHEL hates python 2.7
#This is a hacky way to get it working by installing from source. Should work though. I suggest you test if you have your own red hat system.

yum groupinstall "Development tools"
yum install zlib-devel
yum install bzip2-devel
yum install openssl-devel
yum install ncurses-devel
yum install sqlite-devel

cd /opt
wget --no-check-certificate https://www.python.org/ftp/python/2.7.6/Python-2.7.6.tar.xz
tar xf Python-2.7.6.tar.xz
cd Python-2.7.6
./configure --prefix=/usr/local
make && make altinstall

wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
sudo /usr/local/bin/python2.7 ez_setup.py
sudo /usr/local/bin/easy_install-2.7 pip

yum install -y python-gstreamer1 gstreamer1-plugins-good gstreamer1-plugins-ugly

/usr/local/bin/pip2.7 install -U mopidy

/usr/local/bin/pip2.7 install -U mopidy-spotify

/usr/local/bin/pip2.7 install -U mopidy-local-sqlite

/usr/local/bin/pip2.7 install -U mopidy-gmusic
