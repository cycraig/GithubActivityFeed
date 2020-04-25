import sys
import logging
import dateutil.parser as dt
from datetime import datetime, timezone
from flask import Flask

from config import Config
from service.github import github
from models.db import db
from views import eventbp

# Logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] %(name)s %(levelname)s:%(message)s')

# Flask
app = Flask(__name__)
app.config.from_object(Config)
app.register_blueprint(eventbp)

# GitHub API
if not app.config.get('GITHUB_CLIENT_ID') or not app.config.get('GITHUB_CLIENT_SECRET'):
    logger.error(
        'Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env or environment variables')
    sys.exit(-1)
github.client_id = app.config['GITHUB_CLIENT_ID']
github.client_secret = app.config['GITHUB_CLIENT_SECRET']

# SQLAlchemy (needs to be run on import for pythonanywhere)
db.app = app
db.init_app(app)
# create database tables for models
with app.app_context():
    db.create_all()


@app.template_filter()
def datetimesince(datestr):
    """Returns the difference between the given datetime string and now as text.

    E.g. 13 minutes ago
    """
    try:
        if isinstance(datestr, str):
            datestr = dt.parse(datestr)
        now = datetime.now(timezone.utc)
        diff = now - datestr
        d = diff.days // 365
        if d > 0:
            return "%d %s ago" % (d, "year" if d == 1 else "years")
        d = diff.days // 30
        if d > 0:
            return "%d %s ago" % (d, "month" if d == 1 else "months")
        d = diff.days // 7
        if d > 0:
            return "%d %s ago" % (d, "week" if d == 1 else "weeks")
        d = diff.days
        if d > 0:
            return "%d %s ago" % (d, "day" if d == 1 else "days")
        d = diff.seconds // 3600
        if d > 0:
            return "%d %s ago" % (d, "hour" if d == 1 else "hours")
        d = diff.seconds // 60
        if d > 0:
            return "%d %s ago" % (d, "minute" if d == 1 else "minutes")
        d = diff.seconds
        if d > 0:
            return "%d %s ago" % (d, "second" if d == 1 else "seconds")
    except Exception as e:
        logger.exception(e)
    return "just now"


def run():
    app.run(debug=app.config['DEBUG'])


if __name__ == "__main__":
    run()
