import React from 'react';

import "../static/message.css";

const AgentMessage = ({ item, handleMouseEnter, isHighlighted, feedRef }) => {
    const stepClass = item.step !== null ? `step${item.step}` : '';
    const highlightClass = isHighlighted ? 'highlight' : '';

    return (
        <div 
            className={`message ${item.format} ${stepClass} ${highlightClass}`}
            onMouseEnter={() => handleMouseEnter(item, feedRef)}
        >
            { item.title && <h4>{item.title}</h4>}
            <span>{item.message}</span>
        </div>
    );
};

export default AgentMessage;