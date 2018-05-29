"""
Checks the existence of a tag in a registry by calling skopeo
"""

import sys
import os
import subprocess

import anymarkup

if len(sys.argv) < 2:
    print "Provide path to the processed OpenShift template"
    sys.exit(1)

OPENSHIFT_TEMPLATE = sys.argv[1]
AUTH_FILE = os.path.expanduser('~/skopeo.json')

images = []
for i in anymarkup.parse_file(OPENSHIFT_TEMPLATE)["items"]:
    if i["kind"] == "DeploymentConfig":
        for c in i["spec"]["template"]["spec"]["containers"]:
            images.append(c["image"])

for image in images:
    with open(os.devnull, 'w') as devnull:
        status_code = subprocess.call(
            ['skopeo', 'inspect', '--authfile', AUTH_FILE, 'docker://%s' % (image,)], stdout=devnull)

    if status_code == 0:
        print "OK"
    else:
        print >>sys.stderr, "Could not find image %s in registry" % (image,)
        sys.exit(1)
