import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import '@/styles/globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'slide2anki',
  description: 'Convert lecture slides to Anki flashcards',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen flex flex-col">
          <header className="border-b bg-white">
            <div className="container mx-auto px-4 py-4 flex items-center justify-between">
              <a href="/" className="text-xl font-bold text-primary-600">
                slide2anki
              </a>
              <nav className="flex gap-6">
                <a href="/dashboard" className="text-gray-600 hover:text-gray-900">
                  Dashboard
                </a>
                <a href="/decks" className="text-gray-600 hover:text-gray-900">
                  Decks
                </a>
                <a href="/settings" className="text-gray-600 hover:text-gray-900">
                  Settings
                </a>
              </nav>
            </div>
          </header>
          <main className="flex-1">{children}</main>
          <footer className="border-t bg-white py-4">
            <div className="container mx-auto px-4 text-center text-sm text-gray-500">
              slide2anki - Open source flashcard generation
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
