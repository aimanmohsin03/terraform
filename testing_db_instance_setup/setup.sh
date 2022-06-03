#Mount data directory
sudo mkdir /mnt/data
sudo mkfs -t ext4 /dev/nvme1n1
sudo mount -t ext4 /dev/nvme1n1 /mnt/data

#Install ubuntu packages
sudo apt update
sudo apt -y upgrade
sudo apt-get -y install python3-pip python-dev default-jre ant
sudo rm /usr/bin/python
sudo ln -s /usr/bin/python3.8 /usr/bin/python

#Install postgres:
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
echo "deb http://apt.postgresql.org/pub/repos/apt/ `lsb_release -cs`-pgdg main" |sudo tee  /etc/apt/sources.list.d/pgdg.list
sudo apt update
sudo apt -y install postgresql-14 postgresql-client-14

# Setup OLTPbench
cd
git clone https://github.com/oltpbenchmark/oltpbench.git
cd oltpbench
ant bootstrap
ant resolve
ant build
cd ..

mv -v testing_db_instance_setup/oltp_benchmark_config_files/* oltpbench/config/
mv -v testing_db_instance_setup/loader.py oltpbench/
mv -v testing_db_instance_setup/runner.py oltpbench/

# Copy the data from the old directory to the mounted one.
sudo -i -u postgres psql -c "CREATE USER test WITH LOGIN SUPERUSER PASSWORD 'password';"
sudo rsync -av /var/lib/postgresql /mnt/data
sudo bash -c 'echo "data_directory = '\''/mnt/data/postgresql/14/main'\''" >> /etc/postgresql/14/main/conf.d/initial.conf'
sudo bash -c 'echo "max_connections = 250" >> /etc/postgresql/14/main/conf.d/initial.conf'
sudo service postgresql restart

#Setup postgres:
sudo chmod -R ugo+rw /mnt/data/
sudo chmod -R 0750 /mnt/data/postgresql/