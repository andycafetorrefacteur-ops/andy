/* ============================================================
   ANDY CAFÉ — LUXURY ANIMATION ENGINE
   - Scroll reveals (line, fade, mask, stagger)
   - Magnetic buttons + cursor follow
   - Header solidify on scroll
   - Parallax (data-parallax)
   - Number counters (data-counter)
   - Marquee speed-on-direction
   - Image clip-path reveals
   - Page-load hero choreography
   ============================================================ */

(function () {
  'use strict';

  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var supportsIO = 'IntersectionObserver' in window;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function init() {
    document.documentElement.classList.add('lux-ready');
    autoTagElements();
    if (!prefersReducedMotion) {
      setupReveals();
      setupHeaderSolidify();
      setupMagnetic();
      setupParallax();
      setupCounters();
      setupTilt();
      setupHeroChoreo();
      setupSmoothAnchors();
    } else {
      // Make everything visible immediately
      document.querySelectorAll('.lux-reveal, .lux-reveal-up, .lux-reveal-mask, .lux-reveal-line, .ac-reveal, .lux-stagger-parent')
        .forEach(function (el) { el.classList.add('lux-in', 'visible', 'andy-visible'); });
    }
  }

  /* ========================================================
     AUTO-TAG — apply reveal classes to native Horizon elements
     ======================================================== */
  function autoTagElements() {
    // Native sections
    document.querySelectorAll('.shopify-section').forEach(function (section, i) {
      if (i === 0) return; // hero handled separately
      if (section.classList.contains('header-section') || section.classList.contains('footer-section')) return;
      section.classList.add('lux-reveal-up');
    });

    // Product cards stagger
    document.querySelectorAll('.product-list, .resource-list, [class*="products-grid"]').forEach(function (list) {
      var cards = list.querySelectorAll('.product-card, .resource-list__item, .ac-product-card');
      if (cards.length) {
        list.classList.add('lux-stagger-parent');
        cards.forEach(function (c) { c.classList.add('lux-stagger-child'); });
      }
    });

    // Collection cards
    document.querySelectorAll('.collection-card, .ac-collection-card').forEach(function (c) {
      if (!c.classList.contains('lux-stagger-child')) c.classList.add('lux-reveal-up');
    });

    // Headings get a subtle reveal-up
    document.querySelectorAll('.shopify-section h1, .shopify-section h2').forEach(function (h) {
      if (!h.closest('.lux-reveal-up') && !h.closest('.ac-hero')) {
        h.classList.add('lux-reveal-line');
      }
    });

    // Media blocks - clip reveal
    document.querySelectorAll('.media-with-content__media, .ac-story-visual').forEach(function (m) {
      m.classList.add('lux-reveal-mask');
    });
  }

  /* ========================================================
     REVEALS (single shared observer)
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
            }, i * 80);
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
     HEADER — solidify on scroll
     ======================================================== */
  function setupHeaderSolidify() {
    var header = document.querySelector('header-component, .header, .header-section');
    if (!header) return;

    var ticking = false;
    function update() {
      if (window.scrollY > 24) {
        header.classList.add('lux-header-scrolled');
      } else {
        header.classList.remove('lux-header-scrolled');
      }
      ticking = false;
    }

    window.addEventListener('scroll', function () {
      if (!ticking) {
        window.requestAnimationFrame(update);
        ticking = true;
      }
    }, { passive: true });
    update();
  }

  /* ========================================================
     MAGNETIC BUTTONS
     ======================================================== */
  function setupMagnetic() {
    if (!window.matchMedia('(any-pointer: fine)').matches) return;

    var targets = document.querySelectorAll(
      '.lux-magnetic, .ac-btn-primary, .ac-btn-outline, .ac-add-btn, .ac-coll-arrow'
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
        } else {
          raf = null;
        }
      }

      el.addEventListener('mouseenter', function () {
        rect = el.getBoundingClientRect();
      });

      el.addEventListener('mousemove', function (e) {
        if (!rect) rect = el.getBoundingClientRect();
        var relX = e.clientX - rect.left - rect.width / 2;
        var relY = e.clientY - rect.top - rect.height / 2;
        target.x = (relX / rect.width) * strength;
        target.y = (relY / rect.height) * strength;
        if (!raf) raf = requestAnimationFrame(loop);
      });

      el.addEventListener('mouseleave', function () {
        target.x = 0;
        target.y = 0;
        if (!raf) raf = requestAnimationFrame(loop);
      });
    });
  }

  /* ========================================================
     PARALLAX — apply translate based on data-parallax
     ======================================================== */
  function setupParallax() {
    var els = document.querySelectorAll('[data-parallax]');
    if (!els.length) return;
    if (!window.matchMedia('(min-width: 768px)').matches) return;

    var items = Array.prototype.map.call(els, function (el) {
      return {
        el: el,
        speed: parseFloat(el.dataset.parallax) || 0.2,
        rect: null
      };
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
      if (!ticking) {
        window.requestAnimationFrame(update);
        ticking = true;
      }
    }, { passive: true });
    update();
  }

  /* ========================================================
     COUNTERS — animate numbers up to target on reveal
     ======================================================== */
  function setupCounters() {
    var counters = document.querySelectorAll('[data-counter]');
    if (!counters.length || !supportsIO) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        animateCount(el);
        observer.unobserve(el);
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
    var duration = 1800;
    var start = performance.now();
    var startVal = 0;

    function step(now) {
      var t = Math.min(1, (now - start) / duration);
      var eased = 1 - Math.pow(1 - t, 3);
      var value = startVal + (target - startVal) * eased;
      var display = Number.isInteger(target) ? Math.round(value) : value.toFixed(1);
      el.textContent = display + suffix;
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  /* ========================================================
     TILT — subtle 3D on hover for product/collection cards
     ======================================================== */
  function setupTilt() {
    if (!window.matchMedia('(any-pointer: fine)').matches) return;

    var cards = document.querySelectorAll('.lux-tilt');
    cards.forEach(function (el) {
      var max = 6;
      var rect;

      el.style.transformStyle = 'preserve-3d';
      el.style.willChange = 'transform';

      el.addEventListener('mouseenter', function () {
        rect = el.getBoundingClientRect();
      });

      el.addEventListener('mousemove', function (e) {
        if (!rect) rect = el.getBoundingClientRect();
        var px = (e.clientX - rect.left) / rect.width;
        var py = (e.clientY - rect.top) / rect.height;
        var rx = (0.5 - py) * max;
        var ry = (px - 0.5) * max;
        el.style.transform = 'perspective(900px) rotateX(' + rx.toFixed(2) + 'deg) rotateY(' + ry.toFixed(2) + 'deg)';
      });

      el.addEventListener('mouseleave', function () {
        el.style.transform = 'perspective(900px) rotateX(0) rotateY(0)';
      });
    });
  }

  /* ========================================================
     HERO CHOREO — sequenced fade up on load
     ======================================================== */
  function setupHeroChoreo() {
    var hero = document.querySelector('.ac-hero, .hero, [class*="hero_"]');
    if (!hero) return;

    var content = hero.querySelector('.ac-hero-content, .hero__content, .group-block-content');
    if (!content) {
      // fallback
      content = hero;
    }

    var children = content.children.length
      ? Array.prototype.slice.call(content.children)
      : [content];

    children.forEach(function (child, i) {
      child.style.opacity = '0';
      child.style.transform = 'translateY(40px)';
      child.style.transition = 'opacity 1.1s cubic-bezier(0.22,1,0.36,1) ' + (i * 0.12 + 0.2) + 's, transform 1.1s cubic-bezier(0.22,1,0.36,1) ' + (i * 0.12 + 0.2) + 's';
    });

    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        children.forEach(function (child) {
          child.style.opacity = '1';
          child.style.transform = 'translateY(0)';
        });
      });
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
})();
