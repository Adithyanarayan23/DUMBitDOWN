import React from 'react';
import styles from '../styles/glass.module.css';

/**
 * GlassCard - Reusable glass morphism card with optional stitched border
 * 
 * @param {boolean} stitched - Add stitched border effect
 * @param {boolean} heavy - Use heavy glass styling (more opaque)
 * @param {string} className - Additional CSS classes
 * @param {React.ReactNode} children - Card content
 */
function GlassCard({ stitched = false, heavy = false, className = '', children, ...props }) {
  // Determine which class to use based on props
  let cardClass = styles.glass;
  
  if (stitched && heavy) {
    cardClass = styles.stitchedGlassHeavy;
  } else if (stitched) {
    cardClass = styles.stitchedGlass;
  } else if (heavy) {
    cardClass = styles.glassHeavy;
  }
  
  // Combine with any additional classes
  const combinedClass = `${cardClass} ${className}`.trim();
  
  return (
    <div className={combinedClass} {...props}>
      {children}
    </div>
  );
}

export default GlassCard;
