# charles
Charles River Watershed Association

# Deploy the Web App
Deployed on AWS Elastic Beanstalk.

Lives in `web/app.py`

## Requirements.txt
The packages available to the app on AWS Elastic Beanstalk is controlled by requirements.txt

## Install and configure `awsebcli`
`pip install awsebcli`

go to project directory and `eb init` (to connect this directory to AWS EB)

then `eb create` to create an environment (e.g. Dev vs Prod)

update WSGI path to point to the app:
`eb console` to jump on to the AWS console > Configuration > update WSGI path to:
`app.py` 


## Deploy
Navigate to the repository directory and run `eb deploy --label <version_name>`.
This will deploy the files that are currently in the directory, minus those listed in `.ebignore`.   
The deployment will not related to a specific git commit (for explanation see the `.ebignore` section below).


#### .ebignore
Uses the .ebignore file to not exclude most of the repository when deploying.
awsebcli normally deploys `git HEAD`, but when using .ebignore, it does not and instead deploys whatever files are on the filesystem. 

#### requirements.txt
Elastic Beanstalk needs a `requirements.txt` in order to install the right libraries.

