class PreconnectMiddleware():
    def process_response(self, request, response):
        
        if response['Content-Type'] == 'text/html; charset=utf-8':
            response['Link'] = '<//cdnjs.cloudflare.com>; rel=preconnect, <//www.google-analytics.com>; rel=preconnect, <https://login.persona.org>; rel=preconnect, <https://static.login.persona.org>; rel=preconnect, <//fonts.googleapis.com>; rel=preconnect, <https://fonts.gstatic.com>; rel=preconnect; crossorigin'

        return response
