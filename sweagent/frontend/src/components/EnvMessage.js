import React from 'react';

import "../static/message.css";
import "../static/envMessage.css";

import {
    Prism as SyntaxHighlighter,
    PrismLight as SyntaxHighlighterBash
  } from 'react-syntax-highlighter';
// import bash from 'react-syntax-highlighter/dist/esm/languages/prism/bash';
import { prism } from 'react-syntax-highlighter/dist/esm/styles/prism';

function capitalizeFirstLetter(str) {
    return str[0].toUpperCase() + str.slice(1);
  }


const EnvMessage = ({ item, handleMouseEnter, isHighlighted, feedRef}) => {
    const stepClass = item.step !== null ? `step${item.step}` : '';
    const highlightClass = isHighlighted ? 'highlight' : '';
    const messageTypeClass = "envMessage" + capitalizeFirstLetter(item.type);

    const textStyle={
        backgroundColor: '#f5f2f0',
        boxShadow: "none",
        margin: "0",
        overflowY: "hidden",
        padding: "0.25em 0.5em 0.75em 0.5em",
    }
    
    const customStyle={
        backgroundColor: 'inherit',
    }


    const customStyleMerged = {
        margin: 0,
        padding: '0 0.5em',
        overflowX: 'hidden',
        lineHeight: 'inherit',
        ...customStyle,
    }

    const codeTagProps = {
        style: {
            lineHeight: 'inherit',
            fontSize: 'inherit',
            ...textStyle,
        }
    }

    if (item.type === "command" || item.type === "output") {
        const language = item.type === "command" ? "bash" : "markdown";
        return (
            <div 
                className={`message ${item.format} ${stepClass} ${highlightClass} ${messageTypeClass}`}
                onMouseEnter={() => handleMouseEnter(item, feedRef)}
            >
                <SyntaxHighlighterBash
                    codeTagProps={codeTagProps}
                    customStyle={customStyleMerged}
                    language={language}
                    lineProps={{ style: {wordBreak: 'break-word', whiteSpace: 'pre-wrap'} }}
                    style={prism}
                    wrapLines={true}
                    showLineNumbers={false}
                >
                    {item.message}
                </SyntaxHighlighterBash>
            </div>
        );
    } else {
        return (
            <div 
                className={`message ${item.format} ${stepClass} ${highlightClass} ${messageTypeClass}`}
                onMouseEnter={() => handleMouseEnter(item, feedRef)}
            >
                <span>{item.message}</span>
            </div>
        );
    }
};

export default EnvMessage;