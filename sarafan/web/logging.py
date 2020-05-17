from aiohttp.abc import AbstractAccessLogger


class AccessLogger(AbstractAccessLogger):

    def log(self, request, response, time):
        message = "%(method)s %(path)s %(status)s %(size)s bytes in %(time).4f sec"
        args = {
            'method': request.method,
            'path': request.path,
            'status': response.status,
            'size': response.content_length,
            'time': time
        }
        if response.status % 400 < 100:
            self.logger.info(message, args)
        elif response.status % 500 < 100:
            self.logger.error(message, args)
        else:
            self.logger.info(message, args)
