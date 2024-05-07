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

const EnvFeed = ({ feed,  highlightedStep, handleMouseEnter, handleMouseLeave, selfRef}) => {
    useScrollToBottom(feed, selfRef);

    return (
        <div id="envFeed" className="envFeed">
            <MacBar
              title="Terminal"
              logo={terminalLogo}
              dark={false}
            />
            <div className="scrollableDiv"  ref={selfRef} >
              <div className="innerDiv">
                {feed.map((item, index) => (
                    <EnvMessage
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

export default EnvFeed;
