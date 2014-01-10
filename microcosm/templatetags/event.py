from django import template
import math
register = template.Library()

@register.inclusion_tag('block_event.html',takes_context=True)
def event(context, item, **kwargs):

  if item.item.rsvp_limit > 0:
    attending = item.item.rsvp_limit - item.item.rsvp_spaces
    rsvp_percentage = int( math.ceil( (attending/float(item.item.rsvp_limit))*100 ) )

    context['rsvp_percentage'] = rsvp_percentage

  context['item'] = item

  return context