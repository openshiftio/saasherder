import os
import anymarkup
import yaml
import requests
import copy
import subprocess
import sys
from distutils.spawn import find_executable
from shutil import copyfile
from config import SaasConfig

from validation import VALIDATION_RULES

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SaasHerder(object):

    def __init__(self, config_path, context, environment=None):
        self.config = SaasConfig(config_path, context)

        config_dirname = os.path.dirname(config_path)
        self.repo_path = config_dirname if config_dirname else '.'

        if context:
            self.config.switch_context(context)

        logger.info("Current context: %s" % self.config.current())

        self._default_hash_length = 6
        self._services = None
        self._environment = None

        if environment and environment != "None":
            self._environment = environment

        self.load_from_config()

    # TODO: This function should take context or "all" as an argument instead of the
    # hidden the implicit state. Zen of Python says "Explicit is better than
    # implicit."
    @property
    def services(self):
        """ Loads and returns all the services in service dir """
        if not self._services:
            self._services, self._service_files = self.load_services()

        return self._services

    def load_services(self):
        """ Returns two dictionaries that contain all the services:
          1. Service indexed by service name
          2. List of services indexed by service file. Note that there may be multiple services
            defined in a single service file.
        """

        _services = {}
        _service_files = {}

        for f in os.listdir(self.services_dir):
            service_file = os.path.join(self.services_dir, f)
            service = anymarkup.parse_file(service_file)

            for s in service["services"]:
                s["file"] = f
                self.apply_environment_config(s)

                _services[s["name"]] = s
                _service_files.setdefault(f, []).append(s["name"])

        return _services, _service_files

    def load_from_config(self):
        """ Reads info from the defined configuration file """

        # dir to store pulled templates
        self.templates_dir = os.path.join(self.repo_path, self.config.get("templates_dir"))
        self.mkdir_templates_dir()

        # dir to store the service definitions
        self.services_dir = os.path.join(self.repo_path, self.config.get("services_dir"))

        # dir to store the processed templates
        self.output_dir = os.path.join(self.repo_path, self.config.get("output_dir"))

    def apply_environment_config(self, s):
        """ overrides the parameters of the service with those defined in the environment section """

        if not s.get("environments") or not self._environment:
            return

        found = False
        for env in s.get("environments"):
            if env["name"] == self._environment:
                found = True
                for key, val in env.iteritems():
                    if key == "name":
                        continue
                    if key == "url":
                        logger.warning("You are changing URL for environment %s.", env["name"])
                    if key == "hash":
                        logger.error("You cannot change hash for an environment")

                    if type(val) is not dict:
                        s[key] = val
                    else:
                        if key in s:
                            s[key].update(val)
                        else:
                            s[key] = val

        if not found:
            logger.warning("Could not find given environment %s. Proceeding with top level values." % self._environment)

    def apply_filter(self, template_filter, data):
        data_obj = yaml.safe_load(data)
        to_delete = []
        if data_obj.get("items"):
            for obj in data_obj.get("items"):
                if obj.get("kind") in template_filter:
                    to_delete.append(obj)

        if len(to_delete) > 0:
            logger.info("Removing %s from template." % " and ".join(template_filter))

        for obj in to_delete:
            data_obj["items"].remove(obj)

        return yaml.dump(data_obj, encoding='utf-8', default_flow_style=False)

    def write_service_file(self, name, output=None):
        """ Writes service file to disk, either to original file name, or to a name
            given by output param """

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

    def mkdir_templates_dir(self):
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
        """ Figure out the repo manager and return link to a file. Also enforces 'hash', 'url' and 'path' to be present """

        if not service["hash"]:
            raise Exception("Commit hash or branch name needs to be provided.")
        if not service["url"]:
            raise Exception("URL to a repository needs to be provided.")
        if not service["path"]:
            raise Exception("Path in the repository needs to be provided.")

        if "github" in service.get("url"):
            return self.raw_github(service)
        elif "gitlab" in service.get("url"):
            return self.raw_gitlab(service)

    def get_template_file(self, service):
        """ Return path to a pulled template file """
        return os.path.join(self.templates_dir, "%s.yaml" % service.get("name"))

    def get_services(self, service_names):
        """ Return a list of service objects.
            service_names: can be 'all', a list of service names,
            or the name of a single service
        """

        if service_names == "all":
            result = self.services.values()
        elif isinstance(service_names, list):
            result = [self.services.get(s) for s in service_names if self.services.get(s)]
        else:
            # single service
            result = [self.services.get(service_names)]

        if len(result) == 0:
            logger.error("Could not find services %s" % service_names)

        return result

    def download_template(self, s, token):
        """ Returns a string containing the template of a service """
        url = self.get_raw(s)

        logger.info("Downloading: %s" % self.get_raw(s))

        headers = {}

        if token:
            headers = {"Authorization": "token %s" % token,
                       "Accept": "application/vnd.github.v3.raw"}

        r = requests.get(url, headers=headers)  # FIXME

        if r.status_code != 200:
            raise Exception("Couldn't pull the template.")

        return r.content

    def collect_services(self, service_names, token=None, dry_run=False, fail_on_error=False):
        """ Download templates from repositories """
        service_list = self.get_services(service_names)

        for s in service_list:
            logger.info("Service: %s" % s.get("name"))

            try:
                template = self.download_template(s, token)
            except Exception as e:
                logger.error(e)
                logger.warning("Skipping %s" % s.get("name"))

                if fail_on_error:
                    raise

                continue

            if not dry_run:
                filename = self.get_template_file(s)

                with open(filename, "w") as fp:
                    fp.write(template)

                logger.info("Template written to %s" % filename)

    def update(self, cmd_type, service_name, value, output_file=None):
        """ Update service object and write it to file """
        services = self.get_services(service_name)
        if len(services) == 0:
            raise Exception("Could not found the service")
        elif len(services) > 1:
            raise Exception("Expecting only one service")

        service = services[0]
        if service[cmd_type] == value:
            logger.warning("Skipping update of %s, no change" % service)
            return
        else:
            service[cmd_type] = value

        try:
            # Double check that the service is retrievable with new change, otherwise abort
            self.collect_services(service_name, dry_run=True, fail_on_error=True)
        except Exception as e:
            logger.error("Aborting update: %s" % e)
            return

        if not output_file:
            output_file = os.path.join(self.services_dir, service["file"])

        self.write_service_file(service_name, output_file)

    def process_image_tag(self, services, output_dir, template_filter=None, force=False, local=False):
        """ iterates through the services and runs oc process to generate the templates """

        if not find_executable("oc"):
            raise Exception("Aborting: Could not find oc binary")

        for s in self.get_services(services):
            if s.get("skip") and not force:
                logger.warning("INFO: Skipping %s, use -f to force processing of all templates" % s.get("name"))
                continue

            output = ""
            template_file = self.get_template_file(s)

            # Verify the 'hash' key
            if not s["hash"]:
                logger.warning("Skipping %s (it doesn't contain the 'hash' key)" % s["name"])
                continue
            elif s["hash"] == "master":
                tag = "latest"
            else:
                hash_len = s.get("hash_length", self._default_hash_length)
                tag = s["hash"][:hash_len]

            parameters = [{"name": "IMAGE_TAG", "value": tag}]
            service_params = s.get("parameters", {})

            for key, val in service_params.iteritems():
                parameters.append({"name": key, "value": val})

            params_processed = ["%s=%s" % (i["name"], i["value"]) for i in parameters]
            local_opt = "--local" if local else ""

            cmd = ["oc", "process", local_opt, "--output", "yaml", "-f", template_file]
            process_cmd = cmd + params_processed

            output_file = os.path.join(output_dir, "%s.yaml" % s["name"])

            logger.info("%s > %s" % (" ".join(process_cmd), output_file))

            try:
                output = subprocess.check_output(process_cmd)

                if template_filter:
                    output = self.apply_filter(template_filter, output)

                with open(output_file, "w") as fp:
                    fp.write(output)

            except subprocess.CalledProcessError as e:
                print e.message
                sys.exit(1)

    def template(self, cmd_type, services, output_dir=None, template_filter=None, force=False, local=False):
        """ Process templates """
        if not output_dir:
            output_dir = self.output_dir

        if not os.path.isdir(output_dir):
            os.mkdir(output_dir) #FIXME

        if cmd_type == "tag":
            self.process_image_tag(services, output_dir, template_filter, force, local)

    def get(self, cmd_type, services):
        """ Get information about services printed to stdout """
        services_list = self.get_services(services)

        if len(services_list) == 0:
            raise Exception("Unknown service %s" % services)

        result = []
        for service in services_list:
            if cmd_type in service.keys():
                result.append(service.get(cmd_type))
            elif cmd_type in "template-url":
                result.append(self.get_raw(service))
            elif cmd_type in "hash_length":
                result.append(self._default_hash_length)
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

    def validate(self):
        """ Apply all validation rules on all the templates that must be already available

            Returns two values: bool and list

            The first value (bool) indicates whether the validation is
            succesful. The second value (list) is the list of error messages. It
            only makes if the first value is false.

        """

        valid = True
        errors_service = {}

        for service_name, service in self.services.items():
            if service.get('hash'):
                template_file = self.get_template_file(service)
                template = anymarkup.parse_file(template_file)

                for rule_class in VALIDATION_RULES:
                    rule = rule_class(template)
                    errors = rule.validate()

                    if errors:
                        valid = False
                        errors_service.setdefault(
                            service_name, []).extend(errors)

        return valid, errors_service

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
