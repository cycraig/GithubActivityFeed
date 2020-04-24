from .db import db
from .user import User

class Event(db.Model):
    '''
    Stores a plain JSON-encoded event from the GitHub activity API v3.
    '''

    __tablename__ = 'events'

    event_id = db.Column(db.String(120), primary_key=True)
    event_json = db.Column(db.JSON)
    github_id = db.Column(db.Integer, db.ForeignKey(User.github_id), index=True)

    def __init__(self, event_id, event_json, github_id):
        self.event_id = event_id
        self.event_json = event_json
        self.github_id = github_id

    def __repr__(self):
        return '<Event {} {} {}>'.format(self.event_id, self.github_id, self.event_json)    
