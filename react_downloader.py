#!/usr/bin/env python3
"""
React Source Code Downloader
Downloads exposed React app source files from webpack dev server like browser dev tools
"""

import argparse
import os
import sys
import requests
from urllib.parse import urljoin, urlparse, quote
import json
import time
from pathlib import Path
import re
import base64


class ReactSourceDownloader:
    def __init__(self, base_url, output_dir="downloaded_source"):
        self.base_url = base_url.rstrip('/')
        self.output_dir = output_dir
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.discovered_files = []
        self.source_maps = []
        
    def discover_files(self):
        """Discover source files by analyzing source maps and webpack dev server"""
        print(f"🔍 Scanning {self.base_url} for source files...")
        
        # First get main page and find script/css files
        self._scan_main_page()
        
        # Analyze source maps to get original sources
        self._analyze_source_maps()
        
        # Try webpack dev server endpoints
        self._try_webpack_dev_server()
        
        return self.discovered_files
    
    def _scan_main_page(self):
        """Scan main page for script and CSS files"""
        try:
            response = self.session.get(self.base_url)
            if response.status_code == 200:
                content = response.text
                
                # Find script and CSS files
                script_pattern = r'<script[^>]+src=["\']([^"\']+\.js(?:\?[^"\']*)?)["\']'
                css_pattern = r'<link[^>]+href=["\']([^"\']+\.css(?:\?[^"\']*)?)["\']'
                
                scripts = re.findall(script_pattern, content, re.IGNORECASE)
                styles = re.findall(css_pattern, content, re.IGNORECASE)
                
                # Store main bundles for source map analysis
                for script in scripts:
                    if not script.startswith(('http:', 'https:', '//')):
                        full_url = urljoin(self.base_url + '/', script)
                        self.source_maps.append(full_url)
                
                for style in styles:
                    if not style.startswith(('http:', 'https:', '//')):
                        full_url = urljoin(self.base_url + '/', style)
                        self.source_maps.append(full_url)
                        
        except Exception as e:
            print(f"⚠️  Error scanning main page: {e}")
    
    def _analyze_source_maps(self):
        """Analyze source maps to find original source files"""
        print("🗺️  Analyzing source maps...")
        
        for bundle_url in self.source_maps:
            try:
                # Try to get the source map
                map_urls = [
                    bundle_url + '.map',
                    bundle_url.replace('.js', '.js.map').replace('.css', '.css.map')
                ]
                
                for map_url in map_urls:
                    try:
                        response = self.session.get(map_url, timeout=10)
                        if response.status_code == 200:
                            self._parse_source_map(response.text, map_url)
                            break
                    except:
                        continue
                        
            except Exception as e:
                print(f"⚠️  Error analyzing {bundle_url}: {e}")
    
    def _parse_source_map(self, map_content, map_url):
        """Parse source map and extract source file information"""
        try:
            source_map = json.loads(map_content)
            
            if 'sources' in source_map and 'sourcesContent' in source_map:
                sources = source_map['sources']
                contents = source_map['sourcesContent']
                
                print(f"   Found {len(sources)} source files in map")
                
                for i, (source_path, content) in enumerate(zip(sources, contents)):
                    if content is None:
                        continue
                        
                    # Clean up the source path while preserving structure
                    clean_path = self._clean_source_path(source_path)
                    
                    # Skip node_modules and webpack internal files
                    if (clean_path and 
                        not 'node_modules' in clean_path.lower() and
                        not 'webpack/' in clean_path and
                        not '(webpack)' in clean_path and
                        not clean_path.startswith('multi ') and
                        not clean_path.startswith('webpack:') and
                        clean_path != source_path or not any(skip in source_path.lower() for skip in ['webpack-dev-server', 'hot-dev-server', 'webpack/hot'])):
                        
                        file_type = self._determine_file_type(clean_path)
                        
                        # Avoid duplicates
                        if not any(f['path'] == clean_path for f in self.discovered_files):
                            self.discovered_files.append({
                                'path': clean_path,
                                'content': content,
                                'type': file_type,
                                'source': 'sourcemap',
                                'original_path': source_path
                            })
                        
            # Also try to get sources without content from webpack dev server
            elif 'sources' in source_map:
                for source_path in source_map['sources']:
                    clean_path = self._clean_source_path(source_path)
                    if (clean_path and 
                        not 'node_modules' in clean_path and
                        not any(f['path'] == clean_path for f in self.discovered_files)):
                        
                        # Try to fetch from webpack dev server
                        content = self._fetch_from_webpack_dev_server(source_path)
                        if content:
                            file_type = self._determine_file_type(clean_path)
                            self.discovered_files.append({
                                'path': clean_path,
                                'content': content,
                                'type': file_type,
                                'source': 'webpack-dev-server',
                                'original_path': source_path
                            })
                            
        except Exception as e:
            print(f"⚠️  Error parsing source map: {e}")
    
    def _clean_source_path(self, source_path):
        """Clean up webpack source paths while preserving folder structure"""
        original_path = source_path
        
        # Remove webpack:// prefix
        if source_path.startswith('webpack://'):
            source_path = source_path[10:]
        
        # Handle different webpack path patterns
        if source_path.startswith('./'):
            # Relative paths - keep as is but remove ./
            source_path = source_path[2:]
        elif '/' in source_path:
            # Absolute paths - check if first part is project name
            parts = source_path.split('/')
            # If first part looks like a project name (no extension), skip it
            if len(parts) > 1 and not parts[0].endswith(('.js', '.ts', '.jsx', '.tsx', '.css')):
                # Common project name patterns to skip
                if parts[0] in ['src', '.', '..'] or len(parts[0]) > 20:
                    source_path = '/'.join(parts[1:])
                else:
                    # Keep the structure if it looks like a real folder
                    pass
        
        # Clean up any remaining leading slashes or dots
        source_path = source_path.lstrip('./')
        source_path = source_path.lstrip('/')
        
        # If path is empty or just a filename without folder context,
        # try to infer folder structure from common React patterns
        if '/' not in source_path and source_path:
            if source_path.startswith(('App.', 'index.')):
                source_path = f"src/{source_path}"
            elif source_path.startswith(('component', 'Component')):
                source_path = f"src/components/{source_path}"
            elif source_path.endswith('.css'):
                source_path = f"src/styles/{source_path}"
        
        return source_path if source_path else original_path.split('/')[-1]
    
    def _determine_file_type(self, path):
        """Determine file type from path"""
        if path.endswith('.jsx'):
            return 'jsx'
        elif path.endswith('.tsx'):
            return 'tsx'
        elif path.endswith('.ts'):
            return 'ts'
        elif path.endswith('.js'):
            return 'js'
        elif path.endswith('.css'):
            return 'css'
        elif path.endswith('.scss'):
            return 'scss'
        elif path.endswith('.sass'):
            return 'sass'
        elif path.endswith('.json'):
            return 'json'
        else:
            return 'unknown'
    
    def _try_webpack_dev_server(self):
        """Try to access webpack dev server directly"""
        print("🔧 Trying webpack dev server endpoints...")
        
        # Common webpack dev server patterns
        webpack_patterns = [
            '__webpack_hmr',
            'sockjs-node',
            'webpack-dev-server',
            '__webpack_dev_server__'
        ]
        
        for pattern in webpack_patterns:
            try:
                test_url = f"{self.base_url}/{pattern}"
                response = self.session.get(test_url, timeout=5)
                if response.status_code in [200, 426]:  # 426 for websocket upgrade
                    print(f"✅ Webpack dev server detected at {pattern}")
                    return True
            except:
                continue
        
        return False
    
    def _fetch_from_webpack_dev_server(self, webpack_path):
        """Try to fetch file content from webpack dev server"""
        # Common webpack dev server endpoints for source files
        possible_endpoints = [
            f"__webpack_dev_server__/src/{webpack_path}",
            f"webpack://{webpack_path}",
            f"src/{webpack_path}",
            webpack_path
        ]
        
        for endpoint in possible_endpoints:
            try:
                # URL encode the path properly
                encoded_path = quote(endpoint, safe='/:')
                test_url = f"{self.base_url}/{encoded_path}"
                
                response = self.session.get(test_url, timeout=10)
                if response.status_code == 200:
                    return response.text
            except:
                continue
        
        return None
    
    def print_file_structure(self):
        """Print the discovered file structure in a tree format"""
        if not self.discovered_files:
            print("❌ No source files discovered!")
            return False
            
        print(f"\n📁 Discovered file structure ({len(self.discovered_files)} files):")
        print("=" * 50)
        
        # Group files by directory
        file_tree = {}
        for file_info in self.discovered_files:
            path_parts = file_info['path'].split('/')
            current_level = file_tree
            
            # Build tree structure
            for i, part in enumerate(path_parts):
                if i == len(path_parts) - 1:  # Last part is filename
                    if 'files' not in current_level:
                        current_level['files'] = []
                    current_level['files'].append({
                        'name': part,
                        'type': file_info['type'],
                        'source': file_info['source'],
                        'size': len(file_info['content']) if file_info['content'] else 0
                    })
                else:  # Directory
                    if 'dirs' not in current_level:
                        current_level['dirs'] = {}
                    if part not in current_level['dirs']:
                        current_level['dirs'][part] = {}
                    current_level = current_level['dirs'][part]
        
        # Print tree
        self._print_tree(file_tree, "", True)
        
        # Print summary
        js_files = len([f for f in self.discovered_files if f['type'] in ['js', 'jsx', 'ts', 'tsx']])
        css_files = len([f for f in self.discovered_files if f['type'] in ['css', 'scss', 'sass']])
        other_files = len(self.discovered_files) - js_files - css_files
        
        sourcemap_files = len([f for f in self.discovered_files if f['source'] == 'sourcemap'])
        webpack_files = len([f for f in self.discovered_files if f['source'] == 'webpack-dev-server'])
        
        print(f"\n📊 Summary:")
        print(f"   JS/TS files: {js_files}")
        print(f"   CSS files: {css_files}")
        print(f"   Other files: {other_files}")
        print(f"   From source maps: {sourcemap_files}")
        print(f"   From webpack dev server: {webpack_files}")
        
        return True
    
    def _print_tree(self, tree, prefix, is_root):
        """Recursively print tree structure"""
        # Print directories first
        if 'dirs' in tree:
            dirs = sorted(tree['dirs'].keys())
            for i, dir_name in enumerate(dirs):
                is_last_dir = (i == len(dirs) - 1) and ('files' not in tree)
                print(f"{prefix}{'└── ' if is_last_dir else '├── '}📁 {dir_name}/")
                new_prefix = prefix + ("    " if is_last_dir else "│   ")
                self._print_tree(tree['dirs'][dir_name], new_prefix, False)
        
        # Print files
        if 'files' in tree:
            files = sorted(tree['files'], key=lambda x: x['name'])
            for i, file_info in enumerate(files):
                is_last = i == len(files) - 1
                icon = self._get_file_icon(file_info['type'])
                size_str = f" ({file_info['size']} bytes)" if file_info['size'] > 0 else ""
                source_str = f" [{file_info['source']}]"
                print(f"{prefix}{'└── ' if is_last else '├── '}{icon} {file_info['name']}{size_str}{source_str}")
    
    def _get_file_icon(self, file_type):
        """Get appropriate icon for file type"""
        icons = {
            'js': '📜',
            'jsx': '⚛️ ',
            'ts': '📘',
            'tsx': '⚛️ ',
            'css': '🎨',
            'scss': '🎨',
            'sass': '🎨',
            'json': '📋',
            'unknown': '📄'
        }
        return icons.get(file_type, '📄')
    
    def download_files(self):
        """Download all discovered files using their content from source maps/webpack"""
        if not self.discovered_files:
            print("❌ No files to download!")
            return False
        
        print(f"\n⬇️  Starting download to '{self.output_dir}' directory...")
        print("📁 Recreating folder structure as it appears in dev tools...")
        
        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        successful_downloads = 0
        failed_downloads = 0
        
        for i, file_info in enumerate(self.discovered_files, 1):
            try:
                file_path_display = file_info['path']
                print(f"[{i}/{len(self.discovered_files)}] Creating {file_path_display}")
                
                if not file_info['content']:
                    print(f"    ❌ No content available")
                    failed_downloads += 1
                    continue
                
                # Create full file path
                file_path = os.path.join(self.output_dir, file_info['path'])
                
                # Ensure all parent directories exist
                dir_path = os.path.dirname(file_path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                    # Show folder creation for better visibility
                    if not hasattr(self, '_created_dirs'):
                        self._created_dirs = set()
                    if dir_path not in self._created_dirs:
                        self._created_dirs.add(dir_path)
                        rel_dir = os.path.relpath(dir_path, self.output_dir)
                        print(f"    📁 Created folder: {rel_dir}")
                
                # Write file content
                with open(file_path, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(file_info['content'])
                
                file_size = len(file_info['content'])
                print(f"    ✅ Success ({file_size:,} chars) [{file_info['source']}]")
                successful_downloads += 1
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
                failed_downloads += 1
            
            # Small delay to be respectful
            time.sleep(0.02)
        
        print(f"\n✅ Download complete!")
        print(f"   Successfully created: {successful_downloads} files")
        if failed_downloads > 0:
            print(f"   Failed: {failed_downloads} files")
        
        # Show the created folder structure
        self._show_created_structure()
        
        return successful_downloads > 0
    
    def _show_created_structure(self):
        """Show the actual created folder structure"""
        print(f"\n📁 Created folder structure in '{self.output_dir}':")
        print("=" * 40)
        
        def show_tree(path, prefix=""):
            try:
                items = sorted(os.listdir(path))
                folders = [item for item in items if os.path.isdir(os.path.join(path, item))]
                files = [item for item in items if os.path.isfile(os.path.join(path, item))]
                
                # Show folders first
                for i, folder in enumerate(folders):
                    is_last_folder = (i == len(folders) - 1) and len(files) == 0
                    print(f"{prefix}{'└── ' if is_last_folder else '├── '}📁 {folder}/")
                    folder_path = os.path.join(path, folder)
                    new_prefix = prefix + ("    " if is_last_folder else "│   ")
                    show_tree(folder_path, new_prefix)
                
                # Show files
                for i, file in enumerate(files):
                    is_last = i == len(files) - 1
                    file_path = os.path.join(path, file)
                    size = os.path.getsize(file_path)
                    ext = os.path.splitext(file)[1]
                    icon = self._get_file_icon_by_ext(ext)
                    print(f"{prefix}{'└── ' if is_last else '├── '}{icon} {file} ({size:,} bytes)")
            except PermissionError:
                pass
        
        show_tree(self.output_dir)
    
    def _get_file_icon_by_ext(self, ext):
        """Get file icon by extension"""
        ext_icons = {
            '.js': '📜',
            '.jsx': '⚛️ ',
            '.ts': '📘',
            '.tsx': '⚛️ ',
            '.css': '🎨',
            '.scss': '🎨',
            '.sass': '🎨',
            '.json': '📋',
            '.html': '🌐',
            '.md': '📝',
        }
        return ext_icons.get(ext.lower(), '📄')


def main():
    parser = argparse.ArgumentParser(
        description="Download React app source code from webpack dev server like browser dev tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python react_downloader.py https://example.com
  python react_downloader.py https://example.com -d my_project
  python react_downloader.py http://localhost:3000 -d local_react_app
        """
    )
    
    parser.add_argument('url', help='Base URL of the React application')
    parser.add_argument('-d', '--directory', 
                       help='Output directory name (default: downloaded_source)',
                       default='downloaded_source')
    
    args = parser.parse_args()
    
    # Validate URL
    parsed_url = urlparse(args.url)
    if not parsed_url.scheme or not parsed_url.netloc:
        print("❌ Invalid URL format. Please include http:// or https://")
        sys.exit(1)
    
    print("🚀 React Source Code Downloader")
    print("=" * 40)
    print(f"Target URL: {args.url}")
    print(f"Output Directory: {args.directory}")
    print()
    
    # Initialize downloader
    downloader = ReactSourceDownloader(args.url, args.directory)
    
    # Discover files
    discovered = downloader.discover_files()
    
    if not discovered:
        print("❌ No source files were discovered.")
        print("\nPossible reasons:")
        print("- The application is not a development build")
        print("- Source maps are not available or enabled")
        print("- The webpack dev server is not exposing source files")
        print("- The URL is not accessible")
        sys.exit(1)
    
    # Show file structure
    if not downloader.print_file_structure():
        sys.exit(1)
    
    # Ask for confirmation
    print("\n" + "=" * 50)
    while True:
        choice = input("Do you want to download these files? (y/n): ").lower().strip()
        if choice in ['y', 'yes']:
            break
        elif choice in ['n', 'no']:
            print("Download cancelled.")
            sys.exit(0)
        else:
            print("Please enter 'y' or 'n'")
    
    # Download files
    success = downloader.download_files()
    
    if success:
        print(f"\n🎉 Files have been downloaded to: {os.path.abspath(args.directory)}")
    else:
        print("\n❌ Download failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
