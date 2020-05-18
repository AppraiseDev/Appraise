# Appraise


## Coding conventions

- Python code formatting with [the Black code formatter](https://github.com/psf/black).
- Desired Pylint score > 9.0.
- Static type checking with [Mypy](http://mypy-lang.org/).
- New code developed with [TDD](https://www.oreilly.com/library/view/test-driven-development-with/9781449365141/).


## Testing

    python manage.py test


## Examples

### Creating a simple campaign with DA tasks

1. From the admin panel, create a campaign with only a name, e.g. 'campaign1'.
2. Initialize the campaign:

        python manage.py init_campaign example/manifest.json

3. From the admin panel, create batches uploading `example/batch?.json` files and add them to the campaign 'campaign1'.
4. Validate, process, and update the campaign:

        python manage.py validatecampaigndata campaign1
        python manage.py ProcessCampaignData campaign1 Direct
        python manage.py UpdateEvalDataModels
        python manage.py init_campaign example/manifest.json --csv-output example/output.csv

5. Annotators' usernames and passwords were exported into the CSV file.

