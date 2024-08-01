# Direct MQM/ESA

## Setup

This is an example of 3 campaigns with MQM/ESA/ESAAI (three different batches).

```
# clean up previous iteration
rm -rf static appraise.log db.sqlite3 Batches;

# setup
python3 manage.py migrate;
DJANGO_SUPERUSER_USERNAME=test DJANGO_SUPERUSER_PASSWORD=test python3 manage.py createsuperuser --noinput --email "test@test.test";
python3 manage.py collectstatic --no-post-process;

python3 manage.py StartNewCampaign Examples/MQM+ESA/manifest_esa.json \
    --batches-json Examples/MQM+ESA/batches_esa.json \
    --csv-output Examples/MQM+ESA/output_esa.csv;

python3 manage.py StartNewCampaign Examples/MQM+ESA/manifest_mqm.json \
   --batches-json Examples/MQM+ESA/batches_mqm.json \
   --csv-output Examples/MQM+ESA/output_mqm.csv;
   
python3 manage.py StartNewCampaign Examples/MQM+ESA/manifest_esa_gemba.json \
    --batches-json Examples/MQM+ESA/batches_esa_gemba.json \
    --csv-output Examples/MQM+ESA/output_esa_gemba.csv;

python3 manage.py runserver;

# See Examples/MQM+ESA/outputs.csv for a SSO login for the annotator account
# Collect some annotations, then export annotation scores...

python3 manage.py ExportSystemScoresToCSV example15esa
```

## Audio/Video

The source field accepts HTML, so it's very easy to add multimodal support by including HTML snippets in the `sourceText` field like so:

HTML for video:
```
<video
    src="https://samplelib.com/lib/preview/mp4/sample-5s.mp4"
    controls
    disablepictureinpicture
    preload="auto"
    controlslist="nodownload"
></video>
```

HTML for audio:
```
<audio
    src='https://samplelib.com/lib/preview/mp3/sample-3s.mp3'
    controls controlslist='nodownload'
></audio>
```