---
title: "Web Performance Optimization Strategies"
type: concept
domain: frontend-engineering
level: intermediate
status: active
tags: [web-performance, optimization, frontend, core-web-vitals, javascript]
related:
  - "[[React_Component_Architecture_Patterns]]"
  - "[[Docker_Multi_Stage_Builds]]"
  - "[[Observability_Stack_Design]]"
created: 2026-03-10
updated: 2026-03-10
---

## Overview

Web performance optimization encompasses techniques to reduce load times, improve interactivity, and enhance perceived speed. Google's Core Web Vitals define measurable performance targets for production web applications.

## Core Web Vitals

| Metric | Measurement | Good | Needs Improvement | Poor |
|--------|------------|------|-------------------|------|
| LCP (Largest Contentful Paint) | Load time | ≤2.5s | 2.5–4s | >4s |
| INP (Interaction to Next Paint) | Interactivity | ≤200ms | 200–500ms | >500ms |
| CLS (Cumulative Layout Shift) | Visual stability | ≤0.1 | 0.1–0.25 | >0.25 |

## Loading Performance

### Critical Rendering Path

Minimize the chain of resources required before first render:
1. HTML → CSS (render-blocking) → JavaScript (blocking) → Paint
2. Goal: defer non-critical resources

### Resource Loading Strategies

```html
<!-- Preload critical resources -->
<link rel="preload" href="/fonts/main.woff2" as="font" crossorigin>
<link rel="preload" href="/critical.css" as="style">

<!-- Prefetch next-page resources -->
<link rel="prefetch" href="/next-page.js">

<!-- Defer non-critical scripts -->
<script src="analytics.js" defer></script>
<script src="non-critical.js" async></script>
```

### Code Splitting

```javascript
// Route-based splitting (React + Vite)
const OrdersPage = lazy(() => import('./pages/Orders'));
const UsersPage = lazy(() => import('./pages/Users'));
```

## Image Optimization

- **Format:** Use WebP/AVIF (30-50% smaller than JPEG)
- **Responsive images:** `srcset` for different viewport sizes
- **Lazy loading:** `loading="lazy"` for below-fold images
- **Dimensions:** Always specify width/height to prevent CLS

```html
<img
  src="hero.webp"
  srcset="hero-480.webp 480w, hero-1080.webp 1080w"
  sizes="(max-width: 600px) 480px, 1080px"
  width="1080"
  height="600"
  loading="lazy"
  alt="Hero image"
>
```

## JavaScript Performance

### Bundle Optimization

- **Tree shaking:** Remove unused code at build time
- **Minification:** Terser/esbuild for production builds
- **Bundle analysis:** Analyze size with `rollup-plugin-visualizer`

### Runtime Performance

```javascript
// Debounce expensive operations
function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// Virtualize long lists
import { VirtualList } from 'react-virtual';
// Render only visible rows (10k items → same DOM as 20)
```

## Caching Strategy

| Resource Type | Cache Policy |
|--------------|-------------|
| HTML | No cache / short TTL (60s) |
| Hashed JS/CSS | Immutable (1 year) |
| API responses | Conditional + ETag |
| Fonts | Long TTL (1 year) |
| Images | Content-addressed + CDN |

## CDN and HTTP/2

- Serve static assets via CDN (reduced latency globally)
- HTTP/2 multiplexing: avoid domain sharding (anti-pattern with HTTP/2)
- HTTP/3 QUIC: 0-RTT connection resumption for repeat visitors

## Monitoring Tools

- **Lighthouse** — Automated audit (CI integration)
- **Chrome DevTools Performance** — Runtime profiling
- **Web Vitals library** — Real-user monitoring
- **Datadog / New Relic RUM** — Production performance monitoring

## Conclusion

Focus on Core Web Vitals first — they directly impact search ranking and user experience. LCP is usually fixed by image/font optimization and preloading. INP by reducing JavaScript execution. CLS by reserving space for dynamic content. Measure in production, not just in audits.
