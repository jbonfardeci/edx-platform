Install Devstack on fresh Ubuntu 12.04 LTS Server
-------------------------------------------------
...because no one should be subjected to the problems with Vagrant and Virtual Box. Use VMWare if you can; Virtual Box is too flaky.

1. Download Ubuntu Server 12.0.4 ISO from: http://releases.ubuntu.com/12.04.4/ubuntu-12.04.4-server-amd64.iso

2. Mount ISO with VMWare and follow steps to install.

Tip: Take snapshots of your virtual machine before installing EdX, after a successful install of EdX, after major changes, often. You may need to revert to a previous state after breathing on the EdX platform. Troubleshooting is way to hard if you run into problems; revert to the last working snapshot.

3. Install server OS updates

sudo apt-get update -y
sudo apt-get upgrade -y
sudo reboot

4. Install:
sudo apt-get install -y build-essential software-properties-common python-software-properties curl git-core libxml2-dev libxslt1-dev libfreetype6-dev python-pip python-apt python-dev

5. upgrade Python Package Index
sudo pip install --upgrade pip

6. upgrade virtualenv for running in virtual environment
sudo pip install --upgrade virtualenv

7. On the new server, clone the configuration repo:
cd /var/tmp
git clone -b release https://github.com/edx/configuration

7.1 reboot
sudo reboot

7.2 To allow password based SSH authentication, edit the common role inside of configuration/playbooks/roles/common/defaults/main.yml and set COMMON_SSH_PASSWORD_AUTH to "yes"

8. Install the ansible requirements

cd /var/tmp/configuration
sudo pip install -r requirements.txt

8.1 sudo reboot

9. Run the edx_sandbox.yml playbook in the configuration/playbooks directory, most likely to fail:
cd /var/tmp/configuration/playbooks
sudo ansible-playbook -c local ./edx_sandbox.yml -i "localhost,"

10. It will probably fail on installing NTLK; rerun ansible playbooks:

sudo reboot

10.1 delete /var/tmp/configuration

rm -rf /var/tmp/configuration

10.2 and then run

cd /var/tmp
git clone -b release https://github.com/edx/configuration

cd /var/tmp/configuration
sudo pip install -r requirements.txt

10.3 Then run

cd /var/tmp/configuration/playbooks
sudo ansible-playbook -c local ./edx_sandbox.yml -i "localhost," --limit @/home/<account_name>/edx_sandbox.retry
