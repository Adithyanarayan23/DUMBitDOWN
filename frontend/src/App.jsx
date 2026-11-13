import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import LandingPage from './pages/LandingPage';
import AppPage from './pages/AppPage';

/**
 * App - Main application component with routing
 * Routes: / (landing) and /app (tool interface)
 */
function App() {
  return (
    <Router>
      <div className="app">
        <a href="#main-content" className="skip-link">
          Skip to content
        </a>
        <Navbar />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/app" element={<AppPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
