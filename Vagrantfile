Vagrant.configure("2") do |config|
  config.vm.box = ENV["VAGRANT_BOX"] || "ubuntu/trusty64"

  if Vagrant.has_plugin?("vagrant-cachier")
    config.cache.scope = :box
    config.cache.enable :apt
    config.cache.enable :yum
    config.cache.enable :npm
  end

  config.vm.hostname = "girder"

  # Disable port forwarding for ansible testing, since it makes running
  # VMs in parallel harder.
  unless ENV["ANSIBLE_TESTING"]
    config.vm.network "forwarded_port", guest: 8080, host: 9080
    config.vm.post_up_message = "Girder is running at http://localhost:9080"

    config.vm.synced_folder ".", "/vagrant", disabled: true
    config.vm.synced_folder ".", "/home/vagrant/girder"
  end

  # Disable ansible_local for testing, this makes it easier to test across ansible versions
  if (!ENV["ANSIBLE_TESTING"] && Gem::Version.new(Vagrant::VERSION) > Gem::Version.new('1.8.1'))
    # Vagrant > 1.8.1 is required due to
    # https://github.com/mitchellh/vagrant/issues/6793
    provisioner_type = "ansible_local"
  else
    provisioner_type = "ansible"
  end

  client_testing = ENV["ANSIBLE_CLIENT_TESTING"] || false
  bind_node_modules = (ENV.fetch("BIND_NODE_MODULES", "true") != "false" && !client_testing && !ENV["ANSIBLE_TESTING"])

  if bind_node_modules 
    $script = <<SCRIPT
mkdir -p /home/vagrant/girder/node_modules
chown vagrant:vagrant /home/vagrant/girder/node_modules
mkdir -p /home/vagrant/girder_node_modules
chown vagrant:vagrant /home/vagrant/girder_node_modules
if [[ ! $(grep -q "girder_node_modules" /etc/fstab) ]]; then
  echo "# bind mount girder node_modules" >> /etc/fstab
  echo "/home/vagrant/girder_node_modules /home/vagrant/girder/node_modules none defaults,bind 0 0" >> /etc/fstab
fi
mount /home/vagrant/girder_node_modules
SCRIPT
    config.vm.provision "shell", inline: $script
  end

  config.vm.provision provisioner_type do |ansible|

    if client_testing then
      ansible.groups = {
        "girder" => ["default"]
      }

      ansible.playbook = "devops/ansible/roles/girder/library/test/site.yml"
      ansible.galaxy_role_file = "devops/ansible/roles/girder/library/test/requirements.yml"
    else
      example = ENV["GIRDER_EXAMPLE"] || "girder-dev-environment"
      ansible.playbook = "devops/ansible/examples/#{example}/site.yml"

      if File.exist?("devops/ansible/examples/#{example}/requirements.yml")
        ansible.galaxy_role_file = "devops/ansible/examples/#{example}/requirements.yml"
      end
    end

    if provisioner_type == "ansible_local"
      ansible.provisioning_path = "/home/vagrant/girder"
    end
  end

  config.vm.provider "virtualbox" do |virtualbox|
    virtualbox.memory = 2048
  end
end
