"""
Checks the existence of a tag in a registry by calling skopeo

Usage: check_image.py file [regex]

If regex is supplied the path of the image must match this regex
"""

import os
import re
import subprocess
import sys
import time

import anymarkup

if os.environ.get('AUTH_FILE'):
    AUTH_FILE = os.environ.get('AUTH_FILE')
else:
    AUTH_FILE = os.path.expanduser('~/skopeo.json')

SKOPEO_USER = os.environ.get('SKOPEO_USER')
SKOPEO_PASS = os.environ.get('SKOPEO_PASS')


def skopeo_inspect(image):
    cmd = ['skopeo', 'inspect']

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

    attempt = 1
    max_attemps = 5
    attempt_success = False
    while not attempt_success and attempt <= max_attemps:
        status_code, stdout, stderr = skopeo_inspect(image)
        if status_code == 0:
            print ["OK", image]
            attempt_success = True
            continue

        print >>sys.stderr, ["ERROR", image, stderr]
        if attempt < max_attemps:
            time.sleep(attempt)
        attempt += 1

    if not attempt_success:
        success = False

if not success:
    sys.exit(1)

sys.exit(0)
