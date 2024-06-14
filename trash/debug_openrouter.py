import socket

def check_connection(host="api.openrouter.ai", port=443):
    try:
        socket.create_connection((host, port), timeout=10)
        print(f"Connection to {host} on port {port} successful.")
    except socket.error as err:
        print(f"Connection to {host} on port {port} failed: {err}")

check_connection()
