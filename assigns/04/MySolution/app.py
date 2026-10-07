import email.policy
import sys
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit

import lambda_backend
from controller import Controller
from lambda_backend import Operation
from model import MAX_SOURCE_BYTES, ModelError, SourceModel
from view import render_page

HOST = "127.0.0.1"
PORT = 8000
MAX_REQUEST_BYTES = MAX_SOURCE_BYTES + 16 * 1024
OPERATIONS = {op.value: op for op in Operation}


def make_handler(controller: Controller):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parts = urlsplit(self.path)
            if parts.path != "/":
                return self._send(404, "Not found", "text/plain; charset=utf-8")
            notice = parse_qs(parts.query).get("notice", [""])[0]
            self._send(200, render_page(controller.snapshot(), notice), "text/html; charset=utf-8")

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_REQUEST_BYTES:
                return self._send(413, "Request is too large.", "text/plain; charset=utf-8")
            body = self.rfile.read(length)
            path = urlsplit(self.path).path
            if path == "/draft":
                return self._draft(body)
            try:
                self._dispatch(path, body)
                notice = ""
            except (ModelError, ValueError) as e:
                notice = str(e)
            self._redirect(notice)

        def _dispatch(self, path: str, body: bytes) -> None:
            fields = _fields(body)
            if path == "/upload":
                filename, data = _multipart_file(self.headers.get("Content-Type", ""), body)
                controller.load_upload(filename, data)
            elif path == "/canned":
                controller.load_canned(fields.get("key", ""))
            elif path == "/manual":
                controller.open_manual()
            elif path == "/apply":
                if "text" in fields:
                    controller.edit(fields["text"])
                controller.apply_changes()
            elif path == "/discard":
                controller.discard_changes()
            elif path == "/run":
                operation = OPERATIONS.get(fields.get("op", ""))
                if operation is None:
                    raise ValueError("Unknown action.")
                controller.run(operation)
            else:
                raise ValueError("Unknown route.")

        def _draft(self, body: bytes):
            try:
                controller.edit(_fields(body).get("text", ""))
                status = 204
            except ModelError:
                status = 409
            self._send(status, "", "text/plain; charset=utf-8")

        def _redirect(self, notice: str):
            location = "/" + (f"?notice={quote(notice)}" if notice else "")
            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _send(self, status: int, body: str, content_type: str):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format, *args):
            return

    return Handler


def _fields(body: bytes) -> dict[str, str]:
    parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
    return {key: values[0] for key, values in parsed.items()}


def _multipart_file(content_type: str, body: bytes) -> tuple[str, bytes]:
    if not content_type.startswith("multipart/form-data"):
        raise ValueError("Expected a file upload.")
    raw = b"Content-Type: " + content_type.encode("latin-1") + b"\r\n\r\n" + body
    message = BytesParser(policy=email.policy.HTTP).parsebytes(raw)
    for part in message.iter_parts():
        if part.get_param("name", header="content-disposition") == "source":
            filename = part.get_filename() or "uploaded.txt"
            return filename, part.get_payload(decode=True) or b""
    raise ValueError("No file was selected.")


def make_server(controller: Controller, host: str = HOST, port: int = PORT) -> ThreadingHTTPServer:
    if host not in ("127.0.0.1", "localhost"):
        raise ValueError("The server binds to the loopback interface only.")
    return ThreadingHTTPServer((host, port), make_handler(controller))


def main() -> int:
    controller = Controller(SourceModel(), lambda_backend)
    server = make_server(controller)
    print(f"LAMBDA front-end at http://{HOST}:{server.server_address[1]}/ (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
