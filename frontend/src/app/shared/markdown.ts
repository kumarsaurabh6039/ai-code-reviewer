/** Tiny, safe markdown-ish renderer: everything is HTML-escaped FIRST, then a few patterns are re-added. */
export function renderMarkdown(src: string): string {
  const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const parts = src.split(/```[a-zA-Z]*\n?/);
  return parts.map((part, i) => {
    if (i % 2 === 1) return `<pre class="code">${esc(part.replace(/\n$/, ''))}</pre>`;
    return esc(part)
      .replace(/`([^`\n]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
  }).join('');
}
