import React, { useMemo, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';
import { ArrowRight } from 'lucide-react';
import glassStyles from '../styles/glass.module.css';
import { Link } from 'react-router-dom';

gsap.registerPlugin(ScrollTrigger, useGSAP);

/** Stable dust mote positions — deterministic, no Math.random per render */
function createDustMotes(count = 24) {
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    left: `${(i * 37 + 11) % 100}%`,
    top: `${(i * 53 + 7) % 100}%`,
    size: (i % 3) + 1.5,
    delay: (i % 5) * 1.1,
    duration: 15 + (i % 8),
  }));
}

/**
 * HeroSection - Library bookshelf bars + aisle glow
 * Brand lockup + kinetic type; perspective shelves fade into the aisle
 */
function HeroSection() {
  const sectionRef = useRef(null);
  const brandRef = useRef(null);
  const headlineRef = useRef(null);
  const subheadlineRef = useRef(null);
  const ctaRef = useRef(null);
  const glowRef = useRef(null);
  const shelfLeftRef = useRef(null);
  const shelfRightRef = useRef(null);
  const dustRef = useRef(null);
  const dustMotes = useMemo(() => createDustMotes(24), []);

  const setWillChange = (active) => {
    const value = active ? 'transform' : 'auto';
    [shelfLeftRef, shelfRightRef, glowRef, dustRef].forEach((ref) => {
      if (ref.current) ref.current.style.willChange = value;
    });
  };

  useGSAP(
    () => {
      const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const words = headlineRef.current?.querySelectorAll('.word');

      if (reduceMotion) {
        [
          glowRef,
          shelfLeftRef,
          shelfRightRef,
          dustRef,
          brandRef,
          headlineRef,
          subheadlineRef,
          ctaRef,
        ].forEach((ref) => {
          if (ref.current) gsap.set(ref.current, { opacity: 1, y: 0, filter: 'none', clearProps: 'clipPath' });
        });
        words?.forEach((el) => {
          gsap.set(el, { opacity: 1, y: 0, filter: 'none', clearProps: 'clipPath' });
        });
        return;
      }

      setWillChange(true);

      const tl = gsap.timeline({
        defaults: { ease: 'power3.out' },
        onComplete: () => setWillChange(false),
      });

      tl.fromTo(shelfLeftRef.current, { opacity: 0 }, { opacity: 1, duration: 0.85 }, 0);
      tl.fromTo(shelfRightRef.current, { opacity: 0 }, { opacity: 1, duration: 0.85 }, 0.12);
      tl.fromTo(glowRef.current, { opacity: 0 }, { opacity: 1, duration: 0.95 }, 0.08);
      tl.fromTo(dustRef.current, { opacity: 0 }, { opacity: 1, duration: 0.7 }, 0.3);

      tl.fromTo(
        brandRef.current,
        { y: 18, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.5 },
        0.2
      );

      if (words?.length) {
        tl.fromTo(
          words,
          { y: 20, opacity: 0.35, filter: 'blur(6px)', clipPath: 'inset(0 0 100% 0)' },
          {
            y: 0,
            opacity: 1,
            filter: 'blur(0px)',
            clipPath: 'inset(0 0 0% 0)',
            duration: 0.55,
            stagger: 0.08,
          },
          0.35
        );
      }

      tl.fromTo(subheadlineRef.current, { y: 14, opacity: 0 }, { y: 0, opacity: 1, duration: 0.4 }, 0.85);
      tl.fromTo(ctaRef.current, { y: 14, opacity: 0 }, { y: 0, opacity: 1, duration: 0.4 }, 1.0);

      ScrollTrigger.create({
        trigger: sectionRef.current,
        start: 'top top',
        end: 'bottom top',
        scrub: true,
        onEnter: () => setWillChange(true),
        onEnterBack: () => setWillChange(true),
        onLeave: () => setWillChange(false),
        onLeaveBack: () => setWillChange(false),
        onUpdate: (self) => {
          if (shelfLeftRef.current) gsap.set(shelfLeftRef.current, { y: self.progress * 50 });
          if (shelfRightRef.current) gsap.set(shelfRightRef.current, { y: self.progress * 70 });
          if (glowRef.current) gsap.set(glowRef.current, { y: self.progress * 30 });
          if (dustRef.current) gsap.set(dustRef.current, { y: self.progress * 110 });
        },
        invalidateOnRefresh: true,
      });
    },
    { scope: sectionRef }
  );

  return (
    <section ref={sectionRef} className="hero-section" aria-label="Hero">
      <div className="hero-layer hero-base" aria-hidden="true" />

      <div ref={shelfLeftRef} className="hero-layer hero-shelves-left" aria-hidden="true">
        <div className="bookshelf-pattern left" />
      </div>

      <div ref={shelfRightRef} className="hero-layer hero-shelves-right" aria-hidden="true">
        <div className="bookshelf-pattern right" />
      </div>

      <div ref={glowRef} className="hero-layer hero-glow" aria-hidden="true">
        <div className="aisle-glow" />
        <div className="god-ray" />
      </div>

      <div ref={dustRef} className="hero-layer hero-dust" aria-hidden="true">
        {dustMotes.map((mote) => (
          <div
            key={mote.id}
            className="dust-mote"
            style={{
              left: mote.left,
              top: mote.top,
              width: mote.size,
              height: mote.size,
              animationDelay: `${mote.delay}s`,
              animationDuration: `${mote.duration}s`,
            }}
          />
        ))}
      </div>

      <div className="hero-content">
        <p ref={brandRef} className="hero-brand">
          Dumb<span className="logo-italic">It</span>Down
        </p>

        <h1 ref={headlineRef} className="hero-headline">
          <span className="line line-primary">
            <span className="word">Understand</span>{' '}
            <span className="word italic">Research.</span>
          </span>
          <span className="line">
            <span className="word bold">Instantly.</span>
          </span>
        </h1>

        <p ref={subheadlineRef} className="hero-subheadline">
          RAG-powered simplification for 1,250+ academic papers.
          Ask once, then keep asking.
        </p>

        <div ref={ctaRef} className="hero-ctas">
          <Link to="/app" className={glassStyles.glassButton}>
            Simplify a Paper
            <ArrowRight size={18} aria-hidden="true" />
          </Link>
          <a href="#how-it-works" className={glassStyles.textButton}>
            See How It Works
          </a>
        </div>
      </div>

      <style>{`
        .hero-section {
          position: relative;
          width: 100%;
          min-height: 640px;
          height: 100svh;
          height: 100dvh;
          box-sizing: border-box;
          padding-top: 72px;
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: flex-start;
        }

        .hero-layer {
          position: absolute;
          inset: 0;
          pointer-events: none;
        }

        .hero-base {
          background:
            radial-gradient(
              ellipse 70% 55% at 55% 42%,
              rgba(107, 34, 50, 0.5) 0%,
              rgba(61, 15, 25, 0.22) 42%,
              transparent 70%
            ),
            radial-gradient(
              ellipse 45% 35% at 50% 85%,
              rgba(200, 131, 42, 0.1) 0%,
              transparent 60%
            ),
            linear-gradient(
              180deg,
              var(--color-void) 0%,
              #1a0c0e 45%,
              var(--color-void) 100%
            );
        }

        .bookshelf-pattern {
          position: absolute;
          width: 38%;
          height: 130%;
          top: -15%;
          background: repeating-linear-gradient(
            0deg,
            rgba(13, 8, 6, 0.92) 0px,
            rgba(13, 8, 6, 0.92) 38px,
            rgba(61, 15, 25, 0.55) 38px,
            rgba(61, 15, 25, 0.55) 41px,
            rgba(107, 34, 50, 0.35) 41px,
            rgba(107, 34, 50, 0.35) 42px
          );
          filter: blur(1.5px);
          opacity: 0.9;
        }

        .bookshelf-pattern.left {
          left: -2%;
          transform: perspective(1200px) rotateY(18deg);
          transform-origin: left center;
          mask-image: linear-gradient(
            90deg,
            #000 0%,
            #000 55%,
            rgba(0, 0, 0, 0.45) 78%,
            transparent 100%
          );
          -webkit-mask-image: linear-gradient(
            90deg,
            #000 0%,
            #000 55%,
            rgba(0, 0, 0, 0.45) 78%,
            transparent 100%
          );
        }

        .bookshelf-pattern.right {
          right: -2%;
          transform: perspective(1200px) rotateY(-18deg);
          transform-origin: right center;
          mask-image: linear-gradient(
            270deg,
            #000 0%,
            #000 55%,
            rgba(0, 0, 0, 0.45) 78%,
            transparent 100%
          );
          -webkit-mask-image: linear-gradient(
            270deg,
            #000 0%,
            #000 55%,
            rgba(0, 0, 0, 0.45) 78%,
            transparent 100%
          );
        }

        .aisle-glow {
          position: absolute;
          inset: 0;
          background: radial-gradient(
            ellipse 48% 68% at 52% 48%,
            var(--color-maroon-veil) 0%,
            transparent 68%
          );
          opacity: 0.9;
        }

        .god-ray {
          position: absolute;
          inset: 0;
          background: linear-gradient(
            135deg,
            transparent 28%,
            rgba(107, 34, 50, 0.28) 48%,
            transparent 68%
          );
          animation: god-ray-pulse 8s ease-in-out infinite;
        }

        .dust-mote {
          position: absolute;
          background: var(--color-amber);
          border-radius: 50%;
          opacity: 0.3;
          animation: float 20s ease-in-out infinite;
          pointer-events: none;
        }

        .hero-content {
          position: relative;
          z-index: 10;
          max-width: min(720px, 92vw);
          padding: 0 var(--space-xl);
          margin-left: clamp(1rem, 5vw, 4rem);
        }

        .hero-brand {
          font-family: var(--font-serif);
          font-size: clamp(2rem, 4vw, 2.75rem);
          font-weight: 600;
          color: var(--color-parchment);
          line-height: 1.1;
          letter-spacing: -0.02em;
          margin: 0 0 var(--space-md);
          text-wrap: balance;
        }

        .hero-brand .logo-italic {
          font-style: italic;
          font-weight: 400;
          color: inherit;
        }

        .hero-headline {
          font-family: var(--font-display);
          font-size: clamp(2rem, 4.5vw, 3.75rem);
          font-weight: 400;
          color: var(--color-parchment);
          line-height: 1.14;
          letter-spacing: -0.02em;
          margin-bottom: var(--space-lg);
          text-wrap: balance;
        }

        .hero-headline .line {
          display: block;
        }

        @media (min-width: 640px) {
          .hero-headline .line-primary {
            white-space: nowrap;
          }
        }

        .hero-headline .word {
          display: inline-block;
        }

        .hero-headline .italic {
          font-style: italic;
          padding-bottom: 0.06em;
        }

        .hero-headline .bold {
          font-weight: 700;
        }

        .hero-subheadline {
          font-family: var(--font-body);
          font-size: var(--t-body);
          font-weight: 300;
          color: var(--color-parchment-2);
          max-width: 42ch;
          margin-bottom: var(--space-xl);
          line-height: 1.6;
        }

        .hero-ctas {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: var(--space-xl);
        }

        @media (max-width: 768px) {
          .hero-content {
            margin-left: 0;
            padding: 0 var(--space-lg);
          }

          .hero-ctas {
            flex-direction: column;
            align-items: flex-start;
            gap: var(--space-md);
          }

          .bookshelf-pattern {
            width: 28%;
            opacity: 0.7;
          }
        }
      `}</style>
    </section>
  );
}

export default HeroSection;
