import React, { useState } from 'react';
import Accordion from 'react-bootstrap/Accordion';
import Form from 'react-bootstrap/Form';

function LRunControl({isComputing, isConnected, handleStop, handleSubmit, setDataPath, setTestRun, dataPath, testRun, repoPath, setRepoPath}) {
  const [psType, setPsType] = useState('gh');

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
    <Accordion defaultActiveKey="0">
      <Accordion.Item eventKey="0">
        <Accordion.Header>Problem statement</Accordion.Header>
        <Accordion.Body>
            <div class="input-group mb-3">
              <span class="input-group-text" >Problem statement</span>
              <select class="form-select" aria-label="Select problem statement type" onChange={handlePsTypeChange} >
                <option value="gh" selected>GitHub issue URL</option>
                <option value="write">Write here</option>
              </select>
              {getPsInput()}
            </div>
            <div class="input-group mb-3">
              <span class="input-group-text" >Repository path</span>
              <input type="text" class="form-control" placeholder="Enter repository path (optional when using GitHub issue)" onChange={(e) => setRepoPath(e.target.value)}  /> 
            </div>
            {/* <input type="text" value={dataPath} onChange={(e) => setDataPath(e.target.value)} required /> */}
        </Accordion.Body>
      </Accordion.Item>
      <Accordion.Item eventKey="1">
        <Accordion.Header>Extra settings</Accordion.Header>
        <Accordion.Body>
            <Form.Check // prettier-ignore
              type="switch"
              id="custom-switch"
              label="Test run (no LM queries)"
              defaultChecked={testRun}
              onChange={(e) => setTestRun(e.target.checked)}
          />
          </Accordion.Body>
      </Accordion.Item>
    </Accordion>
    <div class="btn-group" role="group" aria-label="Basic example">
      <button type="submit" className="btn btn-primary" onClick={handleSubmit} disabled={isComputing || !isConnected}>Run</button>
      <button onClick={handleStop} disabled={!isComputing} className="btn btn-primary">Stop</button>
    </div>
  </div>
  );
}

export default LRunControl;