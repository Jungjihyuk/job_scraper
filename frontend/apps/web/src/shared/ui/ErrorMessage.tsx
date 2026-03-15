type Props = { message: string }

export function ErrorMessage({ message }: Props) {
  return (
    <div className='rounded-lg bg-red-50 p-4 text-sm text-red-600'>
      ❌ {message}
    </div>
  )
}
