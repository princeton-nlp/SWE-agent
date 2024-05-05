import React, { useEffect } from 'react';
import MacBar from '../MacBar';
import editorLogo from '../../assets/panel_icons/editor.png';
import { Button, OverlayTrigger, Tooltip } from 'react-bootstrap';
import { Clipboard } from 'react-bootstrap-icons';

const LogPanel = ({ logs, logsRef, setIsTerminalExpanded}) => {

  const copyToClipboard = (text) => {
    // Create a temporary textarea element
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);

    // Select and copy the text
    textarea.select();
    document.execCommand('copy');

    // Clean up
    document.body.removeChild(textarea);
  };

  const handleCopy = () => {
    const contentToCopy = document.getElementById('logContent').innerText;
    copyToClipboard(contentToCopy);
  };

    return (
        <div id="logPanel" className="logPanel">
            <div id="label">
              <img src={editorLogo} alt="log panel" />
              <span>Logs</span>
            </div>
            <MacBar
              barStyle={{
                background: "linear-gradient(to bottom, rgba(0,0,0,0.6), rgba(0,0,0,0.9))",
                height: "2em",
              }}
              messageStyle={{
                color: "white",
                fontSize: "smaller",
                marginBottom: "0.1em",
              }}
              expandFillColor={"black"}
              setIsExpanded={setIsTerminalExpanded}
            />
            <div className="scrollableDiv"  ref={logsRef} style={{ backgroundColor: "#1e1e1e" }}>
              <div className="innerDiv">
                <pre id="logContent">{logs}</pre>
                <div style={{ clear: "both", marginTop: '1em' }}/>
              </div>
              <OverlayTrigger
              placement="top"
              overlay={<Tooltip id="copy-tooltip">Copy to Clipboard</Tooltip>}
            >
              <Button variant="light" onClick={handleCopy}>
                <Clipboard />
              </Button>
            </OverlayTrigger>
            </div>
        </div>
    );
};

export default LogPanel;
