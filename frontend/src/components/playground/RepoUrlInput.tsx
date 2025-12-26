/**
 * RepoUrlInput
 * URL input field with GitHub icon and clear button
 */

import { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';

interface RepoUrlInputProps {
  value: string;
  onChange: (url: string) => void;
  onValidate: (url: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

// GitHub icon
const GitHubIcon = () => (
  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
    <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
  </svg>
);

// Clear icon
const ClearIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

export function RepoUrlInput({ 
  value, 
  onChange, 
  onValidate, 
  disabled,
  placeholder = "https://github.com/owner/repo"
}: RepoUrlInputProps) {
  const [localValue, setLocalValue] = useState(value);

  // Sync with external value
  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  // Debounced validation
  useEffect(() => {
    const timer = setTimeout(() => {
      if (localValue.trim() && localValue !== value) {
        onChange(localValue);
        onValidate(localValue);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [localValue]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalValue(e.target.value);
  };

  const handleClear = () => {
    setLocalValue('');
    onChange('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && localValue.trim()) {
      onChange(localValue);
      onValidate(localValue);
    }
  };

  return (
    <div className="relative">
      {/* GitHub icon */}
      <div className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500">
        <GitHubIcon />
      </div>

      {/* Input */}
      <input
        type="url"
        value={localValue}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        className={cn(
          'w-full pl-12 pr-12 py-4 text-base rounded-xl',
          'bg-zinc-900/50 border border-zinc-800',
          'text-white placeholder-zinc-500',
          'focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500',
          'transition-all duration-200',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      />

      {/* Clear button */}
      {localValue && !disabled && (
        <button
          onClick={handleClear}
          className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <ClearIcon />
        </button>
      )}
    </div>
  );
}
