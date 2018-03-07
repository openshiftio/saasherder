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

    def plain(self):
        header_template = "Context changes: {old:.8}..{new}\n{url}/compare/{old:.8}...{new}\n"

        section_template = textwrap.dedent("""\
                           ### {name}

                           Url: {url}

                           List of services with this url:
                           {names_list}

                           Changes: {old:.8}..{new:.8} (Last updated at {last_changed})
                           {url}/compare/{old:.8}...{new:.8}

                           Commits:
                           {log}""")

        commit_template =  '- %s\n  {url}/commit/%h'

        return self.render(header_template, section_template, commit_template)

    def markdown(self):
        header_template = "Context changes: [{old:.8}..{new}]({url}/compare/{old}...{new})\n\n"

        section_template = textwrap.dedent("""\
                           **[{names}]({url})**

                           Changes: [{old:.8}..{new:.8}]({url}/compare/{old}...{new}) (Last updated at {last_changed})

                           {log}""")

        commit_template =  '- [%h]({url}/commit/%H) %s'


        return self.render(header_template, section_template, commit_template)

    def render(self, header_template, section_template, commit_template):
        """Pretty print the change log"""

        # Build the body
        header = header_template.format(url=self.url, old=self.old, new=self.new)

        body = [header]

        for service in self.changelog.changed_services:
            names_list = "\n".join(["- {}".format(n) for n in service['names']])
            url = service['url']

            section = section_template.format(name=service['name'],
                                              names_list=names_list,
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

        # list of changed services
        self.changed_services = []

    def fetch_diff(self, now, previous):
        """Return the difference between 2 service lists

        This is not a commutative relationship. We are looking for services in
        first list which differ from that in second list. a ⊕ b ≠ b ⊕ a.

        This gets messy when the hash refers to a branch or none. Ignoring such
        services for now.
        """

        # Keep list of services stored by url. Services may have the same
        # project url, we want to group them together. We will extract the
        # values of this dictionary and store it in self.changed_services.
        changed_services_by_url = {}

        for service_name, service in now.items():
            try:
                prev_service = previous[service_name]
                service_hash = service['hash']
                prev_service_hash = prev_service['hash']
            except KeyError:
                # Skip if prev_service is not found
                # or if 'hash' is not defined for either service
                continue

            # Hash may defined to None, in which case we need to skip
            if service_hash is None or prev_service_hash is None:
                continue

            url = service['url'].rstrip('/')

            if prev_service_hash != service_hash:
                if url in changed_services_by_url:
                    changed_services_by_url[url]['names'].append(service_name)
                else:
                    diff_item = dict(name=service_name,
                                     names=[service_name],
                                     url=url,
                                     new=service_hash,
                                     old=prev_service_hash)

                    changed_services_by_url[url] = diff_item

        self.changed_services = changed_services_by_url.values()

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


    def convert_date_to_commit(self, branch, date_or_commit):
        """
        Returns a commit.

        It can be called with either a date or a commit (or branch):
        - date: return the first commit before this date in 'branch'
        - else: return as is
        """

        # Try to dateparse the commit
        try:
            date = parse(date_or_commit)
        except ValueError:
            # Return the date_or_commit object as is: it's not in date format
            return date_or_commit

        # Get the first commit before the date
        return run("git rev-list -1 --before='{}' {}".format(date, branch)).strip()

    def generate(self, context, old, new, format):

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

        # Convert 'old' and 'new' to commits if they are dates
        old = self.convert_date_to_commit(branch, old)
        new = self.convert_date_to_commit(branch, new)

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
            self.checkout(service)

        url = run("git remote get-url origin").strip().rstrip("/").rstrip(".git")

        render = ChangelogRender(self, old, new, url)

        if format == "markdown":
            print render.markdown()
        elif format == "plain":
            print render.plain()

        return 0
