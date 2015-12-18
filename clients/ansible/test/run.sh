#/bin/bash

ansible-playbook -i .vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory \
                 --private-key=.vagrant/machines/girder/virtualbox/private_key \
                 -u vagrant $*
