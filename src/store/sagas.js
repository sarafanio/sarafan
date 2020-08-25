import { 
  FEED_FETCH_REQUESTED, 
  CREATE_POST_REQUESTED, 
  PUBLISH_ESTIMATED_POST,
} from "./actions";
import { call, all, put, spawn, takeLatest, take  } from "redux-saga/effects";
import { addPost } from "../store/actions";
import api from "./api";


function* fetchPosts() {
  const resp = yield call(api.fetchPosts);
  for (let item of resp.result) {
    yield put(addPost(item.magnet, item.content));
  }
}

function* createPost(action) {
  const resp = yield call(api.createPost, action.text);
  console.log("Created post", resp);
  yield take(PUBLISH_ESTIMATED_POST);
  console.log("Need to publish", resp);
  const resp2 = yield call(api.publishPost, resp.magnet, action.privateKey);
  console.log("Second response received", resp2);
}

function* watchFetchPosts() {
  yield takeLatest(FEED_FETCH_REQUESTED, fetchPosts);
}

function* watchCreatePost() {
  yield takeLatest(CREATE_POST_REQUESTED, createPost);
}

export function* rootSaga () {
  const sagas = [
      watchFetchPosts,
      watchCreatePost,
  ];

  yield all(sagas.map(saga =>
    spawn(function* () {
      while (true) {
        try {
          yield call(saga);
          break;
        } catch (e) {
          console.log(e);
        }
      }
    }))
  );
}
