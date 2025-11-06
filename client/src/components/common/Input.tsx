import React from 'react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
}

const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  className = '',
  ...props
}) => {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-neutral-black mb-2 shiny-text-hover">
          {label}
        </label>
      )}
      <input
        className={`input ${error ? 'border-secondary-500 focus:ring-secondary-300 focus:border-secondary-500' : ''} ${className}`}
        {...props}
      />
      {error && (
        <p className="mt-1 text-sm text-secondary-500">{error}</p>
      )}
      {helperText && !error && (
        <p className="mt-1 text-sm text-neutral-400">{helperText}</p>
      )}
    </div>
  )
}

export default Input


