#!/bin/bash
git subtree push --prefix=devops/ansible/roles/girder \
    "https://$ANSIBLE_ROLE_GIRDER_OAUTH_TOKEN@github.com/girder/ansible-role-girder.git" master
