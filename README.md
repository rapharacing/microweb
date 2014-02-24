# Microweb

[Microco.sm](http://microco.sm) is a new platform for discussion forums, founded by [David Kitchen](https://twitter.com/buro9) and [Matt Cottingham](https://twitter.com/mattrco).

We have a live site where you can [see the microcosm platform in action](https://meta.microco.sm). You can also [read more about the project here](http://microco.sm).

Microweb is the official web client for the Microcosm API, written in Django. If you're not familiar with the Microcosm API, you should start by reading the [API documentation](http://microcosm-cc.github.io/) (it's up-to-date and readable, we promise).

If you find any problems, raise an issue on github and we'll respond ASAP.

[![Build Status](https://travis-ci.org/microcosm-cc/microweb.png)](https://travis-ci.org/microcosm-cc/microweb)

## Project setup

We use Django 1.5 and Virtualenv. To create the necessary virtualenv, run the following:

```
virtualenv envname
source envname/bin/activate
pip install -r requirements.txt
```

This will install all dependencies listed in `requirements.txt`

## Project structure

The top-level structure looks like this:

```
├── microweb
│   ├── fabfile.py
│   ├── manage.py
│   ├── microcosm
│   ├── microweb
│   ├── README.md
│   ├── requirements.txt
│   └── upstart.sh
```

Most of the files you'll care about are in the `microcosm` app:

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

The `api` package contains classes for communicating with the Microcosm API. If you're familiar with django, the rest of the packages and modules will look familiar.

### Request middleware

The `request` object is being used quite a bit here, which is possible because of `middleware/context.py`:

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
    request.site = None
    request.create_profile = False

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

So on each request we make a couple (cached) calls to the API, to check if the user has a valid `access_token` cookie, and retrieve some basic site data (title, description).
