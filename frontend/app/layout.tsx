import type { Metadata } from "next";
import { Instrument_Serif } from "next/font/google";
import "./globals.css";

const display = Instrument_Serif({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Trova — Turn your travel videos into bookable storefronts",
    template: "%s · Trova",
  },
  description:
    "Paste a TikTok or YouTube video. Trova finds every hotel you mentioned and turns them into a shareable, bookable storefront.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={display.variable}>
      <body className="min-h-dvh antialiased">{children}</body>
    </html>
  );
}
