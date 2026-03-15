type Props = { message: string; icon?: string }

export function EmptyState({ message, icon = '📭' }: Props) {
  return (
    <div className='flex flex-col items-center justify-center py-16 text-slate-500'>
      <span className='text-4xl'>{icon}</span>
      <p className='mt-4 text-sm'>{message}</p>
    </div>
  )
}
