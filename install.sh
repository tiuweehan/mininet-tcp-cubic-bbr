apt install -y python-pip mininet ethtool netcat moreutils
pip install -r requirements.txt

# this fixes mininet bug with ovs-controller
apt install -y openvswitch-testcontroller
cp /usr/bin/ovs-testcontroller /usr/bin/ovs-controller
