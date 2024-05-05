import React from "react";
import PropTypes from "prop-types"; // Import PropTypes for type checking

import ExpandIcon from "./utils/icons/ExpandIcon";
import "../static/macbar.css";

import Message from './AgentMessage';

const MacBar = ({
  setIsTyping,
  text,
  barStyle,
  messageStyle,
  setIsExpanded,
  expandFillColor,
  showIcons = true,
}) => {
  const messageStyleMerged = {
    backgroundColor: "transparent",
    boxShadow: "none",
    color: "black",
    left: "50%",
    fontSize: "smaller",
    margin: "0em",
    padding: "0em",
    position: 'absolute',
    transform: "translateX(-50%)",
    ...messageStyle,
  };

  const expandFillColorMerged = expandFillColor || "#ffffff";

  return (
    <div className="mac-window-top-bar" style={barStyle}>
      {showIcons && (
        <>
          <div className="mac-window-button close"></div>
          <div className="mac-window-button minimize"></div>
          <div className="mac-window-button expand"></div>
        </>
      )}
      {!!text && <Message
        animationType="type"
        id="title"
        onTypingEnd={() => {setIsTyping(false)}}
        onTypingStart={() => {setIsTyping(true)}}
        style={messageStyleMerged}
        text={text}
      />}
      {!!setIsExpanded && (
        <div
          style={{ position: "absolute", right: "0em" }}
          onClick={() => setIsExpanded((prev) => !prev)}
        >
          {/* <ExpandIcon
            fillColor={expandFillColorMerged}
            height="0.75em"
            style={{ marginRight: "0.75em", cursor: "pointer" }}
          /> */}
        </div>
      )}
    </div>
  );
};

// PropTypes for type checking
MacBar.propTypes = {
  setIsTyping: PropTypes.func,
  text: PropTypes.string,
  barStyle: PropTypes.object,
  messageStyle: PropTypes.object,
  setIsExpanded: PropTypes.func,
};

export default MacBar;
