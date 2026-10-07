import html

from controller import BUTTON_ORDER, CANNED, ViewState
from lambda_backend import Operation

LABELS = {
    Operation.LINT: "Lint",
    Operation.INTERPRET: "Interpret",
    Operation.TYPECHECK: "Type-check",
    Operation.COMPILE: "Compile",
    Operation.EXECUTE: "Execute",
}

STYLE = """
body { font-family: system-ui, sans-serif; margin: 1.5rem auto; max-width: 52rem; padding: 0 1rem; color: #111; background: #fff; }
h1 { font-size: 1.4rem; }
fieldset { margin: 0 0 1rem; border: 1px solid #888; padding: .5rem 1rem; }
textarea { width: 100%; min-height: 14rem; font-family: ui-monospace, monospace; font-size: .95rem; }
button { margin: .25rem .25rem .25rem 0; padding: .4rem .8rem; font-size: .95rem; }
button:disabled { color: #555; }
.reason { color: #333; font-size: .9rem; margin: .1rem 0 .4rem; }
.status { font-weight: bold; }
pre { white-space: pre-wrap; word-wrap: break-word; background: #f3f3f3; padding: .6rem; border: 1px solid #bbb; }
"""

DRAFT_SCRIPT = """
(function () {
  var editor = document.getElementById('editor');
  var timer = null;
  if (!editor) return;
  editor.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () {
      fetch('/draft', {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: new URLSearchParams({text: editor.value})});
    }, 300);
  });
})();
"""


def _attr(value) -> str:
    return html.escape(str(value), quote=True)


def _source_menu(state: ViewState) -> str:
    locked = state.busy is not None or state.has_pending
    disabled = " disabled" if locked else ""
    canned = "".join(
        f'<button type="submit" name="key" value="{_attr(key)}" formaction="/canned"{disabled}>'
        f"{html.escape(name)}</button>"
        for key, (name, _) in CANNED.items()
    )
    return f"""
<fieldset>
<legend>Load source</legend>
<form method="post" action="/upload" enctype="multipart/form-data">
  <label for="file">Choose a UTF-8 text file:</label>
  <input id="file" type="file" name="source" accept=".txt,.lam,text/plain"{disabled}>
  <button type="submit"{disabled}>Load file</button>
</form>
<form method="post" action="/manual">
  <button type="submit"{disabled}>Manual input</button>
</form>
<form method="post" action="/canned">
  {canned}
</form>
</fieldset>"""


def _editor(state: ViewState) -> str:
    if state.has_pending:
        text = state.pending_text
    else:
        text = state.applied_text or ""
    if state.applied_text is None and not state.has_pending:
        return ""
    apply_disabled = " disabled" if state.busy is not None else ""
    return f"""
<fieldset>
<legend>Editor</legend>
<form method="post" action="/apply">
  <label for="editor">Constructor expression:</label>
  <textarea id="editor" name="text" spellcheck="false">{html.escape(text)}</textarea>
  <button type="submit"{apply_disabled}>Apply changes</button>
</form>
<form method="post" action="/discard">
  <button type="submit"{apply_disabled}>Discard changes</button>
</form>
</fieldset>"""


def _actions(state: ViewState) -> str:
    buttons = []
    for button in state.buttons:
        label = LABELS[button.operation]
        disabled = "" if button.enabled else " disabled"
        buttons.append(
            f'<button type="submit" name="op" value="{_attr(button.operation.value)}"{disabled}>'
            f"{html.escape(label)}</button>"
        )
    reasons = "".join(
        f'<p class="reason">{html.escape(LABELS[b.operation])}: {html.escape(b.reason)}</p>'
        for b in state.buttons if not b.enabled and b.reason
    )
    return f"""
<fieldset>
<legend>Actions</legend>
<form method="post" action="/run">
  {''.join(buttons)}
</form>
{reasons}
</fieldset>"""


def _results(state: ViewState) -> str:
    if not state.results:
        return ""
    blocks = []
    for result in state.results:
        title = f"{LABELS[result.operation]} · revision {result.revision} · {result.status.value}"
        blocks.append(f"<h2>{html.escape(title)}</h2><pre>{html.escape(result.message)}</pre>")
    return f"<section><h1>Results</h1>{''.join(blocks)}</section>"


def render_page(state: ViewState, notice: str = "") -> str:
    name = state.source_name or "none"
    revision = state.revision
    status = (f"Busy: {LABELS[state.busy]} is running." if state.busy is not None
              else "Idle.")
    pending = " Unapplied edits present." if state.has_pending else ""
    refresh = '<meta http-equiv="refresh" content="1">' if state.busy is not None else ""
    shown = " ".join(part for part in (notice, state.message) if part)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{refresh}
<title>LAMBDA Front-End</title>
<style>{STYLE}</style>
</head>
<body>
<h1>LAMBDA Front-End</h1>
<p>Source: <strong>{html.escape(name)}</strong> · Revision: <strong>{revision}</strong></p>
<p class="status" role="status" aria-live="polite">{html.escape(status + pending)}</p>
<p role="status">{html.escape(shown)}</p>
{_source_menu(state)}
{_editor(state)}
{_actions(state)}
{_results(state)}
<script>{DRAFT_SCRIPT}</script>
</body>
</html>
"""
