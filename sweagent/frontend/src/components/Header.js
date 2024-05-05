import React from "react";
import "../static/header.css";
import { Link } from 'react-router-dom';

const Header = () => {
  return (
    <>
      <header>
        <Link to="/">
          <button>Home</button>
        </Link>
        <Link
          to="https://discord.gg/AVEFbBn2rH"
          target="_blank"
          rel="noopener noreferrer"
        >
          <button>Discord</button>
        </Link>
      </header>
    </>
  );
};

export default Header;