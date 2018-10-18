"""
Checks the existence of a tag in a registry by calling skopeo

Usage: check_image.py file [regex]

If regex is supplied the path of the image must match this regex
"""

import os
import re
import subprocess
import sys

import anymarkup

AUTH_FILE = os.environ.get('AUTH_FILE', os.path.expanduser('~/skopeo.json'))

try:
    OPENSHIFT_TEMPLATE = sys.argv[1]
except IndexError:
    print "Provide path to the processed OpenShift template"
    sys.exit(1)

try:
    image_path_pattern = re.compile(sys.argv[2])
except IndexError:
    image_path_pattern = None

images = []
for i in anymarkup.parse_file(OPENSHIFT_TEMPLATE)["items"]:
    if i["kind"] in ["DeploymentConfig", "StatefulSet"]:
        for c in i["spec"]["template"]["spec"]["containers"]:
            images.append(c["image"])

for image in images:
    if image_path_pattern and not image_path_pattern.search(image):
        print >>sys.stderr, "Image '%s' does not match '%s'." % (
            image, image_path_pattern.pattern)
        sys.exit(1)

    with open(os.devnull, 'w') as devnull:
        status_code = subprocess.call(
            ['skopeo', 'inspect', '--authfile', AUTH_FILE, 'docker://%s' % (image,)], stdout=devnull)

    if status_code == 0:
        print "OK"
    else:
        print >>sys.stderr, "Could not find image %s in registry" % (image,)
        sys.exit(1)
