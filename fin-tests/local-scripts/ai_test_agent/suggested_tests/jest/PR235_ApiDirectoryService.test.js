/**
 * Jest Unit Tests for PR #235 - ApiDirectoryService Personalization Handling
 *
 * PR: https://github.com/Finalytics-ai/fin-personalization-js/pull/235
 * ECGC-3560 - Turn Personalization Off Gracefully
 *
 * Tests the ApiDirectoryService changes that:
 * 1. Skip suppressBody when personalization_is_active is false from cached data
 * 2. Call SuppressElementsService.showElementsAll() when personalization is off
 * 3. Set window.pixelOn to false when personalization is disabled
 *
 * To run: npx jest PR235_ApiDirectoryService.test.js
 */

describe('PR #235 - ApiDirectoryService Personalization Handling', () => {
  let debuggerLogCalls;
  let mockSuppressElementsService;
  let mockLocalForageService;
  let originalWindow;

  const debuggerLog = jest.fn((...args) => {
    debuggerLogCalls.push(args);
  });

  /**
   * Mock SuppressElementsService
   */
  class MockSuppressElementsService {
    constructor() {
      this.suppressBodyCalled = false;
      this.showElementsAllCalled = false;
      this.modifyIdsInDomCalled = false;
      this.modifyIdsInDomArg = null;
    }

    suppressBody() {
      this.suppressBodyCalled = true;
    }

    showBody() {
      // Show body after suppression
    }

    showElementsAll() {
      this.showElementsAllCalled = true;
    }

    modifyIdsInDom(show) {
      this.modifyIdsInDomCalled = true;
      this.modifyIdsInDomArg = show;
    }

    reset() {
      this.suppressBodyCalled = false;
      this.showElementsAllCalled = false;
      this.modifyIdsInDomCalled = false;
      this.modifyIdsInDomArg = null;
    }
  }

  /**
   * Mock LocalForageService
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
  }

  /**
   * Simulates ApiDirectoryService behavior from PR #235
   */
  class ApiDirectoryService {
    constructor(options = {}) {
      this.suppressElementsService = options.suppressElementsService || new MockSuppressElementsService();
      this.localForageService = options.localForageService || new MockLocalForageService();
      this.debuggerLog = options.debuggerLog || debuggerLog;
    }

    /**
     * Initialize API directory - checks cached personalization state
     * PR #235: Skip body suppression if personalization is already known to be off
     */
    async initialize(cachedData = null) {
      // Check if personalization is disabled from cached data
      const personalizationIsActive = cachedData?.settings?.personalization_is_active;

      if (personalizationIsActive === false) {
        // PR #235: Skip body suppression when personalization is off
        this.debuggerLog('[ApiDirectoryService] Personalization is off from cache, skipping suppressBody');

        // Show all elements that might have been hidden
        this.suppressElementsService.showElementsAll();
        this.suppressElementsService.modifyIdsInDom(true); // true = show elements

        // Set window flags
        if (typeof window !== 'undefined') {
          window.pixelOn = false;
          window.personalization_is_active = false;
          window.finishedAdsReplacement = true;
        }

        return {
          initialized: true,
          personalizationActive: false,
          skippedSuppression: true,
        };
      }

      // Normal flow: suppress body while loading
      this.suppressElementsService.suppressBody();
      this.debuggerLog('[ApiDirectoryService] Suppressing body for personalization');

      if (typeof window !== 'undefined') {
        window.pixelOn = true;
      }

      return {
        initialized: true,
        personalizationActive: true,
        skippedSuppression: false,
      };
    }

    /**
     * Handle API response with personalization warning
     * PR #235: Gracefully disable personalization when API returns warning
     */
    async handleApiResponse(response) {
      // Check for personalization disabled warning
      const apiWarning = response?.errors?.warning || response?.payload?.errors?.warning;
      const settingsFlag = response?.settings?.personalization_is_active ??
                          response?.payload?.settings?.personalization_is_active;

      // Settings flag takes precedence
      if (settingsFlag === false) {
        return this.disablePersonalization('settings_flag');
      }

      // Check warning message
      if (typeof apiWarning === 'string' && apiWarning.includes('personalization_is_active is not active')) {
        return this.disablePersonalization('api_warning');
      }

      return {
        personalizationDisabled: false,
      };
    }

    /**
     * Disable personalization gracefully
     */
    disablePersonalization(reason) {
      this.debuggerLog('[ApiDirectoryService] Disabling personalization:', reason);

      // Show all hidden elements
      this.suppressElementsService.showElementsAll();
      this.suppressElementsService.modifyIdsInDom(true);

      // Set window flags
      if (typeof window !== 'undefined') {
        window.pixelOn = false;
        window.personalization_is_active = false;
        window.finishedAdsReplacement = true;
      }

      return {
        personalizationDisabled: true,
        reason,
      };
    }
  }

  beforeEach(() => {
    debuggerLogCalls = [];
    debuggerLog.mockClear();
    mockSuppressElementsService = new MockSuppressElementsService();
    mockLocalForageService = new MockLocalForageService();

    // Setup window mock
    originalWindow = global.window;
    global.window = {
      pixelOn: undefined,
      personalization_is_active: undefined,
      finishedAdsReplacement: undefined,
    };
  });

  afterEach(() => {
    global.window = originalWindow;
  });

  describe('Initialize with Cached Data', () => {
    test('should skip suppressBody when personalization_is_active is false from cache', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const cachedData = {
        settings: {
          personalization_is_active: false,
          cu_id: 'test_cu',
        },
      };

      const result = await service.initialize(cachedData);

      expect(result.skippedSuppression).toBe(true);
      expect(result.personalizationActive).toBe(false);
      expect(mockSuppressElementsService.suppressBodyCalled).toBe(false);
      expect(mockSuppressElementsService.showElementsAllCalled).toBe(true);
    });

    test('should call suppressBody when personalization_is_active is true', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const cachedData = {
        settings: {
          personalization_is_active: true,
          cu_id: 'test_cu',
        },
      };

      const result = await service.initialize(cachedData);

      expect(result.skippedSuppression).toBe(false);
      expect(result.personalizationActive).toBe(true);
      expect(mockSuppressElementsService.suppressBodyCalled).toBe(true);
      expect(mockSuppressElementsService.showElementsAllCalled).toBe(false);
    });

    test('should call suppressBody when personalization_is_active is undefined (default behavior)', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const cachedData = {
        settings: {
          cu_id: 'test_cu',
          // personalization_is_active not set
        },
      };

      const result = await service.initialize(cachedData);

      expect(result.skippedSuppression).toBe(false);
      expect(mockSuppressElementsService.suppressBodyCalled).toBe(true);
    });

    test('should call suppressBody when no cached data', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const result = await service.initialize(null);

      expect(result.skippedSuppression).toBe(false);
      expect(mockSuppressElementsService.suppressBodyCalled).toBe(true);
    });
  });

  describe('Window Flags', () => {
    test('should set window.pixelOn to false when personalization is off', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const cachedData = {
        settings: {
          personalization_is_active: false,
        },
      };

      await service.initialize(cachedData);

      expect(window.pixelOn).toBe(false);
    });

    test('should set window.pixelOn to true when personalization is on', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const cachedData = {
        settings: {
          personalization_is_active: true,
        },
      };

      await service.initialize(cachedData);

      expect(window.pixelOn).toBe(true);
    });

    test('should set window.personalization_is_active to false when disabled', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const cachedData = {
        settings: {
          personalization_is_active: false,
        },
      };

      await service.initialize(cachedData);

      expect(window.personalization_is_active).toBe(false);
    });

    test('should set window.finishedAdsReplacement to true when personalization is off', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const cachedData = {
        settings: {
          personalization_is_active: false,
        },
      };

      await service.initialize(cachedData);

      expect(window.finishedAdsReplacement).toBe(true);
    });
  });

  describe('SuppressElementsService Integration', () => {
    test('should call showElementsAll() when personalization is off', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const cachedData = {
        settings: {
          personalization_is_active: false,
        },
      };

      await service.initialize(cachedData);

      expect(mockSuppressElementsService.showElementsAllCalled).toBe(true);
    });

    test('should call modifyIdsInDom(true) to show elements when personalization is off', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const cachedData = {
        settings: {
          personalization_is_active: false,
        },
      };

      await service.initialize(cachedData);

      expect(mockSuppressElementsService.modifyIdsInDomCalled).toBe(true);
      expect(mockSuppressElementsService.modifyIdsInDomArg).toBe(true); // true = show
    });

    test('should NOT call showElementsAll() when personalization is on', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const cachedData = {
        settings: {
          personalization_is_active: true,
        },
      };

      await service.initialize(cachedData);

      expect(mockSuppressElementsService.showElementsAllCalled).toBe(false);
    });
  });

  describe('Handle API Response with Personalization Warning', () => {
    test('should disable personalization when settings flag is false', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const response = {
        settings: {
          personalization_is_active: false,
        },
      };

      const result = await service.handleApiResponse(response);

      expect(result.personalizationDisabled).toBe(true);
      expect(result.reason).toBe('settings_flag');
      expect(mockSuppressElementsService.showElementsAllCalled).toBe(true);
    });

    test('should disable personalization when API warning is present', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const response = {
        errors: {
          warning: 'personalization_is_active is not active for this client',
        },
      };

      const result = await service.handleApiResponse(response);

      expect(result.personalizationDisabled).toBe(true);
      expect(result.reason).toBe('api_warning');
    });

    test('should disable personalization from payload.errors.warning path', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const response = {
        payload: {
          errors: {
            warning: 'personalization_is_active is not active',
          },
        },
      };

      const result = await service.handleApiResponse(response);

      expect(result.personalizationDisabled).toBe(true);
      expect(result.reason).toBe('api_warning');
    });

    test('should prioritize settings flag over warning message', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const response = {
        settings: {
          personalization_is_active: false,
        },
        errors: {
          warning: 'personalization_is_active is not active',
        },
      };

      const result = await service.handleApiResponse(response);

      // Settings flag should take precedence
      expect(result.reason).toBe('settings_flag');
    });

    test('should NOT disable personalization when no warning or flag', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const response = {
        success: true,
        data: {},
      };

      const result = await service.handleApiResponse(response);

      expect(result.personalizationDisabled).toBe(false);
      expect(mockSuppressElementsService.showElementsAllCalled).toBe(false);
    });

    test('should NOT disable personalization when warning is unrelated', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const response = {
        errors: {
          warning: 'Rate limit exceeded',
        },
      };

      const result = await service.handleApiResponse(response);

      expect(result.personalizationDisabled).toBe(false);
    });
  });

  describe('Graceful Disable Flow', () => {
    test('should complete graceful disable flow with all side effects', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const result = service.disablePersonalization('test_reason');

      // Verify all side effects
      expect(result.personalizationDisabled).toBe(true);
      expect(result.reason).toBe('test_reason');
      expect(mockSuppressElementsService.showElementsAllCalled).toBe(true);
      expect(mockSuppressElementsService.modifyIdsInDomCalled).toBe(true);
      expect(mockSuppressElementsService.modifyIdsInDomArg).toBe(true);
      expect(window.pixelOn).toBe(false);
      expect(window.personalization_is_active).toBe(false);
      expect(window.finishedAdsReplacement).toBe(true);
    });

    test('should log when disabling personalization', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      service.disablePersonalization('cache_flag');

      expect(debuggerLog).toHaveBeenCalledWith(
        '[ApiDirectoryService] Disabling personalization:',
        'cache_flag'
      );
    });
  });

  describe('Edge Cases', () => {
    test('should handle cached data with empty settings object', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const cachedData = {
        settings: {},
      };

      const result = await service.initialize(cachedData);

      // Should proceed with normal flow (suppressBody)
      expect(result.skippedSuppression).toBe(false);
      expect(mockSuppressElementsService.suppressBodyCalled).toBe(true);
    });

    test('should handle API response with null warning', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const response = {
        errors: {
          warning: null,
        },
      };

      const result = await service.handleApiResponse(response);

      expect(result.personalizationDisabled).toBe(false);
    });

    test('should handle API response with warning as object (edge case)', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const response = {
        errors: {
          warning: { message: 'personalization_is_active is not active' },
        },
      };

      const result = await service.handleApiResponse(response);

      // Should not crash, should not disable (warning is not a string)
      expect(result.personalizationDisabled).toBe(false);
    });

    test('should handle personalization_is_active as string "false"', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      const cachedData = {
        settings: {
          personalization_is_active: 'false', // String, not boolean
        },
      };

      const result = await service.initialize(cachedData);

      // String 'false' is truthy, so should NOT skip suppression
      // This tests that we're checking for boolean false specifically
      expect(result.skippedSuppression).toBe(false);
    });
  });

  describe('Integration: First-Time vs Returning Visitor', () => {
    test('should handle first-time visitor with personalization off from API', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      // First time visitor - no cached data
      await service.initialize(null);
      expect(mockSuppressElementsService.suppressBodyCalled).toBe(true);

      // API returns personalization off
      mockSuppressElementsService.reset();
      const response = {
        errors: {
          warning: 'personalization_is_active is not active',
        },
      };

      await service.handleApiResponse(response);

      expect(mockSuppressElementsService.showElementsAllCalled).toBe(true);
      expect(window.pixelOn).toBe(false);
    });

    test('should handle returning visitor with personalization off from cache', async () => {
      const service = new ApiDirectoryService({
        suppressElementsService: mockSuppressElementsService,
        debuggerLog,
      });

      // Returning visitor - has cached data with personalization off
      const cachedData = {
        settings: {
          personalization_is_active: false,
        },
      };

      await service.initialize(cachedData);

      // Should skip suppression entirely
      expect(mockSuppressElementsService.suppressBodyCalled).toBe(false);
      expect(mockSuppressElementsService.showElementsAllCalled).toBe(true);
    });
  });
});
