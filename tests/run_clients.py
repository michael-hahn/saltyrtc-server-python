import os
import ssl
import umsgpack
import asyncio
import struct
import websockets
import libnacl.public

from saltyrtc.server import (
    NONCE_FORMATTER,
    NONCE_LENGTH,
    Event,
    Server,
    SubProtocol,
    serve,
    util,
)

from saltyrtc.server.common import (
    SIGNED_KEYS_CIPHERTEXT_LENGTH,
    ClientState,
    CloseCode,
)


saltyrtc_cert = os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir, os.pardir, 'saltyrtc.crt'))
saltyrtc_key = os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir, os.pardir, 'saltyrtc.key'))
saltyrtc_permanent_key = os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir, os.pardir, 'saltyrtc/server/permanent-key'))
saltyrtc_dh_params = os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir, 'dh2048.pem'))
saltyrtc_subprotocols = [SubProtocol.saltyrtc_v1.value]
saltyrtc_server_url = 'wss://localhost:8765'
saltyrtc_timeout = 1000000


def key_pair():
    """
    Return a NaCl key pair.
    """
    return libnacl.public.SecretKey()


def initiator_key():
    """
    Return a client NaCl key pair to be used by the initiator only.
    """
    return key_pair()


def responder_key():
    """
    Return a client NaCl key pair to be used by the responder only.
    """
    return key_pair()


def random_cookie():
    """
    Return a random cookie for the client.
    """
    return os.urandom(16)


def server_permanent_keys():
    """
    Return the server's permanent test NaCl key pairs.
    """
    return [
        util.load_permanent_key(saltyrtc_permanent_key),
    ]


def default_event_loop(request=None, config=None):
    # TODO: Currently, we use asyncio as the default loop for convenience,
    #  later we may use things like gevent
    # if request is not None:
    #     config = request.config
    # loop = config.getoption("--loop")
    # if loop == 'uvloop':
    #     import uvloop
    #     asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    # else:
    #     loop = 'asyncio'
    loop = 'asyncio'
    return loop


def event_loop(
        # request   # We do not use the 'request' fixture from pytest
):
    """
    Create an instance of the requested event loop.
    """
    # default_event_loop(request=request)
    default_event_loop()

    # Close previous event loop
    policy = asyncio.get_event_loop_policy()
    policy.get_event_loop().close()

    # Create new event loop
    _event_loop = policy.new_event_loop()
    policy.set_event_loop(_event_loop)

    def fin():
        _event_loop.close()

    # TODO: We need to add this finalizer somehow to our code, maybe.
    # Add finaliser and return new event loop
    # request.addfinalizer(fin)
    return _event_loop


def client_kwargs(
        # event_loop
        el  # Pass in the return value from event_loop()
):
    return {
        'compression': None,
        'subprotocols': saltyrtc_subprotocols,
        'ping_interval': None,
        # 'loop': event_loop,
        'loop': el,
    }


def key_path(key_pair):
    """
    Return the hexadecimal key path from a key pair using the public
    key.

    Arguments:
        - `key_pair`: A :class:`libnacl.public.SecretKey` instance.
    """
    return key_pair.hex_pk().decode()


# def _get_timeout(timeout=None, request=None, config=None):
def _get_timeout(timeout=None):
    """
    Return the defined timeout.
    """
    # NOTE: We are not gonna complicate this function,
    # so we will just return saltyrtc_timeout.
    if timeout is None:
        # timeout = pytest.saltyrtc.timeout
        timeout = saltyrtc_timeout
    # if request is not None:
    #     config = request.config
    # option_timeout = config.getoption("--timeout")
    # if option_timeout is not None:
    #     return max(timeout, float(option_timeout))
    # else:
    #     return timeout
    return timeout


# def pack_nonce():
#     def _pack_nonce(cookie, source, destination, combined_sequence_number):
def pack_nonce(cookie, source, destination, combined_sequence_number):
    return struct.pack(
        NONCE_FORMATTER,
        cookie,
        source, destination,
        struct.pack('!Q', combined_sequence_number)[2:]
    )


def pack_message(
        # request,  # We do not use the request fixture
        el          # Pass in the return value from event_loop
):
    async def _pack_message(client, nonce, message, box=None, timeout=None, pack=True):
        if pack:
            data = umsgpack.packb(message)
        else:
            data = message
        if box is not None:
            _, data = box.encrypt(data, nonce=nonce, pack_nonce=False)
        data = b''.join((nonce, data))
        # timeout = _get_timeout(timeout=timeout, request=request)
        timeout = _get_timeout(timeout=timeout)
        await asyncio.wait_for(client.send(data), timeout, loop=el)
        # await asyncio.wait_for(client.send(data), timeout, loop=event_loop)
        return data
    return _pack_message


def unpack_message(
        # request,  # We do not use the request fixture
        el          # Pass in the return value from event_loop
):
    async def _unpack_message(client, box=None, timeout=None):
        # timeout = _get_timeout(timeout=timeout, request=request)
        timeout = _get_timeout(timeout=timeout)
        # data = await asyncio.wait_for(client.recv(), timeout, loop=event_loop)
        data = await asyncio.wait_for(client.recv(), timeout, loop=el)
        nonce = data[:NONCE_LENGTH]
        (cookie,
         source, destination,
         combined_sequence_number) = struct.unpack(NONCE_FORMATTER, nonce)
        combined_sequence_number, *_ = struct.unpack(
            '!Q', b'\x00\x00' + combined_sequence_number)
        data = data[NONCE_LENGTH:]
        if box is not None:
            data = box.decrypt(data, nonce=nonce)
        else:
            nonce = None
        message = umsgpack.unpackb(data)
        return (
            message,
            nonce,
            cookie,
            source, destination,
            combined_sequence_number
        )
    return _unpack_message

class _DefaultBox:
    pass


class Client:
    def __init__(
            # self, ws_client, pack_message, unpack_message, request,
            self, ws_client, pack_msg, unpack_msg,  # pass in event loop
            timeout=None,
    ) -> None:
        self.ws_client = ws_client
        self.pack_and_send = pack_msg
        self.recv_and_unpack = unpack_msg
        self.timeout = _get_timeout(timeout=timeout)
        self.session_key = None
        self.box = None

    async def send(self, nonce, message, box=_DefaultBox, timeout=None, pack=True):
        if timeout is None:
            timeout = self.timeout
        return await self.pack_and_send(
            self.ws_client, nonce, message,
            box=self.box if box == _DefaultBox else box, timeout=timeout, pack=pack
        )

    async def recv(self, box=_DefaultBox, timeout=None):
        if timeout is None:
            timeout = self.timeout
        return await self.recv_and_unpack(
            self.ws_client,
            box=self.box if box == _DefaultBox else box, timeout=timeout
        )

    def close(self):
        return self.ws_client.close()


def client_factory(
        # request,          # We do not use pytest's request fixture
        # initiator_key,    # We rename it to init_key
        init_key,
        # event_loop,       # We rename it to el
        el,
        # client_kwargs,    # We rename it to c_kwargs
        # server,
        # server_permanent_keys,    # We call it directly
        # responder_key,    # We rename it to r_key
        resp_key
        # pack_nonce,       # We call it directly
        # pack_message,     # We rename it to p_message
        # unpack_message    # We rename it to u_message
):
    """
    Return a simplified :class:`websockets.client.connect` wrapper
    where no parameters are required.
    """
    # Note: The `server` argument is only required to fire up the server.
    # server_ = server

    # Create SSL context
    ssl_context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH, cafile=saltyrtc_cert)
    ssl_context.load_dh_params(saltyrtc_dh_params)

    async def _client_factory(
            # server=None,
            ws_client=None,
            path=init_key,
            # path=initiator_key,
            timeout=None,
            csn=None,
            cookie=None,
            permanent_key=None,
            ping_interval=None,
            explicit_permanent_key=False,
            initiator_handshake=False,
            responder_handshake=False,
            **kwargs
    ):
        # if server is None:
        #     server = server_
        if cookie is None:
            cookie = random_cookie()
        if permanent_key is None:
            permanent_key = server_permanent_keys()[0].pk
        c_kwargs = client_kwargs(el)
        # _kwargs = client_kwargs.copy()
        _kwargs = c_kwargs.copy()
        _kwargs.update(kwargs)
        if ws_client is None:
            ws_client = await websockets.connect(
                # '{}/{}'.format(url(*server.address), key_path(path)),
                '{}/{}'.format(saltyrtc_server_url, key_path(path)),
                ssl=ssl_context, **_kwargs
            )
        p_message = pack_message(el)
        u_message = unpack_message(el)
        client = Client(
            # ws_client, pack_message, unpack_message,
            ws_client, p_message, u_message,
            # request, timeout=timeout
            timeout=timeout
        )
        nonces = {}

        if not initiator_handshake and not responder_handshake:
            return client

        # Do handshake
        # key = initiator_key if initiator_handshake else responder_key
        key = init_key if initiator_handshake else resp_key

        # server-hello
        message, nonce, sck, s, d, start_scsn = await client.recv()
        ssk = message['key']
        nonces['server-hello'] = nonce

        cck, ccsn = cookie, 2 ** 32 - 1 if csn is None else csn
        if responder_handshake:
            # client-hello
            nonce = pack_nonce(cck, 0x00, 0x00, ccsn)
            nonces['client-hello'] = nonce
            await client.send(nonce, {
                'type': 'client-hello',
                # 'key': responder_key.pk,
                'key': resp_key.pk,
            })
            ccsn += 1

        # client-auth
        client.box = libnacl.public.Box(sk=key, pk=ssk)
        nonce = pack_nonce(cck, 0x00, 0x00, ccsn)
        nonces['client-auth'] = nonce
        payload = {
            'type': 'client-auth',
            'your_cookie': sck,
            # 'subprotocols': pytest.saltyrtc.subprotocols,
            'subprotocols': saltyrtc_subprotocols,
        }
        if ping_interval is not None:
            payload['ping_interval'] = ping_interval
        if explicit_permanent_key is not None:
            payload['your_key'] = permanent_key
        await client.send(nonce, payload)
        ccsn += 1

        # server-auth
        client.sign_box = libnacl.public.Box(sk=key, pk=permanent_key)
        message, nonce, ck, s, d, scsn = await client.recv()
        nonces['server-auth'] = nonce

        # Return client and additional data
        additional_data = {
            'id': d,
            'sck': sck,
            'start_scsn': start_scsn,
            'cck': cck,
            'ccsn': ccsn,
            'ssk': ssk,
            'nonces': nonces,
            'signed_keys': message['signed_keys']
        }
        if initiator_handshake:
            additional_data['responders'] = message['responders']
        else:
            additional_data['initiator_connected'] = message['initiator_connected']
        return client, additional_data
    return _client_factory


async def test_client_factory_handshake(
    # server, client_factory, initiator_key, responder_key
    el
):
    """
    We do a complete handshake using the client factory.
    """
    init_key = initiator_key()
    resp_key = responder_key()
    # Initiator handshake
    initiator_factory = client_factory(init_key, el, resp_key)
    # initiator, i = await client_factory(initiator_handshake=True)
    initiator, i = await initiator_factory(initiator_handshake=True)
    assert len(i['signed_keys']) == SIGNED_KEYS_CIPHERTEXT_LENGTH
    signed_keys = initiator.sign_box.decrypt(
        i['signed_keys'], nonce=i['nonces']['server-auth'])
    # assert signed_keys == i['ssk'] + initiator_key.pk
    # assert signed_keys == i['ssk'] + init_key.pk
    await initiator.close()

    # Responder handshake
    responder_factory = client_factory(init_key, el, resp_key)
    # responder, r = await client_factory(responder_handshake=True)
    responder, r = await responder_factory(responder_handshake=True)
    assert len(r['signed_keys']) == SIGNED_KEYS_CIPHERTEXT_LENGTH
    signed_keys = responder.sign_box.decrypt(
        r['signed_keys'], nonce=r['nonces']['server-auth'])
    # assert signed_keys == r['ssk'] + responder_key.pk
    # assert signed_keys == r['ssk'] + resp_key.pk
    await responder.close()
    # await server.wait_connections_closed()


async def main():
    # el = event_loop()
    tasks = []

    for i in range(200):
        tasks.append(test_client_factory_handshake(asyncio.get_event_loop()))

    await asyncio.gather(*tasks)
    # el.close()

if __name__ == '__main__':
    # el = event_loop()
    # el.run_until_complete(test_client_factory_handshake(el))
    # el.close()
    asyncio.run(main())
