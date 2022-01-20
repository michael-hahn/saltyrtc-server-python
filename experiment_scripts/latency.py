from datetime import datetime

def get_time_from_log(log_path):
    """Extract time information from the log file"""
    server_handshake_start_time = None     # time to start the handshake with the server
    server_handshake_end_time = None       # time when server handshake is done
    peer_handshake_start_time = None       # time to start the handshake with the peer
                                           # If responder, this value will remain None
    peer_handshake_end_time = None         # time when peer handshake is done
    with open(log_path, 'r') as log:
        for line in log:
            # A line will look like this:
            # 2022-01-20T00:51:45.283 [WARN ] Connected to server as Initiator (src/lib.rs:474)
            # We split it into 4 parts:
            # 1. datetime: 2022-01-20T00:51:45.283
            # 2. [WARN
            # 3. ]
            # 4. Connected to server as Initiator (src/lib.rs:474)
            data = line.split(" ", 3)
            time = data[0]
            content = data[3].strip()
            if content.startswith("Connected to server as Initiator"):
                server_handshake_start_time = datetime.fromisoformat(time)
            elif content.startswith("Connected to server as Responder"):
                server_handshake_start_time = datetime.fromisoformat(time)
            elif content.startswith("Server handshake completed"):
                server_handshake_end_time = datetime.fromisoformat(time)
            elif content.startswith("Registering new responder"):
                peer_handshake_start_time = datetime.fromisoformat(time)
            elif content.startswith("Peer handshake done"):
                peer_handshake_end_time = datetime.fromisoformat(time)
    return {'server_start': server_handshake_start_time,
            'server_end': server_handshake_end_time,
            'peer_start': peer_handshake_start_time,
            'peer_end': peer_handshake_end_time}

