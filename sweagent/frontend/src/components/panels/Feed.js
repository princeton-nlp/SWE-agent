import React, { useEffect } from 'react';

const Feed = ({ feed, title, highlightedStep, handleMouseEnter, selfRef, otherRef, isComputing }) => {
    // Scroll to the bottom of the feed whenever the feed data changes
    useEffect(() => {
        if (selfRef.current) {
            selfRef.current.scrollTop = selfRef.current.scrollHeight;
        }
    }, [feed, selfRef]);
  
    // Scroll to the first message of the highlighted step from the other feed
    useEffect(() => {
      if (!isComputing && highlightedStep && otherRef.current) {
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
    }, [highlightedStep, otherRef, isComputing]);
  
  
    const feedID = title.toLowerCase().replace(' ', '');
  
    return (
      <div id={feedID} ref={selfRef} >
        <h3>{title}</h3>
        {feed.map((item, index) => {
          const stepClass = item.step !== null ? `step${item.step}` : '';
          const highlightClass = item.step !== null && highlightedStep === item.step ? 'highlight' : '';
          return (
            <div key={index} 
              className={`message ${item.format} ${stepClass} ${highlightClass}`}
              onMouseEnter={() => handleMouseEnter(item.step)}
            >
              <h4>{item.title}</h4>
              {item.message}
            </div>
          );
        }
        )}
      </div>
    )
};

export default Feed;