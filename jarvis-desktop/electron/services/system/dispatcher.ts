import type { CommandResult, ParsedCommand } from "../../../shared/types";
import * as cmds from "./commands";
import { captureScreenshot } from "../screen/capture";

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
    default:
      throw new Error(`Unknown action "${cmd.action}". Weather/news/stock/crypto route through their own IPC channels.`);
  }
}
