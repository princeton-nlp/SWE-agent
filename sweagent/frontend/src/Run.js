import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import io from "socket.io-client";
import "./static/run.css";
import AgentFeed from "./components/panels/AgentFeed";
import EnvFeed from "./components/panels/EnvFeed";
import LogPanel from "./components/panels/LogPanel";
import LRunControl from "./components/controls/LRunControl";

const url = ""; // Will get this from .env
// Connect to Socket.io
const socket = io(url);

function Run() {
  const [isConnected, setIsConnected] = useState(socket.connected);
  const [errorBanner, setErrorBanner] = useState("");

  const [dataPath, setDataPath] = useState(
    "https://github.com/marshmallow-code/marshmallow/issues/1359",
  );
  const [repoPath, setRepoPath] = useState("");
  const [model, setModel] = useState("gpt4");
  const envConfigDefault = { python: "3.10" };
  const [envConfig, setEnvConfig] = useState(envConfigDefault);
  const [testRun, setTestRun] = useState(false);
  const [agentFeed, setAgentFeed] = useState([]);
  const [envFeed, setEnvFeed] = useState([]);
  const [highlightedStep, setHighlightedStep] = useState(null);
  const [logs, setLogs] = useState("");
  const [isComputing, setIsComputing] = useState(false);

  const hoverTimeoutRef = useRef(null);

  const agentFeedRef = useRef(null);
  const envFeedRef = useRef(null);
  const logsRef = useRef(null);

  const [tabKey, setTabKey] = useState("problem");

  const stillComputingTimeoutRef = useRef(null);

  axios.defaults.baseURL = url;

  function scrollToHighlightedStep(highlightedStep, ref) {
    if (highlightedStep && ref.current) {
      console.log(
        "Scrolling to highlighted step",
        highlightedStep,
        ref.current,
      );
      const firstStepMessage = ref.current.querySelector(
        `.step${highlightedStep}`,
      );
      if (firstStepMessage) {
        window.requestAnimationFrame(() => {
          ref.current.scrollTo({
            top: firstStepMessage.offsetTop - ref.current.offsetTop,
            behavior: "smooth",
          });
        });
      }
    }
  }

  function getOtherFeed(feedRef) {
    return feedRef === agentFeedRef ? envFeedRef : agentFeedRef;
  }

  const handleMouseEnter = (item, feedRef) => {
    if (isComputing) {
      return;
    }

    const highlightedStep = item.step;

    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }

    hoverTimeoutRef.current = setTimeout(() => {
      if (!isComputing) {
        setHighlightedStep(highlightedStep);
        scrollToHighlightedStep(highlightedStep, getOtherFeed(feedRef));
      }
    }, 250);
  };

  const handleMouseLeave = () => {
    console.log("Mouse left");
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }
    setHighlightedStep(null);
  };

  const requeueStopComputeTimeout = () => {
    clearTimeout(stillComputingTimeoutRef.current);
    setIsComputing(true);
    stillComputingTimeoutRef.current = setTimeout(() => {
      setIsComputing(false);
      console.log("No activity for 30s, setting isComputing to false");
    }, 30000);
  };

  // Handle form submission
  const handleSubmit = async (event) => {
    setTabKey(null);
    setIsComputing(true);
    event.preventDefault();
    setAgentFeed([]);
    setEnvFeed([]);
    setLogs("");
    setHighlightedStep(null);
    setErrorBanner("");
    try {
      await axios.get(`/run`, {
        params: {
          data_path: dataPath,
          test_run: testRun,
          repo_path: repoPath,
          model: model,
          environment: JSON.stringify(envConfig),
        },
      });
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const handleStop = async () => {
    setIsComputing(false);
    try {
      const response = await axios.get("/stop");
      console.log(response.data);
    } catch (error) {
      console.error("Error stopping:", error);
    }
  };

  // Use effect to listen to socket updates
  React.useEffect(() => {
    const handleUpdate = (data) => {
      requeueStopComputeTimeout();
      if (data.feed === "agent") {
        setAgentFeed((prevMessages) => [
          ...prevMessages,
          {
            type: data.type,
            message: data.message,
            format: data.format,
            step: data.thought_idx,
          },
        ]);
      } else if (data.feed === "env") {
        setEnvFeed((prevMessages) => [
          ...prevMessages,
          {
            message: data.message,
            type: data.type,
            format: data.format,
            step: data.thought_idx,
          },
        ]);
      }
    };

    const scrollLog = () => {
      logsRef.current.scrollTop = logsRef.current.scrollHeight;
    };

    const handleLogMessage = (data) => {
      requeueStopComputeTimeout();
      setLogs((prevLogs) => prevLogs + data.message);
      if (data.level === "critical") {
        console.log("Critical error", data.message);
        setErrorBanner("Critical errror encountered: " + data.message);
      }
      if (logsRef.current) {
        setTimeout(() => {
          scrollLog();
        }, 100);
      }
    };

    const handleFinishedRun = (data) => {
      setIsComputing(false);
    };

    socket.on("update", handleUpdate);
    socket.on("log_message", handleLogMessage);
    socket.on("finish_run", handleFinishedRun);
    socket.on("connect", () => {
      console.log("Connected to server");
      setIsConnected(true);
      setErrorBanner("");
    });

    socket.on("disconnect", () => {
      console.log("Disconnected from server");
      setIsConnected(false);
      setErrorBanner("Connection to flask server lost, please restart it.");
      setIsComputing(false);
      scrollLog(); // reveal copy button
    });

    socket.on("connect_error", (error) => {
      setIsConnected(false);
      setErrorBanner(
        "Failed to connect to the flask server, please restart it.",
      );
      setIsComputing(false);
      scrollLog(); // reveal copy button
    });

    return () => {
      socket.off("update", handleUpdate);
      socket.off("log_message", handleLogMessage);
      socket.off("finish_run", handleFinishedRun);
      socket.off("connect");
      socket.off("disconnect");
      socket.off("connect_error");
    };
  }, []);

  function renderErrorMessage() {
    if (errorBanner) {
      return (
        <div className="alert alert-danger" role="alert">
          {errorBanner}
          <br />
          If you think this was a bug, please head over to{" "}
          <a
            href="https://github.com/princeton-nlp/swe-agent/issues"
            target="blank"
          >
            our GitHub issue tracker
          </a>
          , check if someone has already reported the issue, and if not, create
          a new issue. Please include the full log, all settings that you
          entered, and a screenshot of this page.
        </div>
      );
    }
    return null;
  }

  return (
    <div className="container-demo">
      {renderErrorMessage()}
      <LRunControl
        isComputing={isComputing}
        isConnected={isConnected}
        handleStop={handleStop}
        handleSubmit={handleSubmit}
        setDataPath={setDataPath}
        setTestRun={setTestRun}
        setRepoPath={setRepoPath}
        testRun={testRun}
        setModel={setModel}
        tabKey={tabKey}
        setTabKey={setTabKey}
        envConfig={envConfig}
        setEnvConfig={setEnvConfig}
        envConfigDefault={envConfigDefault}
      />
      <div id="demo">
        <hr />
        <div className="panels">
          <AgentFeed
            feed={agentFeed}
            highlightedStep={highlightedStep}
            handleMouseEnter={handleMouseEnter}
            handleMouseLeave={handleMouseLeave}
            selfRef={agentFeedRef}
            otherRef={envFeedRef}
          />
          <EnvFeed
            feed={envFeed}
            highlightedStep={highlightedStep}
            handleMouseEnter={handleMouseEnter}
            handleMouseLeave={handleMouseLeave}
            selfRef={envFeedRef}
            otherRef={agentFeedRef}
          />
          <LogPanel logs={logs} logsRef={logsRef} isComputing={isComputing} />
        </div>
      </div>
      <hr />
    </div>
  );
}

export default Run;
