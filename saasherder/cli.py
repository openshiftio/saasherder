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
    subparser_pull = subparsers.add_parser("pull")
    subparser_pull.add_argument('service', nargs="*", default="all")
    subparser_pull.add_argument('--token', default=None, help="Token to use when pulling from private repo")

    subparser_update = subparsers.add_parser("update")
    subparser_update.add_argument('-o', '--output-file', default=None,
                                  help='Name of the output file for updated services yaml')
    subparser_update.add_argument('type', choices=["hash", "path"],
                                  help="What to update")
    subparser_update.add_argument('service', nargs="?", default=None,
                                  help="Service to be updated")
    subparser_update.add_argument('value',
                                  help="Value to be used in services yaml")

    subparser_template = subparsers.add_parser("template")
    #subparser_template.add_argument('--all', default=False, action='store_true',
    #                    help='Perform the action on all services')
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

    subparser_template = subparsers.add_parser("get")
    #subparser_template.add_argument('--all', default=False, action='store_true',
    #                    help='Perform the action on all services')
    subparser_template.add_argument("type", choices=["path", "url", "hash", "hash_length", "template-url"],
                                    help="Update image tag with commit hash")
    subparser_template.add_argument("services", nargs="*", default="all",
                                    help="Service which template should be updated")

    subparser_template = subparsers.add_parser("config")
    subparser_template.add_argument("type", choices=["get-contexts"],
                                    help="Subcommands for config command")

    subparser_changelog = subparsers.add_parser("changelog")
    subparser_changelog.add_argument("--context", action="store")
    subparser_changelog.add_argument("old", action="store")
    subparser_changelog.add_argument("new", action="store")

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
      se.get(args.type, args.services)
    elif args.command == "config":
      sc = SaasConfig(args.config)
      if args.type == "get-contexts":
        sc.print_contexts()
    elif args.command == "changelog":
        se.changelog.generate(args.context, args.old, args.new)

if __name__ == "__main__":
  main()
