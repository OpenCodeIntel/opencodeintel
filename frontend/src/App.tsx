import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './components/providers/ThemeProvider';
import { TooltipProvider } from './components/ui/tooltip';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { LandingPage } from './pages/LandingPage';
import { Dashboard } from './components/Dashboard';
import { DocsHomePage } from './pages/DocsHomePage';
import { MCPSetupPage } from './pages/MCPSetupPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0a0b]">
        <div className="text-lg text-white">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function LandingWrapper() {
  const { user } = useAuth();

  // If user is logged in, redirect to dashboard
  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return <LandingPage />;
}

function AppRoutes() {
  const { user } = useAuth();

  return (
    <Routes>
      {/* New Landing Page */}
      <Route path="/" element={<LandingWrapper />} />
      
      <Route 
        path="/login" 
        element={user ? <Navigate to="/dashboard" replace /> : <LoginPage />} 
      />
      <Route 
        path="/signup" 
        element={user ? <Navigate to="/dashboard" replace /> : <SignupPage />} 
      />
      <Route
        path="/dashboard/*"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      
      {/* Documentation Routes - Public, no auth required */}
      <Route path="/docs" element={<DocsHomePage />} />
      <Route path="/docs/mcp-setup" element={<MCPSetupPage />} />
      
      {/* Placeholder routes for future docs pages */}
      <Route path="/docs/quickstart" element={<DocsHomePage />} />
      <Route path="/docs/mcp-tools" element={<MCPSetupPage />} />
      <Route path="/docs/mcp-examples" element={<MCPSetupPage />} />
      <Route path="/docs/features/*" element={<DocsHomePage />} />
      <Route path="/docs/deployment/*" element={<DocsHomePage />} />
      
      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

/**
 * Root application component that sets up global providers and routing.
 *
 * Wraps the app with theme and tooltip contexts, initializes the router, and
 * provides authentication state to the route tree.
 *
 * @returns The root React element with ThemeProvider, TooltipProvider, BrowserRouter, and AuthProvider applied.
 */
export function App() {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem={false}
      disableTransitionOnChange
    >
      <TooltipProvider>
        <BrowserRouter>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  );
}