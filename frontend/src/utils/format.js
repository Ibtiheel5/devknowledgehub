const numberFormatter = new Intl.NumberFormat("fr-FR");

const dateTimeFormatter = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit"
});

const timeFormatter = new Intl.DateTimeFormat("fr-FR", {
  hour: "2-digit",
  minute: "2-digit"
});

export function formatNumber(value) {
  return value == null ? "—" : numberFormatter.format(value);
}

export function formatDateTime(date = new Date()) {
  return dateTimeFormatter.format(date);
}

export function formatTime(date = new Date()) {
  return timeFormatter.format(date);
}

export function pluralize(count, singular, plural = `${singular}s`) {
  return count > 1 ? plural : singular;
}
