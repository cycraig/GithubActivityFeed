from .db import db

class User(db.Model):
    '''
    Stores an OAuth-authenticated GitHub user.
    '''
    __tablename__ = 'users'

    github_id = db.Column(db.Integer, primary_key=True)
    github_login = db.Column(db.String(40))
    github_email = db.Column(db.String(120))
    github_access_token = db.Column(db.String(255), index=True, unique=True)

    def __init__(self, github_access_token):
        self.github_access_token = github_access_token

    def __repr__(self):
        return '<User {} {} {} {}>'.format(self.github_id, self.github_login, self.github_email, self.github_access_token)    
