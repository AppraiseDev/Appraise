# Setup

1. Basic setup:

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
# See Examples/MQM+ESA/README.md
python3 manage.py StartNewCampaign Examples/MQM+ESA/manifest.json \
    --batches-json Examples/MQM+ESA/batches.json \
    --csv-output Examples/MQM+ESA/output.csv
python3 manage.py CreateInviteTokens test_group 20 --create-group test_group
```

Add `--task-confirmation-tokens` if you want to generate annotator confirmation tokens.
See [quality control](#Quality control) for more details.

5. Optionally clean up everything

```
rm -rf static appraise.log db.sqlite3 Batches
```

## Creating a new campaign

The [`Examples/`](Examples/) directory contains a few examples of existing annotation campaigns.
Each campaign needs a _manifest_ and _batches_, both JSON files.

The manifest looks like this:
```
{
    "CAMPAIGN_URL": "http://127.0.0.1:8000/dashboard/sso/",
    "CAMPAIGN_NAME": "example15esa",
    "CAMPAIGN_KEY": "example15esa",
    "CAMPAIGN_NO": 15,
    "REDUNDANCY": 2,

    "TASKS_TO_ANNOTATORS": [
        ["eng", "deu", "uniform",  2, 1]
    ],

    "TASK_TYPE": "Document",
    "TASK_OPTIONS": "ESA;StaticContext"
}
```
- The campaign URL points to where it's being hosted (most usually localhost, see `settings.py`).
- The campaign name should be readable but must consist only of `[a-zA-Z0-9]`
- The campaign key is used for seeding passwords, can be any string.
- The campaign number needs to be unique.
- The supported task types are in `Campaign/utils.py`. Some types can be modified with task options.
- In the associated data we had only one En-De task. The combination of redundancy of 2 and the first 2 in the task distribution simply creates two accounts with the same single task (redundant). If there were e.g. 5 tasks and we wanted no redundancy, the line would be `["eng", "deu", "uniform",  5, 5]`. 
Alternatively to manual manifests, a Django command can be created instead of the manifest file, see `Campaign/management/commands/InitCampaigh*.py`.

The batches file is a list of tasks with items and task descriptions. There are usually at least 100 segments in a task. An example for ESA/MQM:
```
[
    {
        "items": [
            {
                "mqm": [{ "start_i": 0, "end_i": 5, "severity": "minor" }],
                "documentID": "farcaller.110349815253008992#refA#bad4",
                "sourceID": "wmt23",
                "targetID": "wmt23.refA",
                "sourceText": "A bunch of shiny new goodness in #dart",
                "targetText": "Einer Haufen funkelnder glänzender neuer Dinge #dart",
                "itemType": "TGT",
                "_item": "refA | 209 | farcaller.110349815253008992",
                "itemID": 10,
                "isCompleteDocument": false
            },
            # ... more items
        ],
        "task": {
            "batchNo": 1,
            "randomSeed": 123456,
            "requiredAnnotations": 1,
            "sourceLanguage": "eng",
            "targetLanguage": "deu"
        }
    }
    # ... more tasks
]
```

For item:
- `mqm`: the pre-highlighted error spans (used only for ESA/MQM)
- `documentID`: document name from WMT (doesn't have to include system name or anything else)
- `sourceID`: name of source file/testset name, should include also the language
- `targetID`: name of target file, should include system name
- `itemType`: TGT (standard), or BAD (quality control)
- `_item`: should be order of segment in the batch but is not exported so can contain any payload
- `itemID`: ID from the testset pile (line number)
- `isCompleteDocument`: remnant from DA+SQM, false for ESA/MQM 

In addition, ESA/MQM includes introductory tutorial which has a slightly different item structure.

For task:
- `batchNo`: task number
- `randomSeed`: number used in batch generation
- `requiredAnnotations`: how many annotations does a task need, in most cases use 1
- `source/targetLanguage`: source and target language

## Quality control

With `--task-confirmation-tokens`, the annotators will be shown a random key/token if they fail the quality control and a correct one (matching the one in the CSV output with credentials) if they succeed.
The quality control checks if the perturbed samples (`itemType=BAD`) have statistically lower scores than the original ones (`itemType=TGT`).
Even without the switch, the campaign status page will show a p-value (last column for staff account) that corresponds to the outcome of this test.
If it's close to 1, then the annotator is annotating randomly and is of poor quality.
For values close to 0, the annotations are good.
The threshold to generate the valid token for annotators is currently p<=10%.
