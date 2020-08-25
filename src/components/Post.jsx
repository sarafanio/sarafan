import React from 'react';


export default class Post extends React.Component {
  render() {
    return (
      <div className="feed_post">
        <h1>Post {this.props.post.magnet} title</h1>
        <p>Post content: {this.props.post.content}</p>
      </div>
    );
  }
}
