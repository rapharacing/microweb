from django.conf.urls import url
from django.conf.urls import patterns

from microcosms.views import MicrocosmView
from microcosms.views import MembershipView


urlpatterns = patterns('',

    url(r'^$', MicrocosmView.list, name='index'),
    url(r'^microcosms/$', MicrocosmView.list, name='list-microcosms'),
    url(r'^microcosms/create/$', MicrocosmView.create, name='create-microcosm'),
    url(r'^microcosms/(?P<microcosm_id>\d+)/$', MicrocosmView.single, name='single-microcosm'),
    url(r'^microcosms/(?P<microcosm_id>\d+)/edit/$', MicrocosmView.edit, name='edit-microcosm'),
    url(r'^microcosms/(?P<microcosm_id>\d+)/delete/$', MicrocosmView.delete, name='delete-microcosm'),

    url(r'^microcosms/(?P<microcosm_id>\d+)/memberships/$', MembershipView.list, name="list-memberships"),
    url(r'^microcosms/(?P<microcosm_id>\d+)/memberships/create/$', MembershipView.create, name="create-memberships"),
    url(r'^microcosms/(?P<microcosm_id>\d+)/memberships/(?P<group_id>\d+)/edit/$', MembershipView.edit, name="edit-memberships"),

    # Proxy and batch requests to the backend
    url(r'^microcosms/(?P<microcosm_id>\d+)/memberships/api/$', MembershipView.api, name="api-memberships"),
)