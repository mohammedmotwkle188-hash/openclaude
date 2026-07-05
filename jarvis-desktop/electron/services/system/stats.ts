import si from "systeminformation";
import type { SystemStatsSnapshot } from "../../../shared/types";

let lastNetStats: { rx: number; tx: number; t: number } | null = null;

export async function collectSystemStats(): Promise<SystemStatsSnapshot> {
  const [cpuLoad, cpuInfo, mem, battery, fsSize, netStats, temp, procs, gpu] = await Promise.all([
    si.currentLoad(),
    si.cpu(),
    si.mem(),
    si.battery().catch(() => null),
    si.fsSize().catch(() => []),
    si.networkStats().catch(() => []),
    si.cpuTemperature().catch(() => ({ main: null })),
    si.processes().catch(() => ({ all: 0, running: 0, list: [] as any[] })),
    si.graphics().catch(() => ({ controllers: [] as any[] })),
  ]);

  const primaryDisk = fsSize.reduce(
    (acc, d) => ({ used: acc.used + (d.used ?? 0), size: acc.size + (d.size ?? 0) }),
    { used: 0, size: 0 },
  );

  const net = netStats[0];
  let downKbps = 0;
  let upKbps = 0;
  if (net) {
    const now = Date.now();
    if (lastNetStats) {
      const dt = Math.max((now - lastNetStats.t) / 1000, 0.5);
      downKbps = Math.max(0, ((net.rx_bytes - lastNetStats.rx) / dt) / 1024);
      upKbps = Math.max(0, ((net.tx_bytes - lastNetStats.tx) / dt) / 1024);
    }
    lastNetStats = { rx: net.rx_bytes, tx: net.tx_bytes, t: now };
  }

  const gpuCtrl = gpu.controllers?.[0];
  const topByCpu = [...(procs.list ?? [])]
    .sort((a, b) => (b.cpu ?? 0) - (a.cpu ?? 0))
    .slice(0, 5)
    .map((p) => ({ name: p.name ?? "unknown", cpuPercent: Math.round((p.cpu ?? 0) * 10) / 10 }));

  return {
    timestamp: Date.now(),
    cpu: {
      loadPercent: Math.round(cpuLoad.currentLoad * 10) / 10,
      cores: cpuInfo.cores,
      speedGhz: cpuInfo.speed,
      model: `${cpuInfo.manufacturer} ${cpuInfo.brand}`.trim(),
    },
    ram: {
      usedGb: Math.round((mem.active / 1024 ** 3) * 10) / 10,
      totalGb: Math.round((mem.total / 1024 ** 3) * 10) / 10,
      usedPercent: Math.round((mem.active / mem.total) * 1000) / 10,
    },
    gpu: {
      model: gpuCtrl?.model ?? "Unknown GPU",
      loadPercent: typeof gpuCtrl?.utilizationGpu === "number" ? gpuCtrl.utilizationGpu : null,
      vramUsedMb: typeof gpuCtrl?.memoryUsed === "number" ? gpuCtrl.memoryUsed : null,
      vramTotalMb: typeof gpuCtrl?.memoryTotal === "number" ? gpuCtrl.memoryTotal : null,
    },
    battery: {
      hasBattery: battery?.hasBattery ?? false,
      percent: battery?.percent ?? 0,
      isCharging: battery?.isCharging ?? false,
      timeRemainingMin: battery?.timeRemaining && battery.timeRemaining > 0 ? battery.timeRemaining : null,
    },
    storage: {
      usedGb: Math.round((primaryDisk.used / 1024 ** 3) * 10) / 10,
      totalGb: Math.round((primaryDisk.size / 1024 ** 3) * 10) / 10,
      usedPercent: primaryDisk.size ? Math.round((primaryDisk.used / primaryDisk.size) * 1000) / 10 : 0,
    },
    network: {
      interface: net?.iface ?? "n/a",
      downKbps: Math.round(downKbps),
      upKbps: Math.round(upKbps),
      online: true,
    },
    temperature: {
      cpuC: typeof temp.main === "number" && temp.main > 0 ? Math.round(temp.main) : null,
    },
    processes: {
      total: procs.all ?? 0,
      running: procs.running ?? 0,
      topByCpu,
    },
  };
}

export async function checkInternetOnline(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    const res = await fetch("https://1.1.1.1", { method: "HEAD", signal: controller.signal }).catch(() => null);
    clearTimeout(timeout);
    if (res) return true;
    const dns = await import("node:dns/promises");
    await dns.lookup("cloudflare.com");
    return true;
  } catch {
    return false;
  }
}
