export function formatISTTimestamp(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  const formatted = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Kolkata",
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
  return `${formatted} IST`;
}
