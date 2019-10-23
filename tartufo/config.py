import json
import os
import re
import shutil

from tartufo import util


def configure_regexes_from_args(args, default_regexes):
    if args.do_regex:
        if args.rules_filenames or (args.git_rules_repo and args.git_rules):
            rules_regexes = dict(default_regexes) if args.do_default_regexes else {}
            if args.git_rules_repo and args.git_rules:
                configure_regexes_from_git(args.git_rules_repo, args.git_rules, rules_regexes)
            if args.rules_filenames:
                configure_regexes_from_rules_files(args.rules_filenames, rules_regexes)
            return rules_regexes

        return dict(default_regexes)
    return {}


def configure_regexes_from_git(git_url, repo_rules_filenames, rules_regexes):
    rules_project_path = util.clone_git_repo(git_url)
    try:
        rules_filenames = [os.path.join(rules_project_path, repo_rules_filename)
                           for repo_rules_filename in repo_rules_filenames]
        return configure_regexes_from_rules_files(rules_filenames, rules_regexes)
    finally:
        shutil.rmtree(rules_project_path)


def configure_regexes_from_rules_files(rules_filenames, rules_regexes):
    for rules_filename in rules_filenames:
        load_rules_from_file(rules_filename, rules_regexes)

    return rules_regexes


def load_rules_from_file(rules_filename, rules_regexes):
    try:
        with open(rules_filename, "r") as rules_file:
            new_rules = json.loads(rules_file.read())
            for rule in new_rules:
                if rule in rules_regexes:
                    raise ValueError("Rule '{}' has been defined multiple times".format(rule))
                rules_regexes[rule] = re.compile(new_rules[rule])
    except (IOError, ValueError) as err:
        raise Exception("Error reading rules file '{}': {}".format(rules_filename, err))
