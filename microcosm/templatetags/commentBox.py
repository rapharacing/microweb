from django import template
import collections
register = template.Library()

@register.inclusion_tag('forms/block_comment_box.html',takes_context=True)
def commentBox(context, **kwargs):

  # as_component - removes <form> element and submit buttons in block_comment_box.html
  context['as_component']   = True if 'as_component' in kwargs else False

  # no_attachments - removes the attachment section of the comment box
  context['no_attachments'] = True if 'no_attachments' in kwargs else False

  # name - used as name attribute in <textarea>
  if 'name' in kwargs:
    context['name'] = kwargs['name']

  # value = used in <textarea>

  if 'value' in kwargs:
    context['value'] = kwargs['value']

  return context