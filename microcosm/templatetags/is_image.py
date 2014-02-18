from django import template
register = template.Library()

@register.filter
def is_image(file_ext):

	recognised_img_exts = ['gif','jpg','jpeg','bmp','png']

	if file_ext.lower() in recognised_img_exts:
			return True
	else:
			return False