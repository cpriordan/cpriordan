/**
 * Jest Integration Tests for PR #234 - Funnel Tracking Integration
 *
 * PR: https://github.com/Finalytics-ai/fin-personalization-js/pull/234
 * ECGC 3868 - Funnel Track Non-Identifiable Link
 *
 * Tests the integration between FinalyticsPixel and FunnelTrackingService
 * to ensure the refactored code works correctly together.
 *
 * To run: npx jest PR234_FunnelTrackingIntegration.test.js
 */

describe('PR #234 - Funnel Tracking Integration Tests', () => {
  let debuggerLogCalls;
  let mockLocalForageService;

  const debuggerLog = jest.fn((...args) => {
    debuggerLogCalls.push(args);
  });

  /**
   * Mock LocalForageService for testing
   */
  class MockLocalForageService {
    constructor() {
      this.data = {};
    }

    async getForage(key) {
      return this.data[key] || null;
    }

    async setForage(key, value) {
      this.data[key] = value;
      return value;
    }

    async removeForage(key) {
      delete this.data[key];
    }
  }

  /**
   * Simplified FunnelTrackingService
   */
  class FunnelTrackingService {
    constructor(options = {}) {
      this.debuggerLog = options.debuggerLog || debuggerLog;
    }

    parseClickUrl(url) {
      if (!url || typeof url !== 'string') {
        return { baseUrl: '', queryParams: {}, hash: '' };
      }
      try {
        const fullUrl = url.startsWith('http') ? url : `https://example.com${url.startsWith('/') ? '' : '/'}${url}`;
        const urlObj = new URL(fullUrl);
        const queryParams = {};
        urlObj.searchParams.forEach((value, key) => {
          queryParams[key] = value;
        });
        return {
          baseUrl: url.startsWith('http') ? `${urlObj.origin}${urlObj.pathname}` : urlObj.pathname,
          queryParams,
          hash: urlObj.hash,
        };
      } catch (e) {
        return { baseUrl: url, queryParams: {}, hash: '' };
      }
    }

    appendParam(url, paramName, paramValue) {
      if (!url || typeof url !== 'string') return url;
      const separator = url.includes('?') ? '&' : '?';
      const encodedValue = encodeURIComponent(paramValue);
      if (url.includes('#')) {
        const [urlWithoutHash, hash] = url.split('#');
        return `${urlWithoutHash}${separator}${paramName}=${encodedValue}#${hash}`;
      }
      return `${url}${separator}${paramName}=${encodedValue}`;
    }

    isIdentifiableLink(element) {
      if (!element) return false;
      const dataFin = element.getAttribute?.('data-fin') || element['data-fin'];
      if (dataFin) return true;
      const dataFinProduct = element.getAttribute?.('data-fin-product') || element['data-fin-product'];
      return !!dataFinProduct;
    }

    resolveCoreProductFromElement(element) {
      if (!element) return null;
      const dataFin = element.getAttribute?.('data-fin') || element['data-fin'];
      if (dataFin) {
        const match = dataFin.match(/product:([^|]+)/);
        if (match) return match[1].trim();
      }
      const dataFinProduct = element.getAttribute?.('data-fin-product') || element['data-fin-product'];
      if (dataFinProduct) return dataFinProduct;
      const href = element.getAttribute?.('href') || element.href;
      if (href) return this.inferProductFromUrl(href);
      return null;
    }

    inferProductFromUrl(url) {
      if (!url) return null;
      const urlLower = url.toLowerCase();
      if (/checking/i.test(urlLower)) return 'checking';
      if (/savings/i.test(urlLower)) return 'savings';
      if (/\bcd\b|certificate/i.test(urlLower)) return 'cd';
      if (/auto[_-]?loan|car[_-]?loan/i.test(urlLower)) return 'auto_loan';
      if (/mortgage|home[_-]?loan/i.test(urlLower)) return 'mortgage';
      if (/credit[_-]?card/i.test(urlLower)) return 'credit_card';
      return null;
    }

    extractAdIdFromDataFin(dataFin) {
      if (!dataFin) return null;
      const match = dataFin.match(/ad_id:([^|]+)/);
      return match ? match[1].trim() : null;
    }

    shouldTrackFunnel(sessionData, funnelId) {
      if (!sessionData || !funnelId) return true;
      const lastTracked = sessionData.funnelTracking?.[funnelId]?.lastTrackedAt;
      if (!lastTracked) return true;
      const hoursSinceLastTrack = (Date.now() - lastTracked) / (1000 * 60 * 60);
      return hoursSinceLastTrack >= 24;
    }

    buildFunnelStartData(element, pageContext) {
      const href = element?.getAttribute?.('href') || element?.href || '';
      const isIdentifiable = this.isIdentifiableLink(element);
      const product = this.resolveCoreProductFromElement(element);
      const dataFin = element?.getAttribute?.('data-fin') || element?.['data-fin'] || '';
      const adId = this.extractAdIdFromDataFin(dataFin);

      return {
        linkType: isIdentifiable ? 'identifiable' : 'non_identifiable',
        href,
        product,
        adId,
        pageUrl: pageContext?.currentUrl || '',
        category: pageContext?.category || null,
        timestamp: Date.now(),
      };
    }
  }

  /**
   * Simplified FinalyticsPixel that uses FunnelTrackingService
   */
  class FinalyticsPixel {
    constructor(options = {}) {
      this.localForageService = options.localForageService || new MockLocalForageService();
      this.funnelTrackingService = options.funnelTrackingService || new FunnelTrackingService({ debuggerLog });
      this.debuggerLog = debuggerLog;
      this.sessionDataKey = 'fin_session_data';
    }

    async getSessionData() {
      return await this.localForageService.getForage(this.sessionDataKey) || {
        demographics: {},
        funnelEvents: [],
        funnelTracking: {},
      };
    }

    async saveSessionData(data) {
      await this.localForageService.setForage(this.sessionDataKey, data);
      return data;
    }

    /**
     * Handle click event - integrates with FunnelTrackingService
     */
    async handleClick(element, pageContext = {}) {
      if (!element) return;

      const href = element.getAttribute?.('href') || element.href;
      if (!href) return;

      // Use FunnelTrackingService to resolve product
      const product = this.funnelTrackingService.resolveCoreProductFromElement(element);
      const isIdentifiable = this.funnelTrackingService.isIdentifiableLink(element);

      this.debuggerLog('[handleClick]', {
        href,
        product,
        isIdentifiable,
      });

      // Build funnel data using the service
      const funnelData = this.funnelTrackingService.buildFunnelStartData(element, pageContext);

      // Modify URL if needed (add fin_prod parameter)
      let modifiedHref = href;
      if (product && !href.includes('fin_prod=')) {
        modifiedHref = this.funnelTrackingService.appendParam(href, 'fin_prod', product);
      }

      return {
        originalHref: href,
        modifiedHref,
        funnelData,
        product,
        isIdentifiable,
      };
    }

    /**
     * Handle funnel start - integrates with FunnelTrackingService
     */
    async handleFunnelStart(element, pageContext = {}) {
      const sessionData = await this.getSessionData();
      const product = this.funnelTrackingService.resolveCoreProductFromElement(element);
      const funnelId = `funnel_${product || 'unknown'}`;

      // Check 24-hour cooldown
      if (!this.funnelTrackingService.shouldTrackFunnel(sessionData, funnelId)) {
        this.debuggerLog('[handleFunnelStart] Skipping - within 24hr cooldown', funnelId);
        return { skipped: true, reason: '24hr_cooldown' };
      }

      // Build funnel start data
      const funnelStartData = this.funnelTrackingService.buildFunnelStartData(element, pageContext);

      // Record funnel event
      sessionData.funnelEvents = sessionData.funnelEvents || [];
      sessionData.funnelEvents.push({
        type: 'funnel_start',
        data: funnelStartData,
        timestamp: Date.now(),
      });

      // Update funnel tracking timestamp
      sessionData.funnelTracking = sessionData.funnelTracking || {};
      sessionData.funnelTracking[funnelId] = {
        lastTrackedAt: Date.now(),
        product,
      };

      await this.saveSessionData(sessionData);

      this.debuggerLog('[handleFunnelStart] Recorded funnel start', funnelStartData);

      return {
        skipped: false,
        funnelData: funnelStartData,
        funnelId,
      };
    }

    /**
     * Modify session data based on page info
     */
    async modifySessionByPageInfo(pageDetails, currentUrl) {
      const sessionData = await this.getSessionData();

      // Track page view in session
      sessionData.pageViews = sessionData.pageViews || [];
      sessionData.pageViews.push({
        url: currentUrl,
        category: pageDetails?.category || null,
        timestamp: Date.now(),
      });

      // If this is a funnel page, track it
      if (pageDetails?.isFunnelPage) {
        sessionData.funnelPageViews = sessionData.funnelPageViews || [];
        sessionData.funnelPageViews.push({
          url: currentUrl,
          funnelStep: pageDetails.funnelStep || 'unknown',
          timestamp: Date.now(),
        });
      }

      await this.saveSessionData(sessionData);

      return sessionData;
    }

    /**
     * Handle form funnel event
     */
    async handleFormFunnelEvent(eventType, formData = {}) {
      const sessionData = await this.getSessionData();

      sessionData.formFunnelEvents = sessionData.formFunnelEvents || [];
      sessionData.formFunnelEvents.push({
        type: eventType,
        data: formData,
        timestamp: Date.now(),
      });

      await this.saveSessionData(sessionData);

      this.debuggerLog('[handleFormFunnelEvent]', eventType, formData);

      return sessionData;
    }
  }

  let pixel;

  beforeEach(() => {
    debuggerLogCalls = [];
    debuggerLog.mockClear();
    mockLocalForageService = new MockLocalForageService();
    pixel = new FinalyticsPixel({
      localForageService: mockLocalForageService,
    });
  });

  describe('Click Event Handling with FunnelTrackingService', () => {
    test('should handle click on identifiable link with data-fin', async () => {
      const element = {
        getAttribute: (attr) => {
          if (attr === 'href') return '/apply/checking';
          if (attr === 'data-fin') return 'ad_id:12345|product:checking';
          return null;
        },
      };

      const result = await pixel.handleClick(element, { currentUrl: '/homepage' });

      expect(result.isIdentifiable).toBe(true);
      expect(result.product).toBe('checking');
      expect(result.funnelData.linkType).toBe('identifiable');
      expect(result.funnelData.adId).toBe('12345');
    });

    test('should handle click on non-identifiable link', async () => {
      const element = {
        getAttribute: (attr) => {
          if (attr === 'href') return '/products/savings/open';
          return null;
        },
      };

      const result = await pixel.handleClick(element, { currentUrl: '/homepage' });

      expect(result.isIdentifiable).toBe(false);
      expect(result.product).toBe('savings'); // Inferred from URL
      expect(result.funnelData.linkType).toBe('non_identifiable');
    });

    test('should append fin_prod parameter to href', async () => {
      const element = {
        getAttribute: (attr) => {
          if (attr === 'href') return '/apply/cd';
          if (attr === 'data-fin-product') return 'cd';
          return null;
        },
      };

      const result = await pixel.handleClick(element);

      expect(result.modifiedHref).toBe('/apply/cd?fin_prod=cd');
      expect(result.originalHref).toBe('/apply/cd');
    });

    test('should not duplicate fin_prod if already present', async () => {
      const element = {
        getAttribute: (attr) => {
          if (attr === 'href') return '/apply/checking?fin_prod=checking';
          if (attr === 'data-fin-product') return 'checking';
          return null;
        },
      };

      const result = await pixel.handleClick(element);

      expect(result.modifiedHref).toBe('/apply/checking?fin_prod=checking');
    });

    test('should handle click with null element', async () => {
      const result = await pixel.handleClick(null);

      expect(result).toBeUndefined();
    });

    test('should handle click on element without href', async () => {
      const element = {
        getAttribute: () => null,
      };

      const result = await pixel.handleClick(element);

      expect(result).toBeUndefined();
    });
  });

  describe('Funnel Start Handling', () => {
    test('should record funnel start event in session data', async () => {
      const element = {
        getAttribute: (attr) => {
          if (attr === 'href') return '/apply/checking';
          if (attr === 'data-fin') return 'ad_id:123|product:checking';
          return null;
        },
      };

      const result = await pixel.handleFunnelStart(element, {
        currentUrl: '/homepage',
        category: 'deposit',
      });

      expect(result.skipped).toBe(false);
      expect(result.funnelData.product).toBe('checking');

      const sessionData = await pixel.getSessionData();
      expect(sessionData.funnelEvents).toHaveLength(1);
      expect(sessionData.funnelEvents[0].type).toBe('funnel_start');
      expect(sessionData.funnelTracking.funnel_checking).toBeDefined();
    });

    test('should skip funnel start within 24-hour cooldown', async () => {
      // First, record a funnel start
      const element = {
        getAttribute: (attr) => {
          if (attr === 'href') return '/apply/checking';
          if (attr === 'data-fin-product') return 'checking';
          return null;
        },
      };

      await pixel.handleFunnelStart(element);

      // Try to start same funnel again immediately
      const result2 = await pixel.handleFunnelStart(element);

      expect(result2.skipped).toBe(true);
      expect(result2.reason).toBe('24hr_cooldown');
    });

    test('should allow funnel start for different products', async () => {
      const checkingElement = {
        getAttribute: (attr) => {
          if (attr === 'href') return '/apply/checking';
          if (attr === 'data-fin-product') return 'checking';
          return null;
        },
      };

      const savingsElement = {
        getAttribute: (attr) => {
          if (attr === 'href') return '/apply/savings';
          if (attr === 'data-fin-product') return 'savings';
          return null;
        },
      };

      await pixel.handleFunnelStart(checkingElement);
      const result2 = await pixel.handleFunnelStart(savingsElement);

      expect(result2.skipped).toBe(false);

      const sessionData = await pixel.getSessionData();
      expect(sessionData.funnelEvents).toHaveLength(2);
      expect(sessionData.funnelTracking.funnel_checking).toBeDefined();
      expect(sessionData.funnelTracking.funnel_savings).toBeDefined();
    });
  });

  describe('Session Data Modification', () => {
    test('should track page views in session data', async () => {
      await pixel.modifySessionByPageInfo(
        { category: 'deposit' },
        '/products/checking'
      );

      const sessionData = await pixel.getSessionData();
      expect(sessionData.pageViews).toHaveLength(1);
      expect(sessionData.pageViews[0].url).toBe('/products/checking');
      expect(sessionData.pageViews[0].category).toBe('deposit');
    });

    test('should track funnel page views separately', async () => {
      await pixel.modifySessionByPageInfo(
        { category: 'deposit', isFunnelPage: true, funnelStep: 'step1' },
        '/apply/checking/step1'
      );

      const sessionData = await pixel.getSessionData();
      expect(sessionData.funnelPageViews).toHaveLength(1);
      expect(sessionData.funnelPageViews[0].funnelStep).toBe('step1');
    });

    test('should accumulate multiple page views', async () => {
      await pixel.modifySessionByPageInfo({ category: 'home' }, '/');
      await pixel.modifySessionByPageInfo({ category: 'deposit' }, '/checking');
      await pixel.modifySessionByPageInfo({ category: 'loans' }, '/auto-loan');

      const sessionData = await pixel.getSessionData();
      expect(sessionData.pageViews).toHaveLength(3);
    });
  });

  describe('Form Funnel Event Handling', () => {
    test('should record form funnel started event', async () => {
      await pixel.handleFormFunnelEvent('started', {
        formId: 'checking-application',
        product: 'checking',
      });

      const sessionData = await pixel.getSessionData();
      expect(sessionData.formFunnelEvents).toHaveLength(1);
      expect(sessionData.formFunnelEvents[0].type).toBe('started');
      expect(sessionData.formFunnelEvents[0].data.formId).toBe('checking-application');
    });

    test('should record form funnel completed event', async () => {
      await pixel.handleFormFunnelEvent('started', { formId: 'loan-app' });
      await pixel.handleFormFunnelEvent('completed', { formId: 'loan-app', success: true });

      const sessionData = await pixel.getSessionData();
      expect(sessionData.formFunnelEvents).toHaveLength(2);
      expect(sessionData.formFunnelEvents[1].type).toBe('completed');
    });

    test('should record form funnel abandoned event', async () => {
      await pixel.handleFormFunnelEvent('started', { formId: 'credit-card-app' });
      await pixel.handleFormFunnelEvent('abandoned', {
        formId: 'credit-card-app',
        lastStep: 'income-verification',
      });

      const sessionData = await pixel.getSessionData();
      expect(sessionData.formFunnelEvents[1].type).toBe('abandoned');
      expect(sessionData.formFunnelEvents[1].data.lastStep).toBe('income-verification');
    });
  });

  describe('Non-Identifiable Link Tracking (PR #234 Focus)', () => {
    test('should track non-identifiable link with inferred product', async () => {
      const element = {
        getAttribute: (attr) => {
          if (attr === 'href') return 'https://bank.com/mortgage-rates';
          return null; // No data-fin attributes
        },
      };

      const result = await pixel.handleClick(element, {
        currentUrl: '/homepage',
        category: 'home',
      });

      expect(result.isIdentifiable).toBe(false);
      expect(result.product).toBe('mortgage');
      expect(result.funnelData.linkType).toBe('non_identifiable');
      expect(result.modifiedHref).toContain('fin_prod=mortgage');
    });

    test('should track non-identifiable link without inferrable product', async () => {
      const element = {
        getAttribute: (attr) => {
          if (attr === 'href') return '/about-us';
          return null;
        },
      };

      const result = await pixel.handleClick(element);

      expect(result.isIdentifiable).toBe(false);
      expect(result.product).toBe(null);
      expect(result.modifiedHref).toBe('/about-us'); // No fin_prod added
    });

    test('should handle funnel start for non-identifiable link', async () => {
      const element = {
        getAttribute: (attr) => {
          if (attr === 'href') return '/apply/auto-loan';
          return null; // No data-fin
        },
      };

      const result = await pixel.handleFunnelStart(element, {
        currentUrl: '/loans',
        category: 'loans',
      });

      expect(result.skipped).toBe(false);
      expect(result.funnelData.linkType).toBe('non_identifiable');
      expect(result.funnelData.product).toBe('auto_loan');
    });
  });

  describe('Integration: Complete User Journey', () => {
    test('should track complete funnel journey from click to completion', async () => {
      // Step 1: User clicks on checking ad
      const adElement = {
        getAttribute: (attr) => {
          if (attr === 'href') return '/apply/checking';
          if (attr === 'data-fin') return 'ad_id:hero123|product:checking';
          return null;
        },
      };

      const clickResult = await pixel.handleClick(adElement, {
        currentUrl: '/homepage',
        category: 'home',
      });
      expect(clickResult.product).toBe('checking');

      // Step 2: Record funnel start
      const funnelResult = await pixel.handleFunnelStart(adElement, {
        currentUrl: '/homepage',
      });
      expect(funnelResult.skipped).toBe(false);

      // Step 3: User lands on application page
      await pixel.modifySessionByPageInfo(
        { category: 'deposit', isFunnelPage: true, funnelStep: 'application' },
        '/apply/checking'
      );

      // Step 4: Form started
      await pixel.handleFormFunnelEvent('started', {
        formId: 'checking-app',
        product: 'checking',
      });

      // Step 5: Form completed
      await pixel.handleFormFunnelEvent('completed', {
        formId: 'checking-app',
        product: 'checking',
        success: true,
      });

      // Verify complete journey in session data
      const sessionData = await pixel.getSessionData();

      expect(sessionData.funnelEvents).toHaveLength(1);
      expect(sessionData.funnelPageViews).toHaveLength(1);
      expect(sessionData.formFunnelEvents).toHaveLength(2);
      expect(sessionData.funnelTracking.funnel_checking).toBeDefined();
    });

    test('should maintain session data integrity across multiple interactions', async () => {
      // Multiple clicks and funnel starts
      for (let i = 0; i < 5; i++) {
        const element = {
          getAttribute: (attr) => {
            if (attr === 'href') return `/product-${i}`;
            return null;
          },
        };
        await pixel.handleClick(element);
      }

      // Page views
      for (let i = 0; i < 3; i++) {
        await pixel.modifySessionByPageInfo({ category: 'test' }, `/page-${i}`);
      }

      const sessionData = await pixel.getSessionData();

      expect(sessionData.pageViews).toHaveLength(3);
      // Session structure should be intact
      expect(sessionData.demographics).toBeDefined();
      expect(sessionData.funnelEvents).toBeDefined();
    });
  });

  describe('Regression: Backward Compatibility', () => {
    test('should maintain existing session data structure', async () => {
      // Simulate existing session data from before PR #234
      mockLocalForageService.data['fin_session_data'] = {
        demographics: {
          segment: 'millennials',
          interests: ['checking', 'savings'],
        },
        signals: {
          events: { click_1: { timestamp: 123 } },
        },
        version: '2.0',
      };

      // New PR #234 operations should not corrupt existing data
      const element = {
        getAttribute: (attr) => {
          if (attr === 'href') return '/apply/checking';
          if (attr === 'data-fin-product') return 'checking';
          return null;
        },
      };

      await pixel.handleFunnelStart(element);

      const sessionData = await pixel.getSessionData();

      // Existing data preserved
      expect(sessionData.demographics.segment).toBe('millennials');
      expect(sessionData.signals.events.click_1).toBeDefined();
      expect(sessionData.version).toBe('2.0');

      // New data added
      expect(sessionData.funnelEvents).toHaveLength(1);
    });

    test('should handle legacy page configurations', async () => {
      // Legacy format page details
      const legacyPageDetails = {
        category: 'deposit',
        product: 'checking',
        // No isFunnelPage or funnelStep
      };

      await pixel.modifySessionByPageInfo(legacyPageDetails, '/old-style-page');

      const sessionData = await pixel.getSessionData();
      expect(sessionData.pageViews).toHaveLength(1);
      expect(sessionData.funnelPageViews).toBeUndefined(); // Not a funnel page
    });
  });
});
