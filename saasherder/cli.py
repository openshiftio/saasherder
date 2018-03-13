#!/usr/bin/env python

import argparse

from saasherder import SaasHerder
from config import SaasConfig

def main():
    parser = argparse.ArgumentParser(description='')

    parser.add_argument('-d', '--debug', default=False, action='store_true',
                        help='Run in debug mode')
    parser.add_argument('-c', '--config', default="config.yaml",
                        help='Config file for saas herder')
    parser.add_argument('--context', default=None,
                        help='Context to use')
    parser.add_argument('--environment', default=None,
                        help='Environment to use to override service defined values')

    subparsers = parser.add_subparsers(dest="command")

    # subcommand: pull
    subparser_pull = subparsers.add_parser("pull",
                                           help="Download templates from repositories and store them locally")

    subparser_pull.add_argument('service', nargs="*", default="all")
    subparser_pull.add_argument('--token', default=None, help="Token to use when pulling from private repo")

    # subcommand: update
    subparser_update = subparsers.add_parser("update",
                                             help="Replace parameters in a service template and write it to a file")

    subparser_update.add_argument('-o', '--output-file', default=None,
                                  help='Name of the output file for updated services yaml')
    subparser_update.add_argument('type', choices=["hash", "path"],
                                  help="What to update")
    subparser_update.add_argument('service', nargs="?", default=None,
                                  help="Service to be updated")
    subparser_update.add_argument('value',
                                  help="Value to be used in services yaml")

    # subcommand: template
    subparser_template = subparsers.add_parser("template",
                                               help="Runs oc process to generate the templates. Requires running pull first")

    subparser_template.add_argument('-f', '--force', default=False, action='store_true',
                        help='Force processing of all templates (i.e. those with skip: True)')
    subparser_template.add_argument('--local', default=False, action='store_true',
                        help='Use --local option for oc process - processing happen locally instead on server')
    subparser_template.add_argument('--output-dir', default=None,
                        help='Output directory where the updated templates will be stored')
    subparser_template.add_argument('--filter', default=None,
                        help='Comma separated list of kinds you want to filter out')
    subparser_template.add_argument("type", choices=["tag"],
                                    help="Update image tag with commit hash")
    subparser_template.add_argument("services", nargs="*", default="all",
                                    help="Service which template should be updated")

    # subcommand: get
    subparser_get = subparsers.add_parser("get", help="Extracts info from a service")

    subparser_get.add_argument("type", choices=["path", "url", "hash", "hash_length", "template-url"],
                                    help="Update image tag with commit hash")
    subparser_get.add_argument("services", nargs="*", default="all",
                                    help="Services to query")

    # subcommand: config
    subparser_config = subparsers.add_parser("config", help="Extracts info from the configuration file")

    subparser_config.add_argument("type", choices=["get-contexts"],
                                    help="Prints the list of contexts in the configuration file")

    # subcommand: changelog
    subparser_changelog = subparsers.add_parser("changelog")

    subparser_changelog.add_argument("--context", action="store")
    subparser_changelog.add_argument("--format", choices=['markdown', 'plain'], default='plain')
    subparser_changelog.add_argument("old", action="store", help="Commit or a date (parsed by dateutil.parser)")
    subparser_changelog.add_argument("new", action="store", help="Commit or a date (parsed by dateutil.parser)")

    # Execute command
    args = parser.parse_args()

    se = SaasHerder(args.config, args.context, args.environment)

    if args.command == "pull":
      if args.service:
        se.collect_services(args.service, args.token)
    elif args.command == "update":
      se.update(args.type, args.service, args.value, output_file=args.output_file)
    elif args.command == "template":
      filters = args.filter.split(",") if args.filter else None
      se.template(args.type, args.services, args.output_dir, filters, force=args.force, local=args.local)
    elif args.command == "get":
      for val in se.get(args.type, args.services):
        print val
    elif args.command == "config":
      sc = SaasConfig(args.config)
      if args.type == "get-contexts":
        for context in sc.get_contexts():
          print context
    elif args.command == "changelog":
        se.changelog.generate(args.context, args.old, args.new, args.format)

if __name__ == "__main__":
  main()
