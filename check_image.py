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

if os.environ.get('AUTH_FILE'):
    AUTH_FILE = os.environ.get('AUTH_FILE')
else:
    AUTH_FILE = os.path.expanduser('~/skopeo.json')

SKOPEO_USER = os.environ.get('SKOPEO_USER')
SKOPEO_PASS = os.environ.get('SKOPEO_PASS')


def skopeo_inspect(image, auth=True):
    cmd = ['skopeo', 'inspect']

    if auth:
        if SKOPEO_USER and SKOPEO_PASS:
            cmd += ['--creds', '{}:{}'.format(SKOPEO_USER, SKOPEO_PASS)]
        else:
            cmd += ['--authfile', AUTH_FILE]

    cmd += ['docker://{}'.format(image)]

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    return (p.returncode, stdout, stderr)


try:
    OPENSHIFT_TEMPLATE = sys.argv[1]
except IndexError:
    print "Provide path to the processed OpenShift template"
    sys.exit(1)

try:
    image_path_pattern = re.compile(sys.argv[2])
except IndexError:
    image_path_pattern = None

images = set()
for i in anymarkup.parse_file(OPENSHIFT_TEMPLATE, force_types=None)["items"]:
    try:
        for c in i["spec"]["template"]["spec"]["containers"]:
            images.add(c["image"])
    except KeyError:
        pass

success = True

for image in images:
    if image_path_pattern and not image_path_pattern.search(image):
        print >>sys.stderr, ["ERROR_NO_MATCH",
                             image, image_path_pattern.pattern]
        success = False
        continue

    status_code, stdout_auth, stderr_auth = skopeo_inspect(image, True)
    if status_code == 0:
        print ["OK_AUTH", image]
        continue

    status_code, stdout_noauth, stderr_noauth = skopeo_inspect(image, False)
    if status_code == 0:
        print ["OK_NOAUTH", image]
        continue

    print >>sys.stderr, ["ERROR_AUTH", image, stderr_auth]
    print >>sys.stderr, ["ERROR_NOAUTH", image, stderr_noauth]
    success = False

if not success:
    sys.exit(1)

sys.exit(0)
