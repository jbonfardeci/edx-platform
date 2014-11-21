Install a EdX Devstack Vagrant Box on VMware Fusion or Create Your Own Ubuntu 12.0.4 LTS Server
------------------------------------------------------------------------------------------------
Vagrant is an awesome tool but there are many, many problems with VirtualBox. After fighting SSH timeout issues for several days I opened the Vagrantfile to see if I could adjust settings for my environment: Mac OS 10.9 with VirtualBox 4.3.12 and Vagrant 1.6.5. I then saw a Ruby looping statement for detecing the Vagrant VMware Fusion plugin. The EdX team built a VMware box. Yes! VMware is rock solid, so I gladly paid $79 for the plugin here - http://www.vagrantup.com/vmware. 

After purchasing the VMware plugin, you'll be emailed the download link for the license, `license.lic`. Download it to a new directory -- let's call it "VagrantLicense." Install it by running: 
```
mkdir VagrantLicense
cd VagrantLicense
$ vagrant plugin install vagrant-vmware-fusion
$ vagrant plugin license vagrant-vmware-fusion license.lic
```

Now create a directory for your EdX devstack project wherever you like and download the EdX Vagrantfile:
```
mkdir devstack
cd devstack
curl -L https://raw.githubusercontent.com/edx/configuration/master/vagrant/release/devstack/Vagrantfile > Vagrantfile
```

We need to change the `unless Vagrant.has_plugin...` statement beginning on the second line of the Vagrant file, replacing `vagrant-vbguest` with `vagrant-vmware-fusion`. Open "Vagrantfile" in your favorite text editor and change the statement to match:

```
1 Vagrant.require_version ">= 1.5.3"
2 unless Vagrant.has_plugin?("vagrant-vmware-fusion")
  raise "Please install the vagrant-vmware-fusion plugin by running `vagrant plugin install vagrant-vmware-fusion`"
end
```

Then change the private network IP to match your host computer's IP schema on this line. Replace `192.169.10.33` to match yours. On Mac, run `ifconfig` to get your IP, on Windows, `ipconfig`. For example, if your IP is `192.168.1.10` then change the IP in the Vagrantfile to `192.168.1.20` - as long as this isn't another IP on your network.
```
config.vm.network :private_network, ip: "192.168.10.33" # change this this match your IP schema
```

Save and run this back in terminal:

```
vagrant plugin install vagrant-vmware-fusion
vagrant up
```

You'll be asked to enter your password shortly. Enter the password for your host computer, not the virtual machine. This is to allow Vagrant to create the shared folders from the VM in your devstack directory - the EdX files you'll be editing.
```
Password: 
```

If you get the following error while Vagrant is setting up your server:
```
* The following required packages can not be built:

* freetype
```

...run this
```
vagrant ssh
sudo apt-get install libfreetype6-dev
exit
vagrant reload --provision
```

Success!

Now run 
```
vagrant ssh
```

Then
```
sudo su edxapp
paver devstack lms
```

Switch to your local browser and enter the URL 127.0.0.0:8000

If you get this welcome message in the site:
```
OperationFailure at /
command SON([('authenticate', 1), ('user', u'edxapp'), ('nonce', u'a513b1220c786416'), ('key', u'1521314a7ba261acafe2bbe9d7169d66')]) failed: auth fails
```

See this thread: https://groups.google.com/forum/#!topic/edx-code/yt9n8p-YmSo

Press Control-C to stop the Django web server, and exit ssh. ```exit```
Then run:
```
vagrant ssh

SCRIPTFILE=/tmp/fix-mongo.sh
cat > "$SCRIPTFILE" << eof
#!/bin/bash

apt-get purge mongodb-10gen
cd /edx/app/edx_ansible/edx_ansible/playbooks
/edx/app/edx_ansible/venvs/edx_ansible/bin/ansible-playbook -i localhost, -c local run_role.yml -e 'role=mongo' -e 'mongo_create_users=True'

sleep 5 #to allow mongo process to start, if you need it;
mongo localhost <<EOF
use edxapp;

db.createUser(
{
user: "edxapp",
pwd: "password",
roles: [ "readWrite" ]
}
);

use cs_comments_service;

db.createUser(
{
user: "cs_comments_service",
pwd: "cs_comments_service",
roles: [ "readWrite" ]
}
);
EOF
eof
sudo bash "$SCRIPTFILE"
rm "$SCRIPTFILE"
```
Exit: ```exit``` and ```vagrant ssh``` back in. Start again with ```sudo su edxapp```, and run ```paver devstack lms```

###OR Create your own server from scratch...

Download Ubuntu Server 12.0.4 ISO from: http://releases.ubuntu.com/12.04.4/ubuntu-12.04.4-server-amd64.iso

Mount ISO with VMWare and follow steps to install.
Tip: Take snapshots of your virtual machine before installing EdX, after a successful install of EdX, after major changes, often. You may need to revert to a previous state after breathing on the EdX platform. Troubleshooting is way to hard if you run into problems; revert to the last working snapshot.

Install server OS updates
```
sudo apt-get update -y
sudo apt-get upgrade -y
sudo reboot <br/>
```

Install:
```
sudo apt-get install -y build-essential software-properties-common python-software-properties curl git-core libxml2-dev libxslt1-dev libfreetype6-dev python-pip python-apt python-dev
```

Upgrade Python Package Index
```
sudo pip install --upgrade pip
```

Upgrade virtualenv for running in virtual environment -- refer to the most excellent book, "Two Scoops of Django -- Best Practices for Django 1.6" by Daniel Greenfield and Audrey Roy 
```
sudo pip install --upgrade virtualenv
```

On the new server, clone the configuration repo:
```
cd /var/tmp
git clone -b release https://github.com/edx/configuration
sudo reboot
```

To allow password based SSH authentication, edit the common role inside of configuration/playbooks/roles/common/defaults/main.yml and set COMMON_SSH_PASSWORD_AUTH to "yes"

Install the ansible requirements

```
cd /var/tmp/configuration
sudo pip install -r requirements.txt
sudo reboot
```

Run the edx_sandbox.yml playbook in the configuration/playbooks directory, most likely to fail:
```
cd /var/tmp/configuration/playbooks
sudo ansible-playbook -c local ./edx_sandbox.yml -i "localhost,"
```

It will probably fail so you'll need to rerun ansible playbooks:
```
sudo reboot
```

Delete /var/tmp/configuration and reinstall. Replace &lt;account_name&gt; with your account name.
```
cd /var/tmp
rm -rf configuration
git clone -b release https://github.com/edx/configuration
cd configuration
sudo pip install -r requirements.txt
cd playbooks
sudo ansible-playbook -c local ./edx_sandbox.yml -i "localhost," --limit @/home/<account_name>/edx_sandbox.retry
```
