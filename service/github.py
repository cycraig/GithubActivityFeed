import re
import logging
import requests
from typing import List, Dict
from urllib.parse import urlencode, parse_qs

logger = logging.getLogger(__name__)

GITHUB_URL = "https://github.com"
GITHUB_API_URL = "https://api.github.com"
GITHUB_OAUTH_URL = GITHUB_URL + "/login/oauth"


class GitHubAPI(object):
    """
    Barebones wrapper for performing authorised GitHub API requests with access tokens.
    """

    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id
        self.client_secret = client_secret

    def oauth_url(self, scopes: str = None, redirect_uri: str = None, state: str = None) -> str:
        """Returns a URL for GitHub OAuth authentication that the user should be redirected to.

        See: https://developer.github.com/apps/building-oauth-apps/authorizing-oauth-apps/#web-application-flow
        """
        params = {}
        params['client_id'] = self.client_id
        if scopes:
            params['scope'] = scopes
        if redirect_uri:
            params['redirect_uri'] = redirect_uri
        if state:
            params['state'] = state
        url = "%s/authorize?%s" % (GITHUB_OAUTH_URL, urlencode(params))
        return url

    def oauth_callback(self, code: str) -> str:
        """Returns a GitHub access token.

        Callback for the GitHub OAuth system.

        Receives a 'code' in the request parameters from GitHub, which is then exchanged for
        an access token with a second POST to GitHub.

        The access token can then be stored and used in subsequent API calls to authenticate
        as that user (with the given scopes).
        """
        url = GITHUB_OAUTH_URL + '/access_token'
        params = {}
        params['code'] = code
        params['client_id'] = self.client_id
        params['client_secret'] = self.client_secret

        logger.debug(
            "GitHub API OAuth exchanging code for access token %s" % url)
        response = requests.post(url, data=params)
        content = parse_qs(response.content)
        logger.debug("response.content = %s", content)
        token = content.get(b'access_token', None)
        if token is not None:
            token = token[0].decode("ascii")
        return token

    def validate_username(self, username: str) -> bool:
        """Returns whether the string is a valid GitHub username.

        A GitHub username:
        - may only contain alphanumeric characters or hyphens.
        - cannot have multiple consecutive hyphens.
        - cannot begin or end with a hyphen.
        - has a maximum length of 39 characters.
        """
        # Credit to https://github.com/shinnn/github-username-regex for regex
        # TODO: compile once, re-use pattern instance
        pattern = re.compile(r"^[a-z\d](?:[a-z\d]|-(?=[a-z\d])){0,38}$")
        return pattern.match(username) is not None

    def get_user(self, user: str, token: str = None) -> Dict:
        """Returns JSON-encoded GitHub user details as a dictionary.

        If the token is None, only public events will be returned.

        GET /users/:username

        See: https://developer.github.com/v3/users/
        """
        user = user.strip()
        logger.debug("GitHub API requesting user details for '%s'" % user)

        # validate username
        # TODO: check if more aggressive sanitisation is required on the user string
        if not user:
            raise ValueError("user cannot be empty")
        if not self.validate_username(user.strip()):
            raise ValueError("invalid username '%s'" % user)

        # get events
        path = "/users/%s" % user
        response = self.get(path, token)
        checkResponse(response)
        return response.json()

    def get_user_received_events(self, user: str, token: str = None) -> List:
        """Returns a list of dictionary JSON-encoded GitHub events for the user.

        If the token is None, only public events will be returned.

        GET /users/:username/received_events

        See: https://developer.github.com/v3/activity/events/#list-public-events
        """
        user = user.strip()
        logger.debug("GitHub API requesting events for user '%s'" % user)

        # validate username
        # TODO: check if more aggressive sanitisation is required on the user string
        if not user:
            raise ValueError("user cannot be empty")
        if not self.validate_username(user.strip()):
            raise ValueError("invalid username '%s'" % user)

        # get events
        path = "/users/%s/received_events" % user
        response = self.get(path, token)
        checkResponse(response)
        return response.json()

    def get(self, path: str, token: str = None) -> requests.models.Response:
        """Performs a GET request on the given GitHub path and returns the response.
        """
        # GitHub authorization: https://developer.github.com/v3/#authentication
        url = GITHUB_API_URL + path
        logger.debug("GET %s" % url)
        headers = {}
        if token:
            headers["Authorization"] = "token %s" % token
        response = requests.get(url, allow_redirects=True, headers=headers)
        checkResponse(response)
        return response


def checkResponse(response: requests.models.Response):
    """Raises a GitHubAPIError if the response does not have an ok status code or the content type is not JSON.
    """
    if not response or not response.ok or not 'application/json' in response.headers.get('Content-Type', ''):
        emsg = None
        try:
            emsg = "%s: %s" % (response.status_code,
                               response.json()['message'])
        except Exception:
            pass
        raise GitHubAPIError(emsg)


class GitHubAPIError(Exception):
    pass

# Singleton so it's easier to separate layers
github = GitHubAPI()
