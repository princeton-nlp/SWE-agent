import React from 'react';

import "../static/message.css";
import "../static/envMessage.css";

import {
    Prism as SyntaxHighlighter,
  } from 'react-syntax-highlighter';
import bash from 'react-syntax-highlighter/dist/esm/languages/prism/bash';
import { prism } from 'react-syntax-highlighter/dist/esm/styles/prism';

// SyntaxHighlighter.registerLanguage('bash', bash);


const EnvMessage = ({ item, handleMouseEnter, handleMouseLeave, isHighlighted, feedRef}) => {
    const stepClass = item.step !== null ? `step${item.step}` : '';
    const highlightClass = isHighlighted ? 'highlight' : '';

    const customStyle = {
        margin: 0,
        padding: '0 0.5em',
        overflowX: 'hidden',
        lineHeight: 'inherit',
        backgroundColor: 'transparent',
    }

    const codeTagProps = {
        style: {
            boxShadow: "none",
            margin: "0",
            overflowY: "hidden",
            padding: "0.25em 0.5em 0.75em 0.5em",
            lineHeight: 'inherit',
            fontSize: 'inherit',
        }
    }

    const typeToLanguage = {
        "command": "bash",
        "output": "markdown",
        "diff": "diff",
    }

    if (item.type === "command" || item.type === "output") {
        return (
            <div 
                className={`message ${stepClass} ${highlightClass}`}
                onMouseEnter={() => handleMouseEnter(item, feedRef)}
                onMouseLeave={handleMouseLeave}
            >
                <SyntaxHighlighter
                    codeTagProps={codeTagProps}
                    customStyle={{customStyleMerged: customStyle, overflow: 'hidden'}}
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
                className={`message ${stepClass} ${highlightClass}`}
                onMouseEnter={() => handleMouseEnter(item, feedRef)}
            >
                <span>{item.message}</span>
            </div>
        );
    }
};

export default EnvMessage;