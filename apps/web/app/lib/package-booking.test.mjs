import assert from "node:assert/strict";
import test from "node:test";
import {
  buildPackageBookingHref,
  isBookableApiPackage,
  parsePackageId,
  resolvePackageSelection,
} from "./package-booking.mjs";

const verifiedPackage = {
  id: 42,
  is_active: true,
  is_demo: false,
  is_verified: true,
  source: "Provider-supplied",
  verified_at: "2026-11-06T00:00:00Z",
};

test("parses a positive numeric API package ID", () => {
  assert.deepEqual(parsePackageId("42"), { kind: "valid", id: 42 });
});

test("rejects static, zero, fractional, and unsafe package IDs", () => {
  for (const value of ["pkg-1", "0", "1.5", "2147483648", "9007199254740992"]) {
    assert.deepEqual(parsePackageId(value), { kind: "invalid" });
  }
});

test("does not select a package when the query parameter is missing", () => {
  assert.deepEqual(parsePackageId(null), { kind: "missing" });
  assert.deepEqual(resolvePackageSelection(null, null), { kind: "missing", id: "" });
});

test("selects only the requested active and verified API package", () => {
  assert.deepEqual(
    resolvePackageSelection("42", verifiedPackage),
    { kind: "selected", id: "42" },
  );
  assert.deepEqual(
    resolvePackageSelection("42", { ...verifiedPackage, id: 43 }),
    { kind: "unavailable", id: "" },
  );
  assert.deepEqual(
    resolvePackageSelection("42", { ...verifiedPackage, is_active: false }),
    { kind: "unavailable", id: "" },
  );
  assert.deepEqual(
    resolvePackageSelection("42", { ...verifiedPackage, is_demo: true }),
    { kind: "demo", id: "" },
  );
  assert.deepEqual(
    resolvePackageSelection("42", { ...verifiedPackage, is_verified: false }),
    { kind: "unavailable", id: "" },
  );
  assert.deepEqual(
    resolvePackageSelection("42", { ...verifiedPackage, source: null }),
    { kind: "unavailable", id: "" },
  );
});

test("requires source and verification timestamp before package booking", () => {
  assert.equal(isBookableApiPackage(verifiedPackage), true);
  assert.equal(isBookableApiPackage({ ...verifiedPackage, verified_at: null }), false);
  assert.equal(isBookableApiPackage({ ...verifiedPackage, source: "  " }), false);
});

test("does not select a static package ID", () => {
  assert.deepEqual(
    resolvePackageSelection("pkg-1", { id: 1, is_active: true }),
    { kind: "invalid", id: "" },
  );
});

test("builds API package links with the actual city and locality", () => {
  assert.equal(
    buildPackageBookingHref(42, " Raichur ", " Manvi "),
    "/booking?package_id=42&city=Raichur&locality=Manvi",
  );
});

test("preserves static package IDs without converting or adding a city filter", () => {
  assert.equal(buildPackageBookingHref("pkg-1", "Raichur"), "/booking?package_id=pkg-1");
});
