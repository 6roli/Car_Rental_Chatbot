import http.server
import socketserver
from urllib.parse import urlparse
import os

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/chat":
            # Here, you can call your app.py logic to get chat response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"message": "Hello from the backend"}')
        else:
            super().do_GET()  # Handle other file requests (like index.html)

PORT = 8000
Handler = MyHandler
httpd = socketserver.TCPServer(("", PORT), Handler)
print("serving at port", PORT)
httpd.serve_forever()


# In server.py
from app import get_chat_response  # assuming you have this function in app.py

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/chat":
            # Call the function in app.py
            response = get_chat_response()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(response.encode())  # Ensure response is in bytes
        else:
            super().do_GET()
