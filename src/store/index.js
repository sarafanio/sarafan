import { createStore, applyMiddleware } from 'redux'
import sarafanApp from './reducers'
import createSagaMiddleware from 'redux-saga'
import { rootSaga } from "./sagas";

const sagaMiddleware = createSagaMiddleware()
export const store = createStore(
    sarafanApp,
    applyMiddleware(sagaMiddleware)
)
sagaMiddleware.run(rootSaga)