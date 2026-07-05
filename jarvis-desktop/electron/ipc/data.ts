import { randomUUID } from "node:crypto";
import { ipcMain } from "electron";
import { IPC } from "../../shared/types";
import { fetchWeather, fetchNews, fetchStockQuote, fetchCryptoPrice } from "../services/system/webdata";
import { addReminder, listReminders, toggleReminder } from "../services/memory/db";

export function registerDataIpc() {
  ipcMain.handle(IPC.weatherGet, (_evt, location?: string) => fetchWeather(location));
  ipcMain.handle(IPC.newsGet, () => fetchNews());
  ipcMain.handle(IPC.stockGet, (_evt, symbol: string) => fetchStockQuote(symbol));
  ipcMain.handle(IPC.cryptoGet, (_evt, symbol: string) => fetchCryptoPrice(symbol));

  ipcMain.handle(IPC.remindersList, () => listReminders());
  ipcMain.handle(IPC.remindersAdd, (_evt, text: string, dueAt: number) => {
    const item = { id: randomUUID(), text, dueAt, done: false };
    addReminder(item);
    return item;
  });
  ipcMain.handle(IPC.remindersToggle, (_evt, id: string) => {
    toggleReminder(id);
    return true;
  });

  // Calendar has no external provider wired up yet — returns an empty list so the
  // renderer's Calendar widget renders "No events" instead of erroring. Hook up a
  // CalDAV/Google Calendar adapter here to make it live.
  ipcMain.handle(IPC.calendarList, () => []);
}
