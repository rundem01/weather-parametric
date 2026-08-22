import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
  preload: true,
});

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#07080a",
  colorScheme: "dark",
};

export const metadata: Metadata = {
  metadataBase: new URL(APP_URL),
  title: {
    default: "Weather Parametric Insurance | GenLayer",
    template: "%s | GenLayer",
  },
  description:
    "A decentralized weather parametric insurance application powered by GenLayer Intelligent Contracts and consensus-verified weather data.",
  applicationName: "Weather Parametric Insurance",
  keywords: [
    "GenLayer",
    "Weather Insurance",
    "Parametric Insurance",
    "Intelligent Contracts",
    "AI Consensus",
    "Decentralized Insurance",
    "Weather Data",
  ],
  authors: [{ name: "Weather Parametric Insurance" }],
  creator: "Weather Parametric Insurance",
  publisher: "Weather Parametric Insurance",
  alternates: { canonical: APP_URL },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: APP_URL,
    siteName: "Weather Parametric Insurance",
    title: "Weather Parametric Insurance | GenLayer",
    description:
      "Verify predefined weather conditions through GenLayer consensus and move an insurance policy through a transparent lifecycle.",
    images: [
      {
        url: "/og-image.svg",
        width: 1200,
        height: 630,
        alt: "Weather Parametric Insurance powered by GenLayer",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Weather Parametric Insurance | GenLayer",
    description:
      "Verify predefined weather conditions through GenLayer consensus and move an insurance policy through a transparent lifecycle.",
    images: ["/og-image.svg"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} antialiased`} suppressHydrationWarning>
      <body className="min-h-screen bg-[#07080a] text-white selection:bg-white/20 selection:text-white">
        {children}
      </body>
    </html>
  );
}
