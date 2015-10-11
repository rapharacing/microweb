from django.conf.urls import url
from django.conf.urls import patterns

from microcosms import views


urlpatterns = patterns('',

    url(r'^$', views.list_microcosms, name='index'),
    url(r'^microcosms/$', views.list_microcosms, name='list-microcosms'),
    url(r'^microcosms/create/$', views.create_microcosm, name='create-microcosm'),
    url(r'^microcosms/(?P<microcosm_id>\d+)/$', views.single_microcosm, name='single-microcosm'),
    url(r'^microcosms/(?P<parent_id>\d+)/create/microcosm/$', views.create_microcosm, name='create-child-microcosm'),
    url(r'^microcosms/(?P<microcosm_id>\d+)/edit/$', views.edit_microcosm, name='edit-microcosm'),
    url(r'^microcosms/(?P<microcosm_id>\d+)/delete/$', views.delete_microcosm, name='delete-microcosm'),

    url(r'^microcosms/(?P<microcosm_id>\d+)/memberships/$', views.list_members, name="list-memberships"),
    url(r'^microcosms/(?P<microcosm_id>\d+)/memberships/create/$', views.create_members,
        name="create-memberships"),
    url(r'^microcosms/(?P<microcosm_id>\d+)/memberships/(?P<group_id>\d+)/edit/$', views.edit_members,
        name="edit-memberships"),

    # Proxy and batch requests to the backend
    url(r'^microcosms/(?P<microcosm_id>\d+)/memberships/api/$', views.members_api, name="api-memberships"),
)