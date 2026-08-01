import os
import json
import requests
import time
import re
import importlib.util
from typing import Dict, List, Optional

# Load settings from settings-postman.py (hyphen in filename prevents normal import)
_settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings-postman.py')
_spec = importlib.util.spec_from_file_location("settings_postman", _settings_path)
_settings_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_settings_mod)

POSTMAN_KEY = _settings_mod.POSTMAN_KEY
REQUEST_TIMEOUT = getattr(_settings_mod, 'REQUEST_TIMEOUT', 30)


class PostmanExporter:
    """Tool for exporting Postman collections via API"""
    
    def __init__(self):
        self.api_key = POSTMAN_KEY
        self.base_url = "https://api.getpostman.com"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def get_workspaces(self):
        """Get all workspaces"""
        response = requests.get(
            f"{self.base_url}/workspaces",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    
    def find_finalytics_workspace(self):
        """Find the Finalytics workspace"""
        workspaces = self.get_workspaces()
        for workspace in workspaces.get('workspaces', []):
            if 'finalytics' in workspace['name'].lower():
                return workspace['id']
        raise ValueError("Finalytics workspace not found")
    
    def get_collections_in_workspace(self, workspace_id):
        """Get all collections in a specific workspace"""
        response = requests.get(
            f"{self.base_url}/workspaces/{workspace_id}",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        workspace_data = response.json()
        return workspace_data.get('workspace', {}).get('collections', [])
    
    def get_collection_details(self, collection_id):
        """Get detailed collection data including tests"""
        response = requests.get(
            f"{self.base_url}/collections/{collection_id}",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    
    def sanitize_filename(self, name):
        """Sanitize collection name for filename"""
        # Replace invalid filename characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()
    
    def export_collection_to_file(self, collection_data, output_dir):
        """Export collection data to JSON file"""
        collection_info = collection_data.get('collection', {})
        collection_name = collection_info.get('info', {}).get('name', 'unknown')
        
        # Create sanitized filename
        filename = f"{self.sanitize_filename(collection_name)}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Write collection data to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(collection_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def get_all_collections(self):
        """Get all collections directly accessible via API"""
        response = requests.get(
            f"{self.base_url}/collections",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json().get('collections', [])
    
    def export_all_finalytics_collections(self):
        """Export all collections from Finalytics workspace"""
        try:
            # Get collections directly from API (more reliable than workspace approach)
            collections = self.get_all_collections()
            print(f"Found {len(collections)} accessible collections")
            
            # Set output directory
            output_dir = os.path.join(os.path.dirname(__file__), 'tests', 'postman')
            
            exported_files = []
            
            # Export each collection
            for collection in collections:
                collection_id = collection['id']
                collection_name = collection['name']
                
                print(f"Exporting collection: {collection_name}")
                
                try:
                    # Get detailed collection data
                    collection_data = self.get_collection_details(collection_id)
                    
                    # Export to file
                    filepath = self.export_collection_to_file(collection_data, output_dir)
                    exported_files.append(filepath)
                    
                    print(f"Exported: {filepath}")
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        print(f"Collection '{collection_name}' not accessible (404) - skipping")
                    else:
                        print(f"HTTP error for collection '{collection_name}': {e}")
                except Exception as e:
                    print(f"Error exporting collection '{collection_name}': {str(e)}")
                    continue
            
            print(f"\nExported {len(exported_files)} collections to {output_dir}")
            return exported_files
            
        except Exception as e:
            print(f"Error exporting collections: {str(e)}")
            raise


def export_postman_collections():
    """Convenience function to export Finalytics collections"""
    exporter = PostmanExporter()
    return exporter.export_all_finalytics_collections()


def export_specific_collection(collection_name, output_dir=None):
    """Export a specific collection by name"""
    exporter = PostmanExporter()
    
    # Find workspace and collections
    workspace_id = exporter.find_finalytics_workspace()
    collections = exporter.get_collections_in_workspace(workspace_id)
    
    # Find matching collection
    target_collection = None
    for collection in collections:
        if collection['name'].lower() == collection_name.lower():
            target_collection = collection
            break
    
    if not target_collection:
        raise ValueError(f"Collection '{collection_name}' not found in Finalytics workspace")
    
    # Get collection details and export
    collection_data = exporter.get_collection_details(target_collection['id'])
    
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), 'tests', 'postman')
    
    return exporter.export_collection_to_file(collection_data, output_dir)


class PostmanTestRunner:
    """Run and validate Postman collection tests"""
    
    def __init__(self, api_url: str, token: str):
        self.api_url = api_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {token}"
        }
        self.current_timestamp = int(time.time() * 1000)
    
    def load_collection(self, collection_path: str) -> Dict:
        """Load Postman collection JSON"""
        with open(collection_path, 'r') as f:
            data = json.load(f)
            return data.get('collection', data)  # Handle nested structure
    
    def replace_timestamps(self, payload_str: str, timestamp: Optional[int] = None) -> str:
        """Replace Postman timestamp variables with actual timestamp"""
        if timestamp is None:
            timestamp = self.current_timestamp
            
        # Replace {{$timestamp}} variables
        payload_str = re.sub(r'\{\{\$timestamp\}\}', str(timestamp), payload_str)
        # Replace standalone timestamp values
        payload_str = re.sub(r'"timestamp":\s*\d+', f'"timestamp": {timestamp}', payload_str)
        return payload_str
    
    def extract_postman_validation(self, script_exec: List[str]) -> Dict:
        """Extract validation patterns from Postman test scripts"""
        if not script_exec:
            return {}
        
        script_text = '\n'.join(script_exec)
        # Strip whole-line JS comments (e.g. stale/replaced assertions left
        # commented out above the active one) so the regexes below don't pick
        # up dead code as a live expectation.
        script_text = '\n'.join(
            line for line in script_text.split('\n') if not line.strip().startswith('//')
        )
        validation = {
            'pm_tests': [],
            'expects_ads': None,
            'expected_ad_names': [],
            'expected_algorithms': [],
            'expected_classes': []
        }
        
        # Extract pm.test patterns for ad expectations
        pm_test_matches = re.findall(r'pm\.test\("([^"]+)".*?expect\(([^)]+)\)\.to\.eql\("([^"]+)"\)', script_text)
        validation['pm_tests'] = pm_test_matches
        
        # Check for "More than 0 ads" expectations
        if 'jsonData.ads.length' in script_text:
            if '.to.be.greaterThan(0)' in script_text or 'ads[0]' in script_text:
                validation['expects_ads'] = True
            elif '.to.eql(0)' in script_text:
                validation['expects_ads'] = False
        
        # Extract utils.findFirstAd patterns
        find_ad_matches = re.findall(r'utils\.findFirstAd\(\s*[\'"]([^\'\"]+)[\'\"],\s*[\'"]([^\'\"]+)[\'\"],?\s*[\'"]?([^\'\"]*)[\'"]?\)', script_text)
        for match in find_ad_matches:
            div_class, ad_name, search_type = match
            validation['expected_ad_names'].append({
                'name': ad_name,
                'div_class': div_class,
                'search_type': search_type or 'class'
            })
        
        # Extract utils.algCheck patterns
        alg_matches = re.findall(r'utils\.algCheck\(\s*[\'"]([^\'\"]+)[\'\"],\s*[\'"]([^\'\"]*)[\'\"]\)', script_text)
        for alg_match in alg_matches:
            algorithm, product = alg_match
            validation['expected_algorithms'].append({
                'algorithm': algorithm,
                'product': product
            })
        
        return validation
    
    def validate_algorithm(self, expected_alg: str, actual_alg: str, product: str = '', core_product: str = '') -> bool:
        """Match algorithm validation like Postman's real utils.algCheck.

        The collection's own algCheck(alg, core_product) checks
        ad.algorithms.includes(alg) AND ad.core_product === core_product
        (a separate field on the ad) -- not whether the product name is a
        substring of the algorithms string.
        """
        if not actual_alg:
            return False

        # Split expected algorithm and check if all parts exist
        expected_parts = [part.strip() for part in expected_alg.split(',')]

        for part in expected_parts:
            if part not in actual_alg:
                return False

        # Match core_product like the collection's algCheck does
        if product:
            if core_product != product:
                return False
        elif core_product:
            return False

        return True
    
    def validate_ad_name(self, expected_info: Dict, ads: List[Dict]) -> bool:
        """Match Postman's findFirstAd logic"""
        expected_name = expected_info['name']
        div_class = expected_info.get('div_class')
        
        for ad in ads:
            ad_name = ad.get('name', '')
            
            # Check if expected name is contained in actual name
            if expected_name.lower() in ad_name.lower():
                # Also check div_class if specified
                if div_class:
                    if ad.get('div_class') == div_class:
                        return True
                else:
                    return True
        return False
    
    def process_response_like_postman(self, response_json: Dict, validation: Dict) -> Dict:
        """Process API response using Postman validation patterns"""
        ads = response_json.get('ads', [])
        
        results = {
            'status_200': True,  # Always true if we got this far
            'ads_count_check': None,
            'validation_errors_check': not response_json.get('errors', False),
            'ad_name_checks': {},
            'algorithm_checks': {},
            'total_ads': len(ads)
        }
        
        # Check ad count expectations
        if validation.get('expects_ads') is not None:
            if validation['expects_ads']:
                results['ads_count_check'] = len(ads) > 0
            else:
                results['ads_count_check'] = len(ads) == 0
        
        # Validate specific ad names
        for expected_ad in validation.get('expected_ad_names', []):
            ad_key = f"{expected_ad['div_class']} {expected_ad['name']}"
            results['ad_name_checks'][ad_key] = self.validate_ad_name(expected_ad, ads)
        
        # Validate algorithms
        for expected_alg in validation.get('expected_algorithms', []):
            alg_key = f"{expected_alg['algorithm']} {expected_alg['product']}"
            found_alg = False
            for ad in ads:
                if self.validate_algorithm(expected_alg['algorithm'], ad.get('algorithms', ''),
                                            expected_alg['product'], ad.get('core_product', '')):
                    found_alg = True
                    break
            results['algorithm_checks'][alg_key] = found_alg
        
        return results
    
    def run_single_test(self, test_item: Dict) -> Dict:
        """Run a single test from Postman collection"""
        test_name = test_item.get('name', 'Unknown')
        
        # Get request data
        request_data = test_item.get('request', {})
        
        if request_data.get('method') != 'POST':
            return {"name": test_name, "status": "skipped", "reason": "Not POST"}
        
        # Get the body
        body = request_data.get('body', {})
        if body.get('mode') != 'raw':
            return {"name": test_name, "status": "skipped", "reason": "No raw body"}
        
        raw_body = body.get('raw', '')
        if not raw_body:
            return {"name": test_name, "status": "skipped", "reason": "Empty body"}
        
        try:
            # Replace timestamps
            updated_body = self.replace_timestamps(raw_body)
            payload = json.loads(updated_body)
            
            # Get test validation expectations
            validation = {}
            test_events = test_item.get('event', [])
            for event in test_events:
                if event.get('listen') == 'test':
                    script = event.get('script', {})
                    validation = self.extract_postman_validation(script.get('exec', []))
                    break
            
            # Make the API call
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                result_json = response.json()
                results = self.process_response_like_postman(result_json, validation)
                
                # Calculate pass/fail based on validation
                passed_tests = []
                failed_tests = []
                
                # Status check always passes if we got here
                passed_tests.append("Status code is 200")
                
                # Ad count check
                if results['ads_count_check'] is not None:
                    check_name = f"More than 0 ads: {results['total_ads']} ad(s)"
                    if results['ads_count_check']:
                        passed_tests.append(check_name)
                    else:
                        failed_tests.append(check_name)
                
                # Validation errors check
                if results['validation_errors_check']:
                    passed_tests.append("Validation Errors")
                else:
                    failed_tests.append("Validation Errors")
                
                # Ad name checks
                for ad_check, passed in results['ad_name_checks'].items():
                    check_name = f"Ad Name: {ad_check}"
                    if passed:
                        passed_tests.append(check_name)
                    else:
                        failed_tests.append(check_name)
                
                # Algorithm checks
                for alg_check, passed in results['algorithm_checks'].items():
                    check_name = f"Algorithm: {alg_check}"
                    if passed:
                        passed_tests.append(check_name)
                    else:
                        failed_tests.append(check_name)
                
                return {
                    "name": test_name,
                    "status": "completed",
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "total_ads": results['total_ads'],
                    "response_time": result_json.get('t', 0),
                    "validation": validation
                }
            else:
                return {
                    "name": test_name, 
                    "status": "api_error", 
                    "error": f"{response.status_code}: {response.text}"
                }
                
        except json.JSONDecodeError as e:
            return {"name": test_name, "status": "json_error", "error": str(e)}
        except requests.RequestException as e:
            return {"name": test_name, "status": "request_error", "error": str(e)}
        except Exception as e:
            return {"name": test_name, "status": "error", "error": str(e)}
    
    def run_collection(self, collection_path: str) -> Dict:
        """Run entire Postman collection"""
        collection = self.load_collection(collection_path)
        items = collection.get('item', [])
        
        results = []
        total_passed = 0
        total_failed = 0
        
        print(f"🎯 Running Postman Collection: {collection.get('info', {}).get('name', 'Unknown')}")
        print(f"Found {len(items)} test cases")
        print("=" * 60)
        
        for i, item in enumerate(items, 1):
            print(f"\n[{i}/{len(items)}] Running: {item.get('name', 'Unknown')}")
            result = self.run_single_test(item)
            results.append(result)
            
            if result['status'] == 'completed':
                passed = len(result['passed_tests'])
                failed = len(result['failed_tests'])
                total_passed += passed
                total_failed += failed
                
                if failed == 0:
                    print(f"  ✅ ALL PASSED ({passed}/{passed + failed})")
                else:
                    print(f"  ❌ PARTIAL ({passed}/{passed + failed}) - {failed} failed")
                    for test in result['failed_tests']:
                        print(f"    ❌ {test}")
            else:
                print(f"  💥 {result['status'].upper()}: {result.get('error', 'Unknown error')}")
            
            # Small delay between tests
            time.sleep(0.1)
        
        # Summary
        print(f"\n{'=' * 60}")
        print("📊 COLLECTION SUMMARY")
        print(f"{'=' * 60}")
        print(f"✅ Total Passed: {total_passed}")
        print(f"❌ Total Failed: {total_failed}")
        print(f"📊 Success Rate: {total_passed/(total_passed + total_failed)*100:.1f}%" if (total_passed + total_failed) > 0 else "N/A")
        print(f"🕒 Total Tests: {len(items)}")
        
        return {
            'results': results,
            'summary': {
                'total_passed': total_passed,
                'total_failed': total_failed,
                'total_tests': len(items),
                'success_rate': total_passed/(total_passed + total_failed) if (total_passed + total_failed) > 0 else 0
            }
        }


def run_postman_test_suite(collection_path: str, api_url: str = "http://localhost:8001/api/v1/getads/",
                          token: str = None) -> Dict:
    """
    Convenience function to run a Postman test suite

    Args:
        collection_path: Path to Postman collection JSON file
        api_url: API endpoint URL
        token: API authentication token (falls back to FIN_API_TOKEN env var if None)

    Returns:
        Dict with test results and summary
    """
    if token is None:
        token = os.environ.get('FIN_API_TOKEN') or getattr(_settings_mod, 'FIN_API_TOKEN', None)
        if not token:
            raise ValueError("No token provided. Set FIN_API_TOKEN in environment or settings-postman.py")
    
    runner = PostmanTestRunner(api_url, token)
    return runner.run_collection(collection_path)


# Example usage functions
def test_sqb_demo():
    """Run SQB Demo test suite"""
    return run_postman_test_suite('/home/ubuntu/projects/ga/tests/postman/Demo SQB.json')


def test_mission_fed():
    """Run Mission Fed test suite"""
    return run_postman_test_suite('/home/ubuntu/projects/ga/tests/postman/MissionFed.postman_collection.json')


def test_langley():
    """Run Langley test suite"""
    return run_postman_test_suite('/home/ubuntu/projects/ga/tests/postman/Langley.postman_collection.json')


# Module for Postman collection export and test functionality
# Export: Call export_postman_collections() or export_specific_collection()
# Testing: Use functions above or run directly: python postman_tools.py <collection_path>

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        collection_path = sys.argv[1]
        results = run_postman_test_suite(collection_path)
        
        # Print failed tests
        if results['summary']['total_failed'] > 0:
            print("\n❌ Failed Tests Details:")
            for result in results['results']:
                if result.get('status') == 'completed' and result.get('failed_tests'):
                    print(f"\n{result['name']}:")
                    for failed_test in result['failed_tests']:
                        print(f"  - {failed_test}")
    else:
        print("Usage: python postman_tools.py <path_to_collection.json>")
        print("\nAvailable collections:")
        print("- /home/ubuntu/projects/ga/tests/postman/Demo SQB.json")
        print("- /home/ubuntu/projects/ga/tests/postman/MissionFed.postman_collection.json") 
        print("- /home/ubuntu/projects/ga/tests/postman/Langley.postman_collection.json")