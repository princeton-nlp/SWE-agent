import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import io from 'socket.io-client';
import './App.css';

// Connect to Socket.io
const socket = io(); // Adjust the URL based on your Flask server

function App() {
  const [dataPath, setDataPath] = useState('https://github.com/klieret/swe-agent-test-repo/issues/1');
  const [testRun, setTestRun] = useState(true);
  const [responseMessage, setResponseMessage] = useState('');
  const [agentFeed, setAgentFeed] = useState([]);
  const [envFeed, setEnvFeed] = useState([]);

  // Handle form submission
  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      const response = await axios.get(`/run`, { params: { data_path: dataPath, test_run: testRun } });
      setResponseMessage(response.data);
      setAgentFeed([]); // Clear the agent feed messages
      setEnvFeed([]); // Clear the environment feed messages
    } catch (error) {
      console.error('Error:', error);
    }
  };

  // Use effect to listen to socket updates
  React.useEffect(() => {
    socket.on('update', (data) => {
      const updateFeed = data.feed === 'agent' ? setAgentFeed : setEnvFeed;
      updateFeed(prevMessages => [...prevMessages, { title: data.title, message: data.message, format: data.format }]);
    });
  }, []);

  return (
    <div>
      <h1>Start run</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="data_path">Data Path:</label>
        <input type="text" value={dataPath} onChange={(e) => setDataPath(e.target.value)} required />
        <label htmlFor="test_run">Test run (no LM queries)</label>
        <input type="checkbox" checked={testRun} onChange={(e) => setTestRun(e.target.checked)} />
        <button type="submit">Run</button>
      </form>
      <div>{responseMessage}</div>
      <h2>Trajectory</h2>
      <div id="container">
        <Feed feed={agentFeed} title="Agent Feed" />
        <Feed feed={envFeed} title="Environment Feed" />
      </div>
    </div>
  );
}

const Feed = ({ feed, title }) => {
  const feedRef = useRef(null); // Create a ref for the feed container

  // Scroll to the bottom of the feed whenever the feed data changes
  useEffect(() => {
      if (feedRef.current) {
          feedRef.current.scrollTop = feedRef.current.scrollHeight;
      }
  }, [feed]); // Dependency array includes 'feed' to trigger the effect when it changes


  return (
    <div id={`${title.toLowerCase().replace(' ', '')}`} ref={feedRef} >
      <h3>{title}</h3>
      {feed.map((item, index) => (
        <div key={index} className={`message ${item.format}`}>
          <h4>{item.title}</h4>
          {item.message}
        </div>
      ))}
    </div>
  )
};

export default App;

