import React, { useState } from 'react';

function LRunControl({isComputing, isConnected, handleStop, handleSubmit, setDataPath, setTestRun, dataPath, testRun}) {
  return (
    <div>
      <form onSubmit={handleSubmit}>
        <label htmlFor="data_path">Data Path:</label>
        <input type="text" value={dataPath} onChange={(e) => setDataPath(e.target.value)} required />
        <label htmlFor="test_run">Test run (no LM queries)</label>
        <input type="checkbox" checked={testRun} onChange={(e) => setTestRun(e.target.checked)} />
        <button type="submit" disabled={isComputing || !isConnected}>Run</button>
      </form>
      <button onClick={handleStop} disabled={!isComputing}>Stop Computation</button>
    </div>
  );
}

export default LRunControl;