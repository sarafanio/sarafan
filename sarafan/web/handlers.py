import logging

from aiohttp import web
from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp.web_request import Request

from sarafan.magnet import is_magnet

log = logging.getLogger(__name__)


async def home(request):
    """Reader UI if enabled.

    :param request:
    :return:
    """
    return web.json_response({
        "todo": "UI"
    })


async def hello(request):
    """Hello page containing sarafan node metadata.

    `version` contains sarafan node version.
    `content_service_id` — contains service_id of content node

    :param request:
    :return:
    """
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
        log.warning("Respond with empty peer list: no peers received from application")
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


async def post_list(request):
    """List of posts.


    """
    return web.json_response({
        "result": [
            {
                "magnet": "123456",
                "content": "Markdown text",
            }
        ],
        "next_cursor": "ABas==",
    })


async def create_post(request):
    """Create post and estimate publication cost.
    """
    tmp_post_id = '%s.draft' % str(uuid4())
    base_path = PROJECT_ROOT / 'content' / 'drafts'
    filename = base_path / ('{}.draft'.format(tmp_post_id))
    with zipfile.ZipFile(filename, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        d = await request.json()
        markdown_content = d['text']
        content_json = {
            "version": "1.0",
            "text": markdown_content,
            "nonce": tmp_post_id,
        }
        archive.writestr('content.json', str(json.dumps(content_json)))
    checksum = keccak.new(digest_bytes=32)
    with open(filename, 'rb') as fp:
        chunk = fp.read(1024)
        while chunk:
            checksum.update(chunk)
            chunk = fp.read(1024)
    post_magnet = checksum.hexdigest()
    target_path = base_path / '{}.draft'.format(post_magnet)
    shutil.move(filename, target_path)
    # TODO: check if magnet is already exist
    size = os.path.getsize(target_path)
    return web.json_response({
        "magnet": post_magnet,
        "size": size,
        "cost": math.ceil(size / 1000000) + 1,
    })


async def publish(request: web.Request):
    """Publish created post.
    """
    d = await request.json()
    magnet = d['magnet']
    private_key = d['privateKey']
    base_path = PROJECT_ROOT / 'content' / 'drafts'
    target_path = base_path / '{}.draft'.format(magnet)
    await request.app['sarafan'].publish(target_path, magnet, private_key)
    return web.json_response({
        'status': 'queued'
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
            web.get('/', home),
            web.get('/publications', publications),
            web.get('/abuses', abuses),
            web.get('/awards', awards),
            web.get('/api/posts', post_list),
            web.post('/api/create_post', create_post),
            web.post('/api/publish', publish)
        ])
    return app
