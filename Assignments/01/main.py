import sys
import os
import signal
import socket
from urllib.parse import urlparse

MAX_CHILDREN = 100   # max processes we'll spawn
BUFFER_SIZE = 4096   # bytes per recv call
BACKLOG = 50         # max queued connections
DEFAULT_HTTP_PORT = 80
CRLF = "\r\n"

active_children = 0  # tracks how many children are alive

def sigchld_handler(signum, frame):
    # reap any zombie children without blocking
    global active_children
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break
            active_children -= 1
            print(f"[proxy] child {pid} finished  (active: {active_children})")
        except ChildProcessError:
            break

def send_error(client_sock, code, reason, body_text=None):
    # build a simple HTML error page and send it back
    if body_text is None:
        body_text = f"<html><body><h1>{code} {reason}</h1></body></html>"
    body_bytes = body_text.encode("utf-8")
    header = (
        f"HTTP/1.0 {code} {reason}{CRLF}"
        f"Content-Type: text/html{CRLF}"
        f"Content-Length: {len(body_bytes)}{CRLF}"
        f"Connection: close{CRLF}"
        f"{CRLF}"
    )
    try:
        client_sock.sendall(header.encode("utf-8") + body_bytes)
        print(f"[proxy] sent error response: {code} {reason}")
    except OSError:
        pass

def parse_request(raw_request: str):
    lines = raw_request.split("\r\n")

    # skip any leading blank lines (some clients send a stray CRLF first)
    while lines and not lines[0].strip():
        lines.pop(0)

    if not lines:
        raise ValueError((400, "Bad Request"))

    # first line must be:  METHOD URI HTTP/version
    request_line = lines[0].strip()
    parts = request_line.split()
    if len(parts) != 3:
        raise ValueError((400, "Bad Request"))

    method, uri, version = parts

    if not version.startswith("HTTP/"):
        raise ValueError((400, "Bad Request"))

    # we only support GET
    if method == "CONNECT":
        # browser uses CONNECT for HTTPS tunneling - we don't support it
        raise ValueError((501, "Not Implemented"))
    if method != "GET":
        raise ValueError((501, "Not Implemented"))

    # uri must be an absolute http URL
    parsed = urlparse(uri)
    if parsed.scheme.lower() not in ("http", ""):
        raise ValueError((400, "Bad Request"))
    if not parsed.hostname:
        raise ValueError((400, "Bad Request"))

    host = parsed.hostname
    port = parsed.port if parsed.port else DEFAULT_HTTP_PORT
    path = parsed.path if parsed.path else "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    # validate every header line has a colon
    header_lines = []
    for line in lines[1:]:
        if line == "":
            break
        if ":" not in line:
            raise ValueError((400, "Bad Request"))
        header_lines.append(line)

    return method, host, port, path, version, header_lines

def build_server_request(host, port, path, header_lines):
    # build a clean HTTP/1.0 request to forward to the origin server
    request = f"GET {path} HTTP/1.0{CRLF}"

    has_host = False
    for hdr in header_lines:
        name, _, value = hdr.partition(":")
        name_lower = name.strip().lower()
        if name_lower == "host":
            has_host = True
            request += f"{hdr}{CRLF}"
        elif name_lower in ("connection", "proxy-connection"):
            continue  # strip these, we'll add our own
        else:
            request += f"{hdr}{CRLF}"

    # add Host header if browser didn't include one
    if not has_host:
        request += f"Host: {host}:{port}{CRLF}" if port != 80 else f"Host: {host}{CRLF}"

    request += f"Connection: close{CRLF}"
    request += CRLF
    return request

def handle_client(client_sock, client_addr):
    pid = os.getpid()
    try:
        # give the client 5 seconds to send its request
        client_sock.settimeout(5)

        # read until we get the full headers
        raw_data = b""
        while True:
            try:
                chunk = client_sock.recv(BUFFER_SIZE)
            except socket.timeout:
                print(f"[{pid}] timeout waiting for data from {client_addr[0]}")
                client_sock.close()
                return
            if not chunk:
                break
            raw_data += chunk
            if b"\r\n\r\n" in raw_data:
                break

        if not raw_data:
            print(f"[{pid}] client {client_addr[0]} sent empty request, ignoring")
            client_sock.close()
            return

        raw_request = raw_data.decode("utf-8", errors="replace")

        # parse and validate the request
        try:
            method, host, port, path, version, header_lines = parse_request(raw_request)
        except ValueError as e:
            code, reason = e.args[0]
            # print the first line so we can see exactly what the client sent
            first_line = raw_request.split("\r\n")[0][:120]
            print(f"[{pid}] {code} {reason} from {client_addr[0]}  |  received: {repr(first_line)}")
            send_error(client_sock, code, reason)
            client_sock.close()
            return

        print(f"[{pid}] {client_addr[0]}:{client_addr[1]}  GET http://{host}:{port}{path}")

        # connect to the origin server
        print(f"[{pid}] connecting to {host}:{port} ...")
        try:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.settimeout(10)
            server_sock.connect((host, port))
            print(f"[{pid}] connected to {host}:{port}")
        except (socket.error, OSError) as e:
            print(f"[{pid}] could not reach {host}:{port} -> {e}")
            send_error(client_sock, 502, "Bad Gateway",
                       f"<html><body><h1>502 Bad Gateway</h1>"
                       f"<p>Could not connect to {host}:{port} — {e}</p></body></html>")
            client_sock.close()
            return

        # forward the request
        outgoing = build_server_request(host, port, path, header_lines)
        try:
            server_sock.sendall(outgoing.encode("utf-8"))
            print(f"[{pid}] request forwarded to {host}")
        except OSError as e:
            print(f"[{pid}] failed to send request to {host} -> {e}")
            send_error(client_sock, 502, "Bad Gateway")
            server_sock.close()
            client_sock.close()
            return

        # stream the response back to the client
        total_bytes = 0
        try:
            while True:
                data = server_sock.recv(BUFFER_SIZE)
                if not data:
                    break
                client_sock.sendall(data)
                total_bytes += len(data)
        except OSError:
            pass

        print(f"[{pid}] done  —  {total_bytes} bytes sent back to {client_addr[0]}")
        server_sock.close()
        client_sock.close()

    except Exception as e:
        print(f"[{pid}] unexpected error for {client_addr}: {e}", file=sys.stderr)
        try:
            send_error(client_sock, 500, "Internal Server Error")
            client_sock.close()
        except OSError:
            pass

def main():
    global active_children

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>")
        sys.exit(1)

    try:
        port = int(sys.argv[1])
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        print("Error: port must be an integer between 1 and 65535.")
        sys.exit(1)

    # clean up finished children automatically
    signal.signal(signal.SIGCHLD, sigchld_handler)

    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listen_sock.bind(("", port))
    except OSError as e:
        print(f"Error: could not bind to port {port} -> {e}")
        print("Tip: port < 1024 needs sudo, or the port is already in use.")
        sys.exit(1)
    listen_sock.listen(BACKLOG)

    # figure out the WSL / LAN IP so we can print the right address for Windows
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except OSError:
        local_ip = "127.0.0.1"

    print("=" * 55)
    print(f"  HTTP Proxy started on port {port}")
    print(f"  Max concurrent clients : {MAX_CHILDREN}")
    print()
    print(f"  Linux / same-machine:  127.0.0.1:{port}")
    print(f"  Windows (WSL) browser: {local_ip}:{port}")
    print("=" * 55)
    print("Waiting for connections...\n")

    while True:
        try:
            client_sock, client_addr = listen_sock.accept()
        except InterruptedError:
            # happens when SIGCHLD interrupts accept(), just retry
            continue

        print(f"[proxy] new connection from {client_addr[0]}:{client_addr[1]}  (active children: {active_children})")

        # too many children running already
        if active_children >= MAX_CHILDREN:
            print(f"[proxy] too many connections, rejecting {client_addr[0]}")
            send_error(client_sock, 503, "Service Unavailable",
                       "<html><body><h1>503 Service Unavailable</h1>"
                       "<p>Too many concurrent connections.</p></body></html>")
            client_sock.close()
            continue

        pid = os.fork()

        if pid == 0:
            # child: handle this one client then exit
            listen_sock.close()
            handle_client(client_sock, client_addr)
            os._exit(0)
        else:
            # parent: keep accepting new connections
            active_children += 1
            client_sock.close()
            print(f"[proxy] forked child {pid}  (active: {active_children})")

if __name__ == "__main__":
    main()
