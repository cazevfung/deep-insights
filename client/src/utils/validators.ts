/**
 * URL validation utilities
 */

export const isValidUrl = (url: string): boolean => {
  try {
    const urlObj = new URL(url)
    return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
  } catch {
    return false
  }
}

export const validateUrls = (urls: string[]): {
  valid: string[]
  invalid: string[]
} => {
  const valid: string[] = []
  const invalid: string[] = []

  urls.forEach((url) => {
    if (isValidUrl(url)) {
      valid.push(url)
    } else {
      invalid.push(url)
    }
  })

  return { valid, invalid }
}

export const parseUrlsFromText = (text: string): string[] => {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
}



