"use client";

import { SearchBar } from "@/components/search-bar";

export function HomeSearch() {
  return (
    <SearchBar
      placeholder="Search hospitals, doctors, diagnostic labs..."
      onSearch={(query) => {
        if (typeof window !== "undefined") {
          window.location.href = `/find?search=${encodeURIComponent(query)}`;
        }
      }}
    />
  );
}
