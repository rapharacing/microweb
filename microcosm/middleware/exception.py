import bernhard
import traceback
import logging

import microweb.settings


class ExceptionMiddleware():

    def __init__(self):

        if not hasattr(microweb.settings, 'RIEMANN_ENABLED'):
            raise AssertionError, 'Please declare RIEMANN_ENABLED in settings.py'

        if microweb.settings.RIEMANN_ENABLED:
            self.client = bernhard.Client()

    def process_exception(self, request, exception):

        logging.error(traceback.format_exc())

        if microweb.settings.RIEMANN_ENABLED:
            # TODO: use a UDP method
            self.client.send({
                'host': 'localhost',
                'service' : 'microweb',
                'description' : traceback.format_exc(),
                'tags' : ['exception', 'ExceptionMiddleware'],
            })

        return None