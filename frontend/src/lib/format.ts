import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";

dayjs.extend(utc);
dayjs.extend(timezone);

const BJ_TZ = "Asia/Shanghai";

export function formatPremiumUSD(cents: number): string {
  const dollars = cents / 100;
  return "$" + dollars.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

export function formatPremiumCNY(cents: number, rate = 7.25): string {
  const yuan = (cents / 100) * rate;
  return "¥" + yuan.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

export function formatBeijingTime(isoString: string): string {
  return dayjs(isoString).tz(BJ_TZ).format("HH:mm:ss");
}

export function formatBeijingDate(isoString: string): string {
  return dayjs(isoString).tz(BJ_TZ).format("MM-DD HH:mm");
}

export function formatContract(
  symbol: string,
  strike: number,
  expiry: string,
  putCall: string
): string {
  const pc = putCall?.toUpperCase() === "PUT" ? "P" : "C";
  const exp = dayjs(expiry).format("MM/DD");
  return `${symbol} ${strike}${pc} ${exp}`;
}

export function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}

export function formatIV(iv?: number | null): string {
  if (iv == null || iv === 0) return "—";
  return (iv * 100).toFixed(1) + "%";
}

export function formatVolOI(volume?: number, oi?: number): string {
  if (!volume || !oi || oi === 0) return "—";
  return (volume / oi).toFixed(1) + "x";
}

export function isUSMarketOpen(): boolean {
  const now = dayjs().tz("America/New_York");
  const day = now.day();
  if (day === 0 || day === 6) return false;
  const hour = now.hour();
  const minute = now.minute();
  const minutes = hour * 60 + minute;
  return minutes >= 570 && minutes < 960; // 9:30 - 16:00 ET
}
