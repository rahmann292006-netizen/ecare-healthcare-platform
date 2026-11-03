import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { LocationProvider } from "@/components/location-provider";
import { AuthProvider } from "@/components/auth-provider";
import { Suspense } from "react";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "eCare - Healthcare Discovery Demo",
  description: "Illustrative healthcare listings and demo screening bookings.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-ink">
        <LocationProvider>
          <AuthProvider>
            <Suspense fallback={<div className="min-h-16 border-b border-border" />}><Navbar /></Suspense>
            <main className="flex-1">{children}</main>
            <Footer />
          </AuthProvider>
        </LocationProvider>
      </body>
    </html>
  );
}
