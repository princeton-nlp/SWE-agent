import os
from flask import Flask, render_template, request
import threading
import sys

from sweagent import CONFIG_DIR, PACKAGE_DIR
from sweagent.agent.agents import AgentArguments, AgentHook
from sweagent.agent.models import ModelArguments
from sweagent.environment.swe_env import EnvironmentArguments
import sweagent.environment.utils as env_utils
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



class WebUpdate:
    def up_agent(
            self,
            title: str,
            message: str,
            format: str = "text",
    ):
        socketio.emit('update', {'feed': 'agent',  'title': title, 'message': message, 'format': format})
    
    def up_env(
            self,
            message: str,
            format: str = "markdown",
    ):
        socketio.emit('update', {'feed': 'env',  'title': '', 'message': message, 'format': format})



class MainUpdateHook(MainHook):
    def __init__(self, wu: WebUpdate):
        self._wu = wu

    def on_start(self):
        self._wu.up_agent(title="Started", message="Environment container initialized")
    
    def on_end(self):
        self._wu.up_agent(title="Ended", message="The run has ended")

    def on_instance_completed(self, *, info, trajectory):
        self._wu.up_agent(title="Instance completed", message=f"Instance completed")


class AgentUpdateHook(AgentHook):
    def __init__(self, wu: WebUpdate):
        self._wu = wu
        self._sub_action = None

    def on_actions_generated(self, *, thought: str, action: str, output: str):
        self._wu.up_agent(title="Thought", message=thought, format="markdown")
    
    def on_sub_action_started(self, *, sub_action: dict):
        msg = f"```bash\n{sub_action['action']}\n```"
        self._sub_action = sub_action["action"].strip()
        self._wu.up_env(message=msg)
    
    def on_sub_action_executed(self, *, obs: str, done: bool):
        language = ""
        if self._sub_action == "submit":
            language = "diff"
        msg = f"```{language}\n{obs}\n```"
        self._wu.up_env(message=msg)


@app.route('/run', methods=['GET'])
def run():
    data_path = request.args["data_path"]
    test_run = request.args["test_run"].lower() == "true"
    model_name = "gpt4"
    if test_run:
        print(">>>>>>>>>> test_run")
        os.environ["SWE_AGENT_EXPERIMENTAL_COMMUNICATE"] = "1"
        model_name = "instant_empty_submit"
        env_utils.START_UP_DELAY = 1
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
    wu = WebUpdate()
    main.add_hook(MainUpdateHook(wu))
    main.agent.add_hook(AgentUpdateHook(wu))
    thread = threading.Thread(target=main.main)
    thread.start()
    return 'Commands are being executed', 202


if __name__ == "__main__":
    socketio.run(app, port=5001, debug=True)