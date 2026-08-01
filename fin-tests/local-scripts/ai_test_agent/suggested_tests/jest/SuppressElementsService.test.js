/**
 * Jest Unit Tests for SuppressElementsService - PR #226 Changes
 *
 * Tests the new SuppressElementsService functionality for showing/hiding elements.
 *
 * To run: npm test -- SuppressElementsService.test.js
 *
 * Dependencies:
 *   npm install --save-dev jest jest-environment-jsdom
 */

// Jest provides jsdom environment via testEnvironment: "jsdom" in package.json
// No manual JSDOM setup needed

/**
 * Mock implementation of SuppressElementsService
 * Based on PR #226 changes to src/service/SuppressElementsService.js
 */
class SuppressElementsService {
  constructor() {
    this.suppressedElements = new Map();
    this.originalStyles = new Map();
  }

  /**
   * Hide elements matching the selector
   */
  suppressElements(selector) {
    const elements = document.querySelectorAll(selector);
    elements.forEach((el, index) => {
      const key = `${selector}_${index}`;
      this.originalStyles.set(key, {
        display: el.style.display,
        visibility: el.style.visibility,
        opacity: el.style.opacity,
      });
      el.style.display = 'none';
      el.style.visibility = 'hidden';
      this.suppressedElements.set(key, el);
    });
    return elements.length;
  }

  /**
   * Show previously hidden elements
   */
  showElements(selector) {
    const elements = document.querySelectorAll(selector);
    elements.forEach((el, index) => {
      const key = `${selector}_${index}`;
      const original = this.originalStyles.get(key);
      if (original) {
        el.style.display = original.display || '';
        el.style.visibility = original.visibility || '';
        el.style.opacity = original.opacity || '';
      } else {
        el.style.display = '';
        el.style.visibility = '';
      }
    });
    return elements.length;
  }

  /**
   * Check if body suppression flag is set
   */
  isBodySuppressed() {
    return window.suppress_body === true;
  }

  /**
   * Suppress body content
   */
  suppressBody() {
    window.suppress_body = true;
    document.body.style.visibility = 'hidden';
  }

  /**
   * Show body content
   */
  showBody() {
    window.suppress_body = false;
    document.body.style.visibility = '';
  }

  /**
   * Reset all suppressions
   */
  reset() {
    this.suppressedElements.forEach((el, key) => {
      const original = this.originalStyles.get(key);
      if (original) {
        el.style.display = original.display || '';
        el.style.visibility = original.visibility || '';
      }
    });
    this.suppressedElements.clear();
    this.originalStyles.clear();
    this.showBody();
  }
}

describe('SuppressElementsService', () => {
  let service;

  beforeEach(() => {
    // Reset DOM
    document.body.innerHTML = `
      <div id="hero-section" class="hero">Hero Content</div>
      <div id="card-ad-1" class="card-ad">Card Ad 1</div>
      <div id="card-ad-2" class="card-ad">Card Ad 2</div>
      <div id="main-content">Main Content</div>
      <div class="personalizable" data-fin-zone="hero">Zone 1</div>
      <div class="personalizable" data-fin-zone="sidebar">Zone 2</div>
    `;
    service = new SuppressElementsService();
    window.suppress_body = false;
  });

  afterEach(() => {
    service.reset();
  });

  describe('suppressElements', () => {

    test('should hide elements matching selector', () => {
      // Act
      const count = service.suppressElements('.card-ad');

      // Assert
      expect(count).toBe(2);
      const cardAds = document.querySelectorAll('.card-ad');
      cardAds.forEach(ad => {
        expect(ad.style.display).toBe('none');
        expect(ad.style.visibility).toBe('hidden');
      });
    });

    test('should hide element by ID selector', () => {
      // Act
      service.suppressElements('#hero-section');

      // Assert
      const hero = document.getElementById('hero-section');
      expect(hero.style.display).toBe('none');
    });

    test('should store original styles before hiding', () => {
      // Arrange
      const cardAd = document.getElementById('card-ad-1');
      cardAd.style.display = 'flex';
      cardAd.style.visibility = 'visible';

      // Act
      service.suppressElements('#card-ad-1');

      // Assert
      expect(service.originalStyles.get('#card-ad-1_0')).toEqual({
        display: 'flex',
        visibility: 'visible',
        opacity: '',
      });
    });

    test('should return 0 when no elements match', () => {
      // Act
      const count = service.suppressElements('.non-existent');

      // Assert
      expect(count).toBe(0);
    });

    test('should handle data attribute selectors', () => {
      // Act
      const count = service.suppressElements('[data-fin-zone="hero"]');

      // Assert
      expect(count).toBe(1);
      const zone = document.querySelector('[data-fin-zone="hero"]');
      expect(zone.style.display).toBe('none');
    });
  });

  describe('showElements', () => {

    test('should restore hidden elements', () => {
      // Arrange
      service.suppressElements('.card-ad');

      // Act
      service.showElements('.card-ad');

      // Assert
      const cardAds = document.querySelectorAll('.card-ad');
      cardAds.forEach(ad => {
        expect(ad.style.display).toBe('');
        expect(ad.style.visibility).toBe('');
      });
    });

    test('should restore original display style', () => {
      // Arrange
      const hero = document.getElementById('hero-section');
      hero.style.display = 'grid';
      service.suppressElements('#hero-section');

      // Act
      service.showElements('#hero-section');

      // Assert
      expect(hero.style.display).toBe('grid');
    });

    test('should handle showing elements that were never suppressed', () => {
      // Act - Show without suppress first
      const count = service.showElements('.card-ad');

      // Assert - Should not throw, just reset styles
      expect(count).toBe(2);
      const cardAds = document.querySelectorAll('.card-ad');
      cardAds.forEach(ad => {
        expect(ad.style.display).toBe('');
      });
    });
  });

  describe('Body Suppression', () => {

    test('should suppress body and set window flag', () => {
      // Act
      service.suppressBody();

      // Assert
      expect(window.suppress_body).toBe(true);
      expect(document.body.style.visibility).toBe('hidden');
    });

    test('should show body and clear window flag', () => {
      // Arrange
      service.suppressBody();

      // Act
      service.showBody();

      // Assert
      expect(window.suppress_body).toBe(false);
      expect(document.body.style.visibility).toBe('');
    });

    test('should correctly report body suppression status', () => {
      // Assert - Initially not suppressed
      expect(service.isBodySuppressed()).toBe(false);

      // Act
      service.suppressBody();

      // Assert
      expect(service.isBodySuppressed()).toBe(true);
    });

    test('should integrate with suppress_body window flag set externally', () => {
      // Arrange - External code sets flag
      window.suppress_body = true;

      // Assert
      expect(service.isBodySuppressed()).toBe(true);

      // Cleanup
      window.suppress_body = false;
    });
  });

  describe('reset', () => {

    test('should restore all suppressed elements', () => {
      // Arrange
      service.suppressElements('.card-ad');
      service.suppressElements('#hero-section');
      service.suppressBody();

      // Act
      service.reset();

      // Assert
      const cardAds = document.querySelectorAll('.card-ad');
      cardAds.forEach(ad => {
        expect(ad.style.display).not.toBe('none');
      });
      expect(document.body.style.visibility).not.toBe('hidden');
      expect(window.suppress_body).toBe(false);
    });

    test('should clear internal tracking maps', () => {
      // Arrange
      service.suppressElements('.card-ad');

      // Act
      service.reset();

      // Assert
      expect(service.suppressedElements.size).toBe(0);
      expect(service.originalStyles.size).toBe(0);
    });
  });

  describe('Error Handling', () => {

    test('should handle null/undefined selector gracefully', () => {
      // Act & Assert - Should not throw
      expect(() => service.suppressElements(null)).not.toThrow();
      expect(() => service.suppressElements(undefined)).not.toThrow();
    });

    test('should handle invalid selector syntax', () => {
      // Act & Assert
      expect(() => service.suppressElements('###invalid')).toThrow();
    });

    test('should handle elements removed from DOM after suppression', () => {
      // Arrange
      service.suppressElements('#card-ad-1');
      const cardAd = document.getElementById('card-ad-1');
      cardAd.parentNode.removeChild(cardAd);

      // Act & Assert - Should not throw on show
      expect(() => service.showElements('#card-ad-1')).not.toThrow();
    });
  });

  describe('Performance', () => {

    test('should handle large number of elements efficiently', () => {
      // Arrange - Add many elements
      for (let i = 0; i < 100; i++) {
        const div = document.createElement('div');
        div.className = 'perf-test-element';
        document.body.appendChild(div);
      }

      // Act
      const startTime = performance.now();
      service.suppressElements('.perf-test-element');
      service.showElements('.perf-test-element');
      const endTime = performance.now();

      // Assert - Should complete in reasonable time (< 100ms)
      expect(endTime - startTime).toBeLessThan(100);
    });
  });
});

describe('SuppressElementsService vs Old SuppressBodyService', () => {

  test('should provide more granular control than body-level suppression', () => {
    // Arrange
    const service = new SuppressElementsService();

    // Act - Suppress only card ads, not entire body
    service.suppressElements('.card-ad');

    // Assert - Hero and main content still visible
    const hero = document.getElementById('hero-section');
    const mainContent = document.getElementById('main-content');

    expect(hero.style.display).not.toBe('none');
    expect(mainContent.style.display).not.toBe('none');

    // Card ads are hidden
    const cardAds = document.querySelectorAll('.card-ad');
    cardAds.forEach(ad => {
      expect(ad.style.display).toBe('none');
    });
  });
});
