import { combineReducers } from 'redux'

import {
  ADD_PUBLICATION,
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
const sarafanApp = combineReducers({
  publications,
})
export default sarafanApp