import React, { useEffect } from 'react';
import Message from '../AgentMessage';
import MacBar from '../MacBar';
import workspaceLogo from '../../assets/panel_icons/workspace.png';
import "../../static/agentFeed.css";

function useScrollToBottom(feed, ref) {
  useEffect(() => {
      if (ref.current) {
          ref.current.scrollTop = ref.current.scrollHeight;
      }
  }, [feed, ref]);
}

const AgentFeed = ({ feed, highlightedStep, handleMouseEnter, handleMouseLeave, selfRef, }) => {
    useScrollToBottom(feed, selfRef);

    return (
        <div id="agentFeed" className="agentFeed">
          <MacBar
              title="Agent"
              logo={workspaceLogo}
            />
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
