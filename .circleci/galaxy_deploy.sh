#!/bin/bash
set -e

# Ansible role repo to deploy to
readonly ANSIBLE_ROLE_GITHUB_ORG="girder"
readonly ANSIBLE_ROLE_GITHUB_REPO="ansible-role-girder"

readonly SUBTREE_PREFIX="devops/ansible/roles/girder"
readonly SUBTREE_DEST_REPO="git@github.com:$ANSIBLE_ROLE_GITHUB_ORG/$ANSIBLE_ROLE_GITHUB_REPO.git"
readonly SUBTREE_DEST_BRANCH="master"

# Make sure all git objects are accessible
# This is useful in CI contexts where shallow clones are common
git fetch --unshallow origin || git fetch origin

# Push any changes that have occurred
git reset --hard
git branch ansible-role-subtree "origin/$SUBTREE_DEST_BRANCH"
git filter-branch --subdirectory-filter "$SUBTREE_PREFIX" ansible-role-subtree
git push "$SUBTREE_DEST_REPO" ansible-role-subtree:"$SUBTREE_DEST_BRANCH"

# Install ansible for ansible-galaxy
pip install ansible

# Import the changes into Ansible Galaxy
ansible-galaxy login --github-token="$ANSIBLE_GALAXY_GITHUB_TOKEN"
ansible-galaxy import girder ansible-role-girder
