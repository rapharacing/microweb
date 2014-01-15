from django import template
register = template.Library()

@register.inclusion_tag('block_list_comments.html',takes_context=True)
def list_comment(context, comment, **kwargs):

  context['comment'] = comment
  return context