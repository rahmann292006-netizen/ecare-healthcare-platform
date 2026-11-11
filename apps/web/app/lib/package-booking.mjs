/**
 * @typedef {{ kind: "missing" } | { kind: "invalid" } | { kind: "valid"; id: number }} PackageIdSelection
 * @typedef {{ kind: "missing" | "invalid" | "unavailable" | "demo"; id: "" } | { kind: "selected"; id: string }} PackageResolution
 */

/**
 * @param {string | null} value
 * @returns {PackageIdSelection}
 */
export function parsePackageId(value) {
  if (value === null) return { kind: "missing" };
  if (!/^[1-9]\d*$/.test(value)) return { kind: "invalid" };

  const id = Number(value);
  return Number.isInteger(id) && id <= 2_147_483_647
    ? { kind: "valid", id }
    : { kind: "invalid" };
}

/**
 * @param {{ is_active?: boolean; is_demo?: boolean; is_verified?: boolean; source?: string | null; verified_at?: string | null } | null} record
 */
export function isBookableApiPackage(record) {
  return Boolean(
    record &&
    record.is_active === true &&
    record.is_demo === false &&
    record.is_verified === true &&
    typeof record.source === "string" &&
    record.source.trim() &&
    typeof record.verified_at === "string" &&
    record.verified_at.trim(),
  );
}

/**
 * @param {string | null} value
 * @param {{ id: number; is_active: boolean; is_demo?: boolean; is_verified?: boolean; source?: string | null; verified_at?: string | null } | null} record
 * @returns {PackageResolution}
 */
export function resolvePackageSelection(value, record) {
  const parsed = parsePackageId(value);
  if (parsed.kind !== "valid") return { kind: parsed.kind, id: "" };
  if (!record || record.id !== parsed.id || !record.is_active) {
    return { kind: "unavailable", id: "" };
  }
  if (record.is_demo) return { kind: "demo", id: "" };
  if (!isBookableApiPackage(record)) return { kind: "unavailable", id: "" };
  return { kind: "selected", id: String(record.id) };
}

/**
 * @param {string | number} id
 * @param {string | null} [city]
 * @param {string | null} [locality]
 */
export function buildPackageBookingHref(id, city, locality) {
  const params = new URLSearchParams({ package_id: String(id) });
  if (parsePackageId(String(id)).kind === "valid" && city?.trim()) {
    params.set("city", city.trim());
  }
  if (parsePackageId(String(id)).kind === "valid" && locality?.trim()) {
    params.set("locality", locality.trim());
  }
  return `/booking?${params.toString()}`;
}
