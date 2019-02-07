# ROLLING DEPLOY

A sample script to perform rolling deployments on aws.

### SETUP ###

* cp .env.example .env
* edit .env to include the ARN of your load balancer target group
* this script assumes you have aws credentials set up in your /home/user/.aws directory

### EXECUTING ###
* docker-compose up &
* docker-compose exec app ./deploy old_ami_id new_ami_id
* docker-compose down


### RUNNING TESTS ###
* docker-compose up &
* docker-compose exec app python -m unittest discover tests
* docker-compose down
