import React from 'react';

import "../static/message.css";
import "../static/envMessage.css";

import {
    Prism as SyntaxHighlighter,
  } from 'react-syntax-highlighter';
import bash from 'react-syntax-highlighter/dist/esm/languages/prism/bash';
import { prism } from 'react-syntax-highlighter/dist/esm/styles/prism';

// SyntaxHighlighter.registerLanguage('bash', bash);

function capitalizeFirstLetter(str) {
    return str[0].toUpperCase() + str.slice(1);
}


const EnvMessage = ({ item, handleMouseEnter, handleMouseLeave, isHighlighted, feedRef}) => {
    const stepClass = item.step !== null ? `step${item.step}` : '';
    const highlightClass = isHighlighted ? 'highlight' : '';
    const messageTypeClass = "envMessage" + capitalizeFirstLetter(item.type);

    const paddingBottom = item.type === "command" ? "0" : "0.5em";
    const paddingTop = ["output", "diff"].includes(item.type) ? "0" : "0.5em";

    const customStyle = {
        margin: 0,
        padding: `${paddingTop} 0.5em ${paddingBottom} 0.5em`,
        overflowX: 'hidden',
        lineHeight: 'inherit',
        backgroundColor: 'transparent',
    }

    const codeTagProps = {
        style: {
            boxShadow: "none",
            margin: "0",
            overflowY: "hidden",
            padding: "0",
            lineHeight: 'inherit',
            fontSize: 'inherit',
        }
    }

    const typeToLanguage = {
        "command": "bash",
        "output": "markdown",
        "diff": "diff",
    }

    if (item.type !== "text") {
        return (
            <div 
                className={`message ${stepClass} ${highlightClass}  ${messageTypeClass}`}
                onMouseEnter={() => handleMouseEnter(item, feedRef)}
                onMouseLeave={handleMouseLeave}
            >
                <SyntaxHighlighter
                    codeTagProps={codeTagProps}
                    customStyle={customStyle}
                    language={typeToLanguage[item.type]}
                    // lineProps={{ style: {wordBreak: 'break-word', whiteSpace: 'normal'} }}
                    style={{backgroundColor: 'transparent', ...prism}}
                    wrapLines={true}
                    showLineNumbers={false}
                >
                    {item.message}
                </SyntaxHighlighter>
            </div>
        );
    } else {
        return (
            <div 
                className={`message ${stepClass} ${highlightClass} ${messageTypeClass}`}
                onMouseEnter={() => handleMouseEnter(item, feedRef)}
            >
                <span>{item.message}</span>
            </div>
        );
    }
};

export default EnvMessage;