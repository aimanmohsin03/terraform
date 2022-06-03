# DBTune SW-Client
The DBTune SW-Client, client, is a python script enabling tuning of databases via www.hypermapit.com.

## Create a tuning job
To create a tuning job, login to the web portal and create "New DB Tune job".

Depending on the type of dbms and environment it's running on you have to supply different information.
### PostgreSQL 12 on Ubuntu
#### name of the database
The name of the database to tune.
#### username
The script will be acting as this user when interacting with the database.

## Install the script
```
git clone https://github.com/toburn/DBTuneSwClient.git
```

## Run the tuning job
Via the web console you will get your personal API-KEY and JOB-ID to use when running the tuning job like so:
```
python client.py <API-KEY> <JOB-ID>
```

The script will iteratively...
* Fetch a new db configuration from the backend optimizer
* Apply the configuration to the database
* Restart the database
* Measure the performance

### Problems?
#### Not having the privileges?
You might have to sudo...
```
sudo python client.py <API-KEY> <JOB-ID>
```
#### Script stops when exiting the ssh session used to access the system?
You could nohup...
```
nohup sudo python client.py <API-KEY> <JOB-ID>
```

## What does the job do to my system?
### Ubuntu
#### Updating the config
The script creates a subdirectory conf.d and writes a file postgresql.conf in the directory:
```
/etc/postgresql/12/main/conf.d/postgresql.conf
```
Additionally, the following line is appended in the main configuration file
```
include_dir 'conf.d'
```
Configuration values in the temporary configuration file takes precedence in accordance with 18.1.5 here:
https://www.postgresql.org/docs/9.5/config-setting.html
#### Restarting the DB
Restart of the DB is performed by a system call 
```
sudo service postgresql restart
```
This will cause a small downtime to the db.

#### Reading the performance
The performance is measured by reading the number of commits via:
```
sudo -i -u <username> psql -c \"SELECT xact_commit FROM pg_stat_database WHERE datname='<datname>';
```
...and calculate the number of commits during the observation time.

### Undo?
The configuration changes can be undone by removing the added include line in the configuration file
or by removing the added temporary configuration file, and restart the database.

## Adding support for a new DBMS
For each combination of DBMS and system it's running on requiring specific interaction there needs to be an
adapter implementation under ./adapters subclassing Adapter and override the following functions: 
```
    def update_config(self, tuningRequest):
        print("Must bo overridden by subclass")
    
    
    def restart(self):
        print("Must bo overridden by subclass")
        
    
    def get_output(self):
        print("Must bo overridden by subclass")
```

 Additionally, the dbms_adapter_factory.py must be updated to detect and create the appropriate Adapter subclass given
 the adapter_data provided by the backend.


## Supported databases
* PostgreSQL on Ubuntu
