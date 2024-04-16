import os
from flask import Flask, render_template_string, request
import threading
import sys
from sweagent import CONFIG_DIR, PACKAGE_DIR
from sweagent.agent.agents import AgentArguments
from sweagent.agent.models import ModelArguments
from sweagent.environment.swe_env import EnvironmentArguments

# baaaaaaad
sys.path.append(str(PACKAGE_DIR.parent))
from run import ActionsArguments, main, ScriptArguments


app = Flask(__name__)


html_page = """
<!DOCTYPE html>
<html>
<head>
    <title>Run Command</title>
</head>
<body>
    <h1>Start run</h1>
    <form action="/run" method="post">
        <label for="data_path">Data Path:</label>
        <input type="text" id="data_path" name="data_path" value="https://github.com/klieret/swe-agent-test-repo/issues/1" required>
        <button type="submit">Run</button>
        <input type="checkbox" id="test_run" name="test_run" checked>
        <label for="test_run">Test run (no LM queries)</label><br><br>
    </form>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(html_page)


@app.route('/run', methods=['POST'])
def run():
    data_path = request.form['data_path']
    test_run = 'test_run' in request.form
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
        skip_existing=True,
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
    thread = threading.Thread(target=main, args=(defaults,))
    thread.start()
    return 'Commands are being executed', 202

if __name__ == "__main__":
    app.run(port=5000)