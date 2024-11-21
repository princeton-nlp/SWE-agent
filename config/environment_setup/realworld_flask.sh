# export CONDUIT_SECRET='something-really-secret'

export FLASK_APP="autoapp.py"
export FLASK_DEBUG=1

pip install -r "requirements/dev.txt"

flask db init
flask db migrate
flask db upgrade