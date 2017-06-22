import os
import pytest
import tempfile
from shutil import copyfile

from saasherder import SaasHerder

temp_dir = tempfile.mkdtemp()
temp_path = os.path.join(temp_dir, "config.yaml")

class TestSH(object):
  def setup_method(self, method):
    # Start from fresh config.yaml
    copyfile("tests/data/config.yaml", temp_path)

  def test_sh_load(self):
    sh = SaasHerder(temp_path, None)
    assert sh.output_dir == "saas-processed"

  def test_sh_services_num(self):
    sh = SaasHerder(temp_path, None)
    assert len(sh.services) == 2

  def test_sh_get_services(self):
    sh = SaasHerder(temp_path, None)
    assert len(sh.get_services("redirector")) > 0

  def test_sh_get_services_all(self):
    sh = SaasHerder(temp_path, None)
    assert len(sh.get_services("all")) == len(sh.services)

  