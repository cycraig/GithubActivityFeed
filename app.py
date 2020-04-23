import os
import sys
import logging
import dateutil.parser as dt
from datetime import datetime, timezone
from flask import Flask, flash, render_template, request, g, session, redirect, url_for, render_template_string, jsonify

from config import Config
from service.github import GitHubAPI, GitHubAPIError
from service.github_event_template import github_event_templates, github_event_icons

# Logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] %(name)s %(levelname)s:%(message)s')

# Flask
app = Flask(__name__)
app.config.from_object(Config)

# GitHub API
if not app.config.get('GITHUB_CLIENT_ID',None) or not app.config.get('GITHUB_CLIENT_SECRET', None):
    logger.error('Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env or environment variables')
    sys.exit(-1)
github = GitHubAPI(app.config['GITHUB_CLIENT_ID'], app.config['GITHUB_CLIENT_SECRET'])

# TODO: use a database
users = {}
id = 0


@app.before_request
def before_request():
    global users
    g.user = None
    if 'user_id' in session:
        # User.query.get(session['user_id'])
        g.user = users.get(session['user_id'], None)
    # print(g.user)


@app.after_request
def after_request(response):
    # db_session.remove()
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route('/oauth-callback')
def oauth_callback():
    global id
    global users
    code = request.args.get('code')
    access_token = github.oauth_callback(code)
    next_url = request.args.get('next') or url_for('index')
    if access_token is None:
        return redirect(next_url)

    #user = User.query.filter_by(github_access_token=access_token).first()
    user = None
    # print(users)
    for u in users:
        if users[u]['github_access_token'] == access_token:
            user = users[u]
            break
    if user is None:
        # User(access_token)
        user = {'user_id': id, 'github_access_token': access_token}
        # db_session.add(user)
        users[id] = user
        id += 1

    #user.github_access_token = access_token
    g.user = user
    github_user = github.get('/user', access_token).json()
    user['github_login'] = github_user['login']

    # db_session.commit()
    session['user_id'] = user['user_id']
    return redirect(next_url)


@app.route('/login')
def login():
    user_id = session.get('user_id', None)
    if user_id is None or not user_id in users:
        return redirect(github.oauth_url())
    else:
        return redirect(url_for('events'))


@app.route('/logout')
def logout():
    # remove the user_id from the session
    session.pop('user_id', None)
    flash("Logged out!")
    return redirect(url_for('index'))


@app.route("/events")
def events():
    # TODO: an OAuth token still doesn't retrieve private events?
    token = None

    # Extract user to retrieve events of from args.
    # If absent default to the logged-in user, otherwise cycraig
    target_user = request.args.get("user", None)
    if g.user:
        token = g.user.get("github_access_token", None)
        if target_user is None:
            target_user = g.user.get("github_login", None)
    if target_user is None:
        target_user = "cycraig"

    try:
        user_details = github.get_user(target_user, token)
        events = github.get_user_received_events(target_user, token)
        return render_template("events.html", events=events, target_user=target_user, user_details=user_details, event_templates=github_event_templates, event_icons=github_event_icons)
    except Exception as e:
        logger.exception(e)
        flash(str(e))
        return render_template("events.html", events=None, target_user=target_user, user_details=user_details)


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
        if d > 0: return "%d %s ago" % (d, "year" if d == 1 else "years")
        d = diff.days // 30
        if d > 0: return "%d %s ago" % (d, "month" if d == 1 else "months")
        d = diff.days // 7
        if d > 0: return "%d %s ago" % (d, "week" if d == 1 else "weeks")
        d = diff.days
        if d > 0: return "%d %s ago" % (d, "day" if d == 1 else "days")
        d = diff.seconds // 3600
        if d > 0: return "%d %s ago" % (d, "hour" if d == 1 else "hours")
        d = diff.seconds // 60
        if d > 0: return "%d %s ago" % (d, "minute" if d == 1 else "minutes")
        d = diff.seconds
        if d > 0: return "%d %s ago" % (d, "second" if d == 1 else "seconds")
    except Exception as e:
        logger.exception(e)
    return "just now"


if __name__ == "__main__":
    app.run(debug=True)
