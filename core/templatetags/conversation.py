from django import template
register = template.Library()

@register.inclusion_tag('block_conversation.html',takes_context=True)
def conversation(context, item, **kwargs):

    if hasattr(item,'item'):
        context['item'] = item.item
    else:
        context['item'] = item

    if 'unread' in kwargs:
        context['unread'] = kwargs['unread']
    else:
        context['unread'] = False

    return context
