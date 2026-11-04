function escapeCell(value) {
  if (value == null) return "";
  const text = typeof value === "object" ? JSON.stringify(value) : String(value);
  if (/[",\n;]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

export function toCsv(rows, columns) {
  const header = columns.map((column) => escapeCell(column.label ?? column.key)).join(";");
  const body = rows.map((row) =>
    columns.map((column) => escapeCell(column.value ? column.value(row) : row[column.key])).join(";")
  );
  return [header, ...body].join("\r\n");
}

export function downloadBlob(content, filename, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function downloadCsv(filename, rows, columns) {
  downloadBlob(`\uFEFF${toCsv(rows, columns)}`, filename, "text/csv;charset=utf-8");
}

export function downloadJson(filename, data) {
  downloadBlob(JSON.stringify(data, null, 2), filename, "application/json;charset=utf-8");
}
