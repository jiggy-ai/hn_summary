
.PHONY: help build push all

help:
	    @echo "Makefile commands:"
	    @echo "build"
	    @echo "push"
	    @echo "all"

.DEFAULT_GOAL := all

build:
	    docker build -t wskish/hn-summary:${TAG} .

push:
	    docker push wskish/hn-summary:${TAG}

all: build push
