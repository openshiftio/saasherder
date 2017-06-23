import os
import pytest
import tempfile
from shutil import copyfile

from config import SaasConfig

temp_dir = tempfile.mkdtemp()
temp_path = os.path.join(temp_dir, "config.yaml")


class TestConfig(object):
  def setup_method(self, method):
    # Start from fresh config.yaml
    copyfile("tests/data/config.yaml", temp_path)

  def test_config_load(self):
    sc = SaasConfig(temp_path)
    assert sc.config["current"] == "saas"

  def test_context_exists(self):
    sc = SaasConfig(temp_path)
    assert sc.context_exists("saas")
  
  def test_context_not_exists(self):
    sc = SaasConfig(temp_path)
    assert not sc.context_exists("foo")

  def test_context_add(self):
    sc = SaasConfig(temp_path)
    sc.add_context("foo", "x", "y", "z")
    sc.load()
    assert sc.context_exists("foo")

  def test_switch_context(self):
    sc = SaasConfig(temp_path)
    sc.add_context("foo", "x", "y", "z")
    sc.switch_context("foo")
    assert sc.config["current"] == "foo"

  def test_context_current(self):
    sc = SaasConfig(temp_path)
    assert sc.current() == "saas"

  def test_context_get(self):
    sc = SaasConfig(temp_path)
    assert sc.get("services_dir") == "tests/data/service"

  def test_config_get_contexts(self):
    sc = SaasConfig(temp_path)
    assert len(list(sc.get_contexts())) == 2

  def test_set_context_on_init(self):
    context = "foobar"
    sc = SaasConfig(temp_path, None)
    assert sc.current() == "saas"
    sc = SaasConfig(temp_path, context)
    assert sc.current() == context
    