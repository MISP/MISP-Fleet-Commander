"""The picture of a MISP instance: the logo its login page shows, as a data URI.

The login page is read anonymously. The logo is fetched by the backend, from the server's own URL, so the browser
needs no access to the MISP instance (or trust in its certificate), and MFC never follows a URL the page chose: only
the path of the image is kept.
"""
import base64
import hashlib
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from application import redisClient
from application.controllers.utils import mispGetHTMLRequest

KEY_INSTANCE_PICTURE = 'instance-picture'
CACHE_SECONDS = 3600
CACHE_SECONDS_WITHOUT_PICTURE = 600  # Shorter, so an instance that was down gets its picture soon after
MAX_PICTURE_BYTES = 1024 * 1024
TIMEOUT = (3, 10)
# MISP 3 shows one logo for the light theme and one for the dark theme: MFC has a light theme
PREFERRED_CLASS = 'logo-light'


class _ImageCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            attributes = dict(attrs)
            if attributes.get('src'):
                self.images.append(attributes)


def pickLogoSource(html: str):
    """The `src` of the login page's logo: the light-theme one if marked as such (MISP 3), else the first image"""
    collector = _ImageCollector()
    try:
        collector.feed(html)
        collector.close()
    except Exception:
        return None
    if not collector.images:
        return None
    preferred = [img for img in collector.images
                 if any(c.endswith(PREFERRED_CLASS) for c in (img.get('class') or '').split())]
    return (preferred or collector.images)[0]['src'].strip()


def inlinePicture(src: str):
    """An inline image (`data:image/...`) kept as is, None for anything else"""
    if src.lower().startswith('data:image/') and ';base64,' in src[:100].lower():
        return src
    return None


def picturePathOnServer(serverURL: str, src: str):
    """The image's URL on the server itself: MISP builds its image URLs from `MISP.baseurl`, which may not be the
    address MFC uses (or not reachable from it), so only the path and query of `src` are kept"""
    parts = urlsplit(src)
    if parts.scheme not in ('', 'http', 'https'):
        return None
    path = parts.path or ''
    if not path:
        return None
    if not path.startswith('/'):
        path = '/' + path
    return urljoin(serverURL, path + (f'?{parts.query}' if parts.query else ''))


def fetchPicture(server):
    """The instance's logo as a data URI, '' when there is none or it cannot be read"""
    page = mispGetHTMLRequest(server, '/users/login', timeout=TIMEOUT)
    if not isinstance(page, str):
        return ''
    src = pickLogoSource(page)
    if not src:
        return ''
    inline = inlinePicture(src)
    if inline is not None:
        return inline if len(inline) <= MAX_PICTURE_BYTES * 4 // 3 + 100 else ''
    if src.lower().startswith('data:'):
        return ''
    url = picturePathOnServer(server.url, src)
    if url is None:
        return ''
    response = mispGetHTMLRequest(server, url, rawResponse=True, timeout=TIMEOUT)
    if isinstance(response, dict) or getattr(response, 'status_code', None) != 200:
        return ''
    contentType = (response.headers.get('Content-Type') or '').split(';')[0].strip().lower()
    content = response.content or b''
    if not contentType.startswith('image/') or not content or len(content) > MAX_PICTURE_BYTES:
        return ''
    return f'data:{contentType};base64,{base64.b64encode(content).decode()}'


def _cacheKey(server):
    # Per server and URL: a server moved to another address gets a new picture
    return f'{KEY_INSTANCE_PICTURE}:{server.id}:{hashlib.sha256(server.url.encode()).hexdigest()[:16]}'


def getPicture(server, anonymousServer):
    """The cached picture of `server`, fetched (with `anonymousServer`, which has no authkey) when not cached"""
    key = _cacheKey(server)
    cached = redisClient.get(key)
    if cached is not None:
        return cached
    try:
        picture = fetchPicture(anonymousServer)
    except Exception:
        picture = ''
    redisClient.set(key, picture, ex=CACHE_SECONDS if picture else CACHE_SECONDS_WITHOUT_PICTURE)
    return picture
