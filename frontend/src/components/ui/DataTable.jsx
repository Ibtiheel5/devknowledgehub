import styles from "./DataTable.module.css";

export function DataTable({
  columns = [],
  data = [],
  emptyState,
  rowKey,
  getRowKey
}) {
  const getKey = (row, index) =>
    typeof getRowKey === "function"
      ? getRowKey(row, index)
      : rowKey
        ? row[rowKey]
        : index;

  return (
    <div className={styles.wrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={styles.headerCell}
                style={column.width ? { width: column.width } : undefined}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td className={styles.emptyCell} colSpan={columns.length}>
                {emptyState || "Aucune donnée."}
              </td>
            </tr>
          ) : (
            data.map((row, index) => (
              <tr key={getKey(row, index)} className={styles.row}>
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={styles.cell}
                    data-align={column.align}
                  >
                    {column.render
                      ? column.render(row, index)
                      : String(row[column.key] ?? "—")}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
