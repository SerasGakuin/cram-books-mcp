/**
 * Service factory for dependency injection
 * Allows swapping real GAS services with mocks for testing
 */
import type {
  ISpreadsheetService,
  ICacheService,
  IPropertiesService,
  ISpreadsheet,
} from "../interfaces/spreadsheet";

// Service instances
let spreadsheetService: ISpreadsheetService | null = null;
let cacheService: ICacheService | null = null;
let propertiesService: IPropertiesService | null = null;

/**
 * Get SpreadsheetApp service
 * In production, returns actual SpreadsheetApp wrapper
 * In tests, returns mocked service
 */
export function getSpreadsheetService(): ISpreadsheetService {
  if (!spreadsheetService) {
    // Production: wrap actual SpreadsheetApp
    spreadsheetService = {
      openById: (id: string): ISpreadsheet => SpreadsheetApp.openById(id) as unknown as ISpreadsheet,
    };
  }
  return spreadsheetService;
}

/**
 * Set SpreadsheetApp service (for testing)
 */
export function setSpreadsheetService(service: ISpreadsheetService): void {
  spreadsheetService = service;
}

/**
 * Get CacheService
 * In production, returns actual CacheService.getScriptCache()
 * In tests, returns mocked service
 */
export function getCacheService(): ICacheService {
  if (!cacheService) {
    const scriptCache = CacheService.getScriptCache();
    cacheService = {
      put: (key: string, value: string, expirationInSeconds: number) =>
        scriptCache.put(key, value, expirationInSeconds),
      get: (key: string) => scriptCache.get(key),
      remove: (key: string) => scriptCache.remove(key),
    };
  }
  return cacheService;
}

/**
 * Set CacheService (for testing)
 */
export function setCacheService(service: ICacheService): void {
  cacheService = service;
}

/**
 * Get PropertiesService
 * In production, returns actual PropertiesService.getScriptProperties()
 * In tests, returns mocked service
 */
export function getPropertiesService(): IPropertiesService {
  if (!propertiesService) {
    const scriptProps = PropertiesService.getScriptProperties();
    propertiesService = {
      getProperty: (key: string) => scriptProps.getProperty(key),
      setProperty: (key: string, value: string) => scriptProps.setProperty(key, value),
      deleteProperty: (key: string) => scriptProps.deleteProperty(key),
      getProperties: () => scriptProps.getProperties(),
    };
  }
  return propertiesService;
}

/**
 * Set PropertiesService (for testing)
 */
export function setPropertiesService(service: IPropertiesService): void {
  propertiesService = service;
}

/**
 * Reset all services to null (for testing cleanup)
 */
export function resetServices(): void {
  spreadsheetService = null;
  cacheService = null;
  propertiesService = null;
}
