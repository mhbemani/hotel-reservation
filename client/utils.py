# محتویات client/utils.py
import socket
import json

# می‌توانید مقادیر را از config.json هم بخوانید
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8000

def send_request(sock, action, params=None):
    """
    ارسال یک درخواست JSON به سرور و دریافت پاسخ دیکدشده.
    """
    req = {'action': action}
    if params is not None:
        req['params'] = params
    raw = json.dumps(req).encode('utf-8') + b"\n"
    sock.sendall(raw)
    # دریافت تا اولین newline
    buffer = b''
    while b"\n" not in buffer:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buffer += chunk
    return json.loads(buffer.decode('utf-8').strip())


