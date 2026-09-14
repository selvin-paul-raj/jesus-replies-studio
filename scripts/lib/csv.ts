/**
 * Minimal RFC4180-ish CSV parser: handles quoted fields with embedded
 * commas, newlines, and "" as an escaped quote. Good enough for our own
 * controlled batch format (JSON blobs in cells) -- not a general-purpose
 * CSV library, and no dependency is worth adding for this alone.
 */
export function parseCsv(content: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;
  let i = 0;

  const endField = () => {
    row.push(field);
    field = "";
  };
  const endRow = () => {
    endField();
    rows.push(row);
    row = [];
  };

  while (i < content.length) {
    const char = content[i];
    if (inQuotes) {
      if (char === '"') {
        if (content[i + 1] === '"') {
          field += '"';
          i += 2;
        } else {
          inQuotes = false;
          i += 1;
        }
      } else {
        field += char;
        i += 1;
      }
      continue;
    }
    if (char === '"') {
      inQuotes = true;
      i += 1;
    } else if (char === ",") {
      endField();
      i += 1;
    } else if (char === "\r") {
      i += 1; // normalize CRLF -- \n below ends the row
    } else if (char === "\n") {
      endRow();
      i += 1;
    } else {
      field += char;
      i += 1;
    }
  }
  if (field.length > 0 || row.length > 0) endRow();

  return rows.filter((r) => !(r.length === 1 && r[0] === "")); // drop trailing blank line
}

/** First row is the header; each following row becomes {header: cell}. */
export function csvToObjects(content: string): Record<string, string>[] {
  const rows = parseCsv(content);
  if (rows.length === 0) return [];
  const [header, ...dataRows] = rows;
  return dataRows.map((row) => {
    const obj: Record<string, string> = {};
    header.forEach((key, idx) => {
      obj[key.trim()] = row[idx] ?? "";
    });
    return obj;
  });
}
