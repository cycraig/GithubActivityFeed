import os
import sys
import logging
import dateutil.parser as dt
from datetime import datetime, timezone
from flask import Flask, flash, render_template, request, g, session, redirect, url_for, render_template_string, jsonify

from config import Config
from service.github import GitHubAPI, GitHubAPIError
from service.github_event_template import github_event_templates, github_event_icons
from models.db import db
from models.user import User
from models.event import Event

# Logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] %(name)s %(levelname)s:%(message)s')

# Flask
app = Flask(__name__)
app.config.from_object(Config)

# GitHub API
if not app.config.get('GITHUB_CLIENT_ID', None) or not app.config.get('GITHUB_CLIENT_SECRET', None):
    logger.error(
        'Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env or environment variables')
    sys.exit(-1)
github = GitHubAPI(app.config['GITHUB_CLIENT_ID'],
                   app.config['GITHUB_CLIENT_SECRET'])

# SQLAlchemy (needs to be run on import for pythonanywher# initialise database and start app
db.app = app
db.init_app(app)
# create database tables for models
with app.app_context():
    db.create_all()


@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])


@app.after_request
def after_request(response):
    # db_session.remove()
    return response


@app.route("/", methods=["GET"])
def index():
    #return render_template("index.html")
    return redirect(url_for('events'))


@app.route('/oauth-callback')
def oauth_callback():
    # Exchange code for access_token
    code = request.args.get('code')
    access_token = github.oauth_callback(code)
    next_url = request.args.get('next') or url_for('index')
    if access_token is None:
        return redirect(next_url)

    # Retrieve an existing user by their access token
    github_user = github.get('/user', access_token).json()
    user = User.query.filter_by(github_access_token=access_token).first()
    if user is None:
        # Search by github_id in case the access_token changed
        id = github_user['id']
        user = User.query.filter_by(github_id=id).first()
        if user is None:
            # Otherwise create a new user
            user = User(access_token)
            user.github_id = github_user['id']
            db.session.add(user)

    # update user information
    user.github_email = github_user['email']
    user.github_login = github_user['login']
    user.github_access_token = access_token

    # persist
    db.session.commit()

    # store user in session
    g.user = user
    session['user_id'] = user.github_id
    return redirect(next_url)


@app.route('/login')
def login():
    session.permanent = True
    if g.user is None:
        return redirect(github.oauth_url())
    else:
        return redirect(url_for('events'))


@app.route('/logout')
def logout():
    # remove the user_id from the session
    session.pop('user_id', None)
    flash("Logged out!")
    return redirect(url_for('index'))


def get_snoozed_events(user: User):
    '''
    Returns the snoozed event objects for the user.
    '''
    if not user:
        return []
    snoozed_events = Event.query.filter_by(github_id=user.github_id).all()
    return snoozed_events


def get_events(target_user: str, user: User):
    '''
    Returns a list of JSON-encoded events for the user with snoozed events filtered out.

    TODO: slow...
    '''
    token = None
    if user:
        token = user.github_access_token
    events = github.get_user_received_events(target_user, token)

    # filter out snoozed events from the list
    snoozed_events = get_snoozed_events(user)
    snoozed_events_ids = set()
    for se in snoozed_events:
        snoozed_events_ids.add(se.event_id)
    return filter(lambda e: e['id'] not in snoozed_events_ids, events)


@app.route("/snooze", methods=["POST"])
def snooze():
    '''Snoozes an event: removes it from the event list and adds it to the user's reminders.
    '''
    if not (request.content_type.startswith('application/json')):
        raise HTTPException("Content type must be application/json")
    if not g.user:
        raise HTTPException("Not logged in", 401)
    data = request.json
    try:
        logger.debug("Snoozing event for user %s: %s" %
                     (g.user.github_login, str(data)))
        if not 'id' in data:
            raise HTTPException("Malformed event", 400)
        event = Event(data['id'], data, g.user.github_id)
        db.session.add(event)
        db.session.commit()
    except Exception as e:
        logger.exception("failed to snooze event", e)
        raise HTTPException("failed to snooze event", 500, request.json)
    resp = jsonify(success=True)
    return resp

@app.route("/unsnooze", methods=["POST"])
def unsnooze():
    '''Unsnoozes an event: removes it from the list of reminders and shows it in the event list.
    '''
    if not (request.content_type.startswith('application/json')):
        raise HTTPException("Content type must be application/json")
    if not g.user:
        raise HTTPException("Not logged in", 401)
    data = request.json
    try:
        logger.debug("Unsnoozing event for user %s: %s" %
                     (g.user.github_login, str(data)))
        if not 'id' in data:
            raise HTTPException("Malformed event", 400)
        event = Event.query.get(data['id'])
        if not event:
            raise HTTPException("No such event found", 404)
        db.session.delete(event)
        db.session.commit()
    except Exception as e:
        logger.exception("failed to unsnooze event", e)
        raise HTTPException("failed to unsnooze event", 500, request.json)
    resp = jsonify(success=True)
    return resp


@app.route("/events", methods=["GET"])
def events():
    # TODO: an OAuth token still doesn't retrieve private events?
    token = None

    # Extract user to retrieve events of from args.
    # If absent default to the logged-in user, otherwise cycraig
    target_user = request.args.get("user", None)
    if g.user:
        token = g.user.github_access_token
        if target_user is None:
            target_user = g.user.github_login
    if target_user is None:
        target_user = "cycraig"

    try:
        user_details = github.get_user(target_user, token)
        events = list(get_events(target_user, g.user))
        return render_template("events.html", events=events, target_user=target_user, user_details=user_details, event_templates=github_event_templates, event_icons=github_event_icons, snoozed=False, logged_in=g.user!=None)
    except Exception as e:
        logger.exception(e)
        flash(str(e))
        return render_template("events.html", events=None, target_user=target_user, user_details=None, snoozed=False, logged_in=g.user!=None)


@app.route("/reminders", methods=["GET"])
def reminders():
    '''Displays a list of snoozed events for the logged-in user.
    '''
    if not g.user:
        flash("Login to access reminders")
        return redirect(url_for('index'))

    try:
        user_details = github.get_user(
            g.user.github_login, g.user.github_access_token)
        events_objects = get_snoozed_events(g.user)
        snoozed_events = [e.event_json for e in events_objects]
        return render_template("events.html", events=snoozed_events, target_user=g.user.github_login, user_details=user_details, event_templates=github_event_templates, event_icons=github_event_icons, snoozed=True, logged_in=g.user!=None)
    except Exception as e:
        logger.exception(e)
        flash(str(e))
        return render_template("events.html", events=None, target_user=g.user.github_login, user_details=None, snoozed=True, logged_in=g.user!=None)


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


class HTTPException(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.errorhandler(HTTPException)
def handle_http_exception(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    flash(str(response))
    return response


def run():
    app.run(debug=True)


if __name__ == "__main__":
    run()
