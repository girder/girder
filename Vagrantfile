# Vagrant > 1.8.1 is required due to
# https://github.com/mitchellh/vagrant/issues/6793
Vagrant.require_version ">= 1.8.3"

def true?(obj)
  obj = obj.to_s.downcase
  obj != "false" && obj != "off" && obj != "0"
end

Vagrant.configure("2") do |config|
  vagrant_box = ENV.fetch("VAGRANT_BOX", "ubuntu/trusty64")
  ansible_example_name = ENV.fetch("GIRDER_EXAMPLE", "girder-dev-environment")
  is_testing = true?(ENV.fetch("ANSIBLE_TESTING", false))
  is_client_testing = true?(ENV.fetch("ANSIBLE_CLIENT_TESTING", false))
  bind_node_modules = true?(ENV.fetch("BIND_NODE_MODULES", true))

  if Vagrant.has_plugin?("vagrant-cachier")
    config.cache.scope = :box
    config.cache.enable :apt
    config.cache.enable :yum
    config.cache.enable :npm
  end

  config.vm.box = vagrant_box
  config.vm.hostname = "girder"
  config.vm.provider "virtualbox" do |virtualbox|
    virtualbox.memory = 2048
  end

  # Disable port forwarding for ansible testing, since it makes running VMs in parallel harder.
  unless is_testing
    config.vm.network "forwarded_port", guest: 8080, host: 9080
    config.vm.post_up_message = "Girder is running at http://localhost:9080"

    config.vm.synced_folder ".", "/vagrant", disabled: true
    config.vm.synced_folder ".", "/home/vagrant/girder"
  end

  # Disable ansible_local for testing, this makes it easier to test across ansible versions
  provisioner_type = is_testing ? "ansible" : "ansible_local"

  config.vm.provision provisioner_type do |ansible|
    ansible.playbook = "devops/vagrants/vagrant-playbook.yml"
    ansible.extra_vars = {
      bind_node_modules: bind_node_modules
    }
    if provisioner_type == "ansible_local"
      ansible.provisioning_path = "/home/vagrant/girder"
    end
  end

  config.vm.provision provisioner_type do |ansible|
    if is_client_testing then
      ansible.groups = {
        "girder" => ["default"]
      }

      ansible.playbook = "devops/ansible/roles/girder/library/test/site.yml"
      ansible.galaxy_role_file = "devops/ansible/roles/girder/library/test/requirements.yml"
    else
      ansible.playbook = "devops/ansible/examples/#{ansible_example_name}/site.yml"

      if File.exist?("devops/ansible/examples/#{ansible_example_name}/requirements.yml")
        ansible.galaxy_role_file = "devops/ansible/examples/#{ansible_example_name}/requirements.yml"
      end
    end

    if provisioner_type == "ansible_local"
      ansible.provisioning_path = "/home/vagrant/girder"
    end
  end
end
