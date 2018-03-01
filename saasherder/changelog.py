# -*- coding: utf-8 -*-

from subprocess import Popen, PIPE
from dateutil.parser import parse

import logging
import os
import textwrap

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run(cmd):
    logger.info("$ {}".format(cmd))
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise Exception("$ {} FAILED with exit code {}"
                        .format(cmd, p.returncode))

    return stdout.decode('utf-8')

class ChangelogRender(object):
    def __init__(self, changelog, old, new, url):
        self.changelog = changelog
        self.old = old
        self.new = new
        self.url = url

    def markdown(self):
        header_template = "Context changes: [{old:.7}..{new}]({url}/compare/{old}...{new})\n\n"

        section_template = textwrap.dedent("""\
                           **[{names}]({url})**

                           Changes: [{old:.7}..{new:.7}]({url}/compare/{old}...{new})

                           Last updated at {last_changed}

                           {log}""")

        commit_template =  '- [%h]({url}/commit/%H) %s'


        return self.render(header_template, section_template, commit_template)

    def render(self, header_template, section_template, commit_template):
        """Pretty print the change log"""

        # Build the body
        header = header_template.format(url=self.url, old=self.old, new=self.new)

        body = [header]

        for service in self.changelog.changed_services:
            names = ", ".join(service['names'])
            url = service['url']

            section = section_template.format(names=names,
                                              url=url,
                                              old=service['old'],
                                              new=service['new'],
                                              log=self.log(service, commit_template),
                                              last_changed=self.last_changed(service))
            body.append(section)

        return '\n'.join(body)

    def log(self, service, commit_template):
        """Get the changelog for one service"""
        template = commit_template.format(url=service['url'])
        git_log_cmd = "git log --format='{}' {}...{}".format(template, service['old'], service['new'])
        return self.changelog.service_run(service, git_log_cmd)

    def last_changed(self, service):
        """Get the commit time for service at specific commit"""
        return self.changelog.service_run(service, "git log -1 --format=%cd {}".format(service['new'])).strip()

class Changelog(object):

    workspace = "_workspace/"

    def __init__(self, parent):
        self.parent = parent

        # Key: url of the service
        # Value: list of services that have changed
        self.changed_services = []

    def fetch_diff(self, now, previous):
        """Return the difference between 2 service lists

        This is not a commutative relationship. We are looking for services in
        first list which differ from that in second list. a ⊕ b ≠ b ⊕ a.

        This gets messy when the hash refers to a branch or none. Ignoring such
        services for now.
        """

        # All the services that changed. We will store only those that exist in
        # now and in previous, for which 'hash' is defined in both
        changed_services = {}
        for service_name, service in now.items():
            try:
                prev_service = previous[service_name]
                service_hash = service['hash']
                prev_service_hash = prev_service['hash']
            except KeyError:
                # Skip if prev_service is not found
                # or if 'hash' is not defined for either service
                continue

            if service_hash is None or prev_service_hash is None:
                continue

            url = service['url'].rstrip('/')

            if prev_service_hash != service_hash:
                if url in changed_services:
                    changed_services[url]['names'].append(service_name)
                else:
                    diff_item = dict(name=service_name,
                                     names=[service_name],
                                     url=url,
                                     new=service_hash,
                                     old=prev_service_hash)

                    changed_services[url] = diff_item

        self.changed_services = changed_services.values()
        return self.changed_services

    def worktree(self, service):
        """Get git worktree path for a service"""
        return self.workspace + service['name']

    def service_run(self, service, cmd):
        """Run in the directory of the service"""
        return run("cd {} && {}".format(self.worktree(service), cmd))

    def _clone(self, service):
        """Private; use checkout instead"""
        run("git clone {} {}".format(service['url'], self.worktree(service)))

    def _fetch(self, service):
        """Private; use checkout instead"""
        self.service_run(service, "git fetch")

    def checkout(self, service):
        """Get a service checked out at specified version"""

        service_name = service['name']

        if os.path.exists(self.worktree(service)):
            logger.info("Found git worktree for {}; updating".format(service_name))
            self._fetch(service)
        else:
            logger.info("Cloning git worktree for {}".format(service_name))
            self._clone(service)

        return self.service_run(service, "git checkout {}".format(service['new']))

    def generate(self, context, old, new):

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
            branch = run("git symbolic-ref --short HEAD").strip()
            logger.info("On branch {} before generating changelog"
                        .format(branch))

        except Exception:
            branch = run("git rev-parse --short HEAD").strip()
            logger.info("HEAD at {} before generating changelog"
                        .format(branch))

        # Resolve commit if a date was passed in 'old'
        try:
            dt_old = parse(old)
            old = run("git rev-list -1 --before='{}' {}".format(dt_old, branch)).strip()
        except:
            pass

        # Resolve commit if a date was passed in 'new'
        try:
            dt_new = parse(new)
            new = run("git rev-list -1 --before='{}' {}".format(dt_new, branch)).strip()
        except:
            pass

        # Checkout to previous version and get services
        run("git checkout {}".format(old))
        previous, _ = self.parent.load_services()

        run("git checkout {}".format(new))
        now, _ = self.parent.load_services()

        # Go back to where we were
        run("git checkout {}".format(branch))

        self.fetch_diff(now, previous)

        logger.info("{} services changed".format(len(self.changed_services)))

        # Fetch all the services that changed
        for service in self.changed_services:
            # only need to checkout the first
            self.checkout(service)

        url = run("git remote get-url origin").rstrip("/").rstrip(".git")

        render = ChangelogRender(self, old, new, url)

        print render.markdown()

        return 0
