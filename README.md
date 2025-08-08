# React Source Downloader

A Python script that downloads React application source code exposed in browser dev tools. This tool extracts original source files from webpack dev servers and source maps, just like your browser's dev tools do.

## 📋 Requirements

- Python 3.6+
- `requests` library

## 🔧 Installation

1. **Clone or download the script**:
   ```bash
   curl -O https://raw.githubusercontent.com/your-repo/react-source-downloader/main/rsdown.py
   ```

2. **Install dependencies**:
   ```bash
   pip install requests
   ```

3. **Make the script executable** (optional):
   ```bash
   chmod +x rsdown.py
   ```

## 💻 Usage

### Basic Usage

```bash
python rsdown.py <URL>
```

### With Custom Output Directory

```bash
python rsdown.py <URL> -d <directory_name>
```

### Examples

```bash
# Download from a live React app
python rsdown.py https://example.com

# Download from local development server
python rsdown.py http://localhost:3000

# Save to custom directory
python rsdown.py https://example.com -d my_react_project

# Download from staging environment
python rsdown.py https://staging.example.com -d staging_source
```

## 🛠️ How It Works

The script mimics how browser dev tools access source files:

1. **🔍 Discovery Phase**: 
   - Scans the main HTML page for JavaScript and CSS bundle references
   - Downloads corresponding source map files (`.map` files)
   - Detects webpack dev server endpoints

2. **📋 Analysis Phase**:
   - Extracts original source file paths and content from source maps
   - Filters out node_modules and webpack internal files
   - Builds a complete file tree structure

3. **⬇️ Download Phase**:
   - Creates the exact folder structure locally
   - Writes original source code (not minified bundles)
   - Preserves file encodings and formats

## 📁 Output Structure

The script maintains the exact folder structure as shown in your browser's dev tools:

```
downloaded_source/
├── src/
│   ├── components/
│   │   ├── Header.jsx
│   │   ├── Footer.jsx
│   │   └── Layout.jsx
│   ├── pages/
│   │   ├── Home.jsx
│   │   └── About.jsx
│   ├── utils/
│   │   └── helpers.js
│   ├── styles/
│   │   └── main.css
│   ├── App.jsx
│   └── index.js
├── public/
│   └── index.html
└── package.json
```

## 🎯 Supported Applications

This tool works with React applications that:

- ✅ Run in **development mode** (not production builds)
- ✅ Have **source maps enabled**
- ✅ Use common build tools like:
  - Create React App
  - Vite
  - Custom Webpack configurations
  - Next.js (development mode)
- ✅ Serve files through webpack dev server

## 📊 Example Output

```bash
🚀 React Source Code Downloader
========================================
Target URL: http://localhost:3000
Output Directory: downloaded_source

🔍 Scanning http://localhost:3000 for source files...
🗺️  Analyzing source maps...
✅ Webpack dev server detected at __webpack_hmr

📁 Discovered file structure (15 files):
==================================================
├── 📁 src/
│   ├── 📁 components/
│   │   ├── ⚛️  Header.jsx (2,341 bytes) [sourcemap]
│   │   └── ⚛️  Footer.jsx (1,203 bytes) [sourcemap]
│   ├── 📁 styles/
│   │   └── 🎨 main.css (1,456 bytes) [sourcemap]
│   ├── ⚛️  App.jsx (3,234 bytes) [sourcemap]
│   └── 📜 index.js (567 bytes) [sourcemap]
└── 📋 package.json (1,890 bytes) [sourcemap]

📊 Summary:
   JS/TS files: 12
   CSS files: 2
   Other files: 1
   From source maps: 14
   From webpack dev server: 1

==================================================
Do you want to download these files? (y/n): y

⬇️  Starting download to 'downloaded_source' directory...
[1/15] Creating src/components/Header.jsx
    📁 Created directory: src/components
    ✅ Success: src/components/Header.jsx (2,341 characters) from sourcemap
[2/15] Creating src/components/Footer.jsx
    ✅ Success: src/components/Footer.jsx (1,203 characters) from sourcemap
...

✅ Download complete!
   Successfully downloaded: 15 files
   Failed downloads: 0 files

📂 File structure created in: /path/to/downloaded_source

🎉 Files have been downloaded to: /path/to/downloaded_source
```

## ⚠️ Limitations

- **Development Mode Only**: Only works with development builds that expose source maps
- **Source Maps Required**: Applications must have source maps enabled
- **No Production Builds**: Minified/production builds typically don't expose source files
- **Network Access**: Requires access to the target application's dev server

## 🐛 Troubleshooting

### No Files Discovered

If the script finds no files, check:

1. **Development Mode**: Ensure the app is running in development mode
2. **Source Maps**: Verify source maps are enabled in the build configuration
3. **Network Access**: Make sure the URL is accessible
4. **Build Tool**: Some build tools may not expose source maps publicly

### Download Errors

Common issues and solutions:

- **Permission Errors**: Ensure write permissions in the output directory
- **Network Timeouts**: Check internet connection and server availability
- **Encoding Issues**: Some special characters might cause encoding problems

## 🔒 Ethical Usage

This tool should only be used on:

- ✅ Your own applications
- ✅ Applications you have permission to analyze
- ✅ Open source projects for educational purposes
- ✅ Applications with explicit consent from owners

**Do not use this tool to**:
- ❌ Extract proprietary source code without permission
- ❌ Violate terms of service
- ❌ Access private or confidential applications


## 🙏 Acknowledgments

- Inspired by browser dev tools functionality
- Thanks to the React and Webpack communities for making source maps possible
- Built with Python and the `requests` library

