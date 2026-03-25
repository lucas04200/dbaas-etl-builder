/**
 * Copies a string to the clipboard with a fallback to execCommand('copy')
 * for non-secure contexts (HTTP) where navigator.clipboard is unavailable.
 */
export async function copyToClipboard(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(String(text))
      return true
    } catch (err) {
      console.error('Failed to copy via navigator.clipboard:', err)
      // fall through to fallback
    }
  }

  // Fallback for non-secure contexts or when navigator.clipboard fails
  const textArea = document.createElement("textarea")
  textArea.value = String(text)

  // Make the textarea out of sight
  textArea.style.position = "fixed"
  textArea.style.left = "-9999px"
  textArea.style.top = "0"
  textArea.style.opacity = "0"

  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()

  try {
    const successful = document.execCommand('copy')
    if (!successful) throw new Error('execCommand copy failed')
    return true
  } catch (err) {
    console.error('Fallback copy failed:', err)
    throw err
  } finally {
    document.body.removeChild(textArea)
  }
}
