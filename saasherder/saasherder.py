import os
import anymarkup
import requests
import copy
import subprocess
from distutils.spawn import find_executable
from shutil import copyfile
from config import SaasConfig

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SaasHerder(object):
  @property
  def services(self):
    """ Loads and returns all the services in service dir """
    if not self._services:
      self._services = {}
      self._service_files = {}
      for f in os.listdir(self.services_dir):
        service_file = os.path.join(self.services_dir, f)
        service = anymarkup.parse_file(service_file)
        for s in service["services"]:
          s["file"] = f
          self._services[s["name"]] = s
          if not self._service_files.get(f):
            self._service_files[f] = []
          self._service_files[f].append(s["name"])

    return self._services

  def __init__(self, config_path, context):
    self.config = SaasConfig(config_path)
    if context:
      self.config.switch_context(context)

    logger.info("Current context: %s" % self.config.current())

    self._services = None
    self.load_from_config()

  def load_from_config(self):
    self.templates_dir = self.config.get("templates_dir")
    self.services_dir = self.config.get("services_dir")
    self.output_dir = self.config.get("output_dir")
    self.prep_templates_dir()


  def write_service_file(self, name, output=None):
    """ Writes service file to disk, either to original file name, or to a name given by output param """
    service_file_cont = {"services": []}
    for n in self._service_files[self.services[name]["file"]]:
      dump = copy.deepcopy(self.services[n])
      filename = dump["file"]
      del dump["file"]
      service_file_cont["services"].append(dump)
      
    if not output:
      output = self.services[name]["file"]
    anymarkup.serialize_file(service_file_cont, output)
    logger.info("Services written to file %s." % output)

  def prep_templates_dir(self):
    """ Create a dir to store pulled templates if it does not exist """
    if not os.path.isdir(self.templates_dir):
      os.mkdir(self.templates_dir)

  def raw_gitlab(self, service):
    """ Construct link to raw file in gitlab """
    return "%s/raw/%s/%s" % (service.get("url").rstrip("/"), service.get("hash"), service.get("path").lstrip("/"))

  def raw_github(self, service):
    """ Construct link to raw file in github """
    url = "https://raw.githubusercontent.com/%s/%s/%s" % ("/".join(service.get("url").rstrip("/").split("/")[-2:]), service.get("hash"), service.get("path").lstrip("/"))
    return url

  def get_raw(self, service):
    """ Figure out the repo manager and return link to a file """
    if "github" in service.get("url"):
      return self.raw_github(service)
    elif "gitlab" in service.get("url"):
      return self.raw_gitlab(service)
  
  def get_template_file(self, service):
    """ Return path to a pulled template file """
    return os.path.join(self.templates_dir, "%s.yaml" % service.get("name"))

  def get_services(self, service_names):
    """ Return service objects """
    result = []
    if type(service_names) is list:
      for s in service_names:
        if self.services.get(s):
          result.append(self.services.get(s))
    elif service_names == "all":
      result = self.services.values()
    else:
      result.append(self.services.get(service_names))
    
    return result

  def collect_services(self, services, token=None, dry_run=False):
    """ Pull/download templates from repositories """
    service_list = self.get_services(services)
    for s in service_list:
      logger.info("Service: %s" % s.get("name"))
      url = self.get_raw(s)
      logger.info("Downloading: %s" % self.get_raw(s))
      headers={}
      if token:
        headers = {"Authorization": "token %s" % token, "Accept": "application/vnd.github.v3.raw"}
      r = requests.get(url, headers=headers) #FIXME
      if r.status_code != 200:
        raise Exception("Couldn't pull the template.")
      filename = self.get_template_file(s)
      if not dry_run:
        with open(filename, "w") as fp:
          fp.write(r.content)
        logger.info("Template written to %s" % filename)

  def update(self, cmd_type, service, value, output_file=None):
    """ Update service object and write it to file """
    services = self.get_services([service])
    if services[0][cmd_type] == value:
      logger.warning("Skipping update of %s, no change" % service)
      return
    else:
      services[0][cmd_type] = value

    try:
      self.collect_services([service], dry_run=True)
    except Exception as e:
      logger.error("Aborting update: %s" % e)
      return  

    if not output_file:
      output_file = os.path.join(self.services_dir, services[0]["file"])
    self.write_service_file(service, output_file)

  def process_image_tag(self, services, output_dir, force=False, local=False):
    services_list = self.get_services(services)
    if not find_executable("oc"):
      raise Exception("Aborting: Could not find oc binary")

    for s in services_list:
      if s.get("skip") and not force:
        logger.warning("INFO: Skipping %s, use -f to force processing of all templates" % s.get("name"))
        continue
      output = ""
      template_file = self.get_template_file(s)
      l = 6 #How many chars to use from hash
      if s.get("hash_length"):
        l = s.get("hash_length")
      tag = "latest" if s["hash"] == "master" else s["hash"][:l]
      parameters = [{"name": "IMAGE_TAG", "value": tag}]
      service_params = s.get("parameters", {})
      for key, val in service_params.iteritems():
        parameters.append({"name": key, "value": val})
      params_processed = ["%s=%s" % (i["name"], i["value"]) for i in parameters]
      local_opt = ""
      if local:
        local_opt = "--local"
      cmd = ["oc", "process", local_opt, "--output", "yaml", "-f", template_file]
      process_cmd = cmd + params_processed
      output_file = os.path.join(output_dir, "%s.yaml" % s["name"])
      logger.info("%s > %s" % (" ".join(process_cmd), output_file))
      try:
        output = subprocess.check_output(process_cmd) 
        with open(output_file, "w") as fp:
          fp.write(output)
      except subprocess.CalledProcessError as e:
        #If the processing failed, try without PARAMS and warn
        output = subprocess.check_output(cmd) 
        with open(output_file, "w") as fp:
          fp.write(output)
        logger.warning("Templating of %s with parameters failed, trying without" % template_file)
        pass

  def template(self, cmd_type, services, output_dir=None, force=False, local=False):
    """ Process templates """
    if not output_dir:
      output_dir = self.templates_dir
    else:
      if not os.path.isdir(output_dir):
        os.mkdir(output_dir) #FIXME

    if cmd_type == "tag":
      self.process_image_tag(services, output_dir, force, local)

  def get(self, cmd_type, services):
    """ Get information about services printed to stdout """
    services_list = self.get_services(services)

    if len(services_list) == 0:
      raise Exception("Unknown serice %s" % services)

    result = []
    for service in services_list:
      if cmd_type in service.keys():
        print(service.get(cmd_type))
        result.append(service.get(cmd_type))
      elif cmd_type in "template-url":
        print(self.get_raw(service))
        result.append(self.get_raw(service))
      else:
        raise Exception("Unknown option for %s: %s" % (service["name"], cmd_type))

    return result

  def print_objects(self, objects):
    for s in self.services.get("services", []):
      template_file = self.get_template_file(s)
      template = anymarkup.parse_file(template_file)
      print(s.get("name"))
      for o in template.get("objects", []):
        if o.get("kind") in objects:
          print("=> %s: %s" % (o.get("kind"), o.get("metadata", {}).get("name")))  

"""
for o in template.get("objects", []):
        if o.get("kind") == "DeploymentConfig":
          for c in o.get("spec").get("template").get("spec").get("containers"):
            image = c.get("image").split(":")[0] #FIXME imagestreams
            if image == "":
              continue
            image = "%s:%s" % (image, s.get("hash")[0:6])
            c["image"] = image
      anymarkup.serialize_file(template, os.path.join(output_dir, "%s.yaml" % s.get("name")))
"""