import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import io from 'socket.io-client';
import './static/run.css';
import AgentFeed from './components/panels/AgentFeed';
import EnvFeed from './components/panels/EnvFeed';
import LogPanel from './components/panels/LogPanel';

const url = ''; // Will get this from .env 
// Connect to Socket.io
const socket = io(url);

function Run() {
  const [dataPath, setDataPath] = useState('https://github.com/klieret/swe-agent-test-repo/issues/1');
  const [testRun, setTestRun] = useState(true);
  const [agentFeed, setAgentFeed] = useState([]);
  const [envFeed, setEnvFeed] = useState([]);
  const [highlightedStep, setHighlightedStep] = useState(null);
  const [logs, setLogs] = useState('');
  const [isComputing, setIsComputing] = useState(false);

  const [isTerminalExpanded, setIsTerminalExpanded] = useState(false);
  const [isLogsExpanded, setIsLogsExpanded] = useState(false);

  const agentFeedRef = useRef(null);
  const envFeedRef = useRef(null);
  const logsRef = useRef(null);

  axios.defaults.baseURL = url;


  function scrollToHighlightedStep(highlightedStep, ref) {
    if (highlightedStep && ref.current) {
        console.log('Scrolling to highlighted step', highlightedStep, ref.current);
        const firstStepMessage = ref.current.querySelector(`.step${highlightedStep}`);
        if (firstStepMessage) {
            window.requestAnimationFrame(() => {
                ref.current.scrollTo({
                    top: firstStepMessage.offsetTop - ref.current.offsetTop,
                    behavior: 'smooth'
                });
            });
        }
    }
  }

  function getOtherFeed(feedRef) {
    return feedRef === agentFeedRef ? envFeedRef : agentFeedRef;
  }

  const handleMouseEnter = (item, feedRef) => {
    const highlightedStep = item.step;
    if (!isComputing) {
      setHighlightedStep(highlightedStep);
      scrollToHighlightedStep(highlightedStep, getOtherFeed(feedRef));
    }
  };


  // Handle form submission
  const handleSubmit = async (event) => {
    setIsComputing(true);
    event.preventDefault();
    setAgentFeed([]);
    setEnvFeed([]); 
    setLogs('');
    try {
      await axios.get(`/run`, { params: { data_path: dataPath, test_run: testRun } });
    } catch (error) {
      console.error('Error:', error);
    }
  };


  const handleStop = async () => {
    setIsComputing(false);
    try {
        const response = await axios.get('/stop');
        console.log(response.data);
    } catch (error) {
        console.error('Error stopping:', error);
    }
  };

  // Use effect to listen to socket updates
  React.useEffect(() => {
    const handleUpdate = (data) => {
      if (data.feed === 'agent') {
        setAgentFeed(prevMessages => [...prevMessages, { title: data.title, message: data.message, format: data.format, step: data.thought_idx }]);
      }
      else if (data.feed === "env") {
        setEnvFeed(prevMessages => [...prevMessages, { message: data.message, type: data.type, format: data.format, step: data.thought_idx }]);
      }
    };

    const handleLogMessage = (data) => {
      setLogs(prevLogs => prevLogs + data.message);
      if (logsRef.current) {
        
        setTimeout(() => {
          logsRef.current.scrollTop = logsRef.current.scrollHeight;
          console.log('Scrolling to bottom', logsRef.current.scrollHeight);
        }, 100);
      }
    }

    const handleFinishedRun = (data) => {
      setIsComputing(false);
    }

    socket.on('update', handleUpdate);
    socket.on('log_message', handleLogMessage);
    socket.on('finish_run', handleFinishedRun);

    return () => {
        socket.off('update', handleUpdate);
        socket.off('log_message', handleLogMessage);
        socket.off('finish_run', handleFinishedRun);
    };
  }, []);

  return (
      
          <div className="container-demo">
            <hr />
            <form onSubmit={handleSubmit}>
              <label htmlFor="data_path">Data Path:</label>
              <input type="text" value={dataPath} onChange={(e) => setDataPath(e.target.value)} required />
              <label htmlFor="test_run">Test run (no LM queries)</label>
              <input type="checkbox" checked={testRun} onChange={(e) => setTestRun(e.target.checked)} />
              <button type="submit" disabled={isComputing}>Run</button>
            </form>
            <button onClick={handleStop} disabled={!isComputing}>Stop Computation</button>
            <div id="demo">
              <hr />
              <div className="panels">
                <AgentFeed feed={agentFeed} id="agent" highlightedStep={highlightedStep} handleMouseEnter={handleMouseEnter} selfRef={agentFeedRef} otherRef={envFeedRef} title="Agent Feed" />
                <EnvFeed feed={envFeed} id="env" highlightedStep={highlightedStep} handleMouseEnter={handleMouseEnter} selfRef={envFeedRef} otherRef={agentFeedRef} setIsTerminalExpanded={setIsTerminalExpanded} title="Environment Feed" />
                <LogPanel logs={logs} logsRef={logsRef} setIsTerminalExpanded={setIsLogsExpanded} />
              </div>
            </div>
          <hr />
          </div>
       
  );
}

export default Run;

