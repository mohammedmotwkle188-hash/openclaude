import { completeOnce } from "./router";
import { captureScreenshotBase64 } from "../screen/capture";

const LOCATE_PROMPT = `You are a UI element locator. You will be shown a screenshot and a description of a UI
element on it. Respond with ONLY two numbers between 0 and 1, separated by a comma: the fractional
x,y position of the CENTER of that element, where (0,0) is the top-left corner and (1,1) is the
bottom-right corner of the image. No words, no explanation, no units — just "x,y".
If you cannot find the element, respond with exactly: not_found`;

export interface ScreenLocation {
  xFrac: number;
  yFrac: number;
}

/**
 * Captures the screen and asks a vision-capable provider to point at the described element,
 * as fractional coordinates of the screenshot. Accuracy depends entirely on the model — this
 * is a best-effort grounding step, not a guaranteed-correct element finder.
 */
export async function locateOnScreen(description: string): Promise<ScreenLocation> {
  const image = await captureScreenshotBase64();
  const { text } = await completeOnce(
    [{ role: "user", text: `Find this element: "${description}"`, image }],
    LOCATE_PROMPT,
  );

  const cleaned = text.trim().toLowerCase();
  if (cleaned.includes("not_found")) {
    throw new Error(`Couldn't find "${description}" on screen.`);
  }

  const match = cleaned.match(/(-?\d*\.?\d+)\s*,\s*(-?\d*\.?\d+)/);
  if (!match) {
    throw new Error(`Vision model returned an unreadable location for "${description}": "${text.slice(0, 80)}"`);
  }

  const xFrac = Math.max(0, Math.min(1, parseFloat(match[1])));
  const yFrac = Math.max(0, Math.min(1, parseFloat(match[2])));
  return { xFrac, yFrac };
}
