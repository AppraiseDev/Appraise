# Appraise

## Basic setup

1. Clone the repository.
2. Install Python 3.5+.
3. Install virtual environments for Python:

        pip3 install --user virtualenv

4. Create environment for the project, activate it, and install Python requirements:

        virtualenv ~/.virtualenv/django2 -p python3
        source ~/.virtualenv/django2/bin/activate
        pip3 install -r requirements.txt

5. Create database and the first super user:

        python manage.py migrate
        python manage.py createsuperuser

    Follow instructions on your screen; do not leave the password empty.

6. Run the app on a local server:

        python manage.py runserver

    Open the browser at http://127.0.0.1:8000/.
    The admin panel is available at http://127.0.0.1:8000/admin

