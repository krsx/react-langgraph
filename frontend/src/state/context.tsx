import React, { createContext, useContext, useReducer, useRef } from 'react'
import { appReducer, initialState } from './reducer'
import type { AppState, Action } from './types'

interface AppContextValue {
  state: AppState
  dispatch: React.Dispatch<Action>
  dirtyGuardRef: React.MutableRefObject<(() => boolean) | null>
}

const AppContext = createContext<AppContextValue | null>(null)

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState)
  const dirtyGuardRef = useRef<(() => boolean) | null>(null)
  return (
    <AppContext.Provider value={{ state, dispatch, dirtyGuardRef }}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
