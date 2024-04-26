# Appraise Evaluation System

    python3 manage.py StartNewCampaign Examples/PairwiseDocNewUI/manifest.json \
        --batches-json Examples/PairwiseDocNewUI/batches.json \
        --csv-output Examples/PairwiseDocNewUI/output.csv

    # See Examples/PairwiseDocNewUI/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python3 manage.py ExportSystemScoresToCSV example17docnewui

# Score Descriptions

In system, we use a specific set of scores to rate the translations. Here is when each score is used:

- **40/50/60**: These scores are used when the source text is not visible. 
    - When using thumbs up/down to independently upvote/downvote translations of specific fragments:
        - **Thumb-up**: The score is 60.
        - **Thumb-down**: The score is 40.
        - **No selection**: The score is 50.
    - When using click and highlight each paragraph to independently mark your preferred translation:
        - **Highlight**: The score is 60.
        - **De-highlight**: The score is 50.

- **41/51/61**: These scores are used when the source text is visible. 
    - When using thumbs up/down to independently upvote/downvote translations of specific fragments:
        - **Thumb-up**: The score is 61.
        - **Thumb-down**: The score is 41.
        - **No selection**: The score is 51.
    - When using click and highlight each paragraph to independently mark your preferred translation:
        - **Highlight**: The score is 61.
        - **De-highlight**: The score is 51. 
