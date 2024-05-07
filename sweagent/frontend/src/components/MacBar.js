import React from "react";

import "../static/macbar.css";


const MacBar = ({
  title,
  logo,
  dark=false
}) => {
  const darkClass = dark ? 'dark' : '';
  return (
    <div className={`mac-window-top-bar ${darkClass}`} >
       <div id="label">
          <img src={logo} alt="title" />
          <span>{title}</span>
        </div>
    </div>
  );
};

export default MacBar;
