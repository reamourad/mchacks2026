export async function callGumloop(_username: string, _projectName: string) {
  return []
}

/**
 * Parse timestamp string in format "MM:SS-MM:SS" or "HH:MM:SS-HH:MM:SS" or "S-S"
 * @param timestamp - Timestamp string (e.g., "0:00-0:04", "1:30-2:15")
 * @returns Object with start and end times in seconds
 */
export function parseTimestamp(timestamp: string): { start: number; end?: number } {
  const parts = timestamp.split('-').map(part => part.trim());

  if (parts.length !== 2) {
    throw new Error(`Invalid timestamp format: ${timestamp}`);
  }

  const parseTime = (timeStr: string): number => {
    const timeParts = timeStr.split(':');

    if (timeParts.length === 3) {
      // HH:MM:SS
      const [hours, minutes, seconds] = timeParts.map(p => parseFloat(p));
      return hours * 3600 + minutes * 60 + seconds;
    } else if (timeParts.length === 2) {
      // MM:SS
      const [minutes, seconds] = timeParts.map(p => parseFloat(p));
      return minutes * 60 + seconds;
    } else if (timeParts.length === 1) {
      // Just seconds
      return parseFloat(timeParts[0]);
    } else {
      throw new Error(`Invalid time format: ${timeStr}`);
    }
  };

  const start = parseTime(parts[0]);
  const end = parseTime(parts[1]);

  return { start, end };
}
