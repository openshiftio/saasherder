import os
import pytest
from subprocess import Popen

fixtures_dir = "tests/data/fixtures/customresource"
pass_fixture = "cs-image-pass.yaml"
fail_fixture = "cs-image-fail.yaml"
check_image_path = "/opt/saasherder"
check_image_bin = "check_image.py"
check_image_py = os.path.join(check_image_path, check_image_bin)
python_bin = "/bin/python"


class TestCheckImage(object):
  def setup_method(self, method):
    if not os.path.exists(check_image_py):
      assert False

  def test_check_image_pass(self):
    DEVNULL = open(os.devnull, 'w')
    target_test = fixtures_dir + "/" +  pass_fixture
    print(os.getcwd())
    proc = Popen([python_bin, check_image_py, target_test],
                 stdout=DEVNULL, stderr=DEVNULL)
    proc.communicate()
    assert proc.returncode == 0

  def test_check_image_fail(self):
    DEVNULL = open(os.devnull, 'w')
    target_test = fixtures_dir +  "/" + fail_fixture
    proc = Popen([python_bin, check_image_py, target_test],
                 stdout=DEVNULL, stderr=DEVNULL)
    proc.communicate()
    assert proc.returncode != 0
