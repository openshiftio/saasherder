#!/bin/bash

# This script writes a list of all images and some other relevant information to
# a semi-colon separated file.
#
# The target file is `images.txt` in the directory where the command is
# executed.
# WARNING: It will remove this file if it exists.
#
# If the variable NO_REFRESH is defined and contains a value, the repos will not
# be git pull'ed and the templates will not be generated. This will speed things
# up, but it is required to run it normally, i.e. without this flag, before
# running it with this flag.
#
# Output columns:
#
# - Repo
# - Context
# - Service
# - Git URL
# - Git Hash
# - Container image
#
# Usage:
#
# ./get-images.sh [path-to-saas-repo [path-to-saas-repo [...]]]
#
# Requirements:
#
# - already cloned saas repos
# - saasherder
# - oc client
# - yq and jq

set -e

OUT="${PWD}/images.txt"

rm -f $OUT

for saasrepo in "$@"; do
    pushd "${saasrepo}"

    [ -z "$NO_REFRESH" ] && git pull

    for context in `saasherder config get-contexts`; do
        [ -z "$context" ] && echo "Empty context" && exit 1

        if [ -z "$NO_REFRESH" ]; then
            rm -rf "${context}-out"
            saasherder --context "${context}" pull
            saasherder --environment production template --local --output-dir "${context}-out" tag
        fi

        for f in `ls ${context}-out/*`; do
            service=$(basename "$f" .yaml)
            git_hash=$(saasherder --context $context get hash $service)
            git_url=$(saasherder --context $context get url $service)
            images=$(yq -r '.items | .[] | select(.kind=="DeploymentConfig").spec.template.spec.containers | .[] | .image ' $f)

            for i in $images; do
                echo "${saasrepo};${context};${service};${git_url};${git_hash};${i}" | tee -a "$OUT"
            done
        done
    done

    popd
done

echo "Output written to $OUT"
