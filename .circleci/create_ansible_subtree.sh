#!/bin/bash
set -e

# Create a subtree with only the Ansible role and push it
readonly SUBTREE_PREFIX="devops/ansible-role-girder"
readonly SUBTREE_DEST_REPO="git@github.com:girder/ansible-role-girder.git"
readonly SUBTREE_DEST_BRANCH="master"

# Make sure all git objects are accessible
# This is useful in CI contexts where shallow clones are common
git fetch --unshallow origin || git fetch origin

# Push any changes that have occurred
git branch --force ansible-role-subtree "origin/$SUBTREE_DEST_BRANCH"
export FILTER_BRANCH_SQUELCH_WARNING=1
git filter-branch --force --subdirectory-filter "$SUBTREE_PREFIX" ansible-role-subtree
git push "$SUBTREE_DEST_REPO" ansible-role-subtree:"$SUBTREE_DEST_BRANCH"
