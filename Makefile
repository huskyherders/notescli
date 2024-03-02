ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
INSTALL_DIR ?= /usr/local/bin
CMD_NAME ?= notescli
install:
	chmod +x cli/notescli.py
	sudo ln -s $(ROOT_DIR)/cli/notescli.py $(INSTALL_DIR)/$(CMD_NAME)