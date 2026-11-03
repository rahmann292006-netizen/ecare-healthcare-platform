export interface DemoLocation {
  id: string;
  city: string;
  state: string;
  label: string;
}

export const DEMO_LOCATIONS: DemoLocation[] = [
  { id: "raichur-karnataka", city: "Raichur", state: "Karnataka", label: "Raichur, Karnataka" },
  { id: "bengaluru-karnataka", city: "Bengaluru", state: "Karnataka", label: "Bengaluru, Karnataka" },
  { id: "hyderabad-telangana", city: "Hyderabad", state: "Telangana", label: "Hyderabad, Telangana" },
  { id: "kalaburagi-karnataka", city: "Kalaburagi", state: "Karnataka", label: "Kalaburagi, Karnataka" },
];

export const DEFAULT_LOCATION_ID = DEMO_LOCATIONS[0].id;
export const LOCATION_STORAGE_KEY = "ecare_demo_location";

export function locationIdFor(city?: string | null, state?: string | null): string {
  return DEMO_LOCATIONS.find((item) => item.city.toLowerCase() === city?.toLowerCase() && item.state.toLowerCase() === state?.toLowerCase())?.id ?? DEFAULT_LOCATION_ID;
}
