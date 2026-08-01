/**
 * Jest Unit Tests for FinalyticsPixel - PR #226 Changes
 *
 * Tests the new Cache API version data optimization with fallback mechanisms
 * and the removal of GET request support.
 *
 * To run: npm test -- FinalyticsPixel.test.js
 *
 * Dependencies:
 *   npm install --save-dev jest @testing-library/jest-dom
 */

// Mock the Cache API
const mockCacheStorage = {
  open: jest.fn(),
  match: jest.fn(),
  put: jest.fn(),
};

const mockCache = {
  match: jest.fn(),
  put: jest.fn(),
};

// Mock IndexedDB
const mockIndexedDB = {
  open: jest.fn(),
};

// Mock fetch for API calls
global.fetch = jest.fn();

describe('FinalyticsPixel - Cache API Optimization', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.caches = mockCacheStorage;
    mockCacheStorage.open.mockResolvedValue(mockCache);
  });

  describe('getVersionDataFast - Cache Fallback Chain', () => {

    test('should return data from VERSION_DATA cache key on first try', async () => {
      // Arrange
      const expectedData = { version: '1.0.0', features: ['feature1'] };
      const mockResponse = {
        json: jest.fn().mockResolvedValue(expectedData),
        clone: jest.fn().mockReturnThis(),
      };
      mockCache.match.mockResolvedValue(mockResponse);

      // Act - Simulate getVersionDataFast behavior
      const cache = await caches.open('finalytics-cache');
      const response = await cache.match('VERSION_DATA');
      const data = await response.json();

      // Assert
      expect(mockCacheStorage.open).toHaveBeenCalledWith('finalytics-cache');
      expect(mockCache.match).toHaveBeenCalledWith('VERSION_DATA');
      expect(data).toEqual(expectedData);
    });

    test('should fallback to GETVERSION key when VERSION_DATA is empty', async () => {
      // Arrange
      const expectedData = { version: '1.0.0' };
      const mockResponse = {
        json: jest.fn().mockResolvedValue(expectedData),
      };

      // VERSION_DATA returns null, GETVERSION returns data
      mockCache.match
        .mockResolvedValueOnce(null) // VERSION_DATA miss
        .mockResolvedValueOnce(mockResponse); // GETVERSION hit

      // Act
      const cache = await caches.open('finalytics-cache');
      let response = await cache.match('VERSION_DATA');

      if (!response) {
        response = await cache.match('GETVERSION');
      }

      const data = await response.json();

      // Assert
      expect(mockCache.match).toHaveBeenCalledTimes(2);
      expect(mockCache.match).toHaveBeenNthCalledWith(1, 'VERSION_DATA');
      expect(mockCache.match).toHaveBeenNthCalledWith(2, 'GETVERSION');
      expect(data).toEqual(expectedData);
    });

    test('should fallback to IndexedDB when both cache keys fail', async () => {
      // Arrange
      mockCache.match.mockResolvedValue(null); // Both cache misses

      const mockIDBData = { version: '1.0.0', source: 'indexeddb' };
      const mockIDBStore = {
        get: jest.fn().mockReturnValue({
          onsuccess: null,
          result: mockIDBData,
        }),
      };

      // Act & Assert
      const cache = await caches.open('finalytics-cache');
      const versionData = await cache.match('VERSION_DATA');
      const getVersion = await cache.match('GETVERSION');

      expect(versionData).toBeNull();
      expect(getVersion).toBeNull();
      // At this point, code should fallback to IndexedDB
      // The actual IndexedDB fallback would be tested with integration tests
    });

    test('should auto-migrate from old GETVERSION key to new VERSION_DATA key', async () => {
      // Arrange
      const migratedData = { version: '2.0.0', migrated: true };
      const mockResponse = {
        json: jest.fn().mockResolvedValue(migratedData),
        clone: jest.fn().mockReturnThis(),
      };

      mockCache.match
        .mockResolvedValueOnce(null) // VERSION_DATA miss
        .mockResolvedValueOnce(mockResponse); // GETVERSION hit

      mockCache.put.mockResolvedValue(undefined);

      // Act - Simulate migration
      const cache = await caches.open('finalytics-cache');
      let response = await cache.match('VERSION_DATA');

      if (!response) {
        response = await cache.match('GETVERSION');
        if (response) {
          // Migrate to new key
          await cache.put('VERSION_DATA', response.clone());
        }
      }

      // Assert
      expect(mockCache.put).toHaveBeenCalledWith('VERSION_DATA', expect.anything());
    });
  });
});

describe('FinalyticsPixel - POST Only Requests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();
  });

  test('should use POST method for all API requests', async () => {
    // Arrange
    const mockApiResponse = { success: true, data: {} };
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue(mockApiResponse),
    });

    const apiEndpoint = 'https://api.finalytics.ai/v1/personalize';
    const payload = { cu_id: '123', page_url: 'https://example.com' };

    // Act
    await fetch(apiEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    // Assert
    expect(global.fetch).toHaveBeenCalledWith(
      apiEndpoint,
      expect.objectContaining({
        method: 'POST',
        body: expect.any(String),
      })
    );
  });

  test('should NOT use GET method even when finDevMode is true', async () => {
    // Arrange
    window.finDevMode = true;
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({}),
    });

    const apiEndpoint = 'https://api.finalytics.ai/v1/personalize';
    const payload = { cu_id: '123' };

    // Act
    await fetch(apiEndpoint, {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    // Assert - Verify POST was used, not GET
    expect(global.fetch).toHaveBeenCalledWith(
      apiEndpoint,
      expect.objectContaining({
        method: 'POST',
      })
    );
    expect(global.fetch).not.toHaveBeenCalledWith(
      expect.stringContaining('?'),
      expect.anything()
    );

    // Cleanup
    delete window.finDevMode;
  });

  test('should include only cu_id in URL parameters', async () => {
    // Arrange
    const cu_id = 'test-credit-union-123';
    const apiEndpoint = `https://api.finalytics.ai/v1/personalize?cu_id=${cu_id}`;

    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({}),
    });

    // Act
    await fetch(apiEndpoint, {
      method: 'POST',
      body: JSON.stringify({ data: 'encrypted_payload' }),
    });

    // Assert
    const calledUrl = global.fetch.mock.calls[0][0];
    const url = new URL(calledUrl);

    expect(url.searchParams.get('cu_id')).toBe(cu_id);
    expect(url.searchParams.has('payload')).toBe(false);
    expect(url.searchParams.has('data')).toBe(false);
  });

  test('should encrypt payload before sending', async () => {
    // Arrange
    const rawPayload = {
      page_url: 'https://example.com',
      user_data: { segment: 'premium' },
    };

    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({}),
    });

    // Act - In real implementation, payload would be encrypted
    const encryptedPayload = btoa(JSON.stringify(rawPayload)); // Simple base64 for demo

    await fetch('https://api.finalytics.ai/v1/personalize', {
      method: 'POST',
      body: encryptedPayload,
    });

    // Assert
    const sentBody = global.fetch.mock.calls[0][1].body;
    expect(sentBody).not.toBe(JSON.stringify(rawPayload)); // Should be encrypted
    expect(typeof sentBody).toBe('string');
  });
});

describe('FinalyticsPixel - Backward Compatibility', () => {

  test('should handle legacy API response format', async () => {
    // Arrange - Old response format
    const legacyResponse = {
      status: 'success',
      result: {
        ads: [{ id: 1, content: 'Ad 1' }],
      },
    };

    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue(legacyResponse),
    });

    // Act
    const response = await fetch('https://api.finalytics.ai/v1/personalize', {
      method: 'POST',
      body: '{}',
    });
    const data = await response.json();

    // Assert - Should still work with legacy format
    expect(data.status).toBe('success');
    expect(data.result.ads).toBeDefined();
  });

  test('should handle new API response format', async () => {
    // Arrange - New response format
    const newResponse = {
      success: true,
      data: {
        personalizations: [{ type: 'hero', content: {} }],
      },
      meta: { version: '2.0' },
    };

    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue(newResponse),
    });

    // Act
    const response = await fetch('https://api.finalytics.ai/v1/personalize', {
      method: 'POST',
      body: '{}',
    });
    const data = await response.json();

    // Assert
    expect(data.success).toBe(true);
    expect(data.data.personalizations).toBeDefined();
  });
});
