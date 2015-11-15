from django import template
register = template.Library()

@register.inclusion_tag('block_microcosm.html',takes_context=True)
def microcosm(context, microcosm, **kwargs):

    context['microcosm'] = microcosm

    if 'unread' in kwargs:
        context['unread'] = kwargs['unread']
    else:
        context['unread'] = False

    if 'showForum' in kwargs:
        context['showForum'] = kwargs['showForum']
    else:
        context['showForum'] = False

    return context