"use client"

import { ThemeProvider as NextThemesProvider } from "next-themes"
import { type ThemeProviderProps } from "next-themes"

/**
 * Provides theme context to descendant components using next-themes.
 *
 * @param children - React nodes rendered within the provider
 * @param props - Remaining ThemeProviderProps forwarded to the underlying theme provider
 */
export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>
}