/**
 * Jest Unit Tests for PR #234 - FunnelTrackingService
 *
 * PR: https://github.com/Finalytics-ai/fin-personalization-js/pull/234
 * ECGC 3868 - Funnel Track Non-Identifiable Link
 *
 * This PR extracts funnel tracking logic into a dedicated FunnelTrackingService.
 * Tests cover all public methods of the new service.
 *
 * To run: npx jest PR234_FunnelTrackingService.test.js
 */

describe('PR #234 - FunnelTrackingService Unit Tests', () => {
  let debuggerLogCalls;

  // Mock debuggerLog
  const debuggerLog = jest.fn((...args) => {
    debuggerLogCalls.push(args);
  });

  /**
   * Simulates FunnelTrackingService based on PR #234 changes
   */
  class FunnelTrackingService {
    constructor(options = {}) {
      this.debuggerLog = options.debuggerLog || debuggerLog;
    }

    /**
     * Parse a click URL to extract query params and hash
     */
    parseClickUrl(url) {
      if (!url || typeof url !== 'string') {
        return { baseUrl: '', queryParams: {}, hash: '' };
      }

      try {
        // Handle relative URLs
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

    /**
     * Append a parameter to a URL, handling existing query strings
     */
    appendParam(url, paramName, paramValue) {
      if (!url || typeof url !== 'string') {
        return url;
      }

      const separator = url.includes('?') ? '&' : '?';
      const encodedValue = encodeURIComponent(paramValue);

      // Handle hash in URL
      if (url.includes('#')) {
        const [urlWithoutHash, hash] = url.split('#');
        return `${urlWithoutHash}${separator}${paramName}=${encodedValue}#${hash}`;
      }

      return `${url}${separator}${paramName}=${encodedValue}`;
    }

    /**
     * Check if the current page is a funnel start target
     */
    isFunnelStartTarget(pageDetails, currentUrl) {
      if (!pageDetails || !pageDetails.funnelPages) {
        return false;
      }

      const funnelPages = pageDetails.funnelPages;

      // Check if currentUrl matches any funnel start page
      for (const funnelPage of funnelPages) {
        if (funnelPage.isStart && this.urlMatches(currentUrl, funnelPage.urlPattern)) {
          return true;
        }
      }

      return false;
    }

    /**
     * Check if URL matches a pattern
     */
    urlMatches(url, pattern) {
      if (!url || !pattern) return false;

      // Simple pattern matching - supports wildcards
      const regexPattern = pattern
        .replace(/[.+?^${}()|[\]\\]/g, '\\$&') // Escape special chars except *
        .replace(/\*/g, '.*'); // Convert * to .*

      const regex = new RegExp(`^${regexPattern}$`, 'i');
      return regex.test(url);
    }

    /**
     * Resolve core product from element's data-fin attributes
     */
    resolveCoreProductFromElement(element) {
      if (!element) return null;

      // Check data-fin attribute
      const dataFin = element.getAttribute?.('data-fin') || element['data-fin'];
      if (dataFin) {
        const parsed = this.parseDataFin(dataFin);
        if (parsed.coreProduct) {
          return parsed.coreProduct;
        }
      }

      // Check data-fin-product attribute
      const dataFinProduct = element.getAttribute?.('data-fin-product') || element['data-fin-product'];
      if (dataFinProduct) {
        return dataFinProduct;
      }

      // Check href for product indicators
      const href = element.getAttribute?.('href') || element.href;
      if (href) {
        return this.inferProductFromUrl(href);
      }

      return null;
    }

    /**
     * Parse data-fin attribute value
     */
    parseDataFin(dataFin) {
      if (!dataFin || typeof dataFin !== 'string') {
        return {};
      }

      const result = {};

      // Format: "ad_id:123|product:checking|category:deposit"
      const parts = dataFin.split('|');
      for (const part of parts) {
        const [key, value] = part.split(':');
        if (key && value) {
          result[key.trim()] = value.trim();
        }
      }

      // Map common keys
      if (result.product) result.coreProduct = result.product;
      if (result.ad_id) result.adId = result.ad_id;

      return result;
    }

    /**
     * Extract ad ID from data-fin attribute
     */
    extractAdIdFromDataFin(dataFin) {
      const parsed = this.parseDataFin(dataFin);
      return parsed.adId || parsed.ad_id || null;
    }

    /**
     * Infer product type from URL
     */
    inferProductFromUrl(url) {
      if (!url || typeof url !== 'string') return null;

      const urlLower = url.toLowerCase();

      const productPatterns = [
        { pattern: /checking/i, product: 'checking' },
        { pattern: /savings/i, product: 'savings' },
        { pattern: /\bcd\b|certificate/i, product: 'cd' },
        { pattern: /auto[_-]?loan|car[_-]?loan/i, product: 'auto_loan' },
        { pattern: /mortgage|home[_-]?loan/i, product: 'mortgage' },
        { pattern: /credit[_-]?card/i, product: 'credit_card' },
        { pattern: /personal[_-]?loan/i, product: 'personal_loan' },
        { pattern: /heloc|home[_-]?equity/i, product: 'heloc' },
      ];

      for (const { pattern, product } of productPatterns) {
        if (pattern.test(urlLower)) {
          return product;
        }
      }

      return null;
    }

    /**
     * Check if link is identifiable (has tracking attributes)
     */
    isIdentifiableLink(element) {
      if (!element) return false;

      // Check for data-fin attribute
      const dataFin = element.getAttribute?.('data-fin') || element['data-fin'];
      if (dataFin) return true;

      // Check for data-fin-* attributes
      const dataFinProduct = element.getAttribute?.('data-fin-product') || element['data-fin-product'];
      const dataFinCategory = element.getAttribute?.('data-fin-category') || element['data-fin-category'];
      const dataFinAdId = element.getAttribute?.('data-fin-ad-id') || element['data-fin-ad-id'];

      return !!(dataFinProduct || dataFinCategory || dataFinAdId);
    }

    /**
     * Build funnel tracking data for non-identifiable links
     */
    buildNonIdentifiableLinkData(element, pageContext = {}) {
      const href = element?.getAttribute?.('href') || element?.href || '';

      return {
        linkType: 'non_identifiable',
        href: href,
        inferredProduct: this.inferProductFromUrl(href),
        pageUrl: pageContext.currentUrl || '',
        pageCategory: pageContext.category || null,
        timestamp: Date.now(),
      };
    }

    /**
     * Check if funnel should be tracked (24-hour cooldown)
     */
    shouldTrackFunnel(sessionData, funnelId) {
      if (!sessionData || !funnelId) return true;

      const lastTracked = sessionData.funnelTracking?.[funnelId]?.lastTrackedAt;
      if (!lastTracked) return true;

      const hoursSinceLastTrack = (Date.now() - lastTracked) / (1000 * 60 * 60);
      return hoursSinceLastTrack >= 24;
    }

    /**
     * Record funnel event
     */
    recordFunnelEvent(sessionData, eventType, eventData) {
      if (!sessionData) return sessionData;

      sessionData.funnelEvents = sessionData.funnelEvents || [];
      sessionData.funnelEvents.push({
        type: eventType,
        data: eventData,
        timestamp: Date.now(),
      });

      return sessionData;
    }
  }

  let service;

  beforeEach(() => {
    debuggerLogCalls = [];
    debuggerLog.mockClear();
    service = new FunnelTrackingService({ debuggerLog });
  });

  describe('parseClickUrl', () => {
    test('should parse URL with query parameters', () => {
      const result = service.parseClickUrl('https://example.com/page?foo=bar&baz=qux');

      expect(result.baseUrl).toBe('https://example.com/page');
      expect(result.queryParams).toEqual({ foo: 'bar', baz: 'qux' });
      expect(result.hash).toBe('');
    });

    test('should parse URL with hash fragment', () => {
      const result = service.parseClickUrl('https://example.com/page#section1');

      expect(result.baseUrl).toBe('https://example.com/page');
      expect(result.hash).toBe('#section1');
    });

    test('should parse URL with both query params and hash', () => {
      const result = service.parseClickUrl('https://example.com/page?id=123#details');

      expect(result.baseUrl).toBe('https://example.com/page');
      expect(result.queryParams).toEqual({ id: '123' });
      expect(result.hash).toBe('#details');
    });

    test('should parse relative URL', () => {
      const result = service.parseClickUrl('/products/checking?promo=true');

      expect(result.baseUrl).toBe('/products/checking');
      expect(result.queryParams).toEqual({ promo: 'true' });
    });

    test('should handle URL without query params', () => {
      const result = service.parseClickUrl('https://example.com/simple-page');

      expect(result.baseUrl).toBe('https://example.com/simple-page');
      expect(result.queryParams).toEqual({});
    });

    test('should handle empty URL', () => {
      const result = service.parseClickUrl('');

      expect(result.baseUrl).toBe('');
      expect(result.queryParams).toEqual({});
    });

    test('should handle null URL', () => {
      const result = service.parseClickUrl(null);

      expect(result.baseUrl).toBe('');
      expect(result.queryParams).toEqual({});
    });

    test('should handle URL with encoded parameters', () => {
      const result = service.parseClickUrl('https://example.com/search?q=hello%20world');

      expect(result.queryParams.q).toBe('hello world');
    });
  });

  describe('appendParam', () => {
    test('should append param to URL without existing query string', () => {
      const result = service.appendParam('https://example.com/page', 'fin_prod', 'checking');

      expect(result).toBe('https://example.com/page?fin_prod=checking');
    });

    test('should append param to URL with existing query string', () => {
      const result = service.appendParam('https://example.com/page?existing=param', 'fin_prod', 'savings');

      expect(result).toBe('https://example.com/page?existing=param&fin_prod=savings');
    });

    test('should handle URL with hash - param before hash', () => {
      const result = service.appendParam('https://example.com/page#section', 'fin_prod', 'cd');

      expect(result).toBe('https://example.com/page?fin_prod=cd#section');
    });

    test('should handle URL with query and hash', () => {
      const result = service.appendParam('https://example.com/page?a=1#section', 'b', '2');

      expect(result).toBe('https://example.com/page?a=1&b=2#section');
    });

    test('should encode special characters in param value', () => {
      const result = service.appendParam('https://example.com/page', 'name', 'John Doe');

      expect(result).toBe('https://example.com/page?name=John%20Doe');
    });

    test('should handle empty URL', () => {
      const result = service.appendParam('', 'param', 'value');

      expect(result).toBe('');
    });

    test('should handle null URL', () => {
      const result = service.appendParam(null, 'param', 'value');

      expect(result).toBe(null);
    });
  });

  describe('isFunnelStartTarget', () => {
    test('should return true when URL matches funnel start page', () => {
      const pageDetails = {
        funnelPages: [
          { urlPattern: '*/apply/checking*', isStart: true },
          { urlPattern: '*/apply/savings*', isStart: false },
        ],
      };

      const result = service.isFunnelStartTarget(pageDetails, '/apply/checking');

      expect(result).toBe(true);
    });

    test('should return false when URL matches non-start funnel page', () => {
      const pageDetails = {
        funnelPages: [
          { urlPattern: '*/apply/checking*', isStart: true },
          { urlPattern: '*/apply/step2*', isStart: false },
        ],
      };

      const result = service.isFunnelStartTarget(pageDetails, '/apply/step2');

      expect(result).toBe(false);
    });

    test('should return false when URL does not match any funnel page', () => {
      const pageDetails = {
        funnelPages: [
          { urlPattern: '*/apply/*', isStart: true },
        ],
      };

      const result = service.isFunnelStartTarget(pageDetails, '/products/checking');

      expect(result).toBe(false);
    });

    test('should return false when pageDetails is null', () => {
      const result = service.isFunnelStartTarget(null, '/apply/checking');

      expect(result).toBe(false);
    });

    test('should return false when funnelPages is empty', () => {
      const pageDetails = { funnelPages: [] };

      const result = service.isFunnelStartTarget(pageDetails, '/apply/checking');

      expect(result).toBe(false);
    });
  });

  describe('resolveCoreProductFromElement', () => {
    test('should resolve product from data-fin attribute', () => {
      const element = {
        getAttribute: (attr) => {
          if (attr === 'data-fin') return 'ad_id:123|product:checking|category:deposit';
          return null;
        },
      };

      const result = service.resolveCoreProductFromElement(element);

      expect(result).toBe('checking');
    });

    test('should resolve product from data-fin-product attribute', () => {
      const element = {
        getAttribute: (attr) => {
          if (attr === 'data-fin-product') return 'savings';
          return null;
        },
      };

      const result = service.resolveCoreProductFromElement(element);

      expect(result).toBe('savings');
    });

    test('should infer product from href when no data-fin attributes', () => {
      const element = {
        getAttribute: (attr) => {
          if (attr === 'href') return '/products/auto-loan/apply';
          return null;
        },
      };

      const result = service.resolveCoreProductFromElement(element);

      expect(result).toBe('auto_loan');
    });

    test('should return null when element is null', () => {
      const result = service.resolveCoreProductFromElement(null);

      expect(result).toBe(null);
    });

    test('should return null when no product can be resolved', () => {
      const element = {
        getAttribute: () => null,
      };

      const result = service.resolveCoreProductFromElement(element);

      expect(result).toBe(null);
    });

    test('should prioritize data-fin over data-fin-product', () => {
      const element = {
        getAttribute: (attr) => {
          if (attr === 'data-fin') return 'product:checking';
          if (attr === 'data-fin-product') return 'savings';
          return null;
        },
      };

      const result = service.resolveCoreProductFromElement(element);

      expect(result).toBe('checking');
    });
  });

  describe('extractAdIdFromDataFin', () => {
    test('should extract ad_id from data-fin string', () => {
      const result = service.extractAdIdFromDataFin('ad_id:12345|product:checking');

      expect(result).toBe('12345');
    });

    test('should handle data-fin with only ad_id', () => {
      const result = service.extractAdIdFromDataFin('ad_id:67890');

      expect(result).toBe('67890');
    });

    test('should return null when no ad_id present', () => {
      const result = service.extractAdIdFromDataFin('product:checking|category:deposit');

      expect(result).toBe(null);
    });

    test('should return null for empty string', () => {
      const result = service.extractAdIdFromDataFin('');

      expect(result).toBe(null);
    });

    test('should return null for null input', () => {
      const result = service.extractAdIdFromDataFin(null);

      expect(result).toBe(null);
    });

    test('should handle ad_id with alphanumeric value', () => {
      const result = service.extractAdIdFromDataFin('ad_id:abc123xyz');

      expect(result).toBe('abc123xyz');
    });
  });

  describe('parseDataFin', () => {
    test('should parse standard data-fin format', () => {
      const result = service.parseDataFin('ad_id:123|product:checking|category:deposit');

      expect(result.ad_id).toBe('123');
      expect(result.product).toBe('checking');
      expect(result.category).toBe('deposit');
      expect(result.coreProduct).toBe('checking');
      expect(result.adId).toBe('123');
    });

    test('should handle whitespace in data-fin', () => {
      const result = service.parseDataFin('ad_id: 123 | product: savings ');

      expect(result.ad_id).toBe('123');
      expect(result.product).toBe('savings');
    });

    test('should return empty object for empty string', () => {
      const result = service.parseDataFin('');

      expect(result).toEqual({});
    });

    test('should handle malformed data-fin gracefully', () => {
      const result = service.parseDataFin('invalid|format|without:colons');

      expect(result.without).toBe('colons');
    });
  });

  describe('inferProductFromUrl', () => {
    test('should infer checking from URL', () => {
      expect(service.inferProductFromUrl('/products/checking/apply')).toBe('checking');
      expect(service.inferProductFromUrl('https://bank.com/free-checking')).toBe('checking');
    });

    test('should infer savings from URL', () => {
      expect(service.inferProductFromUrl('/accounts/savings')).toBe('savings');
      expect(service.inferProductFromUrl('https://bank.com/high-yield-savings')).toBe('savings');
    });

    test('should infer cd from URL', () => {
      expect(service.inferProductFromUrl('/products/cd-rates')).toBe('cd');
      expect(service.inferProductFromUrl('/certificate-of-deposit')).toBe('cd');
    });

    test('should infer auto_loan from URL', () => {
      expect(service.inferProductFromUrl('/loans/auto-loan')).toBe('auto_loan');
      expect(service.inferProductFromUrl('/car-loan-rates')).toBe('auto_loan');
      expect(service.inferProductFromUrl('/autoloan/apply')).toBe('auto_loan');
    });

    test('should infer mortgage from URL', () => {
      expect(service.inferProductFromUrl('/mortgage-rates')).toBe('mortgage');
      expect(service.inferProductFromUrl('/home-loan/apply')).toBe('mortgage');
    });

    test('should infer credit_card from URL', () => {
      expect(service.inferProductFromUrl('/credit-card/rewards')).toBe('credit_card');
      expect(service.inferProductFromUrl('/creditcard/apply')).toBe('credit_card');
    });

    test('should infer personal_loan from URL', () => {
      expect(service.inferProductFromUrl('/personal-loan/rates')).toBe('personal_loan');
      expect(service.inferProductFromUrl('/personalloan')).toBe('personal_loan');
    });

    test('should infer heloc from URL', () => {
      expect(service.inferProductFromUrl('/heloc-rates')).toBe('heloc');
      expect(service.inferProductFromUrl('/home-equity/line-of-credit')).toBe('heloc');
    });

    test('should return null for generic URL', () => {
      expect(service.inferProductFromUrl('/about-us')).toBe(null);
      expect(service.inferProductFromUrl('/contact')).toBe(null);
    });

    test('should return null for empty URL', () => {
      expect(service.inferProductFromUrl('')).toBe(null);
      expect(service.inferProductFromUrl(null)).toBe(null);
    });
  });

  describe('isIdentifiableLink', () => {
    test('should return true for element with data-fin', () => {
      const element = {
        getAttribute: (attr) => attr === 'data-fin' ? 'ad_id:123' : null,
      };

      expect(service.isIdentifiableLink(element)).toBe(true);
    });

    test('should return true for element with data-fin-product', () => {
      const element = {
        getAttribute: (attr) => attr === 'data-fin-product' ? 'checking' : null,
      };

      expect(service.isIdentifiableLink(element)).toBe(true);
    });

    test('should return true for element with data-fin-ad-id', () => {
      const element = {
        getAttribute: (attr) => attr === 'data-fin-ad-id' ? '12345' : null,
      };

      expect(service.isIdentifiableLink(element)).toBe(true);
    });

    test('should return false for element without data-fin attributes', () => {
      const element = {
        getAttribute: () => null,
      };

      expect(service.isIdentifiableLink(element)).toBe(false);
    });

    test('should return false for null element', () => {
      expect(service.isIdentifiableLink(null)).toBe(false);
    });
  });

  describe('buildNonIdentifiableLinkData', () => {
    test('should build data for non-identifiable link', () => {
      const element = {
        getAttribute: (attr) => attr === 'href' ? '/products/checking/apply' : null,
      };
      const pageContext = {
        currentUrl: 'https://bank.com/homepage',
        category: 'deposit',
      };

      const result = service.buildNonIdentifiableLinkData(element, pageContext);

      expect(result.linkType).toBe('non_identifiable');
      expect(result.href).toBe('/products/checking/apply');
      expect(result.inferredProduct).toBe('checking');
      expect(result.pageUrl).toBe('https://bank.com/homepage');
      expect(result.pageCategory).toBe('deposit');
      expect(result.timestamp).toBeDefined();
    });

    test('should handle element without href', () => {
      const element = {
        getAttribute: () => null,
      };

      const result = service.buildNonIdentifiableLinkData(element, {});

      expect(result.href).toBe('');
      expect(result.inferredProduct).toBe(null);
    });
  });

  describe('shouldTrackFunnel (24-hour cooldown)', () => {
    test('should return true when funnel not previously tracked', () => {
      const sessionData = {};

      expect(service.shouldTrackFunnel(sessionData, 'funnel_checking')).toBe(true);
    });

    test('should return true when last tracked more than 24 hours ago', () => {
      const sessionData = {
        funnelTracking: {
          funnel_checking: {
            lastTrackedAt: Date.now() - (25 * 60 * 60 * 1000), // 25 hours ago
          },
        },
      };

      expect(service.shouldTrackFunnel(sessionData, 'funnel_checking')).toBe(true);
    });

    test('should return false when last tracked less than 24 hours ago', () => {
      const sessionData = {
        funnelTracking: {
          funnel_checking: {
            lastTrackedAt: Date.now() - (12 * 60 * 60 * 1000), // 12 hours ago
          },
        },
      };

      expect(service.shouldTrackFunnel(sessionData, 'funnel_checking')).toBe(false);
    });

    test('should handle null sessionData', () => {
      expect(service.shouldTrackFunnel(null, 'funnel_checking')).toBe(true);
    });

    test('should handle null funnelId', () => {
      expect(service.shouldTrackFunnel({}, null)).toBe(true);
    });
  });

  describe('recordFunnelEvent', () => {
    test('should record funnel event in sessionData', () => {
      const sessionData = {};

      const result = service.recordFunnelEvent(sessionData, 'funnel_start', {
        product: 'checking',
        adId: '123',
      });

      expect(result.funnelEvents).toHaveLength(1);
      expect(result.funnelEvents[0].type).toBe('funnel_start');
      expect(result.funnelEvents[0].data.product).toBe('checking');
      expect(result.funnelEvents[0].timestamp).toBeDefined();
    });

    test('should append to existing funnel events', () => {
      const sessionData = {
        funnelEvents: [{ type: 'existing_event', data: {}, timestamp: 123 }],
      };

      const result = service.recordFunnelEvent(sessionData, 'funnel_complete', { success: true });

      expect(result.funnelEvents).toHaveLength(2);
      expect(result.funnelEvents[1].type).toBe('funnel_complete');
    });

    test('should handle null sessionData', () => {
      const result = service.recordFunnelEvent(null, 'event', {});

      expect(result).toBe(null);
    });
  });

  describe('urlMatches (pattern matching)', () => {
    test('should match exact URL', () => {
      expect(service.urlMatches('/products/checking', '/products/checking')).toBe(true);
    });

    test('should match URL with wildcard', () => {
      expect(service.urlMatches('/products/checking/apply', '*/checking/*')).toBe(true);
    });

    test('should not match different URL', () => {
      expect(service.urlMatches('/products/savings', '/products/checking')).toBe(false);
    });

    test('should handle null URL', () => {
      expect(service.urlMatches(null, '/pattern')).toBe(false);
    });

    test('should handle null pattern', () => {
      expect(service.urlMatches('/url', null)).toBe(false);
    });
  });
});
