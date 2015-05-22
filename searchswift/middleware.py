# Copyright (c) 2015 YP Canada.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import kombu
from base64 import b64encode
from swift.common.utils import split_path, get_logger
from swift.common.swob import Request, HTTPBadRequest, HTTPServerError, \
    HTTPMethodNotAllowed, HTTPRequestEntityTooLarge, HTTPLengthRequired, \
    HTTPOk, HTTPPreconditionFailed, HTTPException, HTTPNotFound, \
    HTTPUnauthorized, HTTPConflict, HTTPRequestedRangeNotSatisfiable, \
    Response, HeaderKeyDict

DEFAULT_INDEXABLE_STARTWITH_HEADERS = 'x-object-meta-*'
DEFAULT_INDEXABLE_HEADERS = 'x-user x-user-id x-tenant-name x-tenant-id'

class SearchMiddleware(object):
    """
    Search middleware for swift communication.

    Add to the swift proxy pipeline in proxy-server.conf, such as::

        [pipeline:main]
        pipeline = catch_errors cache tempauth searchmiddleware proxy-server

    And add a searchmiddleware filter section, such as::

        [filter:searchmiddleware]
        use = egg:searchswift#searchmiddleware
        amqp_connection = amqp://guest:guest@localhost/
        # amqp_exchange = swiftsearch # exchange name for messaging
        # amqp_exchange_type = direct # type of exchange to create in rabbitmq
        # amqp_exchange_durable = True # if the exchange / queue needs to be durable to rmq restarts

    :param app: The next WSGI app in the pipeline
    :param conf: The dict of configuration values
    """

    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        self.logger = get_logger(conf, log_route='searchmiddleware')

        self.conn_str = conf.get('amqp_connection', 'amqp://localhost/')
        self.exc_str = conf.get('amqp_exchange', 'swiftsearch')
        self.exc_type = conf.get('amqp_exchange_type', 'direct')
        self.exc_durable = bool(conf.get('amqp_exchange_durable', 'True'))

        # TODO add to index reference for container, object name, content_length, last modified and Etag
        self.index_headers_startwith = DEFAULT_INDEXABLE_STARTWITH_HEADERS
        self.index_headers_startwith = [h.title() for h in self.index_headers_startwith.split()]
        self.index_headers_startwith = [h[:-1] for h in self.index_headers_startwith if h[-1] == '*']

        self.index_headers = DEFAULT_INDEXABLE_HEADERS
        self.index_headers = [h.title() for h in self.index_headers.split()]
        self.index_headers = [h for h in self.index_headers if h[-1] != '*']

    def __call__(self, env, start_response):
        self.logger.debug('Initialising swiftsearch middleware')
        req = Request(env)
        obj = None
        try:
            (version, account, container, obj) = \
                split_path(req.path_info, 4, 4, True)
        except ValueError:
            # not an object request
            pass

        filter_methods = ['POST', 'PUT']
        if req.method in filter_methods:
            self.publish_search(req.path, req)

        # TODO: Get reponse to see if a fake object
        response = self.app(env, start_response)
        return response

    def publish_search(self, path, req):
        """ Publish a verify request on the queue to gate engine """

        headers = HeaderKeyDict(req.headers)
        #self.logger.debug("SWIFTSEARCH avaiable headers: %s" % (headers.items()))

        # TODO(mlopezc1) is this actually faster than a regular regex with match?
        #   swift code loves this pattern (ex tempurl middleware) but not sure how
        #   will this actually perform in high use. Perf comparison later?
        for k, v in headers.items():
            # if header not in the whitelist of allowed full header names or *
            if k not in self.index_headers:
                #self.logger.debug("SWIFTSEARCH k=%s not in %s" % (k, self.index_headers))
                for h in self.index_headers_startwith:
                    if not k.startswith(h):
                        #self.logger.debug("SWIFTSEARCH k=%s not allowed" % (k))
                        del headers[k]

        self.logger.debug("SWIFTSEARCH sending metadata for indexing: %s" % (headers.items()))

        # TODO(mlopez1) what about renaming keys to something more human ? the X- and title format is kinda weird
        exchange = kombu.Exchange(self.exc_str, self.exc_type, durable=self.exc_durable)
        queue = kombu.Queue('search', exchange=exchange, routing_key='search')

        with kombu.Connection(self.conn_str) as connection:
            with connection.Producer(serializer='json') as producer:
                producer.publish({'id': b64encode(path), 'path': path, 'metadata': headers},
                                 exchange=exchange, routing_key='search', declare=[queue])

        return True


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def search_filter(app):
        return SearchMiddleware(app, conf)

    return search_filter
