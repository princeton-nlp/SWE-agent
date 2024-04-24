import ctypes
import inspect
import os
from typing import Dict, Optional
from flask import Flask, render_template, request, make_response
import threading
import sys

from sweagent import CONFIG_DIR, PACKAGE_DIR
from sweagent.agent.agents import AgentArguments, AgentHook
from sweagent.agent.models import ModelArguments
from sweagent.environment.swe_env import EnvironmentArguments
import sweagent.environment.utils as env_utils
from flask_socketio import SocketIO
from flask_cors import CORS
from flask import session
from uuid import uuid4

# baaaaaaad
sys.path.append(str(PACKAGE_DIR.parent))
from run import ActionsArguments, ScriptArguments, Main, MainHook

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins='*')

THREADS: Dict[str, "MainThread"] = {}

@app.route('/')
def index():
    return render_template("index.html")


@socketio.on('connect')
def handle_connect():
    print('Client connected')



class WebUpdate:
    """This class talks to socketio. It's pretty much a wrapper around socketio.emit.
    """
    def _emit(self, event, data):
        """Directly wrap around socketio.emit"""
        socketio.emit(event, data)

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
            format: str = "markdown",
            title="",
            thought_idx: Optional[int] =None,
    ):
        """Update the environment feed"""
        self._emit('update', {'feed': 'env',  'title': title, 'message': message, 'format': format, 'thought_idx': thought_idx})



class MainUpdateHook(MainHook):
    def __init__(self, wu: WebUpdate):
        """This hooks into the Main class to update the web interface"""
        self._wu = wu

    def on_start(self):
        self._wu.up_env(message="Environment container initialized", format="text")
    
    def on_end(self):
        self._wu.up_agent(message="The run has ended", format="text")

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


def ensure_session_id_set():
    """Ensures a session ID is set for this user"""
    session_id = session.get('session_id', None)
    if not session_id:
        session_id = uuid4().hex
        session['session_id'] = session_id
    return session_id



def _async_raise(tid, exctype):
    '''Raises an exception in the threads with id tid
    
    This code is modified from the following SO answer:
    Author: Philippe F
    Posted: Nov 28, 2008
    URL: https://stackoverflow.com/a/325528/
    '''
    if not inspect.isclass(exctype):
        raise TypeError("Only types can be raised (not instances)")
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid),
                                                     ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # "if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


class ThreadWithExc(threading.Thread):
    '''A thread class that supports raising an exception in the thread from
    another thread.

    This code is modified from the following SO answer:
    Author: Philippe F
    Posted: Nov 28, 2008
    URL: https://stackoverflow.com/a/325528/
    '''
    def _get_my_tid(self):
        """determines this (self's) thread id

        CAREFUL: this function is executed in the context of the caller
        thread, to get the identity of the thread represented by this
        instance.
        """
        if not self.is_alive(): 
            raise threading.ThreadError("the thread is not active")

        # do we have it cached?
        if hasattr(self, "_thread_id"):
            return self._thread_id

        # no, look for it in the _active dict
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid

        raise RuntimeError("could not determine the thread's id")

    def raise_exc(self, exctype):
        """Raises the given exception type in the context of this thread.

        If the thread is busy in a system call (time.sleep(),
        socket.accept(), ...), the exception is simply ignored.

        If you are sure that your exception should terminate the thread,
        one way to ensure that it works is:

            t = ThreadWithExc( ... )
            ...
            t.raise_exc( SomeException )
            while t.isAlive():
                time.sleep( 0.1 )
                t.raise_exc( SomeException )

        If the exception is to be caught by the thread, you need a way to
        check that your thread has caught it.

        CAREFUL: this function is executed in the context of the
        caller thread, to raise an exception in the context of the
        thread represented by this instance.
        """
        _async_raise( self._get_my_tid(), exctype )


class MainThread(ThreadWithExc):
    def __init__(self, main: Main):
        super().__init__()
        self._main = main
    
    def run(self) -> None:
        self._main.main()
    
    def stop(self):
        self.raise_exc(SystemExit)


@app.route('/run', methods=['GET', 'OPTIONS'])
def run():
    session_id = ensure_session_id_set()
    if request.method == "OPTIONS":  # CORS preflight
        return _build_cors_preflight_response()
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
    thread = MainThread(main)
    global THREADS
    THREADS[session_id] = thread
    print("||||||||||||||||||||||||||||||||||||||||||||||")
    print(f"Starting session {session_id} with {thread}")
    print("||||||||||||||||||||||||||||||||||||||||||||||")
    thread.start()
    return 'Commands are being executed', 202

@app.route('/stop')
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
    return 'Stopping computation', 202

def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add('Access-Control-Allow-Headers', "*")
    response.headers.add('Access-Control-Allow-Methods', "*")
    return response

if __name__ == "__main__":
    # fixme:
    app.secret_key = 'super secret key'
    socketio.run(app, port=5000, debug=True)