import logging

from aiohttp import web
from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp.web_request import Request

from sarafan.magnet import is_magnet

log = logging.getLogger(__name__)


async def hello(request):
    """Hello page containing sarafan node metadata.

    `version` contains sarafan node version.
    `content_service_id` — contains service_id of content node

    :param request:
    :return:
    """
    raise Exception("HOH")
    return web.json_response(await request.app['sarafan'].hello())


async def discover(request: Request):
    """Discover peering network nodes.

    List of nodes with highest rating will be returned by default.

    ?hash=<magnet> — return list of peers ordered by distance to provided hash

    Peer list size is always limited by the node (recommended is 500 items)
    and has no pagination by design.
    """
    magnet = request.query.get('magnet')
    if magnet and not is_magnet(magnet):
        log.error("Requested value is not a magnet")
        raise HTTPBadRequest()

    if magnet:
        peers = await request.app['sarafan'].nearest_peers(magnet)
    else:
        peers = await request.app['sarafan'].hot_peers()

    if peers is None or len(peers) == 0:
        log.warn("Respond with empty peer list: no peers received from application")
        peers = []

    return web.json_response([{
        'service_id': peer.service_id,
        'rating': peer.rating
    } for peer in peers])


async def upload(request):
    """Upload publication.

    Client should use this endpoint to upload publication to matching peer.

    Peer should check:

    - uploaded file size should be less than 10Mb
    - there is an available disk space
    - content hash within range of interest
    - enough reserved space for pending publication
        (if publication event is not received from chain, yet)
    """
    magnet = request.match_info['magnet']
    content_length = request.content_length
    if content_length > 10 * 1024 ** 2:
        await request.release()
        raise HTTPBadRequest()
    await request.app['sarafan'].store_upload(magnet, request.content)
    return web.json_response({
        "status": "ok"
    }, status=202)


async def publications(requests):
    """Paginated list of last publications with additional metadata.

    ?source=<address>
    ?author=<address>
    ?related=<publication>
    ?cursor=XXX - use cursor for consistent pagination

    :param requests:
    :return:
    """
    return web.json_response({
        "next": None,
        "result": [
            {
                'id': 'asdasdsd',
                'author': '0xdsaadasd',
                'source': '0xADSdsdsd',
                'magnet': '24fj5wbj2abxuhjl',
                'size': 10000000,
                'reply_count': 1,
                'comment_count': 100,
                'awards': 10000000,
                'abuses_volume': 102030
            }
        ]
    })


async def abuses(request):
    """Paginated list of abuses.

    ?publication=<magnet> - to show publication abuses
    ?source=<address> - to show only abuses from provided source
    ?cursor=XXX - use cursor for consistent pagination
    """
    return web.json_response({
        "next": None,
        "result": [
            {
                'id': 'asdasdsd',
                'source': '0xADSdsdsd',
                'magnet': '24fj5wbj2abxuhjl',
                'volume': 10000000,
                'reason': 'Some text',
            }
        ]
    })


async def awards(request):
    """Paginated list of latest awards

    ?publication=<magnet> - to show publication abuses
    ?source=<address> - to show only abuses from provided source
    ?cursor=XXX - use cursor for consistent pagination
    """
    return web.json_response({
        "next": None,
        "result": [
            {
                'id': 'asdasdsd',
                'source': '0xADSdsdsd',
                'magnet': '24fj5wbj2abxuhjl',
                'volume': 10000000,
                'amount': 1234,
            }
        ]
    })


def setup_routes(app, node=True, content_path=None, client=True):
    if node:
        app.add_routes([
            web.get('/hello', hello),
            web.get('/discover', discover),
            web.get('/discover/{magnet}', discover),
            web.post('/upload/{magnet}', upload),
        ])
    if content_path:
        app.add_routes([
            web.static('/content', content_path)
        ])
    if client:
        # TODO: replace with implementation of sarafan-app prototype
        app.add_routes([
            web.get('/publications', publications),
            web.get('/abuses', abuses),
            web.get('/awards', awards),
        ])
    return app
