import os
import filecmp
import tempfile
from saasherder import SaasHerder
from shutil import copytree, copyfile

templates_dir = "tests/data/fixtures/template"
fixtures_dir = "tests/data/fixtures/label"
fixtures_dir_with_repo_url = "tests/data/fixtures/label/with_repo_url"
label_selectors_fixture = "label_selectors.txt"

output_dir = tempfile.mkdtemp()

temp_dir = tempfile.mkdtemp()
tests_dir = os.path.join(temp_dir, 'tests', 'data')
temp_path = os.path.join(temp_dir, "config.yaml")


class TestLabeling(object):
  def setup_method(self, method):
    copyfile("tests/data/config.yaml", temp_path)
    if not os.path.isdir(tests_dir):
      copytree("tests/data", tests_dir)

  def test_label_processed_files(self):
    output_dir = tempfile.mkdtemp()
    se = SaasHerder(temp_path, None)
    se.label("all", templates_dir, output_dir)

    for root, _, files in os.walk(output_dir):
      for f in files:
        if not f.endswith("yaml"):
          continue

        processed = os.path.join(root, f)
        fixture = os.path.join(fixtures_dir, f)
        assert filecmp.cmp(processed, fixture)

  def test_label_selectors(self):
    output_dir = tempfile.mkdtemp()
    se = SaasHerder(temp_path, None)
    label_selectors = se.label("all", templates_dir, output_dir)

    label_selector_fixture = os.path.join(fixtures_dir, label_selectors_fixture)
    with open(label_selector_fixture) as f:
        lines = f.readlines()
    lines = [x.strip() for x in lines]
    for i in range(len(lines)):
        assert lines[i] == label_selectors[i]

  def test_label_processed_files_with_saas_repo_url(self):
    output_dir = tempfile.mkdtemp()
    se = SaasHerder(temp_path, None)
    se.label("all", templates_dir, output_dir, saas_repo_url='https://github.com/app-sre/saas-test')

    for root, _, files in os.walk(output_dir):
      for f in files:
        if not f.endswith("yaml"):
          continue

        processed = os.path.join(root, f)
        fixture = os.path.join(fixtures_dir_with_repo_url, f)
        assert filecmp.cmp(processed, fixture)

  def test_label_selectors_with_saas_repo_url(self):
    output_dir = tempfile.mkdtemp()
    se = SaasHerder(temp_path, None)
    label_selectors = se.label("all", templates_dir, output_dir, saas_repo_url='https://github.com/app-sre/saas-test')

    label_selector_fixture = os.path.join(fixtures_dir_with_repo_url, label_selectors_fixture)
    with open(label_selector_fixture) as f:
        lines = f.readlines()
    lines = [x.strip() for x in lines]
    for i in range(len(lines)):
        assert lines[i] == label_selectors[i]
