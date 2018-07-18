class CorsMiddleware():
    # TODO: Need to process OPTIONS request to return options:
    # add_header 'Access-Control-Allow-Origin' '*';
    # add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
    # add_header 'Access-Control-Allow-Headers' 'DNT,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type';
    # add_header 'Access-Control-Max-Age' 1728000;
    # add_header 'Content-Type' 'text/plain charset=UTF-8';
    # add_header 'Content-Length' 0;
    # return 204;

    def process_response(self, request, response):
        if response['Content-Type'] == 'text/html; charset=utf-8':
            if request.method == 'GET':
                response['Access-Control-Allow-Origin'] = '*'
                response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response['Access-Control-Allow-Headers'] = 'DNT,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type'
            elif request.method == 'POST':
                response['Access-Control-Allow-Origin'] = '*'
                response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response['Access-Control-Allow-Headers'] = 'DNT,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type'
        return response
