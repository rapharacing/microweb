# Microweb

Microcosm is a new platform for discussion forums, founded by David Kitchen and Matt Cottingham.

We have a live (alpha-quality) site where you can [see the microcosm platform in action](https://sandbox.microco.sm). You can also [read more about the project here](http://microco.sm).

Microweb is the official web client for the Microcosm API, written in Django. If you're not familiar with the Microcosm API, you should start by reading the [API documentation](http://microcosm-cc.github.io/) (it's up-to-date and readable, we promise).

Have a look at `CONTRIBUTING.md` if you're interested in helping out -- there are some important caveats (such as deployment and availability of test servers) that you
should know about before starting. That said, we'll be improving test coverage that's decoupled from the API to make contributing or forking much easier.

If you find any problems, raise an issue on github and we'll respond ASAP.

## Project setup

We use Django 1.4 and Virtualenv. To create the necessary virtualenv, run the following:

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

The big difference between `microweb` and most django projects is that there is no `models.py`, since all the web client does is talk to the API instead of storing state locally.
The only reason a database is defined in `settings.py` is because it keeps the test runner happy.

In future `api` will be broken out into a separate python package, so it's important that it remains loosely coupled to the rest of the application.
That means it should know nothing about django, it's simply a thin veneer over the API to make querying and error handling easier.

## An example view

To demonstrate how view classes and the `api` package are used in `microweb`, let's look at how a request is processed and the response rendered.
We'll take the `/microcosms` path as an example, which shows a list of microcosms belonging to the current site to the user.

### Routing and view function

From `microcosm.urls.py`:

```
url(r'^microcosms/$', MicrocosmView.list, name='list-microcosms'),
```

The request is routed to `views.MicrocosmView.list()` in `views.py`.
If we look at that class we see it inherits from `ItemView`, where `list()` is implemented:

```python
class ItemView(object):

    @classmethod
    @exception_handler
    def list(cls, request):

        list = cls.resource_cls.retrieve(
            offset=request.GET.get('offset', None),
            access_token=request.access_token
        )

        view_data = {
            'user': request.whoami,
            'site': request.site,
            'content': list,
        }

        return render(request, cls.many_template, view_data)
```

`list()` is a `classmethod`, so it gets passed the class it is called on as the first argument.
`list()` uses a few class attributes, so let's look at `MicrocosmView` to see these declared:

```python
class MicrocosmView(ItemView):

    item_type = 'microcosm'
    item_plural = 'microcosms'
    resource_cls = Microcosm
    create_form = MicrocosmCreate
    edit_form = MicrocosmEdit
    form_template = 'forms/microcosm.html'
    one_template = 'microcosm.html'
    many_template = 'microcosms.html'
```

`resource_cls` is the class in the `api` package that's used to talk to the Microcosm API. 
We also see `cls.many_template` being used, which is the template the class uses for a list view.

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

So on each request we make a couple (heavily cached) calls to the API, to check if the user has a valid `access_token` cookie, and retrieve some basic site data (title, description).

### Using the api package

Going back to the view, let's look at the implementation of `cls.resource_cls.retrieve(...)` in `api` and see where it takes us. 
You'll see that `api.resources.Microcosm` is a child of `APIResource`, where most of the fun happens:

```python
class APIResource(object):
    """
    Base API resource that performs HTTP operations. Each API class should subclass this
    to deal with custom validation and JSON processing.
    """

    @classmethod
    def retrieve(cls, id=None, offset=None, access_token=None):
        """
        GET an API resource. If resource ID is omitted, returns a list. Appends access_token
        and offset (for paging) if provided.
        """
        
        resource_url = cls.resource_url # Simplified

        params = {}
        if access_token:
            params['access_token'] = access_token

        try:
            response = requests.get(resource_url, params=params, headers={'Host' : HOST})
        except RequestException:
            raise

        try:
            resource = response.json()
        except ValueError:
            raise APIException('The API has returned invalid json', 500)

        if resource['error']:
            raise APIException(resource['error'], response.status_code)

        if not resource['data']:
            raise APIException('No data returned at: %s' % resource_url)

        return resource['data']
```
Lots has been removed from this for simplicity, but it should be clear what it's doing: requesting an API resource using the `requests` library and doing some minor conversion/error handling.

It's important to note that API resources are *not* modelled as Python classes, since it would result in lots of boilerplate while not providing much in the way of convenience.

### Using API data

Instead, the JSON response is simply deserialized into a Python dictionary, and some formatting done on this (e.g. converting timestamps to python datetime.datetime instances).
Example output for a list of microcosms:

```
{
  u'meta': {
    'linkmap': {u'self': u'/api/v1/microcosms'}, 
      u'links': [{u'href': u'/api/v1/microcosms', u'rel': u'self'}], 
      u'permissions': {
        u'superUser': False, 
        u'guest': True, 
        u'read': True, 
        u'create': False, 
        u'update': False, 
        u'delete': False}
      }, 
      u'microcosms': {
        u'links': [
          {u'href': u'/api/v1/microcosms', u'rel': u'first'}, 
          {u'href': u'/api/v1/microcosms', u'rel': u'self'}, 
          {u'href': u'/api/v1/microcosms', u'rel': u'last'}
        ], 
        u'items': [
          {
            u'description': u'Created by selenium', 
            u'title': u'Test microcosm', 
            u'visibility': u'public', 
            u'moderators': None, 
            u'meta': {
              u'flags': {...}, 
              u'links': [...], 
              u'createdBy': {...}, 
              u'created': datetime.datetime(2013, 4, 24, 16, 10, 58, 491381, tzinfo=tzutc())
            }, 
            ...
```

### Templates

Finally, let's look at the template we render to display a list of microcosms to the user:

```
{% extends 'base.html' %}

{% block content %}
    {% if not content.microcosms.items %}
        <p>This site doesn't have any microcosms yet.</p>
    {% else %}
        <ul>
            {% for item in content.microcosms.items %}
            <li>
                <a href="/microcosms/{{ item.id }}/"><h3>{{ item.title }}</h3></a>
                <p>{{ item.description }}</p>
                <p><img src="{{ item.meta.createdBy.gravatar }}">Created by {{ item.meta.createdBy.profileName }} on {{ item.meta.created }}.</p>
            </li>
            {% endfor %}
        </ul>
    {% endif %}

{% endblock %}

{% block sidebar%}
    {% if content.meta.permissions.create %}
    <a id="create_microcosm" href="{% url create-microcosm %}"><h3>Create a microcosm</h3></a>
    {% endif %}
{% endblock%}
```

This is simplified, but it shows how we use the `content` object provided by the view. The `microcosms` object we recieved from the API has an inner list of `items` (microcosms in this case) which we iterate through and display.

`base.html` (which this template extends) contains blocks which render the site and whoami details.

## Error handling

You probably noticed the `@exception_handler` decorator on the view above. This is intended to handle errors across all views in a consistent manner.

Things can go wrong in (at least) three different ways when you call methods in the api package:

* AssertionError: an invalid parameter has been provided (such as a string where a numeric ID was expected)
* APIException: the microcosm API has returned an error. This could be due to invalid data, a bad access token, etc.
* RequestException: something went wrong in transport -- these are exceptions thrown by the `requests` and raised.

As well as these, expect the usual built-ins such as `TypeError` if e.g. a type conversion fails.

The advantages of offloading error-handling work to the decorator are: consistent error reporting to the user, and centralised logging of errors.

Of course, this isn't a license to be careless in views -- you should validate user input if there's something the user can do about it, and format requests to the `api` package appropriately.

## Authentication

We currently allow login through mozilla persona, and set a cookie called `access_token`. As stated above, there is some custom middleware which processes every request, and sets fields on the request object according to the user's authentication status.

If a user is authenticated, the request object will have the following fields:


```
request.access_token     # value of the access_token cookie, if it exists
request.delete_token     # if the access token provided is bad, this is a flag processed in process_response
request.whoami           # dictionary for decoded json from /api/v1/whoami
```

## Deployment

We use fabric to deploy. There are two tasks which determine the environment that will be deployed to: `dev_env` and `prod_env`. Prefix all commands
with one of these two deploy to that environment.

You'll need VMs set up with vagrant and puppet first. For the first run:

* This repo *must* be checked out to a directory named `microweb` (default in git, but don't be tempted to rename).
* Create `microweb/local_settings.py` -- this will be rsynced to the server with the rest of project files. Check `settings.py` for what to declare.
* Run: `fab {env} first_deploy`

In future, you can use `fab {env} redeploy` which skips destroying/creating the virtual environment, saving some time.

It's obviously not ideal to copy `local_settings.py` to the remote verbatim, so this will be parameterised in future.
