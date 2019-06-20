#!/bin/bash


/bin/bash cico_test.sh

set +x
eval "$(./env-toolkit load -f jenkins-env.json \
            GIT_COMMIT \
            QUAY_USERNAME \
            QUAY_PASSWORD \
            DEVSHIFT_TAG_LEN)"
set -x

make build push
