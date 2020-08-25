/*
 * action types
 */
export const FEED_FETCH_REQUESTED = 'FEED_FETCH_REQUESTED';
export const ADD_PUBLICATION = 'ADD_PUBLICATION';
export const CREATE_POST_REQUESTED = 'CREATE_POST_REQUESTED';
export const PUBLISH_ESTIMATED_POST = 'PUBLISH_ESTIMATED_POST';
/*
 * other constants
 */

/*
 * action creators
 */
export function feedFetchRequest(text) {
  return { type: FEED_FETCH_REQUESTED, text }
}

export function addPost(magnet, content) {
  return {
    type: ADD_PUBLICATION,
    magnet: magnet,
    content: content,
  }
}

export function createPostRequest(text, privateKey) {
  return {
    type: CREATE_POST_REQUESTED,
    text: text,
    privateKey: privateKey,
  }
}

export function publishEstimatedPost() {
  return {
    type: PUBLISH_ESTIMATED_POST,
  }
}
