'''
These templates are based on https://github.com/caseyscarborough/github-activity

The MIT License (MIT)
Copyright (c) 2015 Casey Scarborough

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

def make_link(href: str, inner: str) -> str:
    return "<a href='%s' title=%s>%s</a>" % (href, inner, inner)

def make_github_link(item: str, inner: str = None) -> str:
    if not inner:
        inner = item
    return "<a href='%s' title=%s>%s</a>" % ("https://github.com/%s" % item, inner, inner)

def get_comment(e) -> str:
    return e['payload']['comment'].get('body','')

def get_branch(e) -> str:
    payload = e['payload']
    branch = None
    if payload and 'ref' in payload and payload['ref']:
        if payload['ref'][:11] == 'refs/heads/':
          branch = payload['ref'][11:]
        else:
          branch = payload['ref']
    return branch

'''
HTML templates for GitHub activity event descriptions.

TODO: this can be significantly improved...

See: https://developer.github.com/v3/activity/events/types/
'''
github_event_templates = {
    'CommitCommentEvent' : lambda e : 'commented on commit %s<br><small class="comment">%s</small>' % (make_link(e['payload']['comment']['html_url'], e['repo']['name']), get_comment(e)),
    'CreateEvent': lambda e : 'created %s %s at %s' % (e['payload']['ref_type'], make_github_link('%s/tree/%s' % (e['repo']['name'], get_branch(e)), get_branch(e)), make_github_link(e['repo']['name'])),
    'DeleteEvent': lambda e : 'deleted %s %s at %s' % (e['payload']['ref_type'], e['payload']['ref'], make_github_link(e['repo']['name'])),
    'FollowEvent': lambda e : 'started following %s' % make_github_link(e['payload']['target']['login']),
    'ForkEvent': lambda e: 'forked %s to %s' % (make_github_link(e['repo']['name']), make_github_link(e['payload']['forkee']['full_name'])),
    'GistEvent': lambda e: '%s %s' % (e['payload']['action'] + 'ed' if e['payload']['action'] == 'fork' else e['payload']['action'] + 'd', make_link(e['payload']['gist']['html_url'], e['payload']['gist']['id'])),
    'GollumEvent': lambda e: '%s the %s wiki<br><small class="comment">%s</small>' % (e['payload']['pages'][0]['action'], make_github_link(e['repo']['name']), make_github_link(e['payload']['pages'][0]['html_url'], e['payload']['pages'][0]['title'])),
    'IssueCommentEvent': lambda e: 'commented on %s %s<br><small class="comment">%s</small>' % ("pull request" if 'pull_request' in e['payload']['issue'] else "issue", make_link(e['payload']['issue']['html_url'], e['repo']['name']+'#'+str(e['payload']['issue']['number'])), get_comment(e)),
    'IssuesEvent': lambda e: '%s issue %s<br><small class="comment">%s</small>' % (e['payload']['action'], make_link(e['payload']['issue']['html_url'], e['repo']['name']+'#'+str(e['payload']['issue']['number'])), e['payload']['issue']['title']),
    'MemberEvent': lambda e: 'added %s to %s' % (make_github_link(e['payload']['member']['login']), make_github_link(e['repo']['name'])),
    'PublicEvent': lambda e: 'open sourced %s' % make_github_link(e['repo']['name']),
    'PullRequestEvent': lambda e: '%s pull request %s<br><small class="comment">%s</small>TODO' %(e['payload']['action'], make_link(e['payload']['pull_request']['html_url'], e['repo']['name'] + '#' + str(e['payload']['pull_request']['number'])), e['payload']['pull_request']['title']),
    'PullRequestReviewCommentEvent': lambda e: 'commented on pull request %s<br><small class="comment">%s</small>' %(make_link(e['payload']['pull_request']['html_url'], e['repo']['name'] + '#' + str(e['payload']['pull_request']['number'])), get_comment(e)),
    'PushEvent': lambda e: 'pushed to %s at %s<br>TODO' % (make_github_link('%s/tree/%s' % (e['repo']['name'], get_branch(e)), get_branch(e)), make_github_link(e['repo']['name'])),
    'ReleaseEvent': lambda e: 'released %s at %s<br><small class="comment"><span class="octicon octicon-cloud-download"></span>  %s</small>'%(make_link(e['payload']['release']['html_url'], e['payload']['release']['tag_name']), make_github_link(e['repo']['name']), make_link(e['payload']['release']['zipball_url'], 'Download Source Code (zip)')),
    'WatchEvent': lambda e: 'starred %s' % make_github_link(e['repo']['name']),
}

github_event_icons = {
    'CommitCommentEvent': 'far fa-comment',
    'CreateEvent': 'far fa-plus-square',
    #'CreateEvent_repository': 'far fa-plus-square',
    #'CreateEvent_tag': 'fas fa-tag',
    #'CreateEvent_branch': 'fas fa-code-branch',
    'DeleteEvent': 'fas fa-minus-square',
    'FollowEvent': 'fas fa-user-friends',
    'ForkEvent': 'fas fa-share-alt',
    'GistEvent': 'far fa-file-code',
    'GollumEvent': 'fas fa-pencil-alt',
    'IssuesEvent': 'fas fa-clipboard-list',
    'IssueCommentEvent': 'far fa-comments',
    'MemberEvent': 'fas fa-user-plus',
    'PublicEvent': 'fas fa-globe-africa',
    'PullRequestEvent': 'fas fa-compress-alt',
    'PullRequestReviewCommentEvent': 'far fa-comments',
    'PushEvent': 'fas fa-long-arrow-alt-up',
    'ReleaseEvent': 'fas fa-tag',
    'WatchEvent': 'fas fa-star'
}
