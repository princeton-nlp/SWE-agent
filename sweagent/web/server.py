import os
from flask import Flask, render_template, request
import threading
import sys

from sweagent import CONFIG_DIR, PACKAGE_DIR
from sweagent.agent.agents import AgentArguments, AgentHook
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

class MainUpdateHook(MainHook):
    def on_start(self):
        socketio.emit('update', {'event': 'started'})
    
    def on_end(self):
        socketio.emit('update', {'event': 'finished'})

    def on_instance_completed(self, *, info, trajectory):
        socketio.emit('update', {'event': 'instance_completed', **info})


class AgentUpdateHook(AgentHook):
    def on_actions_generated(self, *, thought: str, action: str, output: str):
        socketio.emit('update', {'event': 'actions_generated', 'thought': thought, 'action': action})
    
    def on_sub_action_started(self, *, sub_action: str):
        socketio.emit('update', {'event': 'sub_action_started', 'sub_action': sub_action})
    
    def on_sub_action_executed(self, *, obs: str, done: bool):
        socketio.emit('update', {'event': 'sub_action_executed', 'obs': obs, 'done': done})


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
    main.add_hook(MainUpdateHook())
    main.agent.add_hook(AgentUpdateHook())
    thread = threading.Thread(target=main.main)
    thread.start()
    return 'Commands are being executed', 202


if __name__ == "__main__":
    socketio.run(app, port=5001, debug=True)