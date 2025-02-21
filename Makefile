.PHONY: check-docker check-image check-workdir check-deps build serve server-container pause \
        address stop-server restart-server print-config lint tests pytest isort black flake8 \
        mypy install-act check-act run-act-tests shell

# Usage:
# make check-docker     # check docker and host dependencies
# make check-image      # check if the Docker image exists
# make check workdir    # confirm working dir is correct
# make check-deps       # check dependencies inside Docker
# make build            # build the docker image
# make serve            # serve the website
# make server-container # build server container
# make pause            # pause 1 second (to pause between commands)
# make address          # get Docker container address/port
# make stop-server      # stop the running web server
# make restart-server   # restart the running web server
# make print-config     # print info on variables used
# make lint             # run linters
# make test             # run full testing suite
# make pytest           # run pytest in docker container
# make isort            # run isort in docker container
# make black            # run black in docker container
# make flake8           # run flake8 in docker container
# make mypy             # run mypy in docker container
# make install-act      # install act command
# make check-act        # check if act is installed
# make run-act-tests    # run github action tests locally
# make shell            # create interactive shell in docker container

################################################################################
# GLOBALS                                                                      #
################################################################################

# general variables
CURRENTDIR := $(shell pwd)
PSECS := 1

# extract the github username from the remote URL (SSH or HTTPS)
get_github_user = $(shell \
    remote_url=$(1); \
    if echo $$remote_url | grep -q "git@github.com"; then \
	    dirname $$remote_url | sed 's/\:/ /g' | awk '{print $$2}' | \
	    cut -d/ -f1 | tr '[:upper:]' '[:lower:]'; \
    elif echo $$remote_url | grep -q "https://github.com"; then \
	    echo $$remote_url | sed 's/https:\/\/github.com\/\([^\/]*\)\/.*/\1/' | \
	    tr '[:upper:]' '[:lower:]'; \
    else \
        echo "Invalid remote URL: $$remote_url" && exit 1; \
    fi)

# dynamically retrieve the github username, repository name, and branch
GITHUB_USER = $(call get_github_user,$(shell git config --get remote.origin.url))
REPO_NAME ?= $(shell basename -s .git `git config --get remote.origin.url`)
GIT_BRANCH ?= $(shell git rev-parse --abbrev-ref HEAD)

# docker-related variables
DCTNR := webserver.$(notdir $(PWD))
DCKRSRC = /usr/local/src/$(REPO_NAME)
DCKRTTY := $(if $(filter true,$(NOTTY)),-i,-it)
USE_VOL ?= true
USE_USR ?= true
TESTVOL = $(if $(filter true,$(USE_VOL)),-v ${CURRENTDIR}:${DCKRSRC},)
DCKRUSR = $(if $(filter true,$(USE_USR)),--user $(shell id -u):$(shell id -g),)
DCKRTST = docker run --rm ${DCKRUSR} ${TESTVOL} ${DCKRTTY}
DCKRTAG ?= $(GIT_BRANCH)
DCKR_PULL ?= true
DCKR_NOCACHE ?= false
DCKRIMG ?= ghcr.io/$(GITHUB_USER)/$(REPO_NAME):$(DCKRTAG)

# Define the docker build command with optional --no-cache
define DOCKER_BUILD
	docker build --build-arg DCKRSRC=${DCKRSRC} -t $1 . --load \
	  $(if $(filter true,$(DCKR_NOCACHE)),--no-cache)
endef

# Function to conditionally pull or build the docker image
define DOCKER_PULL_OR_BUILD
	$(if $(filter true,$(DCKR_PULL)), \
	  docker pull $1 || (echo "Pull failed. Building Docker image for $1..." && \
	  $(call DOCKER_BUILD,$1)), $(call DOCKER_BUILD,$1))
endef

################################################################################
# COMMANDS                                                                     #
################################################################################

# check docker and host dependencies
check-docker:
	@ echo "Checking Docker and host dependencies..."
	@ if command -v docker >/dev/null 2>&1; then \
	  echo "✅ Docker is installed."; \
	else \
	  echo "❌ Docker is NOT installed. Please install Docker to proceed."; \
	  exit 1; \
	fi
	@ if docker --version >/dev/null 2>&1; then \
	  echo "✅ Docker is running!"; \
	else \
	  echo "❌ Docker is not running or accessible."; \
	  exit 1; \
	fi

# check if test docker image exists
check-image: check-docker
	@ if ! docker images --format "{{.Repository}}:{{.Tag}}" | \
	    grep -q "^${DCKRIMG}$$"; then \
	  echo "❌ Error: Docker image '${DCKRIMG}' is missing."; \
	  echo "Please build it using 'make build-tests'."; \
	  exit 1; \
	else \
	  echo "✅ Docker image '${DCKRIMG}' exists."; \
	fi

# confirm working dir is correct
check-workdir:
	@ echo "Checking if the working directory inside the container matches ${DCKRSRC}..."
	@ container_workdir=$$(docker run --rm ${DCKRIMG} pwd); \
	if [ "$$container_workdir" = "$(DCKRSRC)" ]; then \
	  echo "✅ Working directory matches ${DCKRSRC}."; \
	else \
	  echo "❌ Working directory does NOT match ${DCKRSRC}. Current: $$container_workdir"; \
	  exit 1; \
	fi

# check if test docker image exists
check-deps: check-image check-workdir
	@ echo "Checking test dependencies inside Docker..."
	@ ${DCKRTST} ${DCKRIMG} sh -c "\
	  command -v bash > /dev/null && \
	  echo '✅ bash is installed!' || echo '❌ bash is missing.' && \
	  command -v find > /dev/null && \
	  echo '✅ find is installed!' || echo '❌ find is missing.' && \
	  command -v git > /dev/null && \
	  echo '✅ git is installed!' || echo '❌ git is missing.' && \
	  command -v make > /dev/null && \
	  echo '✅ make is installed!' || echo '❌ make is missing.' && \
	  command -v pytest > /dev/null && \
	  echo '✅ pytest is installed!' || echo '❌ pytest is missing.' && \
	  command -v isort > /dev/null && \
	  echo '✅ isort is installed!' || echo '❌ isort is missing.' && \
	  command -v flake8 > /dev/null && \
	  echo '✅ flake8 is installed!' || echo '❌ flake8 is missing.' && \
	  command -v mypy > /dev/null && \
	  echo '✅ mypy is installed!' || echo '❌ mypy is missing.' && \
	  command -v black > /dev/null && \
	  echo '✅ black is installed!' || echo '❌ black is missing.' && \
	  command -v sbase > /dev/null && \
	  echo '✅ sbase is installed!' || echo '❌ sbase is missing.' && \
	  echo '✅ All testing dependencies are present!'"

# build docker image with conditional pull and build
build:
	@ echo "Building Docker image..."
	@ $(call DOCKER_PULL_OR_BUILD,${DCKRIMG},testing)

# serve the website
serve: server-container pause address

# build server container
server-container:
	@ echo "Launching web server in Docker container -> ${DCTNR} ..."
	@ if ! docker ps --format="{{.Names}}" | grep -q "${DCTNR}"; then \
		docker run -d \
		           --rm \
		           --name ${DCTNR} \
		           -p 8000 \
		           -v "${CURRENTDIR}":${DCKRSRC} \
		           ${DCKROPT} \
		           ${DCKRIMG} \
		           python3 -m http.server 8000 && \
	  if ! grep -sq "${DCTNR}" "${CURRENTDIR}/.running_containers"; then \
	    echo "${DCTNR}" >> .running_containers; \
	  fi; \
	else \
	  echo "Container already running. Try setting DCTNR manually."; \
	fi

# simply wait for a certain amount of time
pause:
	@ echo "Sleeping ${PSECS} seconds ..."
	@ sleep ${PSECS}

# get containerized server address
address:
	@ if [ -f "${CURRENTDIR}/.running_containers" ]; then \
	while read container; do \
	  if echo "$${container}" | grep -q "${DCTNR}" ; then \
	    echo "Server address: http://$$(docker port ${DCTNR}| grep 0.0.0.0: | \
			      awk '{print $$3}')"; \
	  else \
	    echo "Could not find running container: ${DCTNR}." \
	         "Try running: make list-containers"; \
	  fi \
	done < "${CURRENTDIR}/.running_containers"; \
	else \
	  echo ".running_containers file not found. Is a Docker container running?"; \
	fi

# stop all containers
stop-server:
	@ if [ -f "${CURRENTDIR}/.running_containers" ]; then \
	  echo "Stopping Docker containers ..."; \
	  while read container; do \
	    echo "Container $$(docker stop $$container) stopped."; \
	  done < "${CURRENTDIR}/.running_containers"; \
	  rm -f "${CURRENTDIR}/.running_containers"; \
	else \
	  echo "${CURRENTDIR}/.running_containers file not found."; \
	fi

# restart server
restart-server: stop-server serve

# print info on variables used
print-config:
	@ echo "GitHub User: $(GITHUB_USER)"
	@ echo "Repository Name: $(REPO_NAME)"
	@ echo "Git Branch: $(GIT_BRANCH)"
	@ echo "Docker Source Path: $(DCKRSRC)"
	@ echo "Docker Image: $(DCKRIMG)"
	@ echo "Docker Tag: $(DCKRTAG)"
	@ echo "Current Directory: $(CURRENTDIR)"
	@ echo "Webserver Docker Container: $(DCTNR)"
	@ echo "Pause Time (PSECS): $(PSECS)"

# run linters
lint: isort black flake8 mypy

# run full testing suite
tests: pytest lint

# run pytest in docker container
pytest:
	@ ${DCKRTST} ${DCKRIMG} pytest --reuse-session

# run isort in docker container
isort:
	@ ${DCKRTST} ${DCKRIMG} isort tests/

# run black in docker container
black:
	@ ${DCKRTST} ${DCKRIMG} black tests/

# run flake8 in docker container
flake8:
	@ ${DCKRTST} ${DCKRIMG} flake8 --config=tests/.flake8

# run mypy in docker container
mypy:
	@ ${DCKRTST} ${DCKRIMG} mypy --ignore-missing-imports tests/

# install act command
install-act:
	@ echo "Installing act..."
	@ curl --proto '=https' --tlsv1.2 -sSf \
	  "https://raw.githubusercontent.com/nektos/act/master/install.sh" | \
	  sudo bash -s -- -b ./bin && \
	sudo mv ./bin/act /usr/local/bin/
	@ echo "act installed and moved to /usr/local/bin"

# check if act is installed
check-act:
	@ command -v act >/dev/null 2>&1 && \
	{ echo "✅ 'act' is installed!"; } || \
	{ echo "❌ Command 'act' is not installed. Please install it with: "\
	"'make install-act' 💻🔧"; exit 1; }

# run github action tests locally
run-act-tests: check-act
	@ echo "Running GitHub Action Tests locally..."
	act -j run-tests $(ARGS)

# Command to test with a custom remote URL passed as an argument
test-github-user:
	@ echo "$(call get_github_user,$(REMOTE_URL))"

# create interactive shell in docker container
shell:
	@ ${DCKRTST} ${DCKRIMG} bash || true
