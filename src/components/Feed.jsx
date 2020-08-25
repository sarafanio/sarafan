import React from 'react';
import Post from './Post';
import { connect } from "react-redux";


class Feed extends React.Component {
  render() {
    return (
      <div id="feed">
        <p>Feed:</p>
        {this.props.publications.map((post, index) => (
          <Post key={index} post={post} />
        ))}
      </div>
    );
  }
}

const mapStateToProps = state => {
  return {
    publications: state.publications
  }
}
const mapDispatchToProps = dispatch => {
  return {
    // onTodoClick: id => {
    //   dispatch(toggleTodo(id))
    // }
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(Feed)