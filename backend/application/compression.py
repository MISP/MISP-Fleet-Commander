"""Large JSON answers are sent gzip-compressed to clients that accept it.

A fleet's server list carries the last snapshot of every server (hundreds of KB each, mostly MISP's settings) and a
fleet whose baseline drifts everywhere has thousands of health issues: compressed, these answers are about eight
times smaller on the wire. Level 1 keeps most of the gain for a fraction of the CPU of the default level. Answers
that are already encoded or streamed (files, images) are left alone.
"""

import gzip

from flask import request

MIN_SIZE = 16 * 1024
LEVEL = 1


def compressResponse(response):
    if (response.mimetype != 'application/json' or response.direct_passthrough or response.is_streamed
            or 'Content-Encoding' in response.headers or not 200 <= response.status_code < 300):
        return response
    data = response.get_data()
    if len(data) < MIN_SIZE:
        return response
    response.vary.add('Accept-Encoding')
    if request.accept_encodings.best_match(['gzip']) != 'gzip':
        return response
    response.set_data(gzip.compress(data, compresslevel=LEVEL))
    response.headers['Content-Encoding'] = 'gzip'
    return response
