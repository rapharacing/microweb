from django import template
import math
register = template.Library()

@register.inclusion_tag('block_microcosm.html',takes_context=True)
def microcosm(context, microcosm, **kwargs):

  context['microcosm'] = microcosm
  return context