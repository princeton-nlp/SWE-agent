import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import io from 'socket.io-client';
import './App.css';

const url = ''; // Will get this from .env 
// Connect to Socket.io
const socket = io(url);

function App() {
  const [dataPath, setDataPath] = useState('https://github.com/klieret/swe-agent-test-repo/issues/1');
  const [testRun, setTestRun] = useState(true);
  const [agentFeed, setAgentFeed] = useState([]);
  const [envFeed, setEnvFeed] = useState([]);
  const [highlightedStep, setHighlightedStep] = useState(null);
  const [logs, setLogs] = useState('');
  const [isComputing, setIsComputing] = useState(false);

  const agentFeedRef = useRef(null);
  const envFeedRef = useRef(null);
  const logsRef = useRef(null);

  axios.defaults.baseURL = url;

  const handleMouseEnter = (step) => {
    setHighlightedStep(step);
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
      const updateFeed = data.feed === 'agent' ? setAgentFeed : setEnvFeed;
      updateFeed(prevMessages => [...prevMessages, { title: data.title, message: data.message, format: data.format, step: data.thought_idx }]);
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
    <div>
      <h1>Start run</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="data_path">Data Path:</label>
        <input type="text" value={dataPath} onChange={(e) => setDataPath(e.target.value)} required />
        <label htmlFor="test_run">Test run (no LM queries)</label>
        <input type="checkbox" checked={testRun} onChange={(e) => setTestRun(e.target.checked)} />
        <button type="submit" disabled={isComputing}>Run</button>
      </form>
      <button onClick={handleStop} disabled={!isComputing}>Stop Computation</button>
      <h2>Trajectory</h2>
      <div id="container">
        <Feed feed={agentFeed} highlightedStep={highlightedStep} handleMouseEnter={handleMouseEnter} selfRef={agentFeedRef} otherRef={envFeedRef}  title="Agent Feed" />
        <Feed feed={envFeed} highlightedStep={highlightedStep} handleMouseEnter={handleMouseEnter} selfRef={envFeedRef} otherRef={agentFeedRef} title="Environment Feed" />
      </div>
      <div id="log" ref={logsRef}>
        <h3>Logs</h3>
        <pre >{logs}</pre>
      </div>
    </div>
  );
}

const Feed = ({ feed, title, highlightedStep, handleMouseEnter, selfRef, otherRef }) => {
  // Scroll to the bottom of the feed whenever the feed data changes
  useEffect(() => {
      if (selfRef.current) {
          selfRef.current.scrollTop = selfRef.current.scrollHeight;
      }
  }, [feed]);

  // Scroll to the first message of the highlighted step from the other feed
  useEffect(() => {
    if (highlightedStep && otherRef.current) {
      const firstStepMessage = [...otherRef.current.children].find(
        child => child.classList.contains(`step${highlightedStep}`)
      );
      if (firstStepMessage) {
        window.requestAnimationFrame(() => {
          otherRef.current.scrollTo({
            top: firstStepMessage.offsetTop - otherRef.current.offsetTop,
            behavior: 'smooth'
          });
        });
      }
    }
  }, [highlightedStep, otherRef]);


  const feedID = title.toLowerCase().replace(' ', '');

  return (
    <div id={feedID} ref={selfRef} >
      <h3>{title}</h3>
      {feed.map((item, index) => (
        <div key={index} 
          className={`message ${item.format} step${item.step} ${highlightedStep === item.step ? 'highlight' : ''}`}
          onMouseEnter={() => handleMouseEnter(item.step)}
        >
          <h4>{item.title}</h4>
          {item.message}
        </div>
      ))}
    </div>
  )
};

export default App;

