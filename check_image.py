import anymarkup
import sys
import requests
import re
import os

def tag_in_docker_registry(registry, repo, image, tag):
  """Returns true if the tag is found in this docker registry"""
  url = "https://%s/v2/%s/%s/tags/list" % (registry, repo, image)
  print("Checking Docker Registry %s" % url)
  r = requests.get(url)
  if r.status_code != 200:
    raise Exception("Got %d from %s" % (r.status_code, url))
  return tag in r.json()["tags"]

def tag_in_quay_registry(repo, image, tag):
  """
  Returns true if the tag is found in this quay registry
  This method follows pagination if found in the response

  This is an example response from the API:

  {
    "has_additional": true,
    "page": 1,
    "tags": [
      {
        "reversion": false,
        "manifest_digest": "sha256:ca02144ed4ba51d664d9201e943380b4550ec426720dd056e0f12b1a6228b76e",
        "start_ts": 1527614333,
        "name": "seq100",
        "docker_image_id": "ac3f08b78d4e8627e123a29d47dcc4fe4206016649e609e7f0f7f639aa7ba213"
      },
      ...
    ]
  }
  """
  base_url = "https://quay.io/api/v1/repository/%s/%s/tag/" % (repo, image)
  page = 1
  headers = {}
  token_path = os.path.expanduser("~/.check_image_quay.io")

  # Read token if it exists
  try:
    with open(token_path, 'r') as f:
      token = f.read().strip()
      headers = {'Authorization': 'Bearer {}'.format(token)}
  except IOError:
    pass

  # Loop to follow pagination
  while True:
    url = "{}?page={}".format(base_url, page)
    print("Checking Quay Registry %s" % url)
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
      raise Exception("Got %d from %s" % (r.status_code, url))

    body = r.json()
    tags = [tag_item['name'] for tag_item in body["tags"]]

    if tag in tags:
      return True
    else:
      if body['has_additional']:
        page += 1
      else:
        return False

################################################################################

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
  # remove leading protocol
  i = re.sub('^https?://', '', i)

  image_split = i.split("/")

  if len(image_split) < 3:
    print("WARNING: Registry for image %s is not set, assuming docker.io. Cannot verify image existance there. Skipping." % i)
    continue

  registry = image_split[0]
  repo = '/'.join(image_split[1:-1])
  name = image_split[-1]

  image, tag = name.split(":")

  if registry == 'quay.io':
    tag_present = tag_in_quay_registry(repo, image, tag)
  else:
    tag_present = tag_in_docker_registry(registry, repo, image, tag)

  if tag_present:
    print "OK"
  else:
    raise Exception("Could not find tag %s in registry" % tag)
