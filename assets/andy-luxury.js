/* ============================================================
   ANDY CAFÉ — LUXURY ANIMATION ENGINE · v2
   - Custom cursor (dot + ring, scales on links)
   - Word-by-word hero reveal with mask
   - Magnetic buttons + hover-tilt cards
   - Cursor-following hero gradient
   - Header solidify + pill-on-scroll
   - Scroll reveals (line / mask / fade / stagger)
   - Parallax data-parallax
   - Number counters data-counter
   - Marquee direction-aware speed
   - Smooth anchors
   ============================================================ */

(function () {
  'use strict';

  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var supportsIO = 'IntersectionObserver' in window;
  var isFinePointer = window.matchMedia('(any-pointer: fine)').matches;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function init() {
    document.documentElement.classList.add('lux-ready');
    autoTagElements();
    splitHeroWords();

    if (prefersReducedMotion) {
      document.querySelectorAll(
        '.lux-reveal, .lux-reveal-up, .lux-reveal-mask, .lux-reveal-line, .ac-reveal, .lux-stagger-parent, .lux-stagger-child, .lux-word'
      ).forEach(function (el) { el.classList.add('lux-in', 'visible', 'andy-visible'); });
      return;
    }

    setupReveals();
    setupHeaderSolidify();
    setupMagnetic();
    setupParallax();
    setupCounters();
    setupTilt();
    setupHeroChoreo();
    setupSmoothAnchors();
    setupCursorGradient();
    if (isFinePointer) setupCustomCursor();
  }

  /* ========================================================
     AUTO-TAG
     ======================================================== */
  function autoTagElements() {
    document.querySelectorAll('.shopify-section').forEach(function (section, i) {
      if (i === 0) return;
      if (section.classList.contains('header-section') || section.classList.contains('footer-section')) return;
      section.classList.add('lux-reveal-up');
    });

    document.querySelectorAll('.product-list, .resource-list, [class*="products-grid"], .ac-product-grid, .ac-collections-grid').forEach(function (list) {
      var cards = list.querySelectorAll('.product-card, .resource-list__item, .ac-product-card, .ac-collection-card');
      if (cards.length) {
        list.classList.add('lux-stagger-parent');
        cards.forEach(function (c) {
          c.classList.add('lux-stagger-child');
          c.classList.add('lux-tilt');
        });
      }
    });

    document.querySelectorAll('.collection-card, .ac-collection-card').forEach(function (c) {
      if (!c.classList.contains('lux-stagger-child')) c.classList.add('lux-reveal-up');
    });

    document.querySelectorAll('.shopify-section h1, .shopify-section h2').forEach(function (h) {
      if (!h.closest('.lux-reveal-up') && !h.closest('.ac-hero')) {
        h.classList.add('lux-reveal-line');
      }
    });

    document.querySelectorAll('.media-with-content__media, .ac-story-visual').forEach(function (m) {
      m.classList.add('lux-reveal-mask');
    });
  }

  /* ========================================================
     HERO — split title into words, prep stagger reveal
     ======================================================== */
  function splitHeroWords() {
    var heroes = document.querySelectorAll('.ac-hero h1');
    heroes.forEach(function (h) {
      if (h.dataset.luxSplit) return;
      h.dataset.luxSplit = '1';
      var processNode = function (node) {
        var fragment = document.createDocumentFragment();
        node.childNodes.forEach(function (child) {
          if (child.nodeType === Node.TEXT_NODE) {
            var words = child.textContent.split(/(\s+)/);
            words.forEach(function (w) {
              if (/^\s+$/.test(w)) {
                fragment.appendChild(document.createTextNode(w));
              } else if (w.length) {
                var span = document.createElement('span');
                span.className = 'lux-word';
                var inner = document.createElement('span');
                inner.className = 'lux-word-inner';
                inner.textContent = w;
                span.appendChild(inner);
                fragment.appendChild(span);
              }
            });
          } else if (child.nodeType === Node.ELEMENT_NODE) {
            // For <em> etc, recursively wrap inside
            var clone = child.cloneNode(false);
            clone.appendChild(processNode(child));
            fragment.appendChild(clone);
          }
        });
        return fragment;
      };
      var newContent = processNode(h);
      h.innerHTML = '';
      h.appendChild(newContent);
    });
  }

  /* ========================================================
     REVEALS
     ======================================================== */
  function setupReveals() {
    if (!supportsIO) {
      document.querySelectorAll('.lux-reveal, .lux-reveal-up, .lux-reveal-mask, .lux-reveal-line, .ac-reveal, .lux-stagger-parent')
        .forEach(function (el) { el.classList.add('lux-in', 'visible', 'andy-visible'); });
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        el.classList.add('lux-in', 'visible', 'andy-visible');

        if (el.classList.contains('lux-stagger-parent')) {
          var children = el.querySelectorAll('.lux-stagger-child');
          children.forEach(function (child, i) {
            setTimeout(function () {
              child.classList.add('lux-in', 'visible', 'andy-visible');
            }, i * 90);
          });
        }
        observer.unobserve(el);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });

    document.querySelectorAll(
      '.lux-reveal, .lux-reveal-up, .lux-reveal-mask, .lux-reveal-line, .ac-reveal, .lux-stagger-parent'
    ).forEach(function (el) { observer.observe(el); });
  }

  /* ========================================================
     HEADER solidify
     ======================================================== */
  function setupHeaderSolidify() {
    var header = document.querySelector('header-component, .header, .header-section, .preview-banner');
    if (!header) return;

    var ticking = false;
    function update() {
      if (window.scrollY > 24) header.classList.add('lux-header-scrolled');
      else header.classList.remove('lux-header-scrolled');
      ticking = false;
    }

    window.addEventListener('scroll', function () {
      if (!ticking) { window.requestAnimationFrame(update); ticking = true; }
    }, { passive: true });
    update();
  }

  /* ========================================================
     MAGNETIC
     ======================================================== */
  function setupMagnetic() {
    if (!isFinePointer) return;

    var targets = document.querySelectorAll(
      '.lux-magnetic, .ac-btn-primary, .ac-btn-outline, .ac-add-btn, .ac-coll-arrow, .lux-link'
    );

    targets.forEach(function (el) {
      var strength = 14;
      var rect;
      var raf;
      var current = { x: 0, y: 0 };
      var target = { x: 0, y: 0 };

      function loop() {
        current.x += (target.x - current.x) * 0.15;
        current.y += (target.y - current.y) * 0.15;
        el.style.transform = 'translate(' + current.x.toFixed(2) + 'px,' + current.y.toFixed(2) + 'px)';
        if (Math.abs(target.x - current.x) > 0.05 || Math.abs(target.y - current.y) > 0.05) {
          raf = requestAnimationFrame(loop);
        } else { raf = null; }
      }

      el.addEventListener('mouseenter', function () { rect = el.getBoundingClientRect(); });
      el.addEventListener('mousemove', function (e) {
        if (!rect) rect = el.getBoundingClientRect();
        var relX = e.clientX - rect.left - rect.width / 2;
        var relY = e.clientY - rect.top - rect.height / 2;
        target.x = (relX / rect.width) * strength;
        target.y = (relY / rect.height) * strength;
        if (!raf) raf = requestAnimationFrame(loop);
      });
      el.addEventListener('mouseleave', function () {
        target.x = 0; target.y = 0;
        if (!raf) raf = requestAnimationFrame(loop);
      });
    });
  }

  /* ========================================================
     PARALLAX
     ======================================================== */
  function setupParallax() {
    var els = document.querySelectorAll('[data-parallax]');
    if (!els.length) return;
    if (!window.matchMedia('(min-width: 768px)').matches) return;

    var items = Array.prototype.map.call(els, function (el) {
      return { el: el, speed: parseFloat(el.dataset.parallax) || 0.2 };
    });

    var ticking = false;
    function update() {
      items.forEach(function (item) {
        var rect = item.el.getBoundingClientRect();
        var vh = window.innerHeight;
        if (rect.bottom < 0 || rect.top > vh) return;
        var progress = (rect.top + rect.height / 2 - vh / 2) / vh;
        var offset = -progress * item.speed * 100;
        item.el.style.transform = 'translate3d(0,' + offset.toFixed(2) + 'px,0)';
      });
      ticking = false;
    }

    window.addEventListener('scroll', function () {
      if (!ticking) { window.requestAnimationFrame(update); ticking = true; }
    }, { passive: true });
    update();
  }

  /* ========================================================
     COUNTERS
     ======================================================== */
  function setupCounters() {
    var counters = document.querySelectorAll('[data-counter]');
    if (!counters.length || !supportsIO) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        animateCount(entry.target);
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.5 });

    counters.forEach(function (el) { observer.observe(el); });
  }

  function animateCount(el) {
    var raw = el.getAttribute('data-counter') || el.textContent;
    var match = raw.match(/(-?\d+\.?\d*)/);
    if (!match) return;
    var target = parseFloat(match[1]);
    var suffix = raw.replace(match[0], '');
    var duration = 2000;
    var start = performance.now();

    function step(now) {
      var t = Math.min(1, (now - start) / duration);
      var eased = 1 - Math.pow(1 - t, 3);
      var value = target * eased;
      var display = Number.isInteger(target) ? Math.round(value) : value.toFixed(1);
      el.textContent = display + suffix;
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  /* ========================================================
     TILT (3D)
     ======================================================== */
  function setupTilt() {
    if (!isFinePointer) return;

    var cards = document.querySelectorAll('.lux-tilt');
    cards.forEach(function (el) {
      var max = 5;
      var rect;
      el.style.transformStyle = 'preserve-3d';
      el.style.willChange = 'transform';

      el.addEventListener('mouseenter', function () { rect = el.getBoundingClientRect(); });
      el.addEventListener('mousemove', function (e) {
        if (!rect) rect = el.getBoundingClientRect();
        var px = (e.clientX - rect.left) / rect.width;
        var py = (e.clientY - rect.top) / rect.height;
        var rx = (0.5 - py) * max;
        var ry = (px - 0.5) * max;
        el.style.transform = 'perspective(1100px) rotateX(' + rx.toFixed(2) + 'deg) rotateY(' + ry.toFixed(2) + 'deg) translateY(-4px)';
      });
      el.addEventListener('mouseleave', function () {
        el.style.transform = 'perspective(1100px) rotateX(0) rotateY(0)';
      });
    });
  }

  /* ========================================================
     HERO CHOREO — staggered word reveal + button fade
     ======================================================== */
  function setupHeroChoreo() {
    var hero = document.querySelector('.ac-hero, .hero, [class*="hero_"]');
    if (!hero) return;

    var content = hero.querySelector('.ac-hero-content, .hero__content, .group-block-content');
    if (!content) content = hero;

    // Hide initial
    var children = Array.prototype.slice.call(content.children);
    children.forEach(function (child) {
      child.style.opacity = '0';
      child.style.transform = 'translateY(40px)';
    });

    requestAnimationFrame(function () {
      // Reveal sequence
      children.forEach(function (child, i) {
        var delay = i * 130 + 200;
        setTimeout(function () {
          child.style.transition = 'opacity 1s cubic-bezier(0.22,1,0.36,1), transform 1s cubic-bezier(0.22,1,0.36,1)';
          child.style.opacity = '1';
          child.style.transform = 'translateY(0)';
        }, delay);
      });

      // Word-by-word reveal for h1
      var h1 = content.querySelector('h1');
      if (h1) {
        var words = h1.querySelectorAll('.lux-word-inner');
        words.forEach(function (w, i) {
          var delay = 350 + i * 80;
          setTimeout(function () {
            w.style.transform = 'translateY(0)';
          }, delay);
        });
      }
    });
  }

  /* ========================================================
     SMOOTH ANCHORS
     ======================================================== */
  function setupSmoothAnchors() {
    document.querySelectorAll('a[href^="#"]:not([href="#"])').forEach(function (a) {
      a.addEventListener('click', function (e) {
        var id = a.getAttribute('href');
        if (id.length <= 1) return;
        var target = document.querySelector(id);
        if (!target) return;
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
  }

  /* ========================================================
     CUSTOM CURSOR
     ======================================================== */
  function setupCustomCursor() {
    if (!isFinePointer) return;

    var dot = document.createElement('div');
    dot.className = 'lux-cursor-dot';
    var ring = document.createElement('div');
    ring.className = 'lux-cursor-ring';
    document.body.appendChild(dot);
    document.body.appendChild(ring);

    var pos = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    var ringPos = { x: pos.x, y: pos.y };

    function loop() {
      ringPos.x += (pos.x - ringPos.x) * 0.18;
      ringPos.y += (pos.y - ringPos.y) * 0.18;
      dot.style.transform = 'translate(' + pos.x + 'px,' + pos.y + 'px) translate(-50%,-50%)';
      ring.style.transform = 'translate(' + ringPos.x + 'px,' + ringPos.y + 'px) translate(-50%,-50%)';
      requestAnimationFrame(loop);
    }
    loop();

    window.addEventListener('mousemove', function (e) {
      pos.x = e.clientX;
      pos.y = e.clientY;
    });

    // Activate on hover of interactive elements
    var interactiveSelector = 'a, button, [role="button"], input, select, textarea, label, .lux-magnetic, .ac-product-card, .ac-collection-card, .lux-tilt';

    document.addEventListener('mouseover', function (e) {
      if (e.target.closest(interactiveSelector)) {
        document.body.classList.add('lux-cursor-active');
      }
    });
    document.addEventListener('mouseout', function (e) {
      if (e.target.closest(interactiveSelector)) {
        document.body.classList.remove('lux-cursor-active');
      }
    });

    window.addEventListener('mouseleave', function () { dot.style.opacity = '0'; ring.style.opacity = '0'; });
    window.addEventListener('mouseenter', function () { dot.style.opacity = '1'; ring.style.opacity = '1'; });
  }

  /* ========================================================
     CURSOR-FOLLOWING GRADIENT (hero)
     ======================================================== */
  function setupCursorGradient() {
    if (!isFinePointer) return;

    var hero = document.querySelector('.ac-hero');
    if (!hero) return;

    var bg = hero.querySelector('.ac-hero-bg');
    if (!bg) return;

    var rect;
    var raf;
    var pos = { x: 0.5, y: 0.5 };
    var current = { x: 0.5, y: 0.5 };

    hero.addEventListener('mouseenter', function () { rect = hero.getBoundingClientRect(); });

    hero.addEventListener('mousemove', function (e) {
      if (!rect) rect = hero.getBoundingClientRect();
      pos.x = (e.clientX - rect.left) / rect.width;
      pos.y = (e.clientY - rect.top) / rect.height;
      if (!raf) raf = requestAnimationFrame(loop);
    });

    function loop() {
      current.x += (pos.x - current.x) * 0.08;
      current.y += (pos.y - current.y) * 0.08;
      bg.style.setProperty('--cursor-x', (current.x * 100).toFixed(2) + '%');
      bg.style.setProperty('--cursor-y', (current.y * 100).toFixed(2) + '%');
      bg.style.background =
        'radial-gradient(ellipse 800px 600px at ' + (current.x * 100).toFixed(1) + '% ' + (current.y * 100).toFixed(1) + '%, rgba(201,163,90,0.22), transparent 50%),' +
        'radial-gradient(ellipse at 22% 18%, rgba(201,163,90,0.18), transparent 50%),' +
        'radial-gradient(ellipse at 78% 82%, rgba(90,28,28,0.28), transparent 55%),' +
        'linear-gradient(160deg, #07060a 0%, #0d0a08 30%, #1c1814 65%, #07060a 100%)';
      if (Math.abs(pos.x - current.x) > 0.001 || Math.abs(pos.y - current.y) > 0.001) {
        raf = requestAnimationFrame(loop);
      } else { raf = null; }
    }
  }
})();
