from django import template
register = template.Library()

@register.inclusion_tag('block_list_comments.html',takes_context=True)
def list_comment(context, comment, **kwargs):

    context['result'] = comment

    if 'action' in kwargs:
        context['action'] = kwargs['action']
    else:
        context['action'] = ''

    return context