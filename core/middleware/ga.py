from django.core import exceptions
from django.conf import settings

from pyga.requests import Tracker, Page, Session, Visitor

class GAMiddleware():

    def process_request(self, request):
        if settings.GA_ENABLED:
            ip = request.META["REMOTE_ADDR"]
            if request.META.has_key("CF-Connecting-IP"):
                ip = request.META["CF-Connecting-IP"]

            tracker = Tracker(settings.GA_KEY, request.META["HTTP_HOST"])
            visitor = Visitor()
            visitor.ip_address = ip
            session = Session()
            page = Page(request.path)
            tracker.track_pageview(page, session, visitor)

        return None

    def process_response(self, request, response):
        return response
