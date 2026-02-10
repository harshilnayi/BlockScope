export function isNonEmptyString(value) {
    return typeof value === 'string' && value.trim().length > 0
  }
  
  export function clampNumber(value, min, max) {
    if (typeof value !== 'number') return min
    return Math.min(Math.max(value, min), max)
  }
  
  export function formatFileSize(bytes) {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }
  