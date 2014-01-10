from django import template
register = template.Library()

@register.inclusion_tag('block_conversation.html',takes_context=True)
def conversation(context, item, **kwargs):

  return context