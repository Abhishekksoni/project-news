import type { Metadata } from "next";
import { Orbitron, Rajdhani, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { PostHogProvider } from "./providers";

const orbitron = Orbitron({
  subsets: ["latin"],
  variable: "--font-orbitron",
  display: "swap",
});

const rajdhani = Rajdhani({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-rajdhani",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Project News - AI & Tech Intelligence Radar",
  description:
    "Sci-Fi AI & Tech News Intelligence Dashboard powered by TypeSafe AI Jev System One Decision Engine with LSH MinHash Deduplication.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${orbitron.variable} ${rajdhani.variable} ${jetbrainsMono.variable} dark`}
    >
      <body className="bg-[#030712] text-slate-100 antialiased min-h-screen">
        <PostHogProvider>{children}</PostHogProvider>
      </body>
    </html>
  );
}
