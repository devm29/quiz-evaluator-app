/**
 * Format react-countdown's time parts as m:ss. The default renderer prints
 * days and hours too ("00:00:15:00"), which a quiz of minutes never needs.
 */
export function formatClock({ days = 0, hours = 0, minutes = 0, seconds = 0 }) {
  const totalMinutes = (days * 24 + hours) * 60 + minutes;
  return `${totalMinutes}:${String(seconds).padStart(2, "0")}`;
}
