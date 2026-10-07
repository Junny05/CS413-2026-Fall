import http.client
import threading
import time
import uuid
from urllib.parse import unquote, urlsplit

import pytest

import lambda_backend
from app import MAX_REQUEST_BYTES, make_server
from controller import Controller
from model import MAX_SOURCE_BYTES, SourceModel
from samples import FACTORIAL


@pytest.fixture
def server():
    controller = Controller(SourceModel(), lambda_backend)
    httpd = make_server(controller, port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd, controller
    httpd.shutdown()
    httpd.server_close()


def send(httpd, method, path, body=b"", headers=None):
    host, port = httpd.server_address
    conn = http.client.HTTPConnection(host, port, timeout=10)
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    data = response.read().decode("utf-8")
    location = response.getheader("Location")
    conn.close()
    return response.status, location, data


def form(httpd, path, **fields):
    from urllib.parse import urlencode
    body = urlencode(fields).encode("utf-8")
    return send(httpd, "POST", path, body,
                {"Content-Type": "application/x-www-form-urlencoded",
                 "Content-Length": str(len(body))})


def upload(httpd, filename, data: bytes):
    boundary = uuid.uuid4().hex
    head = (f'--{boundary}\r\nContent-Disposition: form-data; name="source"; '
            f'filename="{filename}"\r\nContent-Type: text/plain\r\n\r\n').encode("utf-8")
    body = head + data + f"\r\n--{boundary}--\r\n".encode("utf-8")
    return send(httpd, "POST", "/upload", body, {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
    })


def notice_of(location):
    query = urlsplit(location).query
    return unquote(query.split("=", 1)[1].replace("+", " ")) if query else ""


def wait_idle(controller, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if controller.snapshot().busy is None:
            return
        time.sleep(0.02)
    raise AssertionError("operation did not finish")


def test_server_binds_loopback_only():
    controller = Controller(SourceModel(), lambda_backend)
    with pytest.raises(ValueError, match="loopback"):
        make_server(controller, host="0.0.0.0", port=0)


def test_index_page_shows_menu_and_disabled_execute(server):
    httpd, _ = server
    status, _, page = send(httpd, "GET", "/")
    assert status == 200
    assert "Manual input" in page
    assert "Factorial (canned)" in page and "Fibonacci (canned)" in page
    assert 'value="execute" disabled' in page
    assert 'value="lint"' in page and 'value="interpret"' in page


def test_load_factorial_then_lint_and_interpret(server):
    httpd, controller = server
    status, location, _ = form(httpd, "/canned", key="factorial")
    assert status == 303 and location == "/"
    _, _, page = send(httpd, "GET", "/")
    assert "Revision: <strong>1</strong>" in page

    form(httpd, "/run", op="interpret")
    wait_idle(controller)
    _, _, page = send(httpd, "GET", "/")
    assert "D0Vint(arg1=120)" in page


def test_open_expression_lint_then_fixed_expression_passes(server):
    httpd, controller = server
    form(httpd, "/manual")
    form(httpd, "/apply", text='D0Evar("x")')
    form(httpd, "/run", op="lint")
    wait_idle(controller)
    _, _, page = send(httpd, "GET", "/")
    assert "Undeclared variable(s): x" in page

    form(httpd, "/apply", text='D0Elet("x", D0Eint(1), D0Evar("x"))')
    form(httpd, "/run", op="lint")
    wait_idle(controller)
    _, _, page = send(httpd, "GET", "/")
    assert "No free variables found." in page


def test_html_like_source_and_output_are_escaped(server):
    httpd, controller = server
    form(httpd, "/manual")
    form(httpd, "/apply", text='D0Evar("<b>x</b>")')
    form(httpd, "/run", op="lint")
    wait_idle(controller)
    _, _, page = send(httpd, "GET", "/")
    assert "<b>x</b>" not in page
    assert "&lt;b&gt;x&lt;/b&gt;" in page


def test_invalid_utf8_upload_is_rejected_and_previous_source_kept(server):
    httpd, controller = server
    form(httpd, "/canned", key="factorial")
    status, location, _ = upload(httpd, "bad.lam", b"\xff\xfe\x00")
    assert status == 303
    assert "not valid UTF-8" in notice_of(location)
    assert controller.snapshot().applied_text is not None
    assert controller.snapshot().revision == 1


def test_valid_upload_creates_revision_with_filename(server):
    httpd, controller = server
    status, location, _ = upload(httpd, "program.lam", b'D0Eint(7)')
    assert location == "/"
    state = controller.snapshot()
    assert state.source_name == "program.lam"
    assert state.applied_text == "D0Eint(7)"


def test_empty_upload_is_rejected(server):
    httpd, controller = server
    _, location, _ = upload(httpd, "empty.lam", b"  \n ")
    assert "empty" in notice_of(location)
    assert controller.snapshot().applied_text is None


def test_rejected_edit_keeps_text_for_correction(server):
    httpd, controller = server
    form(httpd, "/canned", key="factorial")
    _, location, _ = form(httpd, "/apply", text="   ")
    assert "empty" in notice_of(location)
    state = controller.snapshot()
    assert state.applied_text is not None and state.pending_text == "   "
    _, _, page = send(httpd, "GET", "/")
    assert "Unapplied edits present." in page


def test_draft_blocks_source_replacement_and_tool_actions(server):
    httpd, controller = server
    form(httpd, "/canned", key="factorial")
    status, _, _ = send(httpd, "POST", "/draft", b"text=unapplied", {
        "Content-Type": "application/x-www-form-urlencoded", "Content-Length": "14"})
    assert status == 204
    _, location, _ = form(httpd, "/canned", key="fibonacci")
    assert "Apply or discard" in notice_of(location)
    _, location, _ = form(httpd, "/run", op="lint")
    assert "Apply or discard" in notice_of(location)


def test_discard_restores_applied_source(server):
    httpd, controller = server
    form(httpd, "/canned", key="factorial")
    send(httpd, "POST", "/draft", b"text=changed", {
        "Content-Type": "application/x-www-form-urlencoded", "Content-Length": "12"})
    form(httpd, "/discard")
    state = controller.snapshot()
    assert state.pending_text is None
    assert state.applied_text is not None and "fact" in state.applied_text


def test_execute_action_is_refused(server):
    httpd, _ = server
    form(httpd, "/canned", key="factorial")
    _, location, _ = form(httpd, "/run", op="execute")
    assert "Compile" in notice_of(location)


def test_unknown_action_and_route_are_refused(server):
    httpd, _ = server
    _, location, _ = form(httpd, "/run", op="drop_tables")
    assert "Unknown action" in notice_of(location)
    _, location, _ = form(httpd, "/nope")
    assert "Unknown route" in notice_of(location)


def test_quote_heavy_edit_at_limit_is_accepted(server):
    httpd, controller = server
    form(httpd, "/manual")
    text = '"' * MAX_SOURCE_BYTES
    _, location, _ = form(httpd, "/apply", text=text)
    assert notice_of(location) == ""
    assert controller.snapshot().applied_text == text


def test_quote_heavy_edit_over_limit_gets_size_notice(server):
    httpd, controller = server
    form(httpd, "/canned", key="factorial")
    text = '"' * (MAX_SOURCE_BYTES + 1)
    status, location, _ = form(httpd, "/apply", text=text)
    assert status == 303
    assert "64 KiB limit" in notice_of(location)
    assert controller.snapshot().applied_text == FACTORIAL


def test_request_beyond_form_cap_gets_size_notice(server):
    httpd, _ = server
    body = b"x" * (MAX_REQUEST_BYTES + 1)
    status, location, _ = send(httpd, "POST", "/apply", body, {
        "Content-Type": "application/x-www-form-urlencoded",
        "Content-Length": str(len(body))})
    assert status == 303
    assert "64 KiB limit" in notice_of(location)


def test_status_endpoint_reports_busy_until_done(server):
    httpd, controller = server
    form(httpd, "/canned", key="fibonacci")
    form(httpd, "/run", op="interpret")
    _, _, status_body = send(httpd, "GET", "/status")
    wait_idle(controller)
    _, _, final = send(httpd, "GET", "/status")
    assert '"busy": false' in final
    assert status_body in ('{"busy": true}', '{"busy": false}')


def test_busy_flag_is_exposed_to_page_script(server):
    httpd, controller = server
    form(httpd, "/canned", key="fibonacci")
    form(httpd, "/run", op="interpret")
    _, _, page = send(httpd, "GET", "/")
    wait_idle(controller)
    _, _, final = send(httpd, "GET", "/")
    assert 'data-busy="false"' in final
    assert 'http-equiv="refresh"' not in final
    assert "D0Vint(arg1=55)" in final
