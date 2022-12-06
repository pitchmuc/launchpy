#/bin/make
#@ Make Help

SHELL := /bin/bash
PYLAUNCH_NAME ?= "PyLaunch"
PYLAUNCH_VERSION ?= "v0.1.0"
PYLAUNCH_DESCRIPTION ?= "Python wrapper for the Adobe Launch API."
PYLAUNCH_ROOT ?= $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

.DEFAULT_GOAL := help
.PHONY: help #: Testing
help:
	@cd ${PYLAUNCH_ROOT} && awk 'BEGIN {FS = " ?#?: "; print ""${PYLAUNCH_NAME}" "${PYLAUNCH_VERSION}"\n"${PYLAUNCH_DESCRIPTION}"\n\nUsage: make \033[36m<command>\033[0m\n\nCommands:"} /^.PHONY: ?[a-zA-Z_-]/ { printf "  \033[36m%-10s\033[0m %s\n", $$2, $$3 }' $(MAKEFILE_LIST)

.PHONY: init #: Download dependencies into virtual environment
init:
	@cd ${PYLAUNCH_ROOT} && \
	python3 -m venv .venv && \
	poetry install

