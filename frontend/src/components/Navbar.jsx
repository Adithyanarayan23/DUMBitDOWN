import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, ArrowRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import glassStyles from '../styles/glass.module.css';
import { useFocusTrap } from '../hooks/useFocusTrap';

/**
 * Navbar - Transparent on hero, transitions to glass on scroll
 * Mobile hamburger with full-screen glass drawer
 */
function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();
  const drawerRef = useRef(null);
  const hamburgerRef = useRef(null);
  useFocusTrap(drawerRef, isMobileMenuOpen);

  useEffect(() => {
    const handleScroll = () => {
      const next = window.scrollY > 80;
      setIsScrolled((prev) => (prev === next ? prev : next));
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Close mobile menu on route change
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location]);

  // Prevent body scroll when mobile menu is open
  useEffect(() => {
    if (isMobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isMobileMenuOpen]);

  // Focus drawer on open; restore hamburger on close
  useEffect(() => {
    if (isMobileMenuOpen) {
      drawerRef.current?.focus();
      return undefined;
    }
    return undefined;
  }, [isMobileMenuOpen]);

  // Escape closes the mobile drawer
  useEffect(() => {
    if (!isMobileMenuOpen) return undefined;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setIsMobileMenuOpen(false);
        hamburgerRef.current?.focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isMobileMenuOpen]);

  const isApp = location.pathname.startsWith('/app');

  const navLinks = isApp
    ? [{ label: 'Home', to: '/' }]
    : [
        { label: 'How It Works', to: '/#how-it-works' },
        { label: 'Citations', to: '/#features' },
        { label: 'Launch App', to: '/app' },
      ];

  return (
    <>
      <nav
        className={`navbar ${!isApp && isScrolled ? 'navbar-scrolled' : ''} ${isApp ? 'navbar-app' : ''}`}
        aria-label="Primary"
      >
        <div className="navbar-inner">
          <Link to="/" className="navbar-logo">
            Dumb<span className="logo-italic">It</span>Down
          </Link>

          <div className="navbar-links">
            {navLinks.map((link) => (
              <Link key={link.label} to={link.to} className="nav-link">
                {link.label}
              </Link>
            ))}
          </div>

          {!isApp && (
            <Link to="/app" className={`${glassStyles.glassButton} navbar-cta`}>
              Open the Archive
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
          )}

          <button
            ref={hamburgerRef}
            type="button"
            className="navbar-hamburger"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={isMobileMenuOpen}
            aria-controls="mobile-nav-drawer"
          >
            {isMobileMenuOpen ? <X size={24} aria-hidden="true" /> : <Menu size={24} aria-hidden="true" />}
          </button>
        </div>
      </nav>

      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            id="mobile-nav-drawer"
            ref={drawerRef}
            className="mobile-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
            tabIndex={-1}
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'tween', duration: 0.25, ease: [0.23, 1, 0.32, 1] }}
          >
            <div className="mobile-drawer-content">
              {navLinks.map((link, index) => (
                <motion.div
                  key={link.label}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.06 }}
                >
                  <Link
                    to={link.to}
                    className="mobile-nav-link"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    {link.label}
                  </Link>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <style>{`
        .navbar {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          z-index: 100;
          padding: var(--space-md) var(--space-xl);
          transition: background-color var(--transition-normal), border-color var(--transition-normal), backdrop-filter var(--transition-normal);
          background: transparent;
        }

        .navbar-scrolled {
          background: var(--glass-bg-heavy);
          backdrop-filter: var(--glass-blur);
          -webkit-backdrop-filter: var(--glass-blur);
          border-bottom: 1px solid var(--glass-border);
        }

        /* App chrome: logo + Home sit on the page gradient — no glass bar */
        .navbar-app,
        .navbar-app.navbar-scrolled {
          background: transparent;
          backdrop-filter: none;
          -webkit-backdrop-filter: none;
          border-bottom: none;
        }

        .navbar-inner {
          max-width: 1400px;
          margin: 0 auto;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .navbar-logo {
          font-family: var(--font-serif);
          font-size: var(--t-card-title);
          font-weight: 600;
          color: var(--color-parchment);
        }

        .logo-italic {
          font-style: italic;
          font-weight: 400;
        }

        .navbar-links {
          display: flex;
          align-items: center;
          gap: var(--space-xl);
        }

        .nav-link {
          font-family: var(--font-body);
          font-size: var(--t-ui);
          font-weight: 500;
          color: var(--color-parchment-2);
          transition: color var(--transition-normal);
          background: none;
          border: none;
          cursor: pointer;
          padding: var(--space-sm) 0;
        }

        .nav-link:hover {
          color: var(--color-parchment);
        }

        .navbar-cta {
          padding: var(--space-sm) var(--space-lg);
          font-size: var(--t-ui);
        }

        .navbar-hamburger {
          display: none;
          background: none;
          border: none;
          color: var(--color-parchment);
          cursor: pointer;
          padding: var(--space-sm);
          min-width: 44px;
          min-height: 44px;
        }

        .mobile-drawer {
          position: fixed;
          top: 0;
          right: 0;
          bottom: 0;
          width: 100%;
          max-width: 400px;
          background: var(--glass-bg-heavy);
          backdrop-filter: var(--glass-blur);
          -webkit-backdrop-filter: var(--glass-blur);
          border-left: 1px solid var(--glass-border);
          z-index: 101;
          display: flex;
          flex-direction: column;
          padding: var(--space-2xl);
          padding-top: 80px;
          overscroll-behavior: contain;
          outline: none;
        }

        .mobile-drawer-content {
          display: flex;
          flex-direction: column;
          gap: var(--space-xl);
        }

        .mobile-nav-link {
          font-family: var(--font-serif);
          font-size: var(--t-section);
          font-weight: 600;
          color: var(--color-parchment);
          text-align: left;
          background: none;
          border: none;
          cursor: pointer;
          padding: var(--space-md) 0;
          transition: color var(--transition-normal);
          display: block;
        }

        .mobile-nav-link:hover {
          color: var(--color-gold);
        }

        @media (max-width: 768px) {
          .navbar-links,
          .navbar-cta {
            display: none;
          }

          .navbar-hamburger {
            display: flex;
            align-items: center;
            justify-content: center;
          }

          .navbar {
            padding: var(--space-md);
          }
        }
      `}</style>
    </>
  );
}

export default Navbar;
