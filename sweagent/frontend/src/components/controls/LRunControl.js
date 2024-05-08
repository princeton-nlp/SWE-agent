import React, { useState } from "react";
import { Tab, Tabs } from "react-bootstrap";
import Form from "react-bootstrap/Form";
import "../../static/runControl.css";
import { PlayFill, StopFill } from "react-bootstrap-icons";

import { Link } from "react-router-dom";

function LRunControl({
  isComputing,
  isConnected,
  handleStop,
  handleSubmit,
  setDataPath,
  setTestRun,
  testRun,
  setRepoPath,
  setModel,
  tabKey,
  setTabKey,
  envConfig,
  setEnvConfig,
  envConfigDefault,
}) {
  // ps = problem statement
  const [psType, setPsType] = useState("gh");
  const [envInputType, setEnvInputType] = useState("manual");
  const defaultInstallCommand = "pip install --editable .";

  const defaultPS =
    "https://github.com/marshmallow-code/marshmallow/issues/1357";

  const defaultRepo = "https://github.com/swe-agent-demo/marshmallow";

  const handlePsTypeChange = (event) => {
    const selectedType = event.target.value;
    setPsType(selectedType);
  };

  function getPsInput() {
    // Problem statement input controls based on the value of the problem statement type
    // dropdown menu.
    if (psType === "gh") {
      return (
        <div className="input-group mb-3">
          <span className="input-group-text">GitHub issue URL</span>
          <input
            type="text"
            className="form-control"
            onChange={(e) => setDataPath(e.target.value)}
            placeholder={"Example: " + defaultPS}
            defaultValue=""
          />
        </div>
      );
    }
    if (psType === "local") {
      return (
        <div className="input-group mb-3">
          <span className="input-group-text">
            Path to local .md or .txt file with problem statement
          </span>
          <input
            type="text"
            className="form-control"
            onChange={(e) => setDataPath(e.target.value)}
            placeholder="/path/to/your/local/file.md"
            defaultValue=""
          />
        </div>
      );
    }
    if (psType === "write") {
      return (
        <textarea
          className="form-control"
          onChange={(e) => setDataPath("text://" + e.target.value)}
          rows="5"
          placeholder="Enter problem statement"
        />
      );
    }
  }

  function getEnvInput() {
    // Get environment configuration input controls based on the
    // "Environment type" dropdown menu.
    if (envInputType === "conda") {
      return (
        <div className="input-group mb-3">
          <span className="input-group-text">Conda environment</span>
          <input
            type="text"
            className="form-control"
            onChange={(e) =>
              setEnvConfig({ ...envConfig, packages: e.target.value })
            }
            placeholder="/path/to/conda_env.yml"
          />
        </div>
      );
    }
    if (envInputType === "script_path") {
      return (
        <div>
          <div className="input-group mb-3">
            <span className="input-group-text">Setup script</span>
            <input
              type="text"
              className="form-control"
              onChange={(e) =>
                setEnvConfig({ ...envConfig, script_path: e.target.value })
              }
              placeholder="/path/to/setup.sh"
              value=""
            />
          </div>
          <div className="alert alert-info" role="alert">
            The script will be sourced (every line will be run as if it were
            typed into the shell), so make sure there is no exit commands as it
            will close the environment.
          </div>
        </div>
      );
    }
    if (envInputType === "manual") {
      return (
        <div>
          <div className="input-group mb-3">
            <span className="input-group-text">Python version</span>
            <input
              type="text"
              className="form-control"
              onChange={(e) =>
                setEnvConfig({
                  ...envConfig,
                  python: e.target.value || envConfigDefault["python"],
                })
              }
              placeholder={envConfigDefault["python"]}
              defaultValue=""
            />
          </div>
          <div class="input-group mb-3">
            <div class="input-group-text">
              <input
                class="form-check-input mt-0"
                type="checkbox"
                aria-label="Run installation command"
                defaultChecked={true}
                onChange={(e) =>
                  setEnvConfig({
                    ...envConfig,
                    install_command_active: e.target.value,
                  })
                }
              />
            </div>
            <span className="input-group-text">Installation command</span>
            <input
              type="text"
              class="form-control"
              aria-label="Text input with checkbox"
              placeholder={defaultInstallCommand}
              onChange={(e) =>
                setEnvConfig({
                  ...envConfig,
                  install: e.target.value || defaultInstallCommand,
                })
              }
            />
          </div>

          <textarea
            className="form-control"
            onChange={(e) =>
              setEnvConfig({ ...envConfig, pip_packages: e.target.value })
            }
            rows="5"
            placeholder="pip installable packages list, one per line (i.e., requirements.txt)."
          />
        </div>
      );
    }
  }

  function handleEnvInputTypeUpdate(value) {
    // Handle a change in how the user wants to configure the environment.
    // We need to make sure that we clear out config items that aren't "active" anymore
    // For example, if we switch from conda to manual, we should clear out conda env path
    setEnvInputType(value);
    if (value === "conda") {
      setEnvConfig({ packages: "", config_type: "conda" });
    } else if (value === "manual") {
      setEnvConfig({
        python: envConfigDefault["python"],
        config_type: "manual",
        install: "pip install --editable .",
        install_command_active: true,
      });
    } else if (value === "script_path") {
      setEnvConfig({ script_path: "", config_type: "script_path" });
    }
  }

  function onTabClicked(keyClicked) {
    /* Handle clicks on the tabs of the control/setting groups */
    if (keyClicked === tabKey) {
      // Clicking the active tab hides it
      setTabKey(null);
    } else {
      setTabKey(keyClicked);
    }
  }

  return (
    <div>
      <Tabs
        id="controlled-tab-example"
        activeKey={tabKey}
        onSelect={onTabClicked}
        className="mb-3 bordered-tab-contents"
      >
        <Tab eventKey="problem" title="Problem Source">
          <div className="p-3">
            <div className="input-group mb-3">
              <span className="input-group-text">Problem source</span>
              <select
                className="form-select"
                aria-label="Select problem statement type"
                onChange={handlePsTypeChange}
              >
                <option value="gh">GitHub issue URL</option>
                <option value="local">Local file</option>
                <option value="write">Write here</option>
              </select>
            </div>
            <div className="input-group mb-3">{getPsInput()}</div>
            <div className="input-group mb-3">
              <span className="input-group-text">
                Local repo path or GitHub URL
              </span>
              <input
                type="text"
                className="form-control"
                placeholder="Optional when using GitHub issue as problem source."
                onChange={(e) => setRepoPath(e.target.value)}
                defaultValue=""
              />
            </div>
          </div>
        </Tab>
        <Tab eventKey="model" title="Model">
          <div className="p-3">
            <div className="input-group mb-3">
              <span className="input-group-text">Model name</span>
              <input
                type="text"
                className="form-control"
                placeholder="gpt4"
                onChange={(e) => setModel(e.target.value || "gpt4")}
              />
            </div>
            <div className="alert alert-info" role="alert">
              Please make sure that you have your API keys configured in
              keys.cfg
            </div>
          </div>
        </Tab>
        <Tab eventKey="env" title="Environment">
          <div className="p-3">
            <p>
              These settings set up the environment in which SWE-agent operates.
              It's a good idea to explicitly specify all relevant setup commands
              here (though SWE-agent will try to figure them out if they
              aren't).
            </p>
            <div className="input-group mb-3">
              <span className="input-group-text">
                Environment specification
              </span>
              <select
                className="form-select"
                aria-label="Select problem statement type"
                onChange={(e) => handleEnvInputTypeUpdate(e.target.value)}
                defaultValue={envInputType}
              >
                <option value="manual">Python version and packages</option>
                <option value="script_path">Path to shell script</option>
                {/* Currently broken */}
                {/* <option value="conda">Conda environment</option> */}
              </select>
            </div>
            {getEnvInput()}
          </div>
        </Tab>
        <Tab eventKey="settings" title="Extra Settings">
          <div className="p-3">
            <Form.Check
              type="switch"
              id="custom-switch"
              label="Test run (dummy agent without LM queries)"
              checked={testRun}
              onChange={(e) => setTestRun(e.target.checked)}
            />
          </div>
        </Tab>
      </Tabs>
      <div className="runControl p-3">
        <div>
          <div className="btn-group" role="group" aria-label="Basic example">
            <button
              type="submit"
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={isComputing || !isConnected}
            >
              <PlayFill /> Run
            </button>
            <button
              onClick={handleStop}
              disabled={!isComputing}
              className="btn btn-primary"
            >
              <StopFill /> Stop
            </button>
          </div>
        </div>
        <div className="extraButtons">
          <div className="btn-group" role="group" aria-label="Basic example">
            <Link
              to="https://github.com/princeton-nlp/SWE-agent"
              target="_blank"
              rel="noopener noreferrer"
            >
              <button type="button" className="btn btn-outline-secondary">
                GitHub readme
              </button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LRunControl;
