#!/usr/bin/env bash

TOP=$(cd $(dirname $0)/.. && pwd -L)

if [ "$1" = "-q" ]; then
  QUIET="echo"
fi

# clean
cd ${TOP}
rm -rf dist

function _run() {
  if [[ "$QUIET" ]]; then
    echo "$*"
  else
    eval "$@"
  fi
}

function python_package() {
  local SETUP_SCRIPT=$1
  cp ${SETUP_SCRIPT} ${TOP}/setup.py
  python ${TOP}/setup.py clean
  python ${TOP}/setup.py bdist_egg
  python ${TOP}/setup.py sdist
  _run python ${TOP}/setup.py sdist upload -r mycroft
  rm ${TOP}/setup.py
}

VERSION="$(basename $(git describe --abbrev=0 --tags) | sed -e 's/v//g')"

echo "version=\"${VERSION}\"" > ${TOP}/mycroft/__version__.py

# build and upload pypi distribution to internal pypi mirror
cd ${TOP}
python_package mycroft-base-setup.py
python_package skills-sdk-setup.py


# build distributable virtualenv
ARCH="$(dpkg --print-architecture)"
ARTIFACT_BASE="mycroft-standalone-${ARCH}-${VERSION}"
MYCROFT_ARTIFACT_DIR=${TOP}/build/${ARTIFACT_BASE}

virtualenv --always-copy --clear ${MYCROFT_ARTIFACT_DIR}
virtualenv --always-copy --clear --relocatable ${MYCROFT_ARTIFACT_DIR}
. ${MYCROFT_ARTIFACT_DIR}/bin/activate

pip install -r ${TOP}/requirements.txt --trusted-host pypi.mycroft.team
cd ${TOP}/pocketsphinx-python
python setup.py install
cd ${TOP}
python mycroft-base-setup.py install

${TOP}/install-pygtk.sh

virtualenv --always-copy --relocatable ${MYCROFT_ARTIFACT_DIR}

mkdir -p ${TOP}/dist
cd ${TOP}/build
tar -czf ${TOP}/dist/${ARTIFACT_BASE}.tar.gz ${ARTIFACT_BASE}

# package distributable virtualenv into deb
function replace() {
  local FILE=$1
  local PATTERN=$2
  local VALUE=$3
  local TMP_FILE="/tmp/$$.replace"
  cat ${FILE} | sed -e "s/${PATTERN}/${VALUE}/g" > ${TMP_FILE}
  mv ${TMP_FILE} ${FILE}
}

DEB_BASE="mycroft-standalone_${VERSION}-1"
DEB_DIR=${TOP}/build/${DEB_BASE}
mkdir -p ${DEB_DIR}/DEBIAN

echo "Creating debian control file"
# setup control file
CONTROL_FILE=${DEB_DIR}/DEBIAN/control
cp ${TOP}/publish/deb_base/control.template ${CONTROL_FILE}
replace ${CONTROL_FILE} "%%PACKAGE%%" "mycroft-standalone"
replace ${CONTROL_FILE} "%%VERSION%%" "${VERSION}"
replace ${CONTROL_FILE} "%%ARCHITECTURE%%" "${ARCH}"
replace ${CONTROL_FILE} "%%DESCRIPTION%%" "mycroft-standalone"

# setup init scripts
function setup_init_script() {
  local NAME=$1
  echo "Creating init script for ${NAME}"
  INIT_SCRIPT=${DEB_DIR}/etc/init.d/${NAME}
  mkdir -p $(dirname ${INIT_SCRIPT})
  cp ${TOP}/publish/deb_base/init.template ${INIT_SCRIPT}
  replace ${INIT_SCRIPT} "%%NAME%%" "${NAME}"
  replace ${INIT_SCRIPT} "%%DESCRIPTION%%" "${NAME}"
  replace ${INIT_SCRIPT} "%%COMMAND%%" "\/opt\/mycroft\/bin\/${NAME}"
  replace ${INIT_SCRIPT} "%%USERNAME%%" "mycroft"
  chmod a+x ${INIT_SCRIPT}
}

setup_init_script "mycroft-messagebus"
setup_init_script "mycroft-skills"
setup_init_script "mycroft-speech-client"
setup_init_script "mycroft-enclosure-client"

mkdir -p ${DEB_DIR}/opt/mycroft
cp -rf ${TOP}/build/${ARTIFACT_BASE}/* ${DEB_DIR}/opt/mycroft

# install mimic
${TOP}/install-mimic.sh
MIMIC_INSTALL_DIR="${DEB_DIR}/opt/mycroft/bin"
mkdir -p ${MIMIC_INSTALL_DIR}
cp -rf ${TOP}/build/mimic/bin/mimic ${MIMIC_INSTALL_DIR}

mkdir -p ${DEB_DIR}/etc/mycroft
# write installed config file
cat > ${DEB_DIR}/etc/mycroft/mycroft.ini << EOM
[tts]
module = "mimic"
mimic.path = "/opt/mycroft/bin/mimic"
mimic.voice = "/opt/mycroft/lib/python2.7/site-packages/Mycroft-${VERSION}-py2.7.egg/mycroft/tts/mycroft_voice_4.0.flitevox"
[metrics_client]
enabled = True

EOM


# ensures enclosure version
ENCLOSURE_DIR=${DEB_DIR}/opt/enclosure
mkdir -p ${ENCLOSURE_DIR}
cp ${TOP}/mycroft/client/enclosure/version.txt ${ENCLOSURE_DIR}


cd $(dirname ${DEB_DIR})
dpkg-deb --build ${DEB_BASE}
mv *.deb ${TOP}/dist


cd ${TOP}/dist
_run s3cmd -c ${HOME}/.s3cfg.mycroft-artifact-writer sync --acl-public . s3://bootstrap.mycroft.ai/artifacts/${ARCH}/${VERSION}/
echo ${VERSION} > ${TOP}/dist/latest
_run s3cmd -c ${HOME}/.s3cfg.mycroft-artifact-writer put --acl-public ${TOP}/dist/latest s3://bootstrap.mycroft.ai/artifacts/${ARCH}/latest
