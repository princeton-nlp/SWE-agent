import os
from flask import Flask, render_template, request
import threading
import sys

from sweagent import CONFIG_DIR, PACKAGE_DIR
from sweagent.agent.agents import AgentArguments
from sweagent.agent.models import ModelArguments
from sweagent.environment.swe_env import EnvironmentArguments
from flask_socketio import SocketIO

# baaaaaaad
sys.path.append(str(PACKAGE_DIR.parent))
from run import ActionsArguments, ScriptArguments, Main, MainHook

app = Flask(__name__)
socketio = SocketIO(app)


@app.route('/')
def index():
    return render_template("index.html")


@socketio.on('connect')
def handle_connect():
    print('Client connected')

class WebUpdateRunHook(MainHook):
    def on_start(self):
        socketio.emit('update', {'event': 'started'})
    
    def on_end(self):
        socketio.emit('update', {'event': 'finished'})

    def on_instance_completed(self, *, info, trajectory):
        socketio.emit('update', {'event': 'instance_completed', **info})


@app.route('/run', methods=['GET'])
def run():
    data_path = request.args.get("data_path", "")
    test_run = 'test_run' in request.args
    model_name = "gpt4"
    if test_run:
        os.environ["SWE_AGENT_EXPERIMENTAL_COMMUNICATE"] = "1"
        model_name = "instant_empty_submit"
    defaults = ScriptArguments(
        suffix="",
        environment=EnvironmentArguments(
            image_name="sweagent/swe-agent:latest",
            data_path=data_path,
            split="dev",
            verbose=True,
            install_environment=True,
        ),
        skip_existing=False,
        agent=AgentArguments(
            model=ModelArguments(
                model_name=model_name,
                total_cost_limit=0.0,
                per_instance_cost_limit=3.0,
                temperature=0.0,
                top_p=0.95,
            ),
            config_file=CONFIG_DIR / "default_from_url.yaml",
        ),
        actions=ActionsArguments(open_pr=False, skip_if_commits_reference_issue=True),
    )
    main = Main(defaults)
    main.add_hook(WebUpdateRunHook())
    thread = threading.Thread(target=main.main)
    thread.start()
    return 'Commands are being executed', 202


if __name__ == "__main__":
    socketio.run(app, port=5001)