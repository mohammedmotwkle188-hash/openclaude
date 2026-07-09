import type { CommandResult, ParsedCommand } from "../../../shared/types";
import * as cmds from "./commands";
import { captureScreenshot } from "../screen/capture";
import * as automation from "./automation";
import { locateOnScreen } from "../ai/vision";

export async function executeCommand(cmd: ParsedCommand): Promise<CommandResult> {
  try {
    const message = await run(cmd);
    return { id: cmd.id, ok: true, message };
  } catch (err: any) {
    return { id: cmd.id, ok: false, message: err?.message ?? String(err) };
  }
}

async function run(cmd: ParsedCommand): Promise<string> {
  switch (cmd.action) {
    case "open_app":
      return cmds.openApp(cmd.args.app);
    case "media_play":
      return cmds.mediaControl("play");
    case "media_pause":
      return cmds.mediaControl("pause");
    case "media_stop":
      return cmds.mediaControl("stop");
    case "media_next":
      return cmds.mediaControl("next");
    case "media_prev":
      return cmds.mediaControl("prev");
    case "shutdown_pc":
      return cmds.powerAction("shutdown");
    case "restart_pc":
      return cmds.powerAction("restart");
    case "search_google":
      return cmds.searchWeb("google", cmd.args.query);
    case "search_youtube":
      return cmds.searchWeb("youtube", cmd.args.query);
    case "set_volume":
      return cmds.setVolume(Number(cmd.args.percent));
    case "set_brightness":
      return cmds.setBrightness(Number(cmd.args.percent));
    case "screenshot": {
      const file = await captureScreenshot();
      return `Screenshot saved to ${file}`;
    }
    case "open_folder":
      return cmds.openFolder(cmd.args.path);
    case "create_file":
      return cmds.createFile(cmd.args.path);
    case "delete_file":
      return cmds.deleteFile(cmd.args.path);
    case "move_file":
      return cmds.moveFile(cmd.args.from, cmd.args.to);
    case "rename_file":
      return cmds.renameFile(cmd.args.path, cmd.args.name);

    case "click": {
      await automation.clickAt();
      return "Clicked.";
    }
    case "click_on": {
      const loc = await locateOnScreen(cmd.args.target);
      await automation.clickAt(loc.xFrac, loc.yFrac);
      return `Clicked on "${cmd.args.target}".`;
    }
    case "double_click": {
      await automation.doubleClickAt();
      return "Double-clicked.";
    }
    case "double_click_on": {
      const loc = await locateOnScreen(cmd.args.target);
      await automation.doubleClickAt(loc.xFrac, loc.yFrac);
      return `Double-clicked on "${cmd.args.target}".`;
    }
    case "right_click": {
      await automation.clickAt(undefined, undefined, "right");
      return "Right-clicked.";
    }
    case "right_click_on": {
      const loc = await locateOnScreen(cmd.args.target);
      await automation.clickAt(loc.xFrac, loc.yFrac, "right");
      return `Right-clicked on "${cmd.args.target}".`;
    }
    case "type_text":
      return automation.typeText(cmd.args.text);
    case "press_key":
      return automation.pressKeyCombo(cmd.args.combo);
    case "scroll":
      return automation.scroll(cmd.args.direction as "up" | "down" | "left" | "right");
    case "hotkey_copy":
      return automation.hotkey("copy");
    case "hotkey_paste":
      return automation.hotkey("paste");
    case "hotkey_cut":
      return automation.hotkey("cut");
    case "hotkey_undo":
      return automation.hotkey("undo");
    case "hotkey_redo":
      return automation.hotkey("redo");
    case "hotkey_selectall":
      return automation.hotkey("selectAll");

    default:
      throw new Error(`Unknown action "${cmd.action}". Weather/news/stock/crypto route through their own IPC channels.`);
  }
}
