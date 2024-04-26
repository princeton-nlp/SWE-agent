import React, { useEffect } from 'react';
import Message from '../AgentMessage';

import MacBar from '../MacBar';
import editorLogo from '../../assets/panel_icons/editor.png';

const LogPanel = ({ logs, logsRef, setIsTerminalExpanded}) => {


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
                <pre>{logs}</pre>
                <div style={{ clear: "both", marginTop: '1em' }}/>
              </div>
            </div>
        </div>
    );
};

export default LogPanel;
