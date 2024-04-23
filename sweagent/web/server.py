import os
from typing import Optional
from flask import Flask, render_template, request
import threading
import sys

from sweagent import CONFIG_DIR, PACKAGE_DIR
from sweagent.agent.agents import AgentArguments, AgentHook
from sweagent.agent.models import ModelArguments
from sweagent.environment.swe_env import EnvironmentArguments
import sweagent.environment.utils as env_utils
from flask_socketio import SocketIO
from flask_cors import CORS

# baaaaaaad
sys.path.append(str(PACKAGE_DIR.parent))
from run import ActionsArguments, ScriptArguments, Main, MainHook

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins='*')


@app.route('/')
def index():
    return render_template("index.html")


@socketio.on('connect')
def handle_connect():
    print('Client connected')



class WebUpdate:
    def _emit(self, event, data):
        socketio.emit(event, data)


    def up_agent(
            self,
            message: str,
            title: str = "",
            format: str = "markdown",
            thought_idx: Optional[int] =None,
    ):
        self._emit('update', {'feed': 'agent',  'title': title, 'message': message, 'format': format, 'thought_idx': thought_idx})
    
    def up_env(
            self,
            message: str,
            format: str = "markdown",
            title="",
            thought_idx: Optional[int] =None,
    ):
        self._emit('update', {'feed': 'env',  'title': title, 'message': message, 'format': format, 'thought_idx': thought_idx})



class MainUpdateHook(MainHook):
    def __init__(self, wu: WebUpdate):
        self._wu = wu

    def on_start(self):
        self._wu.up_env(message="Environment container initialized", format="text")
    
    def on_end(self):
        self._wu.up_agent(message="The run has ended", format="text")

    def on_instance_completed(self, *, info, trajectory):
        self._wu.up_agent(message=f"Instance completed")
    

class AgentUpdateHook(AgentHook):
    def __init__(self, wu: WebUpdate):
        self._wu = wu
        self._sub_action = None
        self._thought_idx = 0

    def on_actions_generated(self, *, thought: str, action: str, output: str):
        self._thought_idx += 1
        thought, _, discussion = thought.partition("DISCUSSION")
        self._wu.up_agent(title=f"Thought", message=thought, format="markdown", thought_idx=self._thought_idx)
        self._wu.up_agent(title=f"Discussion", message=discussion, format="markdown", thought_idx=self._thought_idx)
    
    def on_sub_action_started(self, *, sub_action: dict):
        msg = f"```bash\n{sub_action['action']}\n```"
        self._sub_action = sub_action["action"].strip()
        self._wu.up_env(message=msg, title=f"Action", thought_idx=self._thought_idx)
    
    def on_sub_action_executed(self, *, obs: str, done: bool):
        language = ""
        if self._sub_action == "submit":
            language = "diff"
        msg = f"```{language}\n{obs}\n```"
        self._wu.up_env(message=msg, thought_idx=self._thought_idx)
        
    def on_query_message_added(
            self, 
            *, 
            role: str, 
            content: str, 
            agent: str, 
            is_demo: bool = False, 
            thought: str = "", 
            action: str = ""
        ):
        if role == "assistant":
            return
        if thought or action:
            return
        if is_demo:
            return self._wu.up_agent(title="Demo", message=content, thought_idx=self._thought_idx + 1)
        self._wu.up_agent(title="Query", message=content, thought_idx=self._thought_idx + 1)



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
    socketio.run(app, port=5000, debug=True)