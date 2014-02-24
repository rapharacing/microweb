# Microweb

[Microco.sm](http://microco.sm) is a new platform for discussion forums, founded by [David Kitchen](https://twitter.com/buro9) and [Matt Cottingham](https://twitter.com/mattrco).

Communities are already using Microco.sm as their forum software of choice, e.g. the [Espruino Forum](http://forum.espruino.com) and [Islington Cycle Club](http://forum.islington.cc).

Microweb is the official web client for Microco.sm, written in Django. If you're not familiar with the Microcosm API, you should start by reading the [API documentation](http://microcosm-cc.github.io/) (it's up-to-date and readable, we promise).

If you find any problems, raise an issue on github and we'll respond ASAP.

[![Build Status](https://travis-ci.org/microcosm-cc/microweb.png)](https://travis-ci.org/microcosm-cc/microweb)

## Project setup

To create a python virtualenv, run the following:

```
virtualenv -p python2.7 envname
source envname/bin/activate
pip install -r requirements.txt
```

This will install all dependencies listed in `requirements.txt`. All commands should be executed with the virtual environment activated.

## Project structure

Currently most of the project is contained within the `microcosm` app (due to be split in a refactor):

```
├── microcosm
│   ├── api
│   ├── forms
│   ├── __init__.py
│   ├── middleware
│   ├── static
│   ├── templates
│   ├── tests.py
│   ├── urls.py
│   ├── views.py
```

The `api` package contains classes for communicating with the Microcosm API. If you're familiar with Django, the rest of the packages and modules will look familiar.

## Tests

Unit tests can be run with:

```
python manage.py test
```

## User authentication

Since authentication is handled by the API, custom middleware is used to provide the authentication context in views. In `middleware/context.py`:

```python
def process_request(self, request):
    """
    Checks for access_token cookie and appends it to the request object
    if it exists. If the access token is invalid, flags it for deletion.

    Populates request.whoami with the result of the whoami API call.
    """

    request.access_token = None
    request.delete_token = False
    request.whoami = None

    if request.COOKIES.has_key('access_token'):
        request.access_token = request.COOKIES['access_token']

        # if a bad access token is provided, flag for deletion
        try:
            request.whoami = WhoAmI.retrieve(request.access_token)
        except APIException, e:
            if e.status_code == 401:
                request.delete_token = True
                    
    ...

```

So on each request we make a couple of calls to the API to check if the user has a valid `access_token` cookie, and retrieve some basic site data (title, description).
