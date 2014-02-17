from django import template
import math
register = template.Library()

@register.inclusion_tag('block_event.html',takes_context=True)
def event(context, item, **kwargs):

  if hasattr(item,'item'):
    context['item'] = item
  else:
    context['item'] = { 'item' : item }

  return context