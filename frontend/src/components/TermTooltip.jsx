import React from 'react';
import {
  useFloating,
  offset,
  flip,
  shift,
  autoUpdate,
  useHover,
  useFocus,
  useDismiss,
  useRole,
  useInteractions,
  FloatingPortal,
} from '@floating-ui/react';

/**
 * Inline term with yellow underline + hover definition.
 */
function TermTooltip({ term, definition }) {
  const [isOpen, setIsOpen] = React.useState(false);

  const { refs, floatingStyles, context } = useFloating({
    open: isOpen,
    onOpenChange: setIsOpen,
    placement: 'top',
    middleware: [offset(8), flip({ fallbackAxisSideDirection: 'start' }), shift()],
    whileElementsMounted: autoUpdate,
  });

  const hover = useHover(context, { move: false });
  const focus = useFocus(context);
  const dismiss = useDismiss(context);
  const role = useRole(context, { role: 'tooltip' });
  const { getReferenceProps, getFloatingProps } = useInteractions([
    hover,
    focus,
    dismiss,
    role,
  ]);

  return (
    <>
      <span
        ref={refs.setReference}
        className="technical-term"
        {...getReferenceProps()}
      >
        {term}
      </span>

      {isOpen && (
        <FloatingPortal>
          <div
            ref={refs.setFloating}
            className="term-tooltip"
            style={floatingStyles}
            {...getFloatingProps()}
          >
            <div className="tooltip-content">
              <span className="tooltip-term">{term}</span>
              <span className="tooltip-definition">{definition}</span>
            </div>
          </div>
        </FloatingPortal>
      )}

      <style>{`
        .technical-term {
          font-family: var(--font-serif);
          color: inherit;
          border-bottom: 1.5px solid var(--color-gold);
          cursor: help;
          transition: border-color 0.15s ease, color 0.15s ease;
        }
        .technical-term:hover {
          border-bottom-color: var(--color-amber);
          color: var(--color-gold);
        }
        .term-tooltip {
          z-index: 1000;
          max-width: 280px;
          background: rgba(13, 8, 6, 0.97);
          border: 1px solid rgba(212, 168, 83, 0.4);
          border-radius: 8px;
          padding: 10px 12px;
          box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }
        .tooltip-content {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .tooltip-term {
          font-family: var(--font-serif);
          font-size: 14px;
          font-weight: 600;
          color: var(--color-gold);
        }
        .tooltip-definition {
          font-family: var(--font-serif);
          font-size: 13px;
          color: var(--color-parchment-2);
          line-height: 1.45;
        }
      `}</style>
    </>
  );
}

export default TermTooltip;
