import React from 'react';

import "../static/message.css";
import "../static/agentMessage.css";
import {Gear} from 'react-bootstrap-icons';

const AgentMessage = ({ item, handleMouseEnter, handleMouseLeave, isHighlighted, feedRef }) => {
    const stepClass = item.step !== null ? `step${item.step}` : '';
    const highlightClass = isHighlighted ? 'highlight' : '';

    return (
        <div 
            className={`message ${item.format} ${stepClass} ${highlightClass}`}
            onMouseEnter={() => handleMouseEnter(item, feedRef)}
            onMouseLeave={handleMouseLeave}
        >
            { item.type !== "thought" && <Gear style={{marginRight: 5}}/>}
            <span>{item.message}</span>
        </div>
    );
};

export default AgentMessage;