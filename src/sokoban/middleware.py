from django.utils import timezone


class TimezoneMiddleware(object):
    def process_request(self, request):
        tz = request.COOKIES.get('timezone', None)
        if tz:
            timezone.activate(tz)
