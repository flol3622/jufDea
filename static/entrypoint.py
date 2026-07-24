"""Install the browser runtime, build the UI, and mount NiceGUI."""

import micropip  # type: ignore
from js import window  # type: ignore

window.console.log("JufDea: installing browser packages")
await micropip.install("nicegui-3.14.0-py3-none-any.whl", deps=False)  # type: ignore  # noqa: F704, PLE1142
await micropip.install("nicegui_pyodide-0.1.1-py3-none-any.whl", deps=False)  # type: ignore  # noqa: F704, PLE1142
await micropip.install(  # type: ignore  # noqa: F704, PLE1142
    ["typing-extensions", "markdown2", "Pygments", "docutils", "tinycss2"]
)
window.console.log("JufDea: browser packages installed")

from app import client  # noqa: E402, I001
from nicegui_pyodide import PyodideRuntime  # noqa: E402

loading = window.document.getElementById("loading")
if loading:
    loading.style.display = "none"

runtime = PyodideRuntime(client)
await runtime.mount()  # type: ignore  # noqa: F704, PLE1142
window.__pyodide_ready = True  # type: ignore
window.console.log("JufDea: ready")
