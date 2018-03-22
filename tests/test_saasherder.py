import os
import pytest
import tempfile
import anymarkup
from shutil import copytree, copyfile

from saasherder import SaasHerder

temp_dir = tempfile.mkdtemp()
tests_dir = os.path.join(temp_dir, 'tests', 'data')
temp_path = os.path.join(temp_dir, "config.yaml")


class TestSH(object):
  def setup_method(self, method):
    copyfile("tests/data/config.yaml", temp_path)
    if not os.path.isdir(tests_dir):
      copytree("tests/data", tests_dir)

  def test_sh_load(self):
    sh = SaasHerder(temp_path, None)
    assert os.path.basename(sh.output_dir) == "saas-processed"

  def test_sh_services_num(self):
    sh = SaasHerder(temp_path, None)
    assert len(sh.services) == 3

  def test_sh_get_services(self):
    sh = SaasHerder(temp_path, None)
    assert len(sh.get_services("redirector")) > 0

  def test_sh_get_services_all(self):
    sh = SaasHerder(temp_path, None)
    assert len(sh.get_services("all")) == len(sh.services)

  def test_sh_get_hash_lenght(self):
    sh = SaasHerder(temp_path, None)
    assert sh.get("hash_length", ["hash_length"])[0] == 7

  def test_sh_get_hash_lenght_default(self):
    sh = SaasHerder(temp_path, None)
    assert sh.get("hash_length", ["redirector"])[0] == 6

  def test_sh_update(self):
    sh = SaasHerder(temp_path, None)
    output_file = os.path.join(temp_dir, "multiple_services.yaml")
    sh.update("hash", "multiple_services", "master", output_file=output_file)
    data = anymarkup.parse_file(output_file)
    assert len(data["services"]) == 2
    assert data["services"][1]["hash"] == "master"


