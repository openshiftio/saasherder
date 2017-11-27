# -*- coding: utf-8 -*-

from subprocess import Popen, PIPE
import logging
import os


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Changelog(object):
    """A Mixin class to go with SaasHerder"""

    workspace = "_workspace/"

    def __init__(self, parent):
        self.parent = parent

    @staticmethod
    def diff(s1, s2):
        """Return the difference between 2 service lists

        This is not a commutative relationship. We are looking for services in
        first list which differ from that in second list. a ⊕ b ≠ b ⊕ a.

        This gets messy when the hash refers to a branch or none. Ignoring such
        services for now.
        """

        # All the services that changed
        changed = [s1[service] for service in s1 if s1[service] != s2[service]]

        def old(service):
            cadidates = [s for s in s2.values()
                         if s['name'] == service['name']]
            return cadidates[0].get('hash') if cadidates else None

        # Filter changed services for which I cannot get a changelog
        useful = [s for s in changed if s.get('hash') and old(s)]

        # Now changed services can be new ones or change in hash
        return [{
            'name': service['name'],
            'url': service['url'],
            'new': service.get('hash', 'master'),  # NOTE: null here is silly
            'old': old(service)
        } for service in useful]

    @staticmethod
    def run(cmd):
        logger.info("$ {}".format(cmd))
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            raise Exception("$ {} FAILED with exit code {}"
                            .format(cmd, p.returncode))

        return stdout.decode('utf-8')

    def worktree(self, service_name):
        """Get git worktree path for a service"""

        return self.workspace + service_name

    def _clone(self, service):
        """Private; use checkout instead"""

        cmd = "git clone {} {}".format(service['url'],
                                       self.worktree(service['name']))
        self.run(cmd)

    def _fetch(self, service):
        """Private; use checkout instead"""

        worktree = self.worktree(service['name'])
        cmd = "cd {} && git fetch ".format(worktree)

        return self.run(cmd)

    def checkout(self, service, version):
        """Get a service checked out at specified version"""

        name = service['name']
        if os.path.exists(self.worktree(name)):
            logger.info("Found git worktree for {}; updating".format(name))
            self._fetch(service)
        else:
            logger.info("Cloning git worktree for {}".format(name))
            self._clone(service)

        worktree = self.worktree(service['name'])
        cmd = "cd {} && git checkout {} ".format(worktree, version)

        return self.run(cmd)

    def log(self, service, new, old):
        """Get the changelog for one service"""

        worktree = self.worktree(service['name'])
        remote = service['url'].strip('/')
        template = '[%h](_REMOTE_/commit/%H) %s'

        cmd = ("cd {} && git log --format='{}' {}...{}"
               .format(worktree, template, new, old))

        return self.run(cmd).replace('_REMOTE_', remote)

    @staticmethod
    def markdown(changelog, new, old):
        """Pretty print the change log

        The incoming object is a list of `(name, messages)` tuples.
        """

        url = "https://github.com/openshiftio/saas-openshiftio"

        # Github's compare view needs the commits in opposite order ?
        header = ("# [saas-openshift.io]({url}): "
                  "[{new}..{old}]({url}/compare/{old}...{new}) \n"
                  .format(url=url, old=old, new=new))

        body = ["## [{s[name]}]({s[url]}): "
                "[{s[new]:.7}..{s[old]:.7}]"
                "({s[url]}/compare/{s[old]}...{s[new]})\n\n"
                "{messages}"
                .format(s=service, messages=messages)
                for (service, messages) in changelog]

        return '\n'.join([header] + body)

    def generate(self, context, new, old):

        logger.info("Generating changelog for {}".format(context))

        # This is :( - using magic mutable state variables instead of
        # explicitly passing arguments. The number of indirections just makes
        # reading and understanding code much more painful than necessary.
        # `self.config["current"]` and `self.config["contexts"]` can be avoided
        # to make this far simpler.
        self.parent.config.switch_context(context)

        # Where am I right now?
        try:
            # This will fail for detached HEAD
            branch = self.run("git symbolic-ref --short HEAD").strip()
            logger.info("On branch {} before generating changelog"
                        .format(branch))

        except Exception:
            branch = self.run("git rev-parse --short HEAD").strip()
            logger.info("HEAD at {} before generating changelog"
                        .format(branch))

        # Checkout to previous version and get services
        self.run("git checkout {}".format(old))
        previous = self.parent.services

        self.run("git checkout {}".format(new))
        now = self.parent.services

        # Go back to where we were
        self.run("git checkout {}".format(branch))

        changed = self.diff(now, previous)
        logger.info("{} services changed".format(len(changed)))

        # Fetch all the services that changed
        for service in changed:
            self.checkout(service, service['new'])

        # Get the changelog for each service as a `(service, [messages])` tuple
        changelog = [(service,
                      self.log(service, service['new'], service['old']))
                     for service in changed]

        markdown = self.markdown(changelog, new, old)

        print(markdown)

        return 0