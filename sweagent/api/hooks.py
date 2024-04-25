from typing import Optional
import sys

from sweagent import PACKAGE_DIR
from sweagent.agent.agents import AgentHook
from flask_socketio import SocketIO

# baaaaaaad
sys.path.append(str(PACKAGE_DIR.parent))
from run import MainHook


class WebUpdate:
    """This class talks to socketio. It's pretty much a wrapper around socketio.emit.
    """
    def __init__(self, socketio: SocketIO):
        self._socketio = socketio


    def _emit(self, event, data):
        """Directly wrap around socketio.emit"""
        self._socketio.emit(event, data)

    def up_agent(
            self,
            message: str,
            title: str = "",
            format: str = "markdown",
            thought_idx: Optional[int] =None,
    ):
        """Update the agent feed"""
        self._emit('update', {'feed': 'agent',  'title': title, 'message': message, 'format': format, 'thought_idx': thought_idx})
    
    def up_env(
            self,
            message: str,
            type_: str,
            format: str = "markdown",
            thought_idx: Optional[int] =None,
    ):
        """Update the environment feed"""
        self._emit('update', {'feed': 'env',  'message': message, 'format': format, 'thought_idx': thought_idx, 'type': type_})
    
    def finish_run(self):
        """Finish the run. We use that to control which buttons are active."""
        self._emit('finish_run', {}) 



class MainUpdateHook(MainHook):
    def __init__(self, wu: WebUpdate):
        """This hooks into the Main class to update the web interface"""
        self._wu = wu

    def on_start(self):
        self._wu.up_env(message="Environment container initialized", format="text", type_="info")
    
    def on_end(self):
        self._wu.up_agent(message="The run has ended", format="text")
        self._wu.finish_run()

    def on_instance_completed(self, *, info, trajectory):
        self._wu.up_agent(message=f"Instance completed")
    

class AgentUpdateHook(AgentHook):
    def __init__(self, wu: WebUpdate):
        """This hooks into the Agent class to update the web interface"""
        self._wu = wu
        self._sub_action = None
        self._thought_idx = 0

    def on_actions_generated(self, *, thought: str, action: str, output: str):
        self._thought_idx += 1
        thought, _, discussion = thought.partition("DISCUSSION")
        if thought.strip():
            self._wu.up_agent(title=f"Thought", message=thought, format="markdown", thought_idx=self._thought_idx)
        if discussion.strip():
            self._wu.up_agent(title=f"Discussion", message=discussion, format="markdown", thought_idx=self._thought_idx)
    
    def on_sub_action_started(self, *, sub_action: dict):
        # msg = f"```bash\n{sub_action['action']}\n```"
        msg = sub_action["action"].strip()
        self._sub_action = sub_action["action"].strip()
        self._wu.up_env(message=msg, thought_idx=self._thought_idx, type_="command")
    
    def on_sub_action_executed(self, *, obs: str, done: bool):
        # language = ""
        # if self._sub_action == "submit":
        #     language = "diff"
        # msg = f"```{language}\n{obs}\n```"
        msg = obs.strip()
        self._wu.up_env(message=msg, thought_idx=self._thought_idx, type_="output")
        
    # def on_query_message_added(
    #         self, 
    #         *, 
    #         role: str, 
    #         content: str, 
    #         agent: str, 
    #         is_demo: bool = False, 
    #         thought: str = "", 
    #         action: str = ""
    #     ):
    #     if role == "assistant":
    #         return
    #     if thought or action:
    #         return
    #     if is_demo:
    #         return self._wu.up_agent(title="Demo", message=content, thought_idx=self._thought_idx + 1)
    #     self._wu.up_agent(title="Query", message=content, thought_idx=self._thought_idx + 1)
