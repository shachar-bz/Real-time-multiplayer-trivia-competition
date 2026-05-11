import "./globals.css";

export const metadata = {
  title: "Multiplayer Trivia",
  description: "Socket.IO multiplayer trivia competition",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
