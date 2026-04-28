/**
 * LazyImage - Performance-optimised image component.
 *
 * Features:
 *  - Native lazy loading via loading="lazy" (Intersection Observer behind the scenes)
 *  - Explicit width/height to prevent Cumulative Layout Shift (CLS)
 *  - Decoding="async" so image decode does not block the main thread
 *  - Responsive srcSet support for retina / high-DPI displays
 *  - Accessible alt text enforcement (required prop)
 *  - Graceful fallback on load error
 */

import React, { useState } from 'react';

/**
 * @param {object}  props
 * @param {string}  props.src           - Primary image URL (1x).
 * @param {string}  props.alt           - Required accessible description.
 * @param {number|string} [props.width] - Intrinsic width in px (prevents CLS).
 * @param {number|string} [props.height]- Intrinsic height in px (prevents CLS).
 * @param {string}  [props.srcSet]      - Responsive sources, e.g. "img@2x.png 2x".
 * @param {string}  [props.sizes]       - Responsive size hints, e.g. "(max-width:768px) 100vw".
 * @param {string}  [props.className]   - CSS classes forwarded to the <img>.
 * @param {string}  [props.fallbackSrc] - URL shown when the primary image fails.
 * @param {object}  [props.style]       - Inline styles forwarded to the <img>.
 */
const LazyImage = ({
  src,
  alt,
  width,
  height,
  srcSet,
  sizes,
  className = '',
  fallbackSrc = '',
  style = {},
  ...rest
}) => {
  const [errored, setErrored] = useState(false);

  const handleError = () => {
    if (!errored && fallbackSrc) {
      setErrored(true);
    }
  };

  return (
    <img
      src={errored && fallbackSrc ? fallbackSrc : src}
      alt={alt}
      width={width}
      height={height}
      srcSet={!errored ? srcSet : undefined}
      sizes={!errored ? sizes : undefined}
      loading="lazy"      /* native lazy loading — defers off-screen images */
      decoding="async"    /* decode off the main thread */
      className={className}
      style={style}
      onError={handleError}
      {...rest}
    />
  );
};

export default LazyImage;
