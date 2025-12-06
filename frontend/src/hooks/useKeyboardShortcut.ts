import { useEffect, useCallback } from 'react'

type KeyCombo = {
  key: string
  metaKey?: boolean
  ctrlKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
}

export function useKeyboardShortcut(
  keyCombo: KeyCombo | KeyCombo[],
  callback: () => void,
  enabled: boolean = true
) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return

      // Don't trigger if user is typing in an input
      const target = event.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        // Allow Escape to work even in inputs
        if (event.key !== 'Escape') return
      }

      const combos = Array.isArray(keyCombo) ? keyCombo : [keyCombo]

      for (const combo of combos) {
        const keyMatch = event.key.toLowerCase() === combo.key.toLowerCase()
        const shiftMatch = combo.shiftKey ? event.shiftKey : !event.shiftKey
        const altMatch = combo.altKey ? event.altKey : !event.altKey

        // Cross-platform modifier handling
        const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
        let modifierMatch = true

        if (combo.metaKey || combo.ctrlKey) {
          modifierMatch = isMac ? event.metaKey : event.ctrlKey
        } else {
          modifierMatch = !event.metaKey && !event.ctrlKey
        }

        if (keyMatch && modifierMatch && shiftMatch && altMatch) {
          event.preventDefault()
          callback()
          return
        }
      }
    },
    [keyCombo, callback, enabled]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}

// Preset shortcuts
export const SHORTCUTS = {
  COMMAND_PALETTE: [
    { key: 'k', metaKey: true },
    { key: 'k', ctrlKey: true }
  ],
  TOGGLE_SIDEBAR: [
    { key: '/', metaKey: true },
    { key: '/', ctrlKey: true }
  ],
  ESCAPE: { key: 'Escape' }
}
