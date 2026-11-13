import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import HeroSection from '../components/HeroSection';
import glassStyles from '../styles/glass.module.css';

gsap.registerPlugin(ScrollTrigger, useGSAP);

/**
 * LandingPage - Hero, How It Works, proof strip, CTA, Footer
 */
function LandingPage() {
  const pageRef = useRef(null);
  const chapterRef = useRef(null);
  const proofRef = useRef(null);
  const ctaRef = useRef(null);
  const location = useLocation();

  useEffect(() => {
    if (!location.hash) return undefined;
    const id = location.hash.replace('#', '');
    const t = window.setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
    return () => window.clearTimeout(t);
  }, [location.hash]);

  useGSAP(
    () => {
      const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const cards = chapterRef.current?.querySelectorAll('.chapter-card');
      const proofContent = proofRef.current?.querySelector('.proof-inner');
      const ctaContent = ctaRef.current?.querySelector('.cta-content');

      if (reduceMotion) {
        cards?.forEach((el) => gsap.set(el, { clearProps: 'transform,clipPath' }));
        if (proofContent) gsap.set(proofContent, { clearProps: 'transform,clipPath' });
        if (ctaContent) gsap.set(ctaContent, { clearProps: 'transform' });
        return;
      }

      // Enhance visible baseline — small y + clip, never blank with opacity 0
      if (cards?.length) {
        gsap.set(cards, { y: 16, clipPath: 'inset(8% 0 0 0)' });
        ScrollTrigger.create({
          trigger: chapterRef.current,
          start: 'top 78%',
          once: true,
          onEnter: () => {
            gsap.to(cards, {
              y: 0,
              clipPath: 'inset(0% 0 0 0)',
              duration: 0.55,
              stagger: 0.14,
              ease: 'power3.out',
            });
          },
        });
      }

      if (proofContent) {
        gsap.set(proofContent, { y: 18, clipPath: 'inset(6% 0 0 0)' });
        ScrollTrigger.create({
          trigger: proofRef.current,
          start: 'top 80%',
          once: true,
          onEnter: () => {
            gsap.to(proofContent, {
              y: 0,
              clipPath: 'inset(0% 0 0 0)',
              duration: 0.6,
              ease: 'power3.out',
            });
          },
        });
      }

      if (ctaContent) {
        gsap.set(ctaContent, { y: 14 });
        ScrollTrigger.create({
          trigger: ctaRef.current,
          start: 'top 82%',
          once: true,
          onEnter: () => {
            gsap.to(ctaContent, { y: 0, duration: 0.5, ease: 'power3.out' });
          },
        });
      }
    },
    { scope: pageRef }
  );

  const steps = [
    {
      number: 'I',
      title: 'Paste or Upload',
      description: 'Drop in a research passage or upload a PDF. We handle the extraction.',
    },
    {
      number: 'II',
      title: 'Smart Retrieval',
      description: 'Our RAG pipeline queries 1,250+ papers, rewrites your query, and finds the most relevant sources.',
    },
    {
      number: 'III',
      title: 'Simplified Insight',
      description: 'A fast LLM streams a plain-English explanation with citations and follow-up capability.',
    },
  ];

  return (
    <main id="main-content" ref={pageRef} className="landing-page" tabIndex={-1}>
      <HeroSection />

      <section id="how-it-works" ref={chapterRef} className="chapter-section">
        <div className="chapter-header">
          <h2 className="chapter-title">How It Works</h2>
        </div>

        <div className="chapter-grid">
          {steps.map((step, index) => (
            <div key={step.number} className="chapter-card">
              <span className="chapter-numeral" aria-hidden="true">
                {step.number}
              </span>
              <h3 className="chapter-card-title">{step.title}</h3>
              <p className="chapter-card-desc">{step.description}</p>
              {index < steps.length - 1 && <div className="chapter-connector" aria-hidden="true" />}
            </div>
          ))}
        </div>

        <style>{`
          .chapter-section {
            padding: clamp(4rem, 10vw, 7rem) var(--space-xl);
            background: linear-gradient(
              180deg,
              var(--color-void) 0%,
              rgba(61, 15, 25, 0.3) 50%,
              var(--color-void) 100%
            );
            position: relative;
            scroll-margin-top: 80px;
          }

          .chapter-header {
            text-align: center;
            margin-bottom: var(--space-3xl);
            position: relative;
          }

          .chapter-title {
            font-family: var(--font-serif);
            font-size: var(--t-section);
            font-weight: 600;
            color: var(--color-parchment);
            position: relative;
            text-wrap: balance;
          }

          .chapter-grid {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: var(--space-2xl);
            position: relative;
          }

          .chapter-card {
            text-align: left;
            padding: var(--space-xl) 0;
            position: relative;
            border-top: 1px solid var(--glass-border);
          }

          .chapter-numeral {
            display: block;
            font-family: var(--font-display);
            font-size: clamp(2.5rem, 4vw, 3.5rem);
            font-weight: 400;
            color: var(--color-gold);
            line-height: 1;
            margin-bottom: var(--space-lg);
            opacity: 0.9;
          }

          .chapter-card-title {
            font-family: var(--font-serif);
            font-size: var(--t-card-title);
            font-weight: 600;
            color: var(--color-parchment);
            margin-bottom: var(--space-md);
          }

          .chapter-card-desc {
            font-family: var(--font-body);
            font-size: var(--t-body);
            font-weight: 300;
            color: var(--color-parchment-2);
            line-height: 1.6;
            max-width: 36ch;
          }

          .chapter-connector {
            position: absolute;
            top: 50%;
            right: -24px;
            width: 48px;
            height: 1px;
            border-top: 1px dashed var(--color-parchment-3);
            opacity: 0.5;
            display: none;
          }

          @media (min-width: 1024px) {
            .chapter-connector {
              display: block;
            }
          }

          @media (max-width: 768px) {
            .chapter-grid {
              grid-template-columns: 1fr;
            }

            .chapter-connector {
              display: none;
            }
          }
        `}</style>
      </section>

      <section id="features" ref={proofRef} className="proof-section">
        <div className="proof-inner">
          <div className="proof-copy">
            <h2 className="proof-title">Every claim traces to a source</h2>
            <p className="proof-desc">
              Explanations come with contribution scores so you can see which papers
              drove the answer — not a black-box summary.
            </p>
            <Link to="/app" className={`${glassStyles.textButton} proof-link`}>
              Try it with a sample
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>

          <div className={`proof-card ${glassStyles.stitchedGlass}`} aria-hidden="true">
            <div className="proof-card-seal">✓</div>
            <h3 className="proof-card-title">
              Multimodal fusion of imaging and genomic biomarkers in early Alzheimer detection
            </h3>
            <p className="proof-card-meta">Chen et al. · 2023</p>
            <div className="proof-contrib">
              <div className="proof-contrib-label">Contribution: 62.4%</div>
              <div className="proof-contrib-track">
                <div className="proof-contrib-fill" />
              </div>
            </div>
            <p className="proof-card-snippet">
              Combined PET and CSF markers improved classification accuracy versus imaging alone…
            </p>
          </div>
        </div>

        <style>{`
          .proof-section {
            padding: clamp(4rem, 10vw, 7rem) var(--space-xl);
            background: linear-gradient(
              180deg,
              var(--color-void) 0%,
              var(--color-maroon-deep) 50%,
              var(--color-void) 100%
            );
            scroll-margin-top: 80px;
          }

          .proof-inner {
            max-width: 1100px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: var(--space-3xl);
            align-items: center;
          }

          .proof-title {
            font-family: var(--font-serif);
            font-size: var(--t-section);
            font-weight: 600;
            color: var(--color-parchment);
            margin-bottom: var(--space-md);
            text-wrap: balance;
            line-height: 1.2;
          }

          .proof-desc {
            font-family: var(--font-body);
            font-size: var(--t-body);
            font-weight: 300;
            color: var(--color-parchment-2);
            line-height: 1.6;
            max-width: 38ch;
            margin-bottom: var(--space-xl);
          }

          .proof-link {
            font-size: var(--t-ui);
          }

          .proof-card {
            padding: var(--space-xl);
            position: relative;
          }

          .proof-card-seal {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background: var(--color-maroon);
            color: var(--color-parchment);
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
          }

          .proof-card-title {
            font-family: var(--font-serif);
            font-size: 18px;
            font-weight: 600;
            color: var(--color-parchment);
            line-height: 1.35;
            margin: 0 0 var(--space-sm);
            padding-right: 36px;
          }

          .proof-card-meta {
            font-family: var(--font-body);
            font-size: var(--t-caption);
            color: var(--color-parchment-3);
            margin: 0 0 var(--space-md);
          }

          .proof-contrib {
            margin-bottom: var(--space-md);
          }

          .proof-contrib-label {
            font-family: var(--font-body);
            font-size: var(--t-caption);
            color: var(--color-parchment-2);
            margin-bottom: var(--space-xs);
          }

          .proof-contrib-track {
            width: 100%;
            height: 4px;
            background: var(--glass-border);
            border-radius: 2px;
            overflow: hidden;
          }

          .proof-contrib-fill {
            height: 100%;
            width: 100%;
            background: var(--color-parchment-3);
            border-radius: 2px;
            transform: scaleX(0.624);
            transform-origin: left center;
          }

          .proof-card-snippet {
            font-family: var(--font-body);
            font-size: var(--t-caption);
            color: var(--color-parchment-2);
            line-height: 1.5;
            margin: 0;
          }

          @media (max-width: 768px) {
            .proof-inner {
              grid-template-columns: 1fr;
              gap: var(--space-2xl);
            }
          }
        `}</style>
      </section>

      <section ref={ctaRef} className="cta-section">
        <div className="cta-divider" aria-hidden="true">
          <span className="cta-ornament">·</span>
        </div>

        <div className="cta-content">
          <h2 className="cta-headline">The archive is <em>open.</em></h2>
          <p className="cta-subtext">
            Start simplifying research today. No signup required.
          </p>
          <Link to="/app" className={`${glassStyles.glassButton} cta-button`}>
            Begin Simplifying
            <ArrowRight size={18} aria-hidden="true" />
          </Link>
        </div>

        <div className="cta-divider" aria-hidden="true">
          <span className="cta-ornament">·</span>
        </div>

        <style>{`
          .cta-section {
            padding: clamp(3rem, 8vw, 5rem) var(--space-xl);
            background: var(--color-void);
          }

          .cta-divider {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: var(--space-md) 0;
          }

          .cta-divider::before,
          .cta-divider::after {
            content: '';
            flex: 1;
            height: 1px;
            background: linear-gradient(
              90deg,
              transparent,
              var(--color-parchment-3),
              transparent
            );
          }

          .cta-ornament {
            padding: 0 var(--space-md);
            color: var(--color-parchment-3);
            font-size: 18px;
          }

          .cta-content {
            text-align: center;
            max-width: 600px;
            margin: 0 auto;
          }

          .cta-headline {
            font-family: var(--font-display);
            font-size: clamp(36px, 5vw, 52px);
            font-weight: 400;
            color: var(--color-parchment);
            margin-bottom: var(--space-md);
            text-wrap: balance;
          }

          .cta-headline em {
            font-style: italic;
          }

          .cta-subtext {
            font-family: var(--font-body);
            font-size: var(--t-body);
            font-weight: 300;
            color: var(--color-parchment-2);
            margin-bottom: var(--space-xl);
          }

          .cta-button {
            font-size: var(--t-body);
            padding: var(--space-md) var(--space-2xl);
          }
        `}</style>
      </section>

      <footer className="footer">
        <div className="footer-inner">
          <Link to="/" className="footer-logo">
            Dumb<span className="logo-italic">It</span>Down
          </Link>

          <p className="footer-center">
            Plain English for dense papers.
          </p>

          <a
            href="https://github.com/ShreyasManchanda/DumbItDown"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-link"
          >
            GitHub
          </a>
        </div>

        <style>{`
          .footer {
            padding: var(--space-xl);
            background: var(--color-void);
            border-top: 1px solid var(--glass-border);
          }

          .footer-inner {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
          }

          .footer-logo {
            font-family: var(--font-serif);
            font-size: var(--t-card-title);
            font-weight: 600;
            color: var(--color-parchment);
          }

          .footer-logo .logo-italic {
            font-style: italic;
            font-weight: 400;
          }

          .footer-center {
            font-family: var(--font-body);
            font-size: var(--t-caption);
            font-weight: 300;
            color: var(--color-parchment-3);
          }

          .footer-link {
            font-family: var(--font-body);
            font-size: var(--t-caption);
            font-weight: 400;
            color: var(--color-parchment-2);
            transition: color var(--transition-normal);
          }

          .footer-link:hover {
            color: var(--color-gold);
          }

          @media (max-width: 768px) {
            .footer-inner {
              flex-direction: column;
              gap: var(--space-md);
              text-align: center;
            }
          }
        `}</style>
      </footer>
    </main>
  );
}

export default LandingPage;
