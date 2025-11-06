import type { ReactNode } from "react";
import "../styles/globals.css";

export const metadata = {
  title: "Schedulify | Class Schedule Sync",
  description: "Upload a screenshot and turn it into a clean calendar in minutes.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="app-shell">{children}</body>
    </html>
  );
}
