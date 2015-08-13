Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/trusty64"
  config.vm.network "forwarded_port", guest: 80, host: 9080
  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "devops/ansible/playbook.yml"
    ansible.verbose = "v"
  end
end
