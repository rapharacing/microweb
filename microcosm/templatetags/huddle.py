from django import template
register = template.Library()

@register.inclusion_tag('block_huddle.html',takes_context=True)
def huddle(context, item, **kwargs):

  # FIXME: probably want a better way to test if huddle object is within
  # a container object ie. a search result object or update object
  if hasattr(item,'item'):
    context['item'] = item
  else:
    context['item'] = { 'item' : item }

  return context