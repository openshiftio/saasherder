import yaml
from itertools import chain
import os
import subprocess


class Changelog:

    workspace = "_workspace/"

    @staticmethod
    def context_dir(context):
        return context + "-services/"

    def path(self, context, service_name):
        """Get YAML config path for a service"""

        return self.context_dir(context) + service_name + ".yaml"

    def definitions(self, context, service_name):
        """Get list of services defined in service file"""

        with open(self.path(context, service_name)) as f:
            parsed = yaml.load(f)
            return parsed['services']

    def service_names(self, context):
        """Get names of all services in a context"""

        dir = self.context_dir(context)
        files = os.listdir(dir)

        return [os.path.splitext(f)[0] for f in files]

    def services(self, context):
        """Get all services in the context"""

        names = self.service_names(context)
        dsls = [self.definitions(context, name) for name in names]
        return list(chain(*dsls))

    @staticmethod
    def diff(s1, s2):
        """Return the difference between 2 service lists

        This is not a commutative relationship. We are looking for services in
        first list which differ from that in second list. a ⊕ b ≠ b ⊕ a.

        This gets messy when the hash refers to a branch or none. Ignoring such
        services for now.
        """

        # All the services that changed
        changed = [service for service in s1 if service not in s2]

        def old(service):
            cadidates = [s for s in s2 if s['name'] == service['name']]
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
        return subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              shell=True, check=True) \
                         .stdout.decode('utf-8')

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

        if os.path.exists(self.worktree(service['name'])):
            self._fetch(service)
        else:
            self._clone(service)

        worktree = self.worktree(service['name'])
        cmd = "cd {} && git checkout {} ".format(worktree, version)

        return self.run(cmd)

    def log(self, service, start, end):
        """Get the changelog for one service"""

        worktree = self.worktree(service['name'])
        cmd = "cd {} && git log --oneline {}..{} ".format(worktree, end, start)

        return self.run(cmd)

    @staticmethod
    def markdown(changelog, start, end):
        """Pretty print the change log

        The incoming object is a list of `(name, messages)` tuples.
        """

        header = "# Changelog \n\n## From version {} to {}".format(start, end)

        body = ["## {} \n{} \n".format(name, messages)
                for (name, messages) in changelog]

        return header + ''.join(body)

    def main(self, context, start, end):

        # Where am I right now?
        branch = self.run("git symbolic-ref --short HEAD")

        # Checkout to previous version and get services
        self.run("git checkout {}".format(end))
        previous = self.services(context)

        self.run("git checkout {}".format(start))
        now = self.services(context)

        # Go back to where we were
        self.run("git checkout {}".format(branch))

        changed = self.diff(previous, now)

        # Fetch all the services that changed
        for service in changed:
            self.checkout(service, service['new'])

        # Get the changelog for each service as a `(name, [messages])` tuple
        changelog = [(service['name'],
                      self.log(service, service['old'], service['new'])) for
                     service in changed]

        markdown = self.markdown(changelog, start, end)

        print(markdown)

        return 0
