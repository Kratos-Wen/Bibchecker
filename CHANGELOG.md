# Changelog

All notable changes to BibCheck will be documented in this file.

## [0.1.0] - 2024-04-03

### Added
- Initial release of BibCheck VS Code Extension
- Bibliography verification against DBLP, Crossref, and OpenAlex databases
- Single file BibTeX processing command: "Refine BibTeX File"
- Active file processing: "Refine Active BibTeX File"
- Batch workspace processing: "Scan Workspace BibTeX Files"
- Folder batch processing: "Scan Folder BibTeX Files"
- Status bar indicator with quick access
- VS Code context menu integration for .bib files
- Configuration options for Python path and script location
- Output channel with detailed processing results

### Features
- **ArXiv Detection (FEATURE 1)**: Automatically detects preprints incorrectly typed as @article and suggests conversion to @misc with proper howpublished field
- **Field Requirements Validation (FEATURE 2)**: Ensures required fields exist for each entry type (@article requires journal, @inproceedings requires booktitle)
- **ArXiv Format Validation (FEATURE 3)**: Validates ArXiv ID format (YYMM.XXXXX[vN]) with version number support
- **Conference Detection (FEATURE 4)**: Identifies when conference names (NeurIPS, ICML, CVPR, etc.) are incorrectly used as journal fields
- Automatic field format validation (year, pages, DOI)
- Author list consistency checks
- Comprehensive error and warning messages with suggested fixes
- English language output for global accessibility

### Technical Details
- Built with TypeScript and Node.js
- Uses Python backend for bibliography verification (bibtex_refiner.py)
- Supports Python 3.8+ with minimal dependencies (bibtexparser, requests)
- Integrated with VS Code Extension API for seamless workflow
- Workspace folder detection and multi-file processing
- Error handling and user-friendly messaging

### Documentation
- Complete guide on 4 validation features
- Integration instructions for developers
- Troubleshooting guide for common issues
- Quick reference for command usage

## Future Plans

### [0.2.0] - Planned
- [ ] Automatic correction mode for common errors
- [ ] Custom validation rule configuration
- [ ] HTML report generation with visual diff
- [ ] Integration with LaTeX/Overleaf projects
- [ ] BibTeX formatting options (case standardization, field ordering)
- [ ] Author name normalization suggestions
- [ ] Journal name resolution to standard abbreviations

### [0.3.0] - Planned
- [ ] Support for additional databases (IEEE Xplore, PubMed)
- [ ] Caching for improved performance on large bibliographies
- [ ] GUI for configuration instead of settings.json only
- [ ] Batch export in various BibTeX formats
- [ ] Integration with reference management tools (Zotero, Mendeley)

### [1.0.0] - Vision
- [ ] Publication-grade bibliography verification as industry standard
- [ ] Multi-language support for UI and documentation
- [ ] Plugin architecture for custom validators
- [ ] API for programmatic access
- [ ] Web version for non-VS Code users

---

## How to Update

### For Users
1. VS Code will automatically notify you of updates
2. Click "Update" or go to Extensions and update BibCheck manually

### For Contributors
1. Update version in package.json
2. Update this CHANGELOG.md with new changes
3. Create git tag (e.g., v0.1.0)
4. Push to repository
5. GitHub Actions (if configured) will publish automatically

---

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/):
- MAJOR.MINOR.PATCH (e.g., 1.0.0)
- MAJOR: Incompatible API changes
- MINOR: Backward-compatible functionality additions
- PATCH: Bug fixes

---

## Support

For feature requests or bug reports, please visit the project repository:
- GitHub Issues: https://github.com/your-username/bibcheck/issues
- Discussion: https://github.com/your-username/bibcheck/discussions

---

**Last Updated**: 2024-04-03
