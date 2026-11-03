"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { DEFAULT_LOCATION_ID, DEMO_LOCATIONS, LOCATION_STORAGE_KEY } from "@/lib/locations";

interface LocationContextValue { locationId: string; setLocationId: (id: string) => void; }
const LocationContext = createContext<LocationContextValue | null>(null);

export function LocationProvider({ children }: { children: React.ReactNode }) {
  const [locationId, setLocationState] = useState(DEFAULT_LOCATION_ID);
  useEffect(() => {
    const saved = window.localStorage.getItem(LOCATION_STORAGE_KEY);
    if (saved && DEMO_LOCATIONS.some((location) => location.id === saved)) setLocationState(saved);
  }, []);
  const setLocationId = useCallback((id: string) => {
    if (!DEMO_LOCATIONS.some((location) => location.id === id)) return;
    setLocationState(id);
    window.localStorage.setItem(LOCATION_STORAGE_KEY, id);
  }, []);
  const value = useMemo(() => ({ locationId, setLocationId }), [locationId, setLocationId]);
  return <LocationContext.Provider value={value}>{children}</LocationContext.Provider>;
}

export function useDemoLocation() {
  const value = useContext(LocationContext);
  if (!value) throw new Error("useDemoLocation must be used inside LocationProvider");
  return value;
}
