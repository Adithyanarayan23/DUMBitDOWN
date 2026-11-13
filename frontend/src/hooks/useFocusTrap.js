import { useEffect } from 'react';

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Keep Tab focus inside `ref` while `active` is true.
 * Does not steal focus on mount — callers should focus the container themselves.
 */
export function useFocusTrap(ref, active) {
  useEffect(() => {
    if (!active) return undefined;
    const root = ref.current;
    if (!root) return undefined;

    const getFocusable = () =>
      Array.from(root.querySelectorAll(FOCUSABLE)).filter(
        (el) => el.getAttribute('aria-hidden') !== 'true' && !el.hasAttribute('disabled')
      );

    const onKeyDown = (e) => {
      if (e.key !== 'Tab') return;
      const nodes = getFocusable();
      if (nodes.length === 0) {
        e.preventDefault();
        root.focus();
        return;
      }
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    root.addEventListener('keydown', onKeyDown);
    return () => root.removeEventListener('keydown', onKeyDown);
  }, [ref, active]);
}
