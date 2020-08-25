import React from 'react';
import { connect } from "react-redux";
import { createPostRequest, publishEstimatedPost } from "../store/actions";

class NewPostForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {text: '', privateKey: '', estimated: false}

    this.handleTextChange = this.handleTextChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleKeyChange = this.handleKeyChange.bind(this);
  }
  handleTextChange(event) {
    this.setState({...this.state, text: event.target.value, estimated: false});
  }
  handleKeyChange(event) {
    this.setState({...this.state, privateKey: event.target.value});
  }
  handleSubmit(event) {
    if (this.state.estimated) {
      this.props.publish()
    } else {
      this.props.createPost(this.state.text, this.state.privateKey);
      this.setState({...this.state, estimated: true});
    }
    event.preventDefault();
  }
  render() {
    return (
    <div id="new_post_form">
      <form action="/api/create_post" method="post" onSubmit={this.handleSubmit}>
        <p>Create new post from markdown:</p>
        <textarea name="text" onChange={this.handleTextChange}></textarea>
        <p>Private key to use:</p>
        <textarea name="private_key" onChange={this.handleKeyChange}></textarea>
        <p><input type="submit" /></p>
      </form>
    </div>
    );
  }
}

const mapStateToProps = state => {
  return { 
    // todoList: todos.allIds 
  }
}

const mapDispatchToProps = dispatch => {
  return {
    createPost: (text, privateKey) => dispatch(createPostRequest(text, privateKey)),
    publish: () => dispatch(publishEstimatedPost()),
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(NewPostForm);
