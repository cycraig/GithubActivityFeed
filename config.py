import os
import sys

basedir = os.path.abspath(os.path.dirname(__file__))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(basedir, '.env'))
except Exception:
    print("Failed to load dotenv!", file=sys.stderr)
    pass

class Config(object):
    """
    Flask configuration variables
    """
    SECRET_KEY = os.getenv('SECRET_KEY') or b'#&TGafg7(@0\\'
    GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
    DEBUG = os.getenv('DEBUG') == '1'
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI') or 'sqlite:///' + os.path.join(basedir, 'data.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('DEBUG') == '1'
