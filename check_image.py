import anymarkup
import sys
import requests

from saasherder.lib import split_repo_name


if len(sys.argv) < 2:
    print("Provide path to the processed OpenShift template")
    sys.exit(1)
f = sys.argv[1]

images = []
for i in anymarkup.parse_file(f)["items"]:
    if i["kind"] == "DeploymentConfig":
        for c in i["spec"]["template"]["spec"]["containers"]:
            images.append(c["image"])


for i in images:
    # split the repo name into its components
    parts = split_repo_name(i)
    # parts= {"registy": $REGISTRY, "image": "$IMAGE:$TAG",
    #         "tag": "$TAG", "image_name": "$IMAGE_WITHOUT_TAG"}

    # case where registry name is not given
    if not parts.get("registry", False):
        print("WARNING: Registry for image %s is not set, assuming docker.io. "
              "Cannot verify image existance there. Skipping." % i)
        continue

    # grab the registry end point of the repository
    registry = parts.get("registry")

    # get the image name without tag of repository
    image_name = parts.get("image_name")

    # get the tag of repository
    tag = parts.get("tag")

    if not registry.startswith("http"):
        registry = "https://%s" % registry

    url = "{0}/v2/{1}/tags/list".format(registry, image_name)

    print("Checking %s" % url)

    r = requests.get(url)

    if r.status_code != 200:
        raise Exception("Got %d from %s" % (r.status_code, url))

    if tag in r.json()["tags"]:
        print("OK")
    else:
        raise Exception("Could not find tag %s in registry" % tag)
