import React from 'react';

import {
    BrowserRouter as Router,
    Switch,
    Route,
} from "react-router-dom";
import { connect } from 'react-redux'

import Navigation from './Navigation';
import Feed from './Feed';
import NewPostForm from './NewPostForm';
import { feedFetchRequest } from "../store/actions";

class App extends React.Component {
  refreshFeed() {
    this.props.dispatch(feedFetchRequest());
  }
  render() {
    return (
      <Router>
        <Navigation />
        <div className="content_container">
          <Switch>
            <Route path="/new">
              <NewPostForm />
            </Route>
            <Route path="/">
              <Feed />
              <button onClick={this.refreshFeed.bind(this)}>refresh</button>
            </Route>
          </Switch>
        </div>
      </Router>
    );
  }
}

export default connect()(App);
