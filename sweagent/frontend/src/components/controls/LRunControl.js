import React, { useState } from 'react';
import { Tab, Tabs } from 'react-bootstrap';
import Form from 'react-bootstrap/Form';
import '../../static/runControl.css';
import { PlayFill, StopFill} from 'react-bootstrap-icons';
import logo from '../../assets/logo.png'
import { Link } from 'react-router-dom';

function LRunControl({isComputing, isConnected, handleStop, handleSubmit, setDataPath, setTestRun, dataPath, testRun, repoPath, setRepoPath}) {
  const [psType, setPsType] = useState('gh');
  const [key, setKey] = useState('problem');

  const handlePsTypeChange = (event) => {
    const selectedType = event.target.value;
    setPsType(selectedType);
  };

  function getPsInput() {
    if (psType == 'gh') {
      return (
        <input 
          type="text" 
          className="form-control" 
          // value={inputValue} 
          onChange={(e) => setDataPath(e.target.value || "https://github.com/klieret/swe-agent-test-repo/issues/1")}
          placeholder="https://github.com/klieret/swe-agent-test-repo/issues/1" />
      );
    }
    if (psType == 'write') {
      return (
        <textarea 
          className="form-control" 
          onChange={(e) => setDataPath("text://" + e.target.value)} 
          rows="5" 
          placeholder="Enter problem statement" />
      );
    }
  }

  return (
    <div>
      <Tabs
        id="controlled-tab-example"
        activeKey={key}
        onSelect={(k) => setKey(k)}
        className="mb-3 bordered-tab-contents"
      >
        <Tab eventKey="problem" title="Problem Statement">
          <div className="p-3">
            <div className="input-group mb-3">
              <span className="input-group-text">Problem statement</span>
              <select className="form-select" aria-label="Select problem statement type" onChange={handlePsTypeChange}>
                <option value="gh">GitHub issue URL</option>
                <option value="write">Write here</option>
              </select>
            </div>
            <div className="input-group mb-3">
              {getPsInput()}
            </div>
            <input type="text" className="form-control" placeholder="Enter repository path (optional when using GitHub issue)" onChange={(e) => setRepoPath(e.target.value)} />
          </div>
        </Tab>
        <Tab eventKey="model" title="Model">
          <div>Model settings coming soon.</div>
        </Tab>
        <Tab eventKey="settings" title="Extra Settings">
          <div className="p-3">
            <Form.Check 
              type="switch"
              id="custom-switch"
              label="Test run (no LM queries)"
              checked={testRun}
              onChange={(e) => setTestRun(e.target.checked)}
            />
          </div>
        </Tab>
      </Tabs>
    <div className="runControl">
      <div>
        <img src={logo} style={{height: 50, marginRight: 20}}/>
        <div class="btn-group" role="group" aria-label="Basic example">
          <button type="submit" className="btn btn-primary" onClick={handleSubmit} disabled={isComputing || !isConnected}><PlayFill/> Run</button>
          <button onClick={handleStop} disabled={!isComputing} className="btn btn-primary"><StopFill/> Stop</button>
        </div>
      </div>
      <div className="extraButtons">
        <div class="btn-group" role="group" aria-label="Basic example">
          <Link
            to="https://github.com/princeton-nlp/SWE-agent"
            target="_blank"
            rel="noopener noreferrer"
          >
            <button type="button" class="btn btn-outline-secondary">GitHub readme</button>
          </Link>
        </div>
      </div>
    </div>
  </div>
  );
}

export default LRunControl;