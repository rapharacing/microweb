from django.core import exceptions
from django.conf import settings

import requests

import logging
logger = logging.getLogger('microcosm.middleware')


class IsogramMiddleware():

	def process_request(self, request):
		if settings.ISOGRAM_ENABLED:
			gifPath = '/isogram'

			if request.path.startswith(gifPath):
				realip = 'HTTP_REAL_IP'
				cfip = 'HTTP_CF_CONNECTING_IP'

				uip = request.META["REMOTE_ADDR"]
				if request.META.has_key(cfip):
					uip = request.META[cfip]
					#logger.error('HTTP_CF_CONNECTING_IP: %s' % uip)
				if request.META.has_key(realip):
					uip = request.META[realip]
					#logger.error('HTTP_REAL_IP: %s' % uip)

				gaPath = 'uip='+uip+'&'+request.GET.urlencode()

				r = requests.post('https://www.google-analytics.com/collect', gaPath)
				#logger.error('status: %s' % str(r.status_code))

		return None

	def process_response(self, request, response):
		return response
