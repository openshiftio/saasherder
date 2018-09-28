.PHONY: build-test-container
build-test-container:
	docker build -t saasherder-test -f tests/Dockerfile.test .

.PHONY: test
test: build-test-container
	docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock \
	    --privileged --net=host saasherder-test

.PHONY: local-test
local-test: build-test-container
	docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock \
        -v $(pwd)/tests:/opt/saasherder/tests \
	    -v $(pwd)/saasherder:/opt/saasherder/saasherder \
	    --privileged --net=host saasherder-test
