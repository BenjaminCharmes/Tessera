export function detectLanguage(filePath: string | null): string {
  if (!filePath) return "markdown";
  const ext = filePath.split(".").pop()?.toLowerCase() ?? "";
  const langMap: Record<string, string> = {
    py: "python",
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    md: "markdown",
    json: "json",
    toml: "ini",
    rs: "rust",
    yaml: "yaml",
    yml: "yaml",
    sh: "shell",
  };
  return langMap[ext] ?? "plaintext";
}
