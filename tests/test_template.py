import os
#import pytest
import tempfile
import anymarkup
from saasherder import SaasHerder
from shutil import copyfile

service_dir = "tests/data/service"
templates_dir = "tests/data/template"
output_dir = tempfile.mkdtemp()

temp_dir = tempfile.mkdtemp()
temp_path = os.path.join(temp_dir, "config.yaml")
  
class TestTemplating(object):
  def setup_method(self, method):
    # Start from fresh config.yaml
    copyfile("tests/data/config.yaml", temp_path)

  def test_template_hash(self):
    hash = "abcdef"
    se = SaasHerder(temp_path, None)
    se.template("tag", "redirector", output_dir, local=True)
    data = anymarkup.parse_file(os.path.join(output_dir, "redirector.yaml"))
    for item in data["items"]:
      if item["kind"] == "DeploymentConfig":
        assert item["spec"]["template"]["spec"]["containers"][0]["image"].endswith(hash)

  def test_template_hash_length(self):
    hash = "abcdef7"
    se = SaasHerder(temp_path, None)
    se.template("tag", "hash_length", output_dir, local=True)
    data = anymarkup.parse_file(os.path.join(output_dir, "hash_length.yaml"))
    for item in data["items"]:
      if item["kind"] == "DeploymentConfig":
        assert item["spec"]["template"]["spec"]["containers"][0]["image"].endswith(hash)
    