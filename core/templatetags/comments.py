from django import template
import collections
register = template.Library()

@register.inclusion_tag('block_comments.html', takes_context=True)
def comments(context, comments, **kwargs):

    if not isinstance(comments, collections.Iterable):
        comments = [comments]

    context['comments'] = comments
    context['hide_permalink'] = True if 'hide_permalink' in kwargs else False

    return context
