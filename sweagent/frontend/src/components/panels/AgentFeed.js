import React, { useEffect } from 'react';
import Message from '../AgentMessage';

import workspaceLogo from '../../assets/panel_icons/workspace.png';
import "../../static/agentFeed.css";

function useScrollToBottom(feed, ref) {
  useEffect(() => {
      if (ref.current) {
          ref.current.scrollTop = ref.current.scrollHeight;
      }
  }, [feed, ref]);
}

const AgentFeed = ({ feed, title, highlightedStep, handleMouseEnter, handleMouseLeave, selfRef, }) => {
    useScrollToBottom(feed, selfRef);

    return (
        <div id="agentFeed" className="agentFeed">
            <div id="label">
              <img src={workspaceLogo} alt="workspace" />
              <span>{title}</span>
            </div>
            <div className="scrollableDiv"  ref={selfRef} >
              <div className="innerDiv">
                {feed.map((item, index) => (
                    <Message
                        key={index}
                        item={item}
                        handleMouseEnter={handleMouseEnter}
                        handleMouseLeave={handleMouseLeave}
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

export default AgentFeed;
