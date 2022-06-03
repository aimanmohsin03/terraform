# Setting up demo database instance
### Step 1
**Create an AWS instance**<br>
you can use any aws instance to start the demo workload, e.g., t2.micro, m5.large, etc.

### Step 2
**Clone the platform repo on your local machine**<br>
`git clone https://{YOUR USERNAME}:{YOUR PERSONAL ACCESS TOKEN}@github.com/dbtuneai/platform.git`<br>
[How to create your github personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)


### Step 3
**Copy the testing_db_instance_setup folder from your local machine to the created aws instance**<br>
`rsync -zarv ./* -e "ssh -i {YOUR_AWS_KEY.pem}" ubuntu@{YOUR_AWS_IP}:/home/ubuntu/testing_db_instance_setup/`

### Step 4
**Run the setup.sh script from testing_db_instance_setup folder on aws instance**<br>
`source setup.sh`

### Step 5
**Use terminal multiplexer for loading the data and running the workload**<br>
`screen`

### Step 6
**Load synthetic data to the database by running the following command from oltpbench folder which will be created once you have run the setup.sh script**<br>
`python loader.py --benchmark tpcc`

### Step 7
**Run synthetic workload by the following command from oltpbench folder**<br>
`python runner.py --benchmark tpcc`

### Step 8
**Detach the terminal after starting the workload**<br>
`press Ctrl-a + Ctrl-d`


# Start the tuning session
### Step 1
**Copy the client folder from your local machine to the created aws instance**<br>
`rsync -zarv --include="*/" --include="*.py" --exclude="*" ../client/* -e "ssh -i {YOUR_AWS_KEY.pem}" ubuntu@{YOUR_AWS_IP}:/home/ubuntu/swclient/`

### Step 2
**Use terminal multiplexer for running the optimization**<br>
`screen`

### Step 3
**Switch to root before running the optimization**<br><br>
`sudo su`

### Step 4
**From swclient folder on your aws instance run**<br>
`python __main__.py apikey jobid`

### Step 5
**Detach the terminal after starting the optimization**<br>
`press Ctrl-a + Ctrl-d`

**jobid:**   You will get this once you create a new tuning session <br>
**apikey:** `For getting the apikey, download the swclient from the dbtune website (Step 1), and access the config.py file in the downloaded client.<br>

## Helpful terminal multiplexer commands
`screen -ls (to list all the screens)`<br>
`screen -r {id} (to attach the screen)`<br>

## You can follow these steps to run platform yourself: 
[Watch the video](https://www.dropbox.com/s/42j2idwk59vp4j5/video_about_setting_up_the_dbtune_open_topics_repo.mp4)
