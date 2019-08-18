import os
import re
import filecmp
#import pytest
import tempfile
import anymarkup
from saasherder import SaasHerder
from shutil import copytree, copyfile
import subprocess

templates_dir = "tests/data/fixtures/template"
fixtures_dir = "tests/data/fixtures/label"
fixtures_dir_annotate = "tests/data/fixtures/label/annotate"

output_dir = tempfile.mkdtemp()

temp_dir = tempfile.mkdtemp()
tests_dir = os.path.join(temp_dir, 'tests', 'data')
temp_path = os.path.join(temp_dir, "config.yaml")


class TestLabeling(object):
  def setup_method(self, method):
    copyfile("tests/data/config.yaml", temp_path)
    if not os.path.isdir(tests_dir):
      copytree("tests/data", tests_dir)

  def test_template_processed_files(self):
    output_dir = tempfile.mkdtemp()
    se = SaasHerder(temp_path, None)
    se.label("all", templates_dir, output_dir)

    for root, _, files in os.walk(output_dir):
      for f in files:
        if not f.endswith("yaml"):
          continue

        processed = os.path.join(root, f)
        with open(processed, 'r') as r:
          print(r.read())
        fixture = os.path.join(fixtures_dir, f)
        assert filecmp.cmp(processed, fixture)

  def test_template_processed_files_annotate(self):
    output_dir = tempfile.mkdtemp()
    se = SaasHerder(temp_path, None)
    se.label("all", templates_dir, output_dir, annotate=True, saas_repo_url='https://github.com/app-sre/saas-test')

    for root, _, files in os.walk(output_dir):
      for f in files:
        if not f.endswith("yaml"):
          continue

        processed = os.path.join(root, f)
        with open(processed, 'r') as r:
          print(r.read())
        fixture = os.path.join(fixtures_dir_annotate, f)
        assert filecmp.cmp(processed, fixture)
