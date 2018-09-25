#!/usr/bin/env bash

# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Ensure we're in a virtualenv.
if [ "$VIRTUAL_ENV" == "" ] ; then
    echo "ERROR: not in a virtual environment."
    exit -1
fi

# Setup variables.
CACHE="/tmp/install-pygtk-$$"
CORES=$1

# Make temp directory.
mkdir -p $CACHE

# Test for py2cairo.
echo -e "\E[1m * Checking for cairo...\E[0m"
python -c "
try: import cairo; raise SystemExit(0)
except ImportError: raise SystemExit(-1)"

if [ $? == 255 ] ; then
    echo -e "\E[1m * Installing cairo...\E[0m"
    # Fetch, build, and install py2cairo.
    (   cd $CACHE
        curl 'https://www.cairographics.org/releases/py2cairo-1.10.0.tar.bz2' > "py2cairo.tar.bz2"
        tar -xvf py2cairo.tar.bz2
        (   cd py2cairo-*
            autoreconf -ivf
            ./configure --prefix=$VIRTUAL_ENV --disable-dependency-tracking
            make -j${CORES}
            make install
        )
    )
fi

# Test for gobject.
echo -e "\E[1m * Checking for gobject...\E[0m"
python -c "
try: import gobject; raise SystemExit(0)
except ImportError: raise SystemExit(-1)"

if [ $? == 255 ] ; then
    echo -e "\E[1m * Installing gobject...\E[0m"
    # Fetch, build, and install gobject.
    (   cd $CACHE
        curl 'http://ftp.gnome.org/pub/GNOME/sources/pygobject/2.28/pygobject-2.28.6.tar.bz2' > 'pygobject.tar.bz2'
        tar -xvf pygobject.tar.bz2
        (   cd pygobject-*
            ./configure --prefix=$VIRTUAL_ENV --disable-introspection
            make -j${CORES}
            make install
        )
    )
fi

# Test for gtk.
echo -e "\E[1m * Checking for gtk...\E[0m"
python -c "
try: import gtk; raise SystemExit(0)
except ImportError: raise SystemExit(-1)" 2&> /dev/null

if [ $? == 255 ] ; then
    echo -e "\E[1m * Installing gtk...\E[0m"
    # Fetch, build, and install gtk.
    (   cd $CACHE
        curl -L 'https://files.pythonhosted.org/packages/source/P/PyGTK/pygtk-2.24.0.tar.bz2' > 'pygtk.tar.bz2'
        tar -xvf pygtk.tar.bz2
        (   cd pygtk-*
            ./configure --prefix=$VIRTUAL_ENV PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$VIRTUAL_ENV/lib/pkgconfig
            make -j${CORES}
            make install
        )
    )
fi
