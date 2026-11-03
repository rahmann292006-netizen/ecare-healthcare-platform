"use client";

import { SearchBar } from "@/components/search-bar";
import { useRouter } from "next/navigation";

export function HomeSearch() {
  const router = useRouter();
  return (
    <SearchBar
      placeholder="Search doctors, specialities, hospitals or diagnostic tests..."
      onSearch={(query, locality) => {
        const params = new URLSearchParams();
        if (query) params.set("search", query);
        if (locality) params.set("locality", locality);
        router.push(`/find${params.size ? `?${params.toString()}` : ""}`);
      }}
    />
  );
}
