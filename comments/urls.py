from django.conf.urls import url
from django.conf.urls import patterns

from comments.views import CommentView

urlpatterns = patterns('',
    url(r'comments/create/$', CommentView.create, name='create-comment'),
    url(r'comments/(?P<comment_id>\d+)/$', CommentView.single, name='single-comment'),
    url(r'comments/(?P<comment_id>\d+)/edit/$', CommentView.edit, name='edit-comment'),
    url(r'comments/(?P<comment_id>\d+)/delete/$', CommentView.delete, name='delete-comment'),
    url(r'comments/(?P<comment_id>\d+)/incontext/$', CommentView.incontext, name='incontext-comment'),
    url(r'comments/(?P<comment_id>\d+)/source/$', CommentView.source, name='source-comment'),
    url(r'comments/(?P<comment_id>\d+)/attachments/$', CommentView.attachments, name='attachment-comment'),
)