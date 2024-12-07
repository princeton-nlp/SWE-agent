import React from "react";
import "../static/header.css";
import logo from "../assets/logo.png";
import { Link } from "react-router-dom";

const Header = () => {
  return (
    <>
      <header>
        <Link
          to="https://github.com/SWE-agent/SWE-agent"
          target="_blank"
          rel="noopener noreferrer"
        >
          <img
            src={logo}
            style={{ height: 50, marginRight: 20 }}
            alt="swe agent logo"
          />
        </Link>
        {/* <Link to="/">
          <button>Home</button>
        </Link>
        <Link
          to="https://discord.gg/AVEFbBn2rH"
          target="_blank"
          rel="noopener noreferrer"
        >
          <button>Discord</button>
        </Link> */}
      </header>
    </>
  );
};

export default Header;
