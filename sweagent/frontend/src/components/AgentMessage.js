import React from "react";

import "../static/message.css";
import "../static/agentMessage.css";
import { Gear } from "react-bootstrap-icons";
import Markdown from "react-markdown";

const AgentMessage = ({
  item,
  handleMouseEnter,
  handleMouseLeave,
  isHighlighted,
  feedRef,
}) => {
  const stepClass = item.step !== null ? `step${item.step}` : "";
  const highlightClass = isHighlighted ? "highlight" : "";

  return (
    <div
      className={`message ${item.format} ${stepClass} ${highlightClass}`}
      onMouseEnter={() => handleMouseEnter(item, feedRef)}
      onMouseLeave={handleMouseLeave}
    >
      {item.type !== "thought" && <Gear style={{ marginRight: 5 }} />}
      <Markdown components={{ p: "span" }}>{item.message}</Markdown>
    </div>
  );
};

export default AgentMessage;
