import { useApp } from '@/state/context'

const PROVIDERS = ['openrouter', 'ollama'] as const

export function ProviderModelPicker() {
  const { state, dispatch } = useApp()
  const activeModels = state.providers?.[state.activeProvider]?.models ?? []

  return (
    <div className="flex flex-col gap-2">
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">Provider</label>
        <select
          className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          value={state.activeProvider}
          onChange={(e) =>
            dispatch({ type: 'PROVIDER_CHANGED', provider: e.target.value as 'openrouter' | 'ollama' })
          }
        >
          {PROVIDERS.map((p) => (
            <option key={p} value={p} disabled={state.providers ? !state.providers[p].available : false}>
              {p}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">Model</label>
        <select
          className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          value={state.activeModel ?? ''}
          onChange={(e) => e.target.value && dispatch({ type: 'MODEL_CHANGED', model: e.target.value })}
        >
          {activeModels.length === 0 && <option value="">No models available</option>}
          {activeModels.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
