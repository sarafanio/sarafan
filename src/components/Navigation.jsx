import React from 'react';
import { Link } from 'react-router-dom';

import './Navigation.css';


class Navigation extends React.Component {
  render() {
    return (
      <div id="navigation">
        <div className="content_container">
          <span className="logo">
            <Link to="/">
              Sarafan
            </Link>
          </span>
          <Link to="/new">new post</Link>
        </div>
      </div>
    );
  }
}

export default Navigation;
