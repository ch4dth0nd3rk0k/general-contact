# test base image
FROM python:3.11

# define the build arguments
ARG DCKRSRC

# install necessary dependencies
RUN apt-get update \
    && apt-get install -y \
      bash \
      git \
      gnupg \
      make \
      tree \
      wget \
      unzip \
    && rm -rf /var/lib/apt/lists/*

# Add the safe.directory config for Git
RUN git config --global --add safe.directory '*'

# download and install Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
    >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# set workdir
WORKDIR ${DCKRSRC}

# copy source
COPY . .

# install requirements (installs sbase)
RUN pip3 install -r tests/requirements.txt

# get chromedriver (sbase installed by requirements.txt)
RUN sbase install chromedriver
