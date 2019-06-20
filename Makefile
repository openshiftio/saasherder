.PHONY: build push build-test-container test local-test clean

IMAGE_NAME := quay.io/openshiftio/saasherder
IMAGE_TAG := $(shell echo ${GIT_COMMIT} | cut -c1-${DEVSHIFT_TAG_LEN})
DOCKER_CONF := $(CURDIR)/.docker

build:
	docker build --no-cache -t $(IMAGE_NAME):$(IMAGE_TAG) .

push:
	docker --config=$(DOCKER_CONF) push $(IMAGE_NAME):$(IMAGE_TAG)

build-test-container:
	docker build -t saasherder-test -f tests/Dockerfile.test .

test: build-test-container
	docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock \
	    --privileged --net=host saasherder-test

local-test: build-test-container
	docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock \
        -v $(pwd)/tests:/opt/saasherder/tests \
	    -v $(pwd)/saasherder:/opt/saasherder/saasherder \
	    --privileged --net=host saasherder-test

clean:
	@rm -rf tests/__pycache__
	@find . -name "*.pyc" -delete
