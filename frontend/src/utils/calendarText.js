const MOJIBAKE_PATTERN = /[ÃÂâ]/;

export function normalizeCalendarText(value) {
  if (value === undefined || value === null) return "";

  let text = String(value);
  for (let attempt = 0; attempt < 2 && MOJIBAKE_PATTERN.test(text); attempt += 1) {
    try {
      const bytes = Uint8Array.from([...text].map((char) => char.charCodeAt(0) & 255));
      const decoded = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
      if (!decoded || decoded === text) break;
      text = decoded;
    } catch {
      break;
    }
  }

  return text;
}
