# VS Code Extension Packaging & Publishing Guide

## Overview

This guide covers packaging BibCheck as a VS Code extension and publishing it to the official VS Code Marketplace, Open VSX Registry, and distributing it locally.

---

## Prerequisites

### System Requirements
- Node.js 16+ (for building TypeScript)
- npm or yarn (package manager)
- Python 3.8+ (for the backend bibtex_refiner.py)
- Git (for version control)

### Install Required Tools

```bash
# Install Node.js from https://nodejs.org/ (includes npm)

# Then install VS Code Extension CLI tools globally:
npm install -g vsce

# Optional: Install openVSX CLI for publishing to Open VSX Registry
npm install -g ovsx
```

---

## Step 1: Prepare the Project

### 1.1 Install Node Dependencies

```bash
cd F:\Hackathon\Google_Scholar_Check
npm install
```

Expected dependencies:
- `vscode`: ^1.85.0 (VS Code API)

### 1.2 Create `tsconfig.json` (if not exists)

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": false,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "sourceMap": true
  },
  "exclude": ["node_modules", ".vscode-test", "dist"]
}
```

### 1.3 Install TypeScript Compiler

```bash
npm install --save-dev typescript
```

---

## Step 2: Compile TypeScript to JavaScript

```bash
# Compile src/extension.ts → dist/extension.js
npx tsc

# Verify the output
dir dist\
# Expected: extension.js, extension.d.ts, extension.js.map
```

---

## Step 3: Create .vscodeignore File

Create `.vscodeignore` in the project root to exclude files from packaging:

```
.github/**
.venv/**
.gitignore
.vscodeignore
src/
tests/
*.ts
*.md
requirements.txt
package-lock.json
node_modules/
dist/*.map
```

---

## Step 4: Update package.json for Publishing

Update the following fields in `package.json`:

```json
{
  "name": "bibcheck",
  "displayName": "BibCheck",
  "description": "Verify and correct BibTeX entries using DBLP, Crossref, and OpenAlex databases. Catch common bibliography errors before publication.",
  "version": "0.1.0",
  "publisher": "your-github-username",
  "repository": {
    "type": "git",
    "url": "https://github.com/your-username/bibcheck"
  },
  "homepage": "https://github.com/your-username/bibcheck/blob/main/README.md",
  "bugs": {
    "url": "https://github.com/your-username/bibcheck/issues"
  },
  "icon": "icon.png",
  "engines": {
    "vscode": "^1.85.0",
    "node": ">=16.0.0"
  },
  "categories": [
    "Other",
    "Data Science",
    "Linters",
    "Scientific"
  ],
  "keywords": [
    "bibtex",
    "bibliography",
    "citation",
    "academic",
    "dblp",
    "crossref",
    "openalex"
  ],
  "activationEvents": [
    "onCommand:bibtexRefiner.refineBibtex",
    "onCommand:bibtexRefiner.refineActiveBibtex",
    "onCommand:bibtexRefiner.refineWorkspaceBibtex",
    "onCommand:bibtexRefiner.refineFolderBibtex"
  ],
  "main": "./dist/extension.js",
  "contributes": {
    "commands": [
      {
        "command": "bibtexRefiner.refineBibtex",
        "title": "BibCheck: Verify BibTeX File"
      },
      {
        "command": "bibtexRefiner.refineActiveBibtex",
        "title": "BibCheck: Verify Active BibTeX File"
      },
      {
        "command": "bibtexRefiner.refineWorkspaceBibtex",
        "title": "BibCheck: Scan and Verify All Workspace BibTeX Files"
      },
      {
        "command": "bibtexRefiner.refineFolderBibtex",
        "title": "BibCheck: Scan and Verify Folder BibTeX Files"
      }
    ],
    "menus": {
      "explorer/context": [
        {
          "command": "bibtexRefiner.refineActiveBibtex",
          "group": "1_modification",
          "when": "resourceExtname == .bib"
        },
        {
          "command": "bibtexRefiner.refineFolderBibtex",
          "group": "1_modification",
          "when": "explorerResourceIsFolder"
        }
      ]
    },
    "configuration": {
      "title": "BibCheck",
      "properties": {
        "bibtexRefiner.pythonPath": {
          "type": "string",
          "default": "python",
          "description": "Python executable path. Use python, python3, or full path to Python interpreter."
        },
        "bibtexRefiner.scriptPath": {
          "type": "string",
          "default": "",
          "description": "Optional absolute path to bibtex_refiner.py. Leave empty to use bundled script."
        }
      }
    }
  },
  "scripts": {
    "compile": "tsc",
    "watch": "tsc -w",
    "package": "vsce package",
    "publish": "vsce publish"
  }
}
```

---

## Step 5: Create Extension Icon (Optional but Recommended)

Create a 128x128 PNG icon:

```bash
# Option 1: Use a simple icon online converter
# - Create or download a 128x128 PNG image
# - Save as: icon.png

# Option 2: Use a placeholder (create via ImageMagick/Python)
# For now, you can skip this - marketplace will show a default icon
```

---

## Step 6: Create LICENSE File

Create `LICENSE` file (MIT License recommended):

```
MIT License

Copyright (c) 2024 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## Step 7: Create CHANGELOG.md

Create `CHANGELOG.md` for version tracking:

```markdown
# Changelog

## [0.1.0] - 2024-04-03

### Added
- Initial release
- BibTeX entry validation against DBLP, Crossref, OpenAlex
- Single file and batch processing
- 4 advanced validation features:
  - ArXiv detection (@article + arXiv = ERROR)
  - Field requirements validation
  - ArXiv format validation (YYMM.XXXXX)
  - Conference detection (NeurIPS, ICML, etc.)

### Features
- VS Code command integration
- Status bar indicator
- Workspace batch processing
- Folder scanning capability
```

---

## Step 8: Package Locally (.vsix)

### Create a local .vsix package:

```bash
cd F:\Hackathon\Google_Scholar_Check

# Build the TypeScript
npm run compile

# Package the extension
vsce package

# Output: bibcheck-0.1.0.vsix
```

### Share the package:
- Upload `.vsix` file to GitHub Releases
- Users can install via: `code --install-extension bibcheck-0.1.0.vsix`

---

## Step 9: Prepare for VS Code Marketplace

### Create Microsoft Account

1. Go to https://azure.microsoft.com/en-us/services/visual-studio-online/
2. Sign in with your Microsoft account (create one if needed)
3. Visit https://marketplace.visualstudio.com/manage/publishers
4. Create a new publisher account

### Get Personal Access Token (PAT)

1. In Azure DevOps: https://dev.azure.com/
2. User settings → Personal access tokens
3. Create new token:
   - **Name**: vsce-publishing
   - **Organization**: Select your organization
   - **Scopes**: "Marketplace" → "Manage"
   - **Expiration**: 1 year
4. Copy the token (save securely!)

### Login to VSCE

```bash
vsce login your-publisher-name
# Paste your PAT when prompted
```

---

## Step 10: Publish to VS Code Marketplace

### First-time publication:

```bash
# Validate before publishing
vsce show

# Publish to marketplace (creates publisher if new)
vsce publish

# Your extension will be available at:
# https://marketplace.visualstudio.com/items?itemName=your-publisher.bibcheck
```

### For updates:

```bash
# Update version in package.json (e.g., 0.1.0 → 0.1.1)
npm version patch

# Publish the update
vsce publish
```

---

## Step 11: Publish to Open VSX Registry (Optional)

For broader distribution (especially popular in VSCodium, Gitpod):

```bash
# Install ovsx CLI
npm install -g ovsx

# Create a token at https://open-vsx.org/
# Generate personal access token in your profile

# Login
ovsx create-namespace your-namespace
ovsx login your-namespace

# Publish
ovsx publish \
  --pat YOUR_OPENVSX_TOKEN \
  --registry https://open-vsx.org

# Available at:
# https://open-vsx.org/user/your-namespace/extension/bibcheck
```

---

## Complete Directory Structure

After all steps, your project should look like:

```
bibcheck/
├── .github/                          # GitHub workflows
├── .venv/                            # Python virtual environment
├── src/
│   └── extension.ts                  # TypeScript extension code
├── dist/
│   ├── extension.js                  # Compiled JavaScript
│   ├── extension.d.ts                # TypeScript definitions
│   └── extension.js.map              # Source map
├── tests/                            # Unit tests
├── bibtex_refiner.py                 # Python backend script
├── enhanced_entry_type_validator.py  # Python validation features
├── BIBTEX_VALIDATOR_DOCUMENTATION_EN.md
├── README.md                         # Extension description
├── CHANGELOG.md                      # Version history
├── LICENSE                           # MIT License
├── .vscodeignore                     # Files to exclude from package
├── package.json                      # Node project config
├── package-lock.json                 # Dependency lock
├── tsconfig.json                     # TypeScript config
└── requirements.txt                  # Python dependencies
```

---

## Testing the Extension Locally

### Option 1: Run in Debug Mode

```bash
# In VS Code, press F5 or:
code --extensionDevelopmentPath=F:\Hackathon\Google_Scholar_Check
```

### Option 2: Install from .vsix

```bash
# After packaging
code --install-extension bibcheck-0.1.0.vsix
```

---

## Troubleshooting

### Issue: "Cannot find module 'vscode'"
```bash
npm install
npm install --save-dev @types/vscode
```

### Issue: "tsc not found"
```bash
npm install --save-dev typescript
npx tsc --version
```

### Issue: "vsce not found"
```bash
npm install -g vsce
vsce --version
```

### Issue: "The main entry point is missing"
```bash
# Ensure dist/extension.js exists and is compiled
npm run compile
ls dist/extension.js
```

### Issue: "Publisher not recognized"
```bash
# Update publisher in package.json to match your VS Code Marketplace account:
# "publisher": "your-actual-publisher-name"
```