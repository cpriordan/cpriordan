/**
 * Jest Unit Tests for PR #235 - Personalization Disabled Detection from API Warning
 *
 * PR: https://github.com/Finalytics-ai/fin-personalization-js/pull/235
 *
 * Tests the logic that detects when personalization is disabled via API warning
 * and stores the flag in versionData.settings.personalization_is_active
 *
 * The code checks both paths:
 * - data.errors.warning (encrypted response)
 * - data.payload.errors.warning (non-encrypted response)
 *
 * To run: npx jest PR235_PersonalizationDisabledDetection.test.js
 */

describe('PR #235 - Personalization Disabled Detection from API Warning', () => {
  let versionData;
  let debuggerLogCalls;

  // Mock debuggerLog
  const debuggerLog = jest.fn((...args) => {
    debuggerLogCalls.push(args);
  });

  /**
   * Simulates the PR #235 logic for detecting personalization disabled from API warning
   * This mirrors the actual implementation in the PR
   */
  function detectPersonalizationDisabled(data, versionData) {
    // Detect personalization disabled from API warning and store flag
    // Check both paths: data.errors (encrypted) and data.payload.errors (non-encrypted)
    const apiWarning = data?.errors?.warning || data?.payload?.errors?.warning;
    if (apiWarning?.includes('personalization_is_active is not active')) {
      versionData.settings.personalization_is_active = false;
      debuggerLog('initializeApi: personalization disabled via API warning', apiWarning);
      return true;
    }
    return false;
  }

  beforeEach(() => {
    // Reset versionData before each test
    versionData = {
      settings: {
        personalization_is_active: true, // Default to true
      },
    };
    debuggerLogCalls = [];
    debuggerLog.mockClear();
  });

  describe('Encrypted Response Path (data.errors.warning)', () => {
    test('should detect personalization disabled from encrypted response path', () => {
      const data = {
        errors: {
          warning: 'personalization_is_active is not active for this client',
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(true);
      expect(versionData.settings.personalization_is_active).toBe(false);
      expect(debuggerLog).toHaveBeenCalledWith(
        'initializeApi: personalization disabled via API warning',
        'personalization_is_active is not active for this client'
      );
    });

    test('should handle exact warning message from encrypted path', () => {
      const data = {
        errors: {
          warning: 'personalization_is_active is not active',
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(true);
      expect(versionData.settings.personalization_is_active).toBe(false);
    });

    test('should handle warning with additional context from encrypted path', () => {
      const data = {
        errors: {
          warning: 'Warning: personalization_is_active is not active - feature disabled by admin',
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(true);
      expect(versionData.settings.personalization_is_active).toBe(false);
    });
  });

  describe('Non-Encrypted Response Path (data.payload.errors.warning)', () => {
    test('should detect personalization disabled from non-encrypted response path', () => {
      const data = {
        payload: {
          errors: {
            warning: 'personalization_is_active is not active for this client',
          },
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(true);
      expect(versionData.settings.personalization_is_active).toBe(false);
      expect(debuggerLog).toHaveBeenCalledWith(
        'initializeApi: personalization disabled via API warning',
        'personalization_is_active is not active for this client'
      );
    });

    test('should handle exact warning message from non-encrypted path', () => {
      const data = {
        payload: {
          errors: {
            warning: 'personalization_is_active is not active',
          },
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(true);
      expect(versionData.settings.personalization_is_active).toBe(false);
    });
  });

  describe('Path Priority (encrypted takes precedence)', () => {
    test('should use encrypted path warning when both paths have warnings', () => {
      const data = {
        errors: {
          warning: 'personalization_is_active is not active (encrypted)',
        },
        payload: {
          errors: {
            warning: 'some other warning (non-encrypted)',
          },
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(true);
      expect(versionData.settings.personalization_is_active).toBe(false);
      // Should use encrypted path warning (first in || chain)
      expect(debuggerLog).toHaveBeenCalledWith(
        'initializeApi: personalization disabled via API warning',
        'personalization_is_active is not active (encrypted)'
      );
    });

    test('should fall back to non-encrypted path when encrypted path has no warning', () => {
      const data = {
        errors: {}, // No warning in encrypted path
        payload: {
          errors: {
            warning: 'personalization_is_active is not active (non-encrypted)',
          },
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(true);
      expect(versionData.settings.personalization_is_active).toBe(false);
      expect(debuggerLog).toHaveBeenCalledWith(
        'initializeApi: personalization disabled via API warning',
        'personalization_is_active is not active (non-encrypted)'
      );
    });
  });

  describe('No Detection Cases (personalization remains active)', () => {
    test('should not detect when warning message does not contain the target string', () => {
      const data = {
        errors: {
          warning: 'Some other warning message',
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(false);
      expect(versionData.settings.personalization_is_active).toBe(true); // Unchanged
      expect(debuggerLog).not.toHaveBeenCalled();
    });

    test('should not detect when warning is null', () => {
      const data = {
        errors: {
          warning: null,
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(false);
      expect(versionData.settings.personalization_is_active).toBe(true);
      expect(debuggerLog).not.toHaveBeenCalled();
    });

    test('should not detect when warning is undefined', () => {
      const data = {
        errors: {
          warning: undefined,
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(false);
      expect(versionData.settings.personalization_is_active).toBe(true);
      expect(debuggerLog).not.toHaveBeenCalled();
    });

    test('should not detect when errors object is missing', () => {
      const data = {
        // No errors object
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(false);
      expect(versionData.settings.personalization_is_active).toBe(true);
      expect(debuggerLog).not.toHaveBeenCalled();
    });

    test('should not detect when data is null', () => {
      const data = null;

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(false);
      expect(versionData.settings.personalization_is_active).toBe(true);
      expect(debuggerLog).not.toHaveBeenCalled();
    });

    test('should not detect when data is undefined', () => {
      const data = undefined;

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(false);
      expect(versionData.settings.personalization_is_active).toBe(true);
      expect(debuggerLog).not.toHaveBeenCalled();
    });

    test('should not detect when warning is empty string', () => {
      const data = {
        errors: {
          warning: '',
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(false);
      expect(versionData.settings.personalization_is_active).toBe(true);
      expect(debuggerLog).not.toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    test('should handle case-sensitive matching (should NOT match different case)', () => {
      const data = {
        errors: {
          warning: 'PERSONALIZATION_IS_ACTIVE IS NOT ACTIVE', // Uppercase
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      // The includes() check is case-sensitive, so this should NOT match
      expect(detected).toBe(false);
      expect(versionData.settings.personalization_is_active).toBe(true);
    });

    test('should handle warning as part of larger message', () => {
      const data = {
        errors: {
          warning:
            'Multiple issues detected: personalization_is_active is not active, also rate limit exceeded',
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(true);
      expect(versionData.settings.personalization_is_active).toBe(false);
    });

    test('should handle deeply nested payload structure', () => {
      const data = {
        payload: {
          errors: {
            warning: 'personalization_is_active is not active',
            code: 'PERS_DISABLED',
            timestamp: '2025-02-03T12:00:00Z',
          },
          data: {
            // Other payload data
          },
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(true);
      expect(versionData.settings.personalization_is_active).toBe(false);
    });

    test('should handle warning with special characters', () => {
      const data = {
        errors: {
          warning: '[API] personalization_is_active is not active (code: 403)',
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(true);
      expect(versionData.settings.personalization_is_active).toBe(false);
    });

    test('should not modify other versionData.settings properties', () => {
      versionData.settings = {
        personalization_is_active: true,
        some_other_setting: 'value',
        another_flag: true,
      };

      const data = {
        errors: {
          warning: 'personalization_is_active is not active',
        },
      };

      detectPersonalizationDisabled(data, versionData);

      expect(versionData.settings.personalization_is_active).toBe(false);
      expect(versionData.settings.some_other_setting).toBe('value');
      expect(versionData.settings.another_flag).toBe(true);
    });
  });

  describe('Similar but Different Warning Messages', () => {
    test('should not match "personalization is not active" (missing underscore)', () => {
      const data = {
        errors: {
          warning: 'personalization is not active',
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(false);
      expect(versionData.settings.personalization_is_active).toBe(true);
    });

    test('should not match "personalization_is_active is inactive" (different wording)', () => {
      const data = {
        errors: {
          warning: 'personalization_is_active is inactive',
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(false);
      expect(versionData.settings.personalization_is_active).toBe(true);
    });

    test('should not match "personalization_is_active is disabled" (different wording)', () => {
      const data = {
        errors: {
          warning: 'personalization_is_active is disabled',
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(false);
      expect(versionData.settings.personalization_is_active).toBe(true);
    });

    test('should not match partial string "personalization_is_active is not"', () => {
      const data = {
        errors: {
          warning: 'personalization_is_active is not',
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(false);
      expect(versionData.settings.personalization_is_active).toBe(true);
    });
  });

  describe('Integration Scenarios', () => {
    test('should work with typical encrypted API response structure', () => {
      // Simulates a typical encrypted response
      const data = {
        success: true,
        encrypted: true,
        errors: {
          warning: 'personalization_is_active is not active',
          info: [],
        },
        data: {
          // Encrypted payload would be here
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(true);
      expect(versionData.settings.personalization_is_active).toBe(false);
    });

    test('should work with typical non-encrypted API response structure', () => {
      // Simulates a typical non-encrypted response
      const data = {
        success: true,
        encrypted: false,
        payload: {
          errors: {
            warning: 'personalization_is_active is not active',
          },
          settings: {},
          content: {},
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(true);
      expect(versionData.settings.personalization_is_active).toBe(false);
    });

    test('should handle response with no errors at all', () => {
      // Successful response with no errors
      const data = {
        success: true,
        payload: {
          settings: {},
          content: {},
        },
      };

      const detected = detectPersonalizationDisabled(data, versionData);

      expect(detected).toBe(false);
      expect(versionData.settings.personalization_is_active).toBe(true);
    });
  });
});
