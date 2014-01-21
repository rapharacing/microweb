#!/usr/bin/python

import json
import sys
import requests
import urlparse
import urllib

"""
Utilities for fetching JSON from the microcosm API and writing it to files
for unit testing.
"""

def main():
    if len(sys.argv) != 3:
        print 'Usage: python %s <api_subdomain> <access_token>' % sys.argv[0]
        sys.exit(2)

    site_subdomain = sys.argv[1]
    access_token = sys.argv[2]
    failures = {}

    # whoami
    ident = 'Fetching whoami'
    print ident
    url = unparse_api_url(site_subdomain, 'api/v1/whoami', access_token=access_token)
    response = requests.get(url, headers={'Accept-Encoding': 'application/json'})
    if response.status_code != 200:
        failures[ident] = response.content
        exit_with_error(failures)
    else:
        whoami = open('whoami.json', 'w')
        whoami.write(response.content)
        whoami.close()

    # microcosms
    ident = 'Creating microcosm'
    print ident
    url = unparse_api_url(site_subdomain, 'api/v1/microcosms', access_token=access_token)
    data = json.dumps({
        'title': 'Generated',
        'description': 'Generated microcosm',
        })
    response = requests.post(url, data=data, headers={'Content-Type': 'application/json'})
    if response.status_code != 200:
        failures[ident] = response.content
        exit_with_error(failures)
    else:
        microcosm = open('microcosm.json', 'w')
        microcosm.write(response.content)
        microcosm.close()
        microcosm_id = response.json()['data']['id']
        print 'Created microcosm with ID: %d' % microcosm_id

    # conversations
    ident = 'Creating conversation without comment'
    print ident
    url = unparse_api_url(site_subdomain, 'api/v1/conversations', access_token=access_token)
    data = json.dumps({
        'microcosmId': microcosm_id,
        'title': 'Generated',
        'description': 'Generated conversation',
    })
    response = requests.post(url, data=data, headers={'Content-Type': 'application/json'})
    if response.status_code != 200:
        failures[ident] = response.content
        exit_with_error(failures)
    else:
        conversation = open('conversation_without_comment.json', 'w')
        conversation.write(response.content)
        conversation.close()

    ident = 'Creating conversation with comment'
    print ident
    url = unparse_api_url(site_subdomain, 'api/v1/conversations', access_token=access_token)
    data = json.dumps({
        'microcosmId': microcosm_id,
        'title': 'Generated',
        'description': 'Generated conversation',
        'firstComment': 'This is the first comment',
    })
    response = requests.post(url, data=data, headers={'Content-Type': 'application/json'})
    if response.status_code != 200:
        failures[ident] = response.content
        exit_with_error(failures)
    else:
        conversation = open('conversation_with_comment.json', 'w')
        conversation.write(response.content)
        conversation.close()


def unparse_api_url(site_subdomain, path, query_params={}, access_token=''):
    netloc = '%s.microco.sm' % site_subdomain
    if access_token:
        query_params['access_token'] = access_token
    querystring = urllib.urlencode(query_params)
    return urlparse.urlunparse(('https', netloc, path, '', querystring, ''))


def exit_with_error(failures):
    print 'Failed. Errors follow...'
    print failures
    sys.exit(1)


if __name__ == '__main__':
    main()
