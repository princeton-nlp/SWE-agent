from __future__ import annotations

from omegaconf import OmegaConf

from sweagent.environment.config.deployment import DeploymentConfig
from sweagent.run.run_single import RunSingleActionConfig

try:
    import flask  # noqa
except ImportError as e:
    msg = (
        "Flask not found. You probably haven't installed the dependencies for SWE-agent. "
        "Please go to the root of the repository and run `pip install -e .`"
    )
    raise RuntimeError(msg) from e
import atexit
import copy
import json
import sys
import tempfile
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from flask import Flask, make_response, render_template, request, session
from flask_cors import CORS
from flask_socketio import SocketIO

from sweagent import CONFIG_DIR, PACKAGE_DIR
from sweagent.agent.agents import AgentConfig
from sweagent.agent.models import ModelArguments
from sweagent.api.hooks import AgentUpdateHook, EnvUpdateHook, MainUpdateHook, WebUpdate
from sweagent.api.utils import AttrDict, ThreadWithExc
from sweagent.environment.swe_env import EnvironmentInstanceConfig

# baaaaaaad
sys.path.append(str(PACKAGE_DIR.parent))
from run import Main, ScriptArguments

app = Flask(__name__, template_folder=Path(__file__).parent)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
# Setting these variables outside of `if __name__ == "__main__"` because when run Flask server with
# `flask run` it will skip the if block. Therefore, the app will return an error for missing `secret_key`
# Setting it here will allow both `flask run` and `python server.py` to work
app.secret_key = "super secret key"
app.config["SESSION_TYPE"] = "memcache"

THREADS: dict[str, MainThread] = {}


def ensure_session_id_set():
    """Ensures a session ID is set for this user"""
    session_id = session.get("session_id", None)
    if not session_id:
        session_id = uuid4().hex
        session["session_id"] = session_id
    return session_id


class MainThread(ThreadWithExc):
    def __init__(self, settings: ScriptArguments, wu: WebUpdate):
        super().__init__()
        self._wu = wu
        self._settings = settings

    def run(self) -> None:
        # fixme: This actually redirects all output from all threads to the socketio, which is not what we want
        with redirect_stdout(self._wu.log_stream):
            with redirect_stderr(self._wu.log_stream):
                try:
                    main = Main(self._settings)
                    main.add_hook(MainUpdateHook(self._wu))
                    main.agent.add_hook(AgentUpdateHook(self._wu))
                    main.env.add_hook(EnvUpdateHook(self._wu))
                    main.main()
                except Exception as e:
                    short_msg = str(e)
                    max_len = 350
                    if len(short_msg) > max_len:
                        short_msg = f"{short_msg[:max_len]}... (see log for details)"
                    traceback_str = traceback.format_exc()
                    self._wu.up_log(traceback_str)
                    self._wu.up_agent(f"Error: {short_msg}")
                    self._wu.up_banner("Critical error: " + short_msg)
                    self._wu.finish_run()
                    raise

    def stop(self):
        while self.is_alive():
            self.raise_exc(SystemExit)
            time.sleep(0.1)
        self._wu.finish_run()
        self._wu.up_agent("Run stopped by user")


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    print("Client connected")


def write_env_yaml(data) -> str:
    data: Any = AttrDict(copy.deepcopy(dict(data)))
    if not data.install_command_active:
        data.install = ""
    del data.install_command_active
    data.pip_packages = [p.strip() for p in data.pip_packages.split("\n") if p.strip()]
    path = Path(tempfile.NamedTemporaryFile(delete=False, suffix=".yml").name)
    # Make sure that the file is deleted when the program exits
    atexit.register(path.unlink)
    path.write_text(yaml.dump(dict(data)))
    return str(path)


@app.route("/run", methods=["GET", "OPTIONS"])
def run():
    session_id = ensure_session_id_set()
    if request.method == "OPTIONS":  # CORS preflight
        return _build_cors_preflight_response()
    # While we're running as a local UI, let's make sure that there's at most
    # one run at a time
    global THREADS
    for thread in THREADS.values():
        if thread.is_alive():
            thread.stop()
    wu = WebUpdate(socketio)
    wu.up_agent("Starting the run")
    # Use Any type to silence annoying false positives from mypy
    run: Any = AttrDict.from_nested_dicts(json.loads(request.args["runConfig"]))
    print(run)
    print(run.environment)
    print(run.environment.base_commit)
    model_name: str = run.agent.model.model_name
    environment_setup = ""
    environment_input_type = run.environment.environment_setup.input_type
    if environment_input_type == "manual":
        environment_setup = str(write_env_yaml(run.environment.environment_setup.manual))
    elif environment_input_type == "script_path":
        environment_setup = run.environment.environment_setup.script_path["script_path"]
    else:
        msg = f"Unknown input type: {environment_input_type}"
        raise ValueError(msg)
    if not environment_setup.strip():
        environment_setup = None
    test_run: bool = run.extra.test_run
    if test_run:
        model_name = "instant_empty_submit"
    agent_config = OmegaConf.load(CONFIG_DIR / "default_from_url.yaml")
    defaults = ScriptArguments(
        suffix="",
        environment=EnvironmentInstanceConfig(
            deployment=DeploymentConfig(),
            data_path=run.environment.data_path,
            base_commit=run.environment.base_commit,
            split="dev",
            verbose=True,
            install_environment=True,
            repo_path=run.environment.repo_path,
            environment_setup=environment_setup,
        ),
        agent=AgentConfig(),
        skip_existing=False,
        actions=RunSingleActionConfig(open_pr=False, skip_if_commits_reference_issue=True),
        raise_exceptions=True,
    )
    defaults.agent.model = ModelArguments(
        name=model_name,
        total_cost_limit=0.0,
        per_instance_cost_limit=3.0,
        temperature=0.0,
        top_p=0.95,
    )
    config = ScriptArguments(**OmegaConf.merge(agent_config, defaults).to_container())
    thread = MainThread(config, wu)
    THREADS[session_id] = thread
    thread.start()
    return "Commands are being executed", 202


@app.route("/stop")
def stop():
    session_id = ensure_session_id_set()
    global THREADS
    print(f"Stopping session {session_id}")
    print(THREADS)
    thread = THREADS.get(session_id)
    if thread and thread.is_alive():
        print(f"Thread {thread} is alive")
        thread.stop()
    else:
        print(f"Thread {thread} is not alive")
    return "Stopping computation", 202


def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response


if __name__ == "__main__":
    app.debug = True
    socketio.run(app, port=8000, debug=True, allow_unsafe_werkzeug=True)
