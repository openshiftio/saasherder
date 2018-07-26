"""
Checks the existence of a tag in a registry by calling skopeo

It enforces that the image must be hosted in Quay.io, belong to a
specific namespace `openshiftio` and start with `rhel-`.
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
IMAGE_PATH_START = "quay.io/openshiftio/rhel-"

images = []
for i in anymarkup.parse_file(OPENSHIFT_TEMPLATE)["items"]:
    if i["kind"] == "DeploymentConfig":
        for c in i["spec"]["template"]["spec"]["containers"]:
            images.append(c["image"])

for image in images:
    if not image.startswith(IMAGE_PATH_START)
        print >>sys.stderr, "Image '%s' does not begin with '%s'." % (image, IMAGE_PATH_START)
        sys.exit(1)

    with open(os.devnull, 'w') as devnull:
        status_code = subprocess.call(
            ['skopeo', 'inspect', '--authfile', AUTH_FILE, 'docker://%s' % (image,)], stdout=devnull)

    if status_code == 0:
        print "OK"
    else:
