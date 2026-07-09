declare module "screenshot-desktop" {
  interface ScreenshotOptions {
    filename?: string;
    format?: "png" | "jpg";
    screen?: string | number;
  }
  function screenshot(options: { filename: string } & ScreenshotOptions): Promise<string>;
  function screenshot(options?: ScreenshotOptions): Promise<Buffer>;
  export default screenshot;
}

declare module "pdf-parse" {
  interface PdfParseResult {
    text: string;
    numpages: number;
  }
  function pdfParse(buffer: Buffer): Promise<PdfParseResult>;
  export default pdfParse;
}
