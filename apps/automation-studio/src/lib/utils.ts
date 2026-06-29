import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Format a number as JPY, e.g. 1234 → "¥1,234". */
export function formatJpy(value: number): string {
  return `¥${Math.round(value).toLocaleString('ja-JP')}`
}
