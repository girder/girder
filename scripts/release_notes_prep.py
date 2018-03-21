# Find head of current branch and merge commit of last release
# Get merges in between
current_branch_head = '8dfeae34'
last_release_head = '3550d330'
cmd = 'git log --oneline --merges %s ^%s' % (current_branch_head, last_release_head)
import subprocess
merge_commits = subprocess.check_output(cmd, shell=True).split('\n')

# remove all merges of master or origin/master
master_merges = ["Merge branch 'master'", "Merge remote-tracking branch 'origin/master'"]
for master_merge in master_merges:
    merge_commits = [commit for commit in merge_commits if commit.find(master_merge) == -1 and commit.strip()]

import re
# map pr #s to commit messages
prs_to_commits = {re.search('#\d+', commit).group(0):commit for commit in merge_commits}

# Get PRs from CHANGELOG.rst

changelog_prs = []
changelog = open('CHANGELOG.rst', 'r')
for line in changelog.readlines():
  changelog_prs.extend(re.findall('#\d+', line))

for pr in changelog_prs:
    if pr in prs_to_commits:
        del prs_to_commits[pr]

# These should now be the PRs that do not appear in the changelog
for pr, commit in prs_to_commits.items():
    # print out lines that can be pasted into GitHub
    print '- [ ] %s' % commit[commit.find('#'):]
