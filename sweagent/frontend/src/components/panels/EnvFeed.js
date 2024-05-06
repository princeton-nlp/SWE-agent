import React, { useEffect } from 'react';
import EnvMessage from '../EnvMessage';

import MacBar from '../MacBar';
import terminalLogo from '../../assets/panel_icons/terminal.png';
import "../../static/envFeed.css";

function useScrollToBottom(feed, ref) {
  useEffect(() => {
      if (ref.current) {
          ref.current.scrollTop = ref.current.scrollHeight;
      }
  }, [feed, ref]);
}

const EnvFeed = ({ feed, id, title, highlightedStep, handleMouseEnter, selfRef, setIsTerminalExpanded}) => {
    useScrollToBottom(feed, selfRef);

    return (
        <div id="envFeed" className="envFeed">
            <div id="label">
              <img src={terminalLogo} alt="workspace" />
              <span>{title}</span>
            </div>
            <MacBar
              barStyle={{ height: "2em" }}
              expandFillColor={"black"}
              setIsExpanded={setIsTerminalExpanded}
            />
            <div className="scrollableDiv"  ref={selfRef} >
              <div className="innerDiv">
                {feed.map((item, index) => (
                    <EnvMessage
                        key={index}
                        item={item}
                        handleMouseEnter={handleMouseEnter}
                        isHighlighted={item.step !== null && highlightedStep === item.step}
                        feedRef={selfRef}
                    />
                ))}
                <div style={{ clear: "both", marginTop: '1em' }}/>
              </div>
            </div>
        </div>
    );
};

export default EnvFeed;
