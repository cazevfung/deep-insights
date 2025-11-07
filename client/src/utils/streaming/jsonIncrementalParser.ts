import { jsonrepair } from 'jsonrepair'

interface IncrementalParseOptions {
  enableRepair?: boolean
}

const INCOMPLETE_JSON_ERROR = 'JSON root not completed yet'

const isLikelyIncomplete = (text: string): boolean => {
  const trimmed = text.trim()
  if (!trimmed) {
    return true
  }

  const opens = (trimmed.match(/[\[{]/g) || []).length
  const closes = (trimmed.match(/[\]}]/g) || []).length
  return closes < opens
}

export function incrementalParseJSON(buffer: string, options: IncrementalParseOptions = {}): any {
  const { enableRepair = true } = options

  if (!buffer || !buffer.trim()) {
    throw new Error(INCOMPLETE_JSON_ERROR)
  }

  let candidate = buffer

  if (enableRepair) {
    try {
      candidate = jsonrepair(buffer)
    } catch (error) {
      // Repair failed; fall back to raw buffer
      candidate = buffer
    }
  }

  if (isLikelyIncomplete(candidate)) {
    throw new Error(INCOMPLETE_JSON_ERROR)
  }

  try {
    return JSON.parse(candidate)
  } catch (error: any) {
    if (error instanceof SyntaxError || /Unexpected end of JSON input/.test(error?.message || '')) {
      throw new Error(INCOMPLETE_JSON_ERROR)
    }
    throw error
  }
}

