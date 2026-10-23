"use client";

import { useRouter } from "next/navigation";
import { SearchBar } from "@/components/search-bar";

export function HomeSearch() {
  const router = useRouter();

  return (
    <SearchBar
      placeholder="Search hospitals, doctors, diagnostic labs..."
      onSearch={(query) => router.push(`/find?search=${encodeURIComponent(query)}`)}
    />
  );
}
