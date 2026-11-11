"use client";

import { createContext, useCallback, useContext, useMemo, useSyncExternalStore } from "react";
import { DEFAULT_LOCATION_ID, DEMO_LOCATIONS, LOCATION_STORAGE_KEY } from "@/lib/locations";

interface LocationContextValue { locationId: string; setLocationId: (id: string) => void; }
const LocationContext = createContext<LocationContextValue | null>(null);

const locationListeners = new Set<() => void>();

function subscribeToLocation(listener: () => void) {
  locationListeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    locationListeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function getStoredLocationId() {
  const saved = window.localStorage.getItem(LOCATION_STORAGE_KEY);
  return saved && DEMO_LOCATIONS.some((location) => location.id === saved)
    ? saved
    : DEFAULT_LOCATION_ID;
}

function getServerLocationId() {
  return DEFAULT_LOCATION_ID;
}

export function LocationProvider({ children }: { children: React.ReactNode }) {
  const locationId = useSyncExternalStore(
    subscribeToLocation,
    getStoredLocationId,
    getServerLocationId,
  );
  const setLocationId = useCallback((id: string) => {
    if (!DEMO_LOCATIONS.some((location) => location.id === id)) return;
    window.localStorage.setItem(LOCATION_STORAGE_KEY, id);
    locationListeners.forEach((listener) => listener());
  }, []);
  const value = useMemo(() => ({ locationId, setLocationId }), [locationId, setLocationId]);
  return <LocationContext.Provider value={value}>{children}</LocationContext.Provider>;
}

export function useDemoLocation() {
  const value = useContext(LocationContext);
  if (!value) throw new Error("useDemoLocation must be used inside LocationProvider");
  return value;
}
