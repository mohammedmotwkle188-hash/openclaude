import fs from "node:fs/promises";
// pdf-parse ships as CJS with no types export path issues under NodeNext; require works fine in the built main bundle.
// eslint-disable-next-line @typescript-eslint/no-var-requires
const pdfParse = require("pdf-parse");

export async function readPdfText(filePath: string): Promise<string> {
  const buffer = await fs.readFile(filePath);
  const result = await pdfParse(buffer);
  return result.text.trim();
}
