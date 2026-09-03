import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SVEYRA",
  description: "Personal style wardrobe and recommendations",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
