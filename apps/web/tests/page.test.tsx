import { render, screen } from '@testing-library/react';
import Home from '@/app/page';

// Mock next/navigation for App Router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

// Mock react-dropzone
jest.mock('react-dropzone', () => ({
  useDropzone: () => ({
    getRootProps: () => ({}),
    getInputProps: () => ({}),
    isDragActive: false,
  }),
}));

describe('Home', () => {
  it('renders the main heading', () => {
    render(<Home />);
    expect(
      screen.getByText('Turn Lecture Slides into Flashcards')
    ).toBeInTheDocument();
  });

  it('renders the upload zone', () => {
    render(<Home />);
    expect(
      screen.getByText(/Drag and drop PDFs here/i)
    ).toBeInTheDocument();
  });

  it('renders feature cards', () => {
    render(<Home />);
    expect(screen.getByText('Vision-Based')).toBeInTheDocument();
    expect(screen.getByText('AI Pipeline')).toBeInTheDocument();
    expect(screen.getByText('Human Review')).toBeInTheDocument();
  });
});
