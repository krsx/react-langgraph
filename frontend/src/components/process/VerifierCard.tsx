import { ProcessCard } from './ProcessCard'

interface Props {
  data: Record<string, unknown>
}

export function VerifierCard({ data }: Props) {
  const valid = data.valid as boolean
  const checks = (data.checks as string[]) ?? []
  const overrideMessage = data.override_message as string | null

  return (
    <ProcessCard
      icon={valid ? '✓' : '✗'}
      title="Verifier"
      badgeText={valid ? 'PASS' : 'FAIL'}
      badgeClass={valid ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}
      detail={data}
    >
      <div className="flex flex-col gap-1">
        <p>{valid ? 'All checks passed' : 'Checks failed'}</p>
        {!valid && checks.length > 0 && (
          <ul className="list-disc list-inside text-gray-600">
            {checks.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        )}
        {overrideMessage && (
          <p className="text-amber-700 mt-1">{overrideMessage}</p>
        )}
      </div>
    </ProcessCard>
  )
}
