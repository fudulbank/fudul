import functools
import logging
import json

from django.core import exceptions as django_exceptions
from django.http import HttpResponse, Http404

def ajax_only(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.is_ajax():
            raise Http404
        try:
            data = view_func(request, *args, **kwargs)
            if data is None:
                data = {}
        except Exception as e:
            #todo: also check field called "message"
            if hasattr(e, 'messages'):
                if len(e.messages) > 1:
                    message = u'<ul>' + \
                        u''.join(
                            map(lambda v: u'<li>%s</li>' % v, e.messages)
                        ) + \
                        u'</ul>'
                else:
                    message = e.messages[0]
            else:
                message = str(e)
            if message == '':
                message = 'Oops, apologies - there was some error'
            logging.debug(message)
            data = {
                'message': message,
                'success': 0
            }
            return HttpResponse(json.dumps(data), content_type='application/json')

        if isinstance(data, HttpResponse):#is this used?
            data.mimetype = 'application/json'
            return data
        else:
            data['success'] = 1
            json_data = json.dumps(data)
            return HttpResponse(json_data, content_type='application/json')
    return wrapper
