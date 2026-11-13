// Modified index.js
import UIController from './js/uiController.js';
import { setupAnimationObserver } from './js/animations.js';

// This flag will prevent app.js from registering duplicate listeners
window.uiInitialized = false;

document.addEventListener('DOMContentLoaded', function() {
    console.log("Document loaded, initializing app...");
    
    // Initialize UI Controller (which sets up event listeners)
    UIController.init();
    
    // Set this flag to true so app.js won't register duplicate listeners
    window.uiInitialized = true;
    
    // Set up animations
    setupAnimationObserver();
    
    console.log('DumbItDown app initialized successfully');
});