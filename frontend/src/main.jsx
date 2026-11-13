import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/globals.css';

/**
 * Application entry point
 * Mounts React app to DOM
 * PDF.js worker is configured lazily via utils/pdfSetup when Document Mode loads.
 */
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
