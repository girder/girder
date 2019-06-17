# Vagrant > 1.8.1 is required due to
# https://github.com/mitchellh/vagrant/issues/6793
Vagrant.require_version ">= 1.8.3"

def true?(obj)
  obj = obj.to_s.downcase
  obj != "false" && obj != "off" && obj != "0"
end

Vagrant.configure("2") do |config|
  vagrant_box = ENV.fetch("VAGRANT_BOX", "bento/ubuntu-18.04")
  bind_node_modules = true?(ENV.fetch("BIND_NODE_MODULES", true))

  if Vagrant.has_plugin?("vagrant-cachier")
    config.cache.scope = :box
    config.cache.enable :apt
    config.cache.enable :npm
  end

  config.vm.box = vagrant_box
  config.vm.hostname = "girder"
  config.vm.provider "virtualbox" do |virtualbox|
    virtualbox.memory = 2048
  end

  config.vm.network "forwarded_port", guest: 8080, host: 9080
  config.vm.post_up_message = <<-eos
Girder has been installed, to run it perform the following steps:
vagrant ssh
girder serve

Visit http://localhost:9080.
eos

  config.vm.synced_folder ".", "/vagrant", disabled: true
  config.vm.synced_folder ".", "/home/vagrant/girder"

  config.vm.provision "ansible_local" do |ansible|
    ansible.compatibility_mode = '2.0'
    ansible.config_file = 'devops/vagrant/ansible.cfg'
    ansible.galaxy_role_file = 'devops/vagrant/vagrant-requirements.yml'
    ansible.playbook = "devops/vagrant/vagrant-playbook.yml"
    ansible.provisioning_path = "/home/vagrant/girder"
    ansible.extra_vars = {
      bind_node_modules: bind_node_modules
    }
  end
end
