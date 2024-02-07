# Appraise

## Basic setup

1. Basic setup 

```
git clone https://github.com/AppraiseDev/Appraise.git
cd Appraise
pip install --user virtualenv
virtualenv venv -p python3
source ./venv/bin/activate
pip install -r requirements.txt
```

2. Create database, the first super user, and collect static files:

Follow instructions on your screen; do not leave the password empty.
```
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py collectstatic --no-post-process
```

3. Run the app on a local server:

```
python3 manage.py runserver
```

Open the browser at http://127.0.0.1:8000/.
The admin panel is available at http://127.0.0.1:8000/admin

4. Start a campaign:

```
# See Examples/DirectMQM/README.md
python3 manage.py StartNewCampaign Examples/DirectMQM/manifest.json \
    --batches-json Examples/DirectMQM/batches.json \
    --csv-output Examples/DirectMQM/output.csv
python3 manage.py CreateInviteTokens test_group 20 --create-group test_group
```

10. Clean up everything

```
rm -rf static appraise.log db.sqlite3 Batches
```

## Creating a new campaign

To create a campaign, a manifest file and data batches in JSON formats are needed.
See examples in [`Examples/`](Examples/) for simple end-to-end examples for
each annotation tasks that are currently available in Appraise.

Alternatively, a Django command can be created instead of the manifest file,
see `Campaign/management/commands/InitCampaign*.py` for examples.


### manifest.json

Specification

- `CAMPAIGN_URL`: URL prefix for the SSO logins starting with the domain name
  (usually `http://127.0.0.1:8000` if run locally) and ending with
  `/dashboard/sso/`
- `CAMPAIGN_NAME`: a readable campaign name, must consist only of `[a-zA-Z0-9]`
- `CAMPAIGN_KEY`: a key used to generate password for user accounts, any UTF-8
  string
- `CAMPAIGN_NO`: a unique integer number used in the user account names
- `REDUNDANCY`: how many times each task needs to be annotated
- `TASKS_TO_ANNOTATORS`: list of task definition 5-tuples:
    - _source language ISO code_, tree-letter version
    - _target language ISO code_, tree-letter version
    - _sampling strategy_, only "uniform" is supported
    - _number of annotators_, how many user accounts will be created for this task
    - _number of tasks_, must be a multiple of the number of annotators
- `TASK_TYPE`: a pre-defined task type name, see `Campaign/utils.py` for a
  complete list of supported task types, the default is _Direct_
