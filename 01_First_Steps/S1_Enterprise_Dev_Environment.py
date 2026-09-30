# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo==0.23.16",
#     "python-dotenv>=1.2",
#     "litellm>=1.90",
# ]
# ///

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="Enterprise Dev Environment")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md(r"""
    # Enterprise Dev Environment

    ---
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 🏗️ Build | 🚢 Ship | 📤 Share

    ### 🏗️ Build
    A working picture of what your machine and your network actually allow —
    as evidence, not assumption — and your first model call through a
    provider-agnostic client.

    ### 🚢 Ship
    Record your egress probe results in `NETWORK.md` and commit it. It is the
    one artifact from this notebook that outlives the session.

    ### 📤 Share
    Tell one colleague what your network does to outbound TLS. Most people
    who work there do not know.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    Most setup guides assume your laptop is yours. Yours probably is not.
    There is a proxy you did not configure, a certificate authority you did
    not install, and a policy that will block something on Thursday.

    None of that is a problem yet. It becomes one the day a model download
    fails, or the day you try to deploy. So we find out now, while finding out
    is cheap.

    This notebook does not fix anything. It produces **evidence** — the kind
    you can put in front of an infrastructure team. The fixes, where fixes
    exist, are in the
    [prerequisites](../../00_Prerequisites/1_Your_Machine/README.md#-if-its-blocked).

    > **Nothing installed yet?** Stop and do the
    > [prerequisites](../../00_Prerequisites/README.md) first. This notebook
    > audits a machine that is already set up; on an empty one it just tells
    > you everything is missing, which you knew.

    **Estimated time:** 40–50 minutes — 25 for Tasks 1–4, 15 for the
    `CLAUDE.md` drill in Task 5.

    ---
    ## Setup
    """)
    return


@app.cell
def _(mo):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(mo.notebook_dir()).parent))
    from helpers import nb, ui

    CFG = nb.bootstrap()
    print(f"✅ repo root: {CFG.root.name}")
    print(f"✅ model:     {CFG}")
    return CFG, nb, ui


@app.cell
def _(mo):
    mo.md(r"""
    ---
    ## Task 1 — What is actually installed

    Version numbers are boring right up until one of them is the reason
    nothing works. Shell out and ask, rather than trusting what you
    installed last year.
    """)
    return


@app.cell
def _(ui):
    import shutil
    import subprocess

    TOOLS = [
        ("python", ["--version"]),
        ("uv", ["--version"]),
        ("git", ["--version"]),
        ("docker", ["--version"]),
        ("claude", ["--version"]),
        ("code", ["--version"]),
    ]

    def _probe(name, args):
        path = shutil.which(name)
        if not path:
            return {"tool": name, "found": "✗", "version": "not on PATH"}
        try:
            out = subprocess.run(
                [path, *args], capture_output=True, text=True, timeout=20
            )
            first = (out.stdout or out.stderr).strip().splitlines()
            return {"tool": name, "found": "✓", "version": first[0] if first else "?"}
        except Exception as exc:  # a tool that hangs is also a finding
            return {"tool": name, "found": "✗", "version": f"{type(exc).__name__}"}

    versions = [_probe(name, args) for name, args in TOOLS]
    ui.table(versions, title="Toolchain")
    return


@app.cell
def _(mo):
    mo.md(r"""
    Anything marked `✗` is a real gap — go install it before the next
    session. `code` missing only means the shell command was not installed;
    VS Code itself may be fine.

    ---
    ## Task 2 — What your network allows

    This is the important cell in this notebook.

    We open a TLS connection to each host this work depends on and report
    four things: whether it resolves, whether it connects, **who signed the
    certificate**, and what the server said.

    That third one is the interesting one. If the issuer is your employer
    rather than a public certificate authority, your traffic is being
    intercepted and re-signed by a corporate proxy. That is normal, it is
    usually fine, and it explains a whole category of errors you would
    otherwise spend a day on.
    """)
    return


@app.cell
def _(ui):
    import os
    import socket
    import ssl

    HOSTS = [
        ("pypi.org", "Python packages"),
        ("api.openai.com", "the model API"),
        ("cdn.jsdelivr.net", "the CDN most web frontends load from"),
        ("huggingface.co", "open model weights"),
        ("registry-1.docker.io", "container images"),
        ("github.com", "this repository"),
    ]

    def _issuer(cert) -> str:
        if not cert:
            return "unknown (session reused or no cert exposed)"
        for field in cert.get("issuer", ()):
            for key, value in field:
                if key == "organizationName":
                    return value
        return "unknown"

    def _check(host: str, why: str) -> dict:
        row = {"host": host, "why": why, "dns": "✗", "tls": "✗", "signed by": ""}
        try:
            row["ip"] = socket.gethostbyname(host)
            row["dns"] = "✓"
        except Exception as exc:
            row["ip"] = f"{type(exc).__name__}"
            return row
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((host, 443), timeout=8) as raw:
                with ctx.wrap_socket(raw, server_hostname=host) as tls:
                    row["tls"] = "✓"
                    row["signed by"] = _issuer(tls.getpeercert())
        except Exception as exc:
            row["signed by"] = f"{type(exc).__name__}: {exc}"[:60]
        return row

    # Concurrently, not one after another. On an open network the difference is
    # a second. On a network that silently drops packets — the one this probe
    # exists to find — a serial loop waits out every timeout in turn, and the
    # notebook looks frozen on exactly the machine you most needed it to work on.
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=len(HOSTS)) as _pool:
        egress = list(_pool.map(lambda pair: _check(*pair), HOSTS))

    ui.table(egress, title="Egress")
    return (os,)


@app.cell
def _(os, ui):
    PROXY_VARS = [
        "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
        "http_proxy", "https_proxy", "no_proxy",
        "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "CURL_CA_BUNDLE",
        "NODE_EXTRA_CA_CERTS",
    ]

    proxy_rows = [
        {"variable": name, "value": os.environ[name]}
        for name in PROXY_VARS
        if os.environ.get(name)
    ]

    ui.table(
        proxy_rows or [{"variable": "(none set)", "value": ""}],
        title="Proxy and certificate environment",
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### One limitation worth knowing

    Concurrency bounds the *total* wait to the slowest host rather than the sum
    of all of them, which is the difference between "slow" and "frozen". It does
    not bound any single probe: `socket` DNS lookups ignore timeouts and block
    until the system resolver gives up, and a hung thread cannot be interrupted
    from Python.

    `helpers/preflight.py` is this probe with a hard wall-clock deadline — it
    abandons a stuck lookup and reports the host as blocked rather than waiting.
    You will want to re-run it against every network you deploy into, which is
    why it is a module rather than a cell:

    ```python
    from helpers.preflight import check_egress

    report = check_egress()
    print(report.verdict())      # the sentence to record in NETWORK.md
    ```

    ### 🚢 Read the results

    - **All public issuers, no proxy variables** — you are on an open
      network. Nothing here will bite you.
    - **Issuer is your employer's name** — TLS is being intercepted. Expect
      certificate errors from tools that do not read the system trust store,
      and expect `REQUESTS_CA_BUNDLE` to become your friend.
    - **Some hosts fail while others pass** — you are behind an allowlist.
      Note exactly which ones. `huggingface.co` failing predicts trouble the
      moment you want open model weights; `registry-1.docker.io` failing
      predicts trouble the moment you build a container.

    **Record the policy in `NETWORK.md` now**, while the table is in front of
    you — we'll need it later. Evidence you gathered beats anything you
    reconstruct afterwards, and it is the single most useful thing to put in
    front of an infrastructure team because it is measured rather than assumed.

    ---
    ## Task 3 — Configuration, and failing on purpose

    Before the first model call: prove you can tell a *missing key* from a
    *wrong key*. They fail very differently, and confusing them costs
    everyone an afternoon at least once.
    """)
    return


@app.cell
def _(nb):
    # Ask for a variable that certainly is not set, and read the error.
    try:
        nb.bootstrap(require=("A_KEY_THAT_DOES_NOT_EXIST",))
        print("unexpected: that should have failed")
    except RuntimeError as exc:
        print("Missing config fails like this:\n")
        print(exc)
    return


@app.cell
def _(mo):
    mo.md(r"""
    Loud, early, and it names the file to fix. Compare that to what a wrong
    key does: nothing at all until the first request, then a 401 from three
    frames inside a library you did not write.

    The lesson generalizes. **Validate configuration where it is loaded, not
    where it is used.**

    ---
    ## Task 4 — One call, two providers

    Everything in this course routes through LiteLLM, so the provider is a
    string in `.env` rather than a code path. Watch what that buys you.
    """)
    return


@app.cell
def _(CFG, mo):
    run_call = mo.ui.run_button(label="Send one message")
    mo.md(f"Model: `{CFG}`  \n{run_call}")
    return (run_call,)


@app.cell
def _(CFG, mo, run_call):
    mo.stop(not run_call.value, mo.md("*Click the button above to make the call.*"))

    from helpers.display import stream_md
    from litellm import completion

    _stream = completion(
        **CFG.kwargs(),
        timeout=120,
        messages=[
            {
                "role": "user",
                "content": (
                    "In two sentences: why would a bank run an LLM on its own "
                    "hardware instead of calling a vendor API?"
                ),
            }
        ],
        stream=True,
    )
    reply = stream_md(_stream)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 🏗️ Activity — change the provider, not the code

    Open `.env` and point `LLM_MODEL` somewhere else — `anthropic/…`,
    `azure/…`, or `ollama/…` if you have one running locally. Re-run the two
    cells above. The call should work unchanged.

    That property is not a convenience. You may well find your firm has an
    approved internal endpoint and no route to `api.openai.com` at all. An
    application that treats its provider as configuration survives that. One
    that imports a vendor SDK directly gets rewritten.

    ---
    ## Task 5 — `CLAUDE.md` is source code

    The last thing, and the one that compounds.

    `CLAUDE.md` is what Claude Code reads before it touches anything. Most
    people treat it as documentation. It is closer to a config file for a
    colleague — and the reflex worth building this week is: **when the agent
    makes the same wrong assumption twice, fix the file, not the prompt.**

    Correcting it in chat fixes this conversation. Writing it down fixes every
    conversation after — including the ones someone else has, on your project,
    after you have handed it over. That difference is most of what an FDE
    delivers.

    ⏱️ **This is a hands-on drill. Budget 15 minutes.** Do it now, at the root
    of this repository.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### The loop

    **1 — Start it, and look before you leap.**

    ```bash
    claude
    ```

    Press `Shift+Tab` until you are in **plan mode**, then ask for something
    real. There is working code in `helpers/` to point it at:

    > add a function to `helpers/preflight.py` that reports which of the proxy
    > environment variables are set, and returns them as a dict

    It proposes; it does not edit. Read the plan. Plan mode is the right default
    any time you are working in code you did not write, which — as an FDE — is
    most of the time.

    **2 — Let it run, and watch for the assumption.**

    Accept the plan. Then look at what it actually wrote, not just whether it
    works. Something in there is not how you would have done it: a naming style,
    a docstring convention, an import placement, an extra dependency you did not
    want, an inline comment explaining *what* instead of *why*.

    **That is the interesting part.** Not a bug — a taste mismatch. Those are
    what recur.

    **3 — Write one line, not a paragraph.**

    There is no `CLAUDE.md` in this repository yet. **Create one**, and add a
    single rule under a `## Conventions` heading. Be concrete and testable:

    | ❌ Vague | ✅ Testable |
    | --- | --- |
    | "Write clean code" | "No new dependencies without asking — prefer stdlib" |
    | "Good comments" | "Comments explain *why*, not *what*" |
    | "Be consistent" | "Functions in `helpers/` take their arguments keyword-only" |

    That file is yours. It lives in your repo, it is version-controlled, and it
    is read by every session you start after this one.

    **4 — `/clear`, then ask for something similar.**

    ```
    /clear
    ```

    Fresh context, same project. Ask for a *different* small helper. The rule
    you wrote should hold without you mentioning it.

    If it does not, your line was too vague — sharpen it and go again. That
    tightening loop is the skill; it is not a sign you did it wrong.

    ---

    ### Why this is the habit worth having

    A `CLAUDE.md` does something no documentation file can: it changes an
    agent's behaviour, in prose, with no code involved. A file that says
    *"explain and debug, but do not write this part for me"* turns the same
    agent into a tutor — same model, same tools, different behaviour.

    That is the whole idea. It is configuration, not documentation, and the
    difference shows up the first time someone else picks up your project.

    > **New to Claude Code?** Permission modes, authentication, and the rest are
    > in the [prerequisites](../../00_Prerequisites/2_Claude_Code/README.md).
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ---
    ## What We Just Built vs. What's In Production

    | What we built | What production does |
    | --- | --- |
    | A one-shot egress probe in a notebook | Continuous synthetic monitoring from inside the VPC, alerting on cert changes |
    | `assert` that a key exists | Secrets from Vault or Key Vault, rotated, never on disk |
    | Provider as an env var | A gateway with routing, rate limits, per-team budgets, and audit logging |
    | `CLAUDE.md` in one repo | Shared agent instructions versioned across an org, reviewed like code |

    ---
    ## 🚀 Advanced Build

    - **Turn the egress probe into a health check.** Make it exit non-zero
      when a required host is unreachable, and run it in CI. That is the first
      check of any observability story worth having.
    - **Diff two machines.** Run this notebook on your work laptop and on a
      personal one. The delta *is* your firm's security posture, and it is a
      far better conversation-starter with IT than a list of questions.
    - **Find the CA.** If the issuer was your employer, locate the root
      certificate on disk and work out which of your tools trust it and which
      do not. Python, Node, Git, and Docker all answer differently.
    """)
    return


if __name__ == "__main__":
    app.run()
