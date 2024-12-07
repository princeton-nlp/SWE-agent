import React, { useState, useEffect } from "react";
import { Tab, Tabs } from "react-bootstrap";
import Form from "react-bootstrap/Form";
import { PlayFill, StopFill } from "react-bootstrap-icons";
import { Link } from "react-router-dom";
import "../../static/runControl.css";

function LRunControl({
  isComputing,
  isConnected,
  handleStop,
  handleSubmit,
  tabKey,
  setTabKey,
  runConfig,
  setRunConfig,
  runConfigDefault,
}) {
  // ps = problem statement
  const [psType, setPsType] = useState("gh");
  const [psInputValue, setPsInputValue] = useState("");
  const defaultInstallCommand = "pip install --editable .";
  const defaultPS =
    "https://github.com/marshmallow-code/marshmallow/issues/1357";

  const handlePsTypeChange = (event) => {
    const selectedType = event.target.value;
    setPsType(selectedType);
  };

  useEffect(() => {
    setPsInputValue("");
  }, [psType]);

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
            onChange={(e) => {
              setPsInputValue(e.target.value);
              setRunConfig((draft) => {
                draft.environment.data_path = e.target.value;
              });
            }}
            placeholder={"Example: " + defaultPS}
            value={psInputValue}
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
            onChange={(e) => {
              setPsInputValue(e.target.value);
              setRunConfig((draft) => {
                draft.environment.data_path = e.target.value;
              });
            }}
            placeholder="/path/to/your/local/file.md"
            value={psInputValue}
          />
        </div>
      );
    }
    if (psType === "write") {
      return (
        <textarea
          className="form-control"
          onChange={(e) =>
            setRunConfig((draft) => {
              draft.environment.data_path = "text://" + e.target.value;
            })
          }
          rows="5"
          placeholder="Enter problem statement"
        />
      );
    }
  }

  function getEnvInput() {
    return (
      <div>
        <div className="input-group mb-3">
          <span className="input-group-text">Docker image name</span>
          <input
            type="text"
            className="form-control"
            onChange={(e) =>
              setRunConfig((draft) => {
                draft.environment.image_name = e.target.value;
              })
            }
            placeholder={runConfigDefault.environment.image_name}
            defaultValue=""
          />
        </div>
        <div className="input-group mb-3">
          <span className="input-group-text">Setup script</span>
          <input
            type="text"
            className="form-control"
            onChange={(e) =>
              setRunConfig((draft) => {
                draft.environment.script = e.target.value;
              })
            }
            placeholder="/path/to/setup.sh"
            defaultValue=""
          />
        </div>
        <div className="alert alert-info" role="alert">
          The script will be sourced (every line will be run as if it were typed
          into the shell), so make sure there is no exit commands as it will
          close the environment.
        </div>
      </div>
    );
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
              <span className="input-group-text">Repository</span>
              <input
                type="text"
                className="form-control"
                placeholder="Local repo path or GitHub repo URL."
                onChange={(e) =>
                  setRunConfig((draft) => {
                    draft.environment.repo_path = e.target.value;
                  })
                }
              />
              <input
                type="text"
                className="form-control"
                placeholder="Optional: branch/tag/hash"
                onChange={(e) =>
                  setRunConfig((draft) => {
                    draft.environment.base_commit = e.target.value;
                  })
                }
                style={{ maxWidth: 250 }}
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
                onChange={(e) =>
                  setRunConfig((draft) => {
                    draft.agent.model.model_name = e.target.value || "gpt4";
                  })
                }
              />
            </div>
            <div className="alert alert-info" role="alert">
              See litellm for different models. Please make sure that you have
              your API keys configured in .env.
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
            {getEnvInput()}
          </div>
        </Tab>
        <Tab eventKey="settings" title="Extra Settings">
          <div className="p-3">
            <Form.Check
              type="switch"
              id="custom-switch"
              label="Test run (dummy agent without LM queries)"
              checked={runConfig.extra.test_run}
              onChange={(e) =>
                setRunConfig((draft) => {
                  draft.extra.test_run = e.target.checked;
                })
              }
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
              to="https://github.com/SWE-agent/SWE-agent"
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
