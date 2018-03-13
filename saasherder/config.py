import os
import anymarkup

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SaasConfig(object):
  def __init__(self, path, context=None):
    self.path = path
    self.load(context)

  def load(self, context=None):
    self.config = anymarkup.parse_file(self.path)
    if not context:
      context = self.current()
    ctx = self.context_exists(context)
    if not ctx and not context:
      raise Exception("Could not find current context %s" % (context))
    elif context != self.current():
      self.switch_context(context)

  def save(self):
    anymarkup.serialize_file(self.config, self.path)

  def context_exists(self, context):
    for c in self.config["contexts"]:
      if context == c["name"]:
        return c
    return None

  def add_context(self, name, services_dir, templates_dir, output_dir):
    c = self.context_exists(name)

    if c:
      logger.info("Context %s exists, updating." % name)
      context = c
    else:
      context = {}

    context["name"] = name
    context["data"] = {}
    context["data"]["services_dir"] = services_dir
    context["data"]["templates_dir"] = templates_dir
    context["data"]["output_dir"] = output_dir

    if not c:
      self.config["contexts"].append(context)

    self.save()

  def switch_context(self, context):
    if context == self.config["current"]:
      return

    if self.context_exists(context):
      self.config["current"] = context
      self.save()
      logger.info("Switchted context to %s" % context)
    else:
      raise Exception("Context %s does not exist" % context)

  def current(self):
    return self.config["current"]

  def get(self, key):
    context = self.context_exists(self.current())

    if not context:
      raise Exception("Context %s, set as 'current', does not exist" % self.current())

    return context["data"][key]

  def get_contexts(self):
    for c in self.config["contexts"]:
      yield c["name"]

