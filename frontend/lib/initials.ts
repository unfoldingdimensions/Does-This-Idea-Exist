/** Two-letter initials from a name — shared by avatars across the app. */
export function initials(name: string): string {
  return name
    .split(/[\s\-_/]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}
