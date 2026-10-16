import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

// Native modal supplies keyboard containment, Escape and focus return outside the scaled canvas.
export function Details({
  label,
  children,
  className = '',
  button = 'Details & data',
}: {
  label: string;
  children: ReactNode;
  className?: string;
  button?: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    if (open) ref.current?.showModal();
  }, [open]);
  return (
    <>
      <button className={`details-button ${className}`} onClick={() => setOpen(true)} aria-haspopup="dialog">
        {button}
        <span className="sr-only"> · {label}</span>
      </button>
      {open &&
        createPortal(
          <dialog
            ref={ref}
            aria-labelledby={id}
            className="details-drawer"
            onClose={() => setOpen(false)}
            onClick={(e) => {
              if (e.target === e.currentTarget) ref.current?.close();
            }}
          >
            <div className="drawer-title">
              <h2 id={id}>{label}</h2>
              <button autoFocus aria-label={`Close ${label}`} onClick={() => ref.current?.close()}>
                Close ×
              </button>
            </div>
            <div className="drawer-body">{children}</div>
          </dialog>,
          document.body,
        )}
    </>
  );
}
