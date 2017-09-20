import anymarkup
import sys
import requests


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
  image_split = i.split("/")
  if len(image_split) == 3:
    registry, repo, name = image_split
  else:
    print("WARNING: Registry for image %s is not set, assuming docker.io. Cannot verify image existance there. Skipping." % i)
    continue
  image, tag = name.split(":")
  if not registry.startswith("http"):
    registry = "https://%s" % registry

  url = "%s/v2/%s/%s/tags/list" % (registry, repo, image)
  print("Checking %s" % url)
  r = requests.get(url)
  if r.status_code != 200:
    raise Exception("Got %d from %s" % (r.status_code, url))
  
  if tag in r.json()["tags"]:
    print("OK")
  else:
    raise Exception("Could not find tag %s in registry" % tag)