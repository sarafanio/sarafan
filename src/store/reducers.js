import { combineReducers } from 'redux'

import {
  ADD_PUBLICATION,
  UPDATE_CURSOR,
} from './actions'

function publications(state = [], action) {
  switch (action.type) {
    case ADD_PUBLICATION:
      return [
        ...state,
        {
          magnet: action.magnet,
          content: action.content,
        }
      ]
    default:
      return state
  }
}

function uiState(state = {}, action) {
  switch (action.type) {
    case UPDATE_CURSOR:
      let ended = !action.cursor;
      return {
        ...state,
        cursor: action.cursor,
        ended
      }
    default:
      return state
  }
}

const sarafanApp = combineReducers({
  publications,
  uiState,
});

export default sarafanApp