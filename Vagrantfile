Vagrant.configure("2") do |config|
  config.vm.box_url = "https://cloud-images.ubuntu.com/vagrant/trusty/current/trusty-server-cloudimg-amd64-vagrant-disk1.box"
  config.vm.box = "trusty_64"
  config.vm.network "forwarded_port", guest: 80, host: 9080
  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "devops/ansible/playbook.yml"
    ansible.verbose = "vvvv"
  end
end
