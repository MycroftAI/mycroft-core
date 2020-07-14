# Build an Ubuntu-based container to run Mycroft
#
#   The steps in this build are ordered from least likely to change to most
#   likely to change.  The intent behind this is to reduce build time so things
#   like Jenkins jobs don't spend a lot of time re-building things that did not
#   change from one build to the next.
#
FROM ubuntu:18.04 as core_builder
ARG platform
ENV TERM linux
ENV DEBIAN_FRONTEND noninteractive
# Un-comment any package sources that include a multiverse
RUN sed -i 's/# \(.*multiverse$\)/\1/g' /etc/apt/sources.list
# Install Server Dependencies for Mycroft
RUN apt-get update && apt-get install -y \
    autoconf \
    automake \
    bison \
    build-essential \
    curl \
    flac \
    git \
    jq \
    libfann-dev \
    libffi-dev \
    libicu-dev \
    libjpeg-dev \
    libglib2.0-dev \
    libssl-dev \
    libtool \
    locales \
    mpg123 \
    pkg-config \
    portaudio19-dev \
    pulseaudio \
    pulseaudio-utils \
    python3 \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-venv \
    screen \
    sudo \
    swig \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set the locale
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

ENV USER root
ENV CI true
# Setup the virtual environment
#   This may not be the most efficient way to do this in terms of number of
#   steps, but it is built to take advantage of Docker's caching mechanism
#   to only rebuild things that have changed since the last build.
RUN mkdir -p /opt/mycroft/mycroft-core /opt/mycroft/skills /root/.mycroft /var/log/mycroft
RUN python3 -m venv "/opt/mycroft/mycroft-core/.venv"

# Install required Python packages.  Generate hash, which mycroft core uses to
# determine if any changes have been made since it last started
WORKDIR /opt/mycroft/mycroft-core
RUN .venv/bin/python -m pip install pip==20.0.2
COPY requirements/requirements.txt .
RUN .venv/bin/python -m pip install -r requirements.txt
COPY requirements/extra-audiobackend.txt .
COPY requirements/extra-stt.txt .
COPY requirements/extra-mark1.txt .
RUN .venv/bin/python -m pip install -r extra-audiobackend.txt \
    && .venv/bin/python -m pip install -r extra-stt.txt \
    && .venv/bin/python -m pip install -r extra-mark1.txt
COPY requirements/tests.txt .
RUN .venv/bin/python -m pip install -r tests.txt
COPY dev_setup.sh .
RUN md5sum requirements.txt tests.txt extra-audiobackend.txt extra-stt.txt extra-mark1.txt dev_setup.sh > .installed

# Add the mycroft core virtual environment to the system path.
ENV PATH /opt/mycroft/mycroft-core/.venv/bin:$PATH

# Install Mark I default skills
RUN msm -p mycroft_mark_1 default
COPY . /opt/mycroft/mycroft-core
RUN .venv/bin/python -m pip install --no-deps /opt/mycroft/mycroft-core
EXPOSE 8181


# Integration Test Suite
#
#   Build against this target to set the container up as an executable that
#   will run the "voight_kampff" integration test suite.
#
FROM core_builder as voight_kampff_builder
ARG platform
# Setup a dummy TTS backend for the audio process
RUN mkdir /etc/mycroft
RUN echo '{"tts": {"module": "dummy"}}' > /etc/mycroft/mycroft.conf
RUN mkdir ~/.mycroft/allure-result

# The behave feature files for a skill are defined within the skill's
# repository.  Copy those files into the local feature file directory
# for test discovery.
WORKDIR /opt/mycroft/mycroft-core
# Generate hash of required packages
RUN python -m test.integrationtests.voight_kampff.test_setup -c test/integrationtests/voight_kampff/default.yml

# Setup and run the integration tests
ENV PYTHONPATH /opt/mycroft/mycroft-core/
WORKDIR /opt/mycroft/mycroft-core/test/integrationtests/voight_kampff
ENTRYPOINT ["./run_test_suite.sh"]
