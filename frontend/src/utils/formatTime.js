export const formatTime = (value) => {
  if (!value) return "never";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "unknown";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};
