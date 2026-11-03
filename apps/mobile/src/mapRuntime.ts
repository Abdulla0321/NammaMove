// Expo Go supplies its own native map configuration. Custom binaries need a key
// embedded at build time; a JavaScript environment value alone cannot update it.
export function canShowBasemap(
  platform: string,
  expoGo: boolean,
  googleMapsKey?: string,
): boolean {
  return platform !== 'web' && (expoGo || Boolean(googleMapsKey?.trim()));
}
