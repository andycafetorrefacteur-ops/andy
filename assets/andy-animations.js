/* ============================================
   ANDY CAFÉ — PREMIUM ANIMATIONS JS
   IntersectionObserver scroll reveals
   Auto-targets Canyon theme elements
   ============================================ */

(function() {
  'use strict';

  // --- Config ---
  var THRESHOLD = 0.12;       // trigger when 12% visible
  var ROOT_MARGIN = '0px 0px -40px 0px'; // trigger a bit before bottom edge

  // --- Wait for DOM ready ---
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function init() {
    applyRevealClasses();
    startObserver();
  }

  /* ============================================
     AUTO-APPLY reveal classes to Canyon elements
     ============================================ */
  function applyRevealClasses() {

    // --- Homepage sections: fade up ---
    var sections = document.querySelectorAll(
      '.shopify-section:not(.header-section):not(.footer-section)'
    );
    sections.forEach(function(section, i) {
      // Skip hero (first section) — it has its own CSS animation
      if (i === 0) return;
      section.classList.add('andy-reveal-up');
    });

    // --- Product cards: stagger + scale ---
    var productLists = document.querySelectorAll(
      '.resource-list, .product-list, [class*="product-grid"]'
    );
    productLists.forEach(function(list) {
      var cards = list.querySelectorAll('.product-card, .collection-card');
      cards.forEach(function(card) {
        card.classList.add('andy-reveal-scale', 'andy-stagger-child');
      });
      // Mark the parent so the observer watches it
      list.classList.add('andy-stagger-parent');
    });

    // --- Media with content: left/right split ---
    var mediaBlocks = document.querySelectorAll('.media-with-content');
    mediaBlocks.forEach(function(block) {
      var media = block.querySelector('.media-with-content__media');
      var content = block.querySelector('.media-with-content__content');
      if (media) media.classList.add('andy-reveal-left');
      if (content) content.classList.add('andy-reveal-right');
    });

    // --- Section headings: reveal up ---
    var headings = document.querySelectorAll(
      '.shopify-section h2, .shopify-section h3'
    );
    headings.forEach(function(h) {
      // Don't double-animate if already inside an animated section
      if (!h.closest('.andy-reveal-up')) {
        h.classList.add('andy-reveal');
      }
    });

    // --- Collection cards (collection page) ---
    var collectionCards = document.querySelectorAll(
      '.collection-card:not(.andy-reveal-scale)'
    );
    collectionCards.forEach(function(card) {
      card.classList.add('andy-reveal-scale', 'andy-stagger-child');
    });

    // --- Blog post cards ---
    var blogCards = document.querySelectorAll('.featured-blog-posts-card');
    blogCards.forEach(function(card) {
      card.classList.add('andy-reveal-scale', 'andy-stagger-child');
    });
  }

  /* ============================================
     INTERSECTION OBSERVER
     ============================================ */
  function startObserver() {
    // Check support
    if (!('IntersectionObserver' in window)) {
      // Fallback: show everything immediately
      document.querySelectorAll('[class*="andy-reveal"]').forEach(function(el) {
        el.classList.add('andy-visible');
      });
      return;
    }

    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          var target = entry.target;

          // If it's a stagger parent, animate children
          if (target.classList.contains('andy-stagger-parent')) {
            var children = target.querySelectorAll('.andy-stagger-child');
            children.forEach(function(child) {
              child.classList.add('andy-visible');
            });
          }

          // Animate the element itself
          target.classList.add('andy-visible');

          // Unobserve after animation — no replay on scroll back
          observer.unobserve(target);
        }
      });
    }, {
      threshold: THRESHOLD,
      rootMargin: ROOT_MARGIN
    });

    // Observe all reveal targets
    var targets = document.querySelectorAll(
      '.andy-reveal, .andy-reveal-up, .andy-reveal-left, ' +
      '.andy-reveal-right, .andy-reveal-scale, .andy-stagger-parent'
    );
    targets.forEach(function(el) {
      observer.observe(el);
    });
  }

})();
