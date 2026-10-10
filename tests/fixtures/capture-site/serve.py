import http.server, functools, sys
class Handler(http.server.SimpleHTTPRequestHandler):
   def do_POST(self):
      self.rfile.read(int(self.headers.get("content-length", 0)))
      return self.do_GET()
http.server.ThreadingHTTPServer(("127.0.0.1", 8765), functools.partial(Handler, directory=sys.argv[1])).serve_forever()
