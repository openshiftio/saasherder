#!/bin/bash

TSTAMP=$(date +%Y%m%d_%H%M%S)
TPLDIR="dsaas-templates"
CONF="/home/`whoami`/.kube/config"
SCRIPT_PATH="python ."
if echo ${0} | grep -q "/"; then
    SCRIPT_PATH="python ${0%/*}"
fi

#Figure out if the tool is installed and set CMD accordingly
if which saasherder; then
    CMD="saasherder"
else
    CMD=${SCRIPT_PATH}/saasherder/cli.py
fi

if [ -z "${DRY_RUN}" ]; then
    DRY_RUN=false
fi

SAAS_GROUPS=$(${CMD} config get-contexts)

function git_prep {
    # should also check that the git master co is clean
    git checkout master
    git pull --rebase upstream master
}

function oc_apply {
    config=""
    [ -n "${CONF}" ] && config="--config=${CONF}"
    if ${DRY_RUN}; then
        echo "oc $config apply -f $1"
    else
        oc $config apply -f $1
    fi
}

function pull_tag {
    local GROUP=$1
    local PROCESSED_DIR=$2

    local TEMPLATE_DIR=${GROUP}-templates

    # lets clear this out to make sure we always have a
    # fresh set of templates, and nothing else left behind
    rm -rf ${TEMPLATE_DIR}; mkdir -p ${TEMPLATE_DIR}

    if [ -e /home/`whoami`/${GROUP}-gh-token-`whoami` ]; then GH_TOKEN=" --token "$(cat /home/`whoami`/${GROUP}-gh-token-`whoami`); fi
    
    ${CMD} --context ${GROUP} pull $GH_TOKEN

    ${CMD} --context ${GROUP} template --output-dir ${PROCESSED_DIR} tag
}

for g in `echo ${SAAS_GROUPS}`; do
    # get some basics in place, no prep in prod deploy
    GROUP=${g}


    if ! ${DRY_RUN}; then
        CONF="/home/`whoami`/.kube/cfg-${GROUP}"
        if [ ! -e ${CONF} ] ; then
            echo "Could not find OpenShift configuration for ${GROUP}"; exit 1;
        fi
    fi

    TSTAMPDIR=${GROUP}-${TSTAMP}
    mkdir -p ${TSTAMPDIR}

    pull_tag ${GROUP} ${TSTAMPDIR}

    for f in `ls ${TSTAMPDIR}`; do
        oc_apply $f
    done

    if [ $(find ${TSTAMPDIR}/ -name \*.yaml | wc -l ) -lt 1 ]; then
        # if we didnt apply anything, dont keep the dir around
        rm -rf $TSTAMPDIR
        echo "R: Nothing to apply"
    fi
done


