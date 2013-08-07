from django.core.exceptions import MiddlewareNotUsed

import microweb
import bernhard
import time


class TimingMiddleware():

    def __init__(self):
        if microweb.settings.RIEMANN_ENABLED:
            self.client = bernhard.Client(host=microweb.settings.RIEMANN_HOST, transport=bernhard.UDPTransport)
        else:
            raise MiddlewareNotUsed

    def process_request(self, request):
        request.start_time = time.time()
        return None

    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            delta = time.time() - request.start_time
            self.client.send({
                'host': 'django',
                'service': 'microweb',
                'metric': delta,
                'tags' : ['timing'],
            })
        return response