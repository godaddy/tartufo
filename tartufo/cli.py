# -*- coding: utf-8 -*-

import argparse
import re

import truffleHogRegexes.regexChecks

from tartufo import config, scanner, util


def main(argv=None):  # noqa:C901
    args = parse_args(argv)

    if not (args.do_entropy or args.do_regex):
        raise RuntimeError("no analysis requested")

    rules_regexes = config.configure_regexes_from_args(args, truffleHogRegexes.regexChecks.regexes)

    # read & compile path inclusion/exclusion patterns
    path_inclusions = []
    path_exclusions = []
    if args.include_paths:
        for pattern in set(l[:-1].lstrip() for l in args.include_paths):
            if pattern and not pattern.startswith("#"):
                path_inclusions.append(re.compile(pattern))
    if args.exclude_paths:
        for pattern in set(l[:-1].lstrip() for l in args.exclude_paths):
            if pattern and not pattern.startswith("#"):
                path_exclusions.append(re.compile(pattern))

    if args.pre_commit:
        output = scanner.find_staged(
            args.repo_path,
            args.output_json,
            args.do_regex,
            args.do_entropy,
            custom_regexes=rules_regexes,
            suppress_output=False,
            path_inclusions=path_inclusions,
            path_exclusions=path_exclusions,
        )
    else:
        if args.repo_path is None and args.git_url is None:
            print("ERROR: One of git_url or --repo_path is required")
            return 1
        output = scanner.find_strings(
            args.git_url,
            args.since_commit,
            args.max_depth,
            args.output_json,
            args.do_regex,
            args.do_entropy,
            custom_regexes=rules_regexes,
            suppress_output=False,
            branch=args.branch,
            repo_path=args.repo_path,
            path_inclusions=path_inclusions,
            path_exclusions=path_exclusions,
        )
    if args.cleanup:
        util.clean_outputs(output)
    else:
        issues_path = output.get("issues_path", None)
        if issues_path:
            print("Results have been saved in {}".format(issues_path))

    if output["found_issues"]:
        return 1
    return 0


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Find secrets hidden in the depths of git."
    )
    parser.add_argument(
        "--json", dest="output_json", action="store_true", help="Output in JSON"
    )
    parser.add_argument(
        "--git-rules-repo",
        dest="git_rules_repo",
        help="Git repo for externally-sourced rules",
    )
    parser.add_argument(
        "--git-rules",
        dest="git_rules_filenames",
        nargs="+",
        default=[],
        action="append",
        help="Git-relative path(s) to regex rules json list file(s)",
    )
    parser.add_argument(
        "--rules",
        dest="rules_filenames",
        nargs="+",
        default=[],
        action="append",
        help="Path(s) to regex rules json list file(s)",
    )
    parser.add_argument(
        "--default-regexes",
        dest="do_default_regexes",
        metavar="BOOLEAN",
        nargs="?",
        default="True",
        const="True",
        help="If set to one of (no, n, false, f, n, 0) and --rules or --git-rules is also specified, ignore default"
             "regexes, otherwise the regexes from the rules files will be appended to the default regexes",
    )
    parser.add_argument(
        "--entropy",
        dest="do_entropy",
        metavar="BOOLEAN",
        nargs="?",
        default="True",
        const="True",
        help="Enable entropy checks [default: True]",
    )
    parser.add_argument(
        "--regex",
        dest="do_regex",
        metavar="BOOLEAN",
        nargs="?",
        default="False",
        const="True",
        help="Enable high signal regex checks [default: False]",
    )
    parser.add_argument(
        "--since_commit",
        dest="since_commit",
        default=None,
        help="Only scan from a given commit hash",
    )
    parser.add_argument(
        "--max_depth",
        dest="max_depth",
        default=1000000,
        help="The max commit depth to go back when searching for " "secrets",
    )
    parser.add_argument(
        "--branch", dest="branch", default=None, help="Name of the branch to be scanned"
    )
    parser.add_argument(
        "-i",
        "--include_paths",
        type=argparse.FileType("r"),
        metavar="INCLUDE_PATHS_FILE",
        help="File with regular expressions (one per line), at least one of which must match a Git "
        'object path in order for it to be scanned; lines starting with "#" are treated as '
        "comments and are ignored. If empty or not provided (default), all Git object paths are "
        "included unless otherwise excluded via the --exclude_paths option.",
    )
    parser.add_argument(
        "-x",
        "--exclude_paths",
        type=argparse.FileType("r"),
        metavar="EXCLUDE_PATHS_FILE",
        help="File with regular expressions (one per line), none of which may match a Git object path "
        'in order for it to be scanned; lines starting with "#" are treated as comments and are '
        "ignored. If empty or not provided (default), no Git object paths are excluded unless "
        "effectively excluded via the --include_paths option.",
    )
    parser.add_argument(
        "--repo_path",
        type=str,
        dest="repo_path",
        default=None,
        help="Path to local repo clone. If provided, git_url will not be used",
    )
    parser.add_argument(
        "--cleanup",
        dest="cleanup",
        action="store_true",
        help="Clean up all temporary result files",
    )
    parser.add_argument(
        "git_url", nargs="?", type=str, help="repository URL for secret searching"
    )
    parser.add_argument(
        "--pre_commit",
        dest="pre_commit",
        action="store_true",
        help="Scan staged files in local repo clone",
    )

    args = parser.parse_args(argv)

    # rules_filenames and git_rules_filenames will be generated as a list of lists, they need to be flattened
    filename_lists = args.rules_filenames
    args.rules_filenames = [filename for filenames in filename_lists for filename in filenames]
    filename_lists = args.git_rules_filenames
    args.git_rules_filenames = [filename for filenames in filename_lists for filename in filenames]

    args.do_entropy = util.str2bool(args.do_entropy)
    args.do_regex = util.str2bool(args.do_regex)
    args.do_default_regexes = util.str2bool(args.do_default_regexes)
    return args
