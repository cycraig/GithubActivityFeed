import logging
from flask import Blueprint, flash, render_template, request, g, session, redirect, url_for, jsonify
from flask_paginate import Pagination

from service.github import github
from service.github_event_template import github_event_templates, github_event_icons
from models.db import db
from models.user import User
from models.event import Event

# Logging
logger = logging.getLogger(__name__)

eventbp = Blueprint('eventbp', __name__)


@eventbp.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])


@eventbp.after_request
def after_request(response):
    # db_session.remove()
    return response


@eventbp.route("/", methods=["GET"])
def index():
    # return render_template("index.html")
    return redirect(url_for('eventbp.events'))


@eventbp.route('/oauth-callback')
def oauth_callback():
    # Exchange code for access_token
    code = request.args.get('code')
    access_token = github.oauth_callback(code)
    next_url = request.args.get('next') or url_for('eventbp.index')
    if access_token is None:
        return redirect(next_url)

    # Retrieve an existing user by their access token
    github_user = github.get('/user', None, access_token).json()
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


@eventbp.route('/login')
def login():
    session.permanent = True
    if g.user is None:
        return redirect(github.oauth_url())
    else:
        return redirect(url_for('eventbp.events'))


@eventbp.route('/logout')
def logout():
    # remove the user_id from the session
    session.pop('user_id', None)
    flash("Logged out!")
    return redirect(url_for('eventbp.index'))


def get_snoozed_events(user: User):
    '''
    Returns the snoozed event objects for the user.
    '''
    if not user:
        return []
    snoozed_events = Event.query.filter_by(github_id=user.github_id).all()
    return snoozed_events


def get_events(target_user: str, user: User, page: int):
    '''
    Returns a list of JSON-encoded events for the user with snoozed events filtered out.

    TODO: slow...
    '''
    token = None
    if user:
        token = user.github_access_token
    events, max_pages = github.get_user_received_events(target_user, page, token)

    # filter out snoozed events from the list
    snoozed_events = get_snoozed_events(user)
    snoozed_events_ids = set()
    for se in snoozed_events:
        snoozed_events_ids.add(se.event_id)
    return list(filter(lambda e: e['id'] not in snoozed_events_ids, events)), max_pages


@eventbp.route("/snooze", methods=["POST"])
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
        if 'id' not in data:
            raise HTTPException("Malformed event", 400)
        event = Event(data['id'], data, g.user.github_id)
        db.session.add(event)
        db.session.commit()
    except Exception as e:
        logger.exception("failed to snooze event", e)
        raise HTTPException("failed to snooze event", 500, request.json)
    resp = jsonify(success=True)
    return resp


@eventbp.route("/unsnooze", methods=["POST"])
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
        if 'id' not in data:
            raise HTTPException("Malformed event", 400)
        event = Event.query.get(data['id'])
        if not event:
            raise HTTPException("No such event found", 404)
        db.session.delete(event)
        db.session.commit()
    except Exception as e:
        logger.exception(e)
        raise HTTPException("failed to unsnooze event", 500, request.json)
    resp = jsonify(success=True)
    return resp


@eventbp.route("/events", methods=["GET"])
def events():
    # TODO: an OAuth token still doesn't retrieve private events?
    token = None

    # Extract user to retrieve events of from args.
    # If absent default to the logged-in user, otherwise cycraig
    target_user = request.args.get("user", None)
    page = request.args.get('page', type=int, default=1)
    if g.user:
        token = g.user.github_access_token
        if target_user is None:
            target_user = g.user.github_login
    if target_user is None:
        target_user = "cycraig"

    try:
        user_details = github.get_user(target_user, token)
        events, max_pages = get_events(target_user, g.user, page)
        pagination = Pagination(page=page, per_page=github.MAX_EVENTS_PER_PAGE, total=max_pages*github.MAX_EVENTS_PER_PAGE, css_framework='bootstrap4')
        return render_template("events.html", events=events, target_user=target_user, user_details=user_details,
                               event_templates=github_event_templates, event_icons=github_event_icons,
                               snoozed=False, logged_in=g.user is not None, pagination=pagination)
    except Exception as e:
        logger.exception(e)
        flash(str(e))
        return render_template("events.html", events=None, target_user=target_user, user_details=None,
                               snoozed=False, logged_in=g.user is not None, pagination=None)


@eventbp.route("/reminders", methods=["GET"])
def reminders():
    '''Displays a list of snoozed events for the logged-in user.
    '''
    if not g.user:
        flash("Login to access reminders")
        return redirect(url_for('eventbp.index'))

    try:
        user_details = github.get_user(
            g.user.github_login, g.user.github_access_token)
        events_objects = get_snoozed_events(g.user)
        snoozed_events = [e.event_json for e in events_objects]
        return render_template("events.html", events=snoozed_events, target_user=g.user.github_login,
                               user_details=user_details, event_templates=github_event_templates,
                               event_icons=github_event_icons, snoozed=True, logged_in=g.user is not None,
                               pagination=None)
    except Exception as e:
        logger.exception(e)
        flash(str(e))
        return render_template("events.html", events=None, target_user=g.user.github_login, user_details=None,
                               snoozed=True, logged_in=g.user is not None, pagination=None)


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


@eventbp.errorhandler(HTTPException)
def handle_http_exception(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    flash(str(response))
    return response
