import React, { useEffect } from 'react';
import Message from '../Message';

import MacBar from '../MacBar';
import terminalLogo from '../../assets/panel_icons/terminal.png';

function useScrollToBottom(feed, ref) {
  useEffect(() => {
      if (ref.current) {
          ref.current.scrollTop = ref.current.scrollHeight;
      }
  }, [feed, ref]);
}

const EnvFeed = ({ feed, id, title, highlightedStep, handleMouseEnter, selfRef, setIsTerminalExpanded}) => {
    useScrollToBottom(feed, selfRef);

    const feedID = id + "Feed";

    return (
        <div id={feedID} className={feedID}>
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
                    <Message
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
