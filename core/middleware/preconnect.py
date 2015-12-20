class PreconnectMiddleware():
    def process_response(self, request, response):
        
        if response['Content-Type'] == 'text/html; charset=utf-8':
            response['Link'] = '<//fonts.googleapis.com>; rel=preconnect, <https://fonts.gstatic.com>; rel=preconnect; crossorigin'

        return response
