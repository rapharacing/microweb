from django.conf.urls import url
from django.conf.urls import patterns

from comments import views

urlpatterns = patterns('',
    url(r'comments/create/$', views.create, name='create-comment'),
    url(r'comments/(?P<comment_id>\d+)/$', views.single, name='single-comment'),
    url(r'comments/(?P<comment_id>\d+)/edit/$', views.edit, name='edit-comment'),
    url(r'comments/(?P<comment_id>\d+)/delete/$', views.delete, name='delete-comment'),
    url(r'comments/(?P<comment_id>\d+)/incontext/$', views.incontext, name='incontext-comment'),
    url(r'comments/(?P<comment_id>\d+)/source/$', views.source, name='source-comment'),
    url(r'comments/(?P<comment_id>\d+)/attachments/$', views.attachments, name='attachment-comment'),
)