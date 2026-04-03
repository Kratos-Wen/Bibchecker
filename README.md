# BibCheck

BibCheck is a publication-grade BibTeX verification and refinement tool for academic writing.
It checks bibliography entries against DBLP, Crossref, and OpenAlex, and it also validates
structural BibTeX issues such as entry type mismatches, missing required fields, ArXiv format
errors, and conference-vs-journal confusion.

BibCheck is available as both a command-line tool and a VS Code extension, so users can
install it directly in VS Code or use it from the terminal.

## Why BibCheck

- Strict title, author, year, and DOI matching
- Structured BibTeX validation before publication
- ArXiv and conference detection rules for common citation mistakes
- CLI workflow for automation and a VS Code extension for day-to-day editing
- Human-readable reports with change summaries

## Features

- Verify bibliography entries against multiple open bibliographic sources
- Preserve citation keys by default, with optional key rewriting
- Normalize and compare titles and author lists consistently
- Generate JSON and HTML reports for review and traceability
- Update matching LaTeX files when citation keys change
- Provide VS Code commands for single-file, workspace, and folder workflows
- Detect common BibTeX structure errors before submission

## Validation Rules

BibCheck applies strict checks designed for publication workflows:

1. **Title** must match exactly after normalization.
2. **Authors** must appear in the correct order.
3. **Year** must match exactly.
4. **DOI** must match when present.
5. **Venue fields** are validated by entry type.
6. **ArXiv entries** are checked for entry type and format.
7. **Conference names** appearing in journal fields are flagged.

## Repository Layout

- [bibtex_refiner.py](bibtex_refiner.py) - main Python engine
- [enhanced_entry_type_validator.py](enhanced_entry_type_validator.py) - structural BibTeX validator
- [src/](src/) - VS Code extension source
- [tests/](tests/) - unit tests
- [docs/](docs/) - packaging and validator documentation

## Installation

### Python backend

```bash
pip install -r requirements.txt
```

### VS Code extension development

```bash
npm install
npm run compile
```

## Command Line Usage

### Verify a BibTeX file in place

```bash
python bibtex_refiner.py refs.bib
```

### Write results to a new file

```bash
python bibtex_refiner.py refs.bib -o refs_refined.bib
```

### Rewrite citation keys

```bash
python bibtex_refiner.py refs.bib --rewrite-keys
```

### Generate a JSON report

```bash
python bibtex_refiner.py refs.bib --report report.json
```

### Enable verbose logging

```bash
python bibtex_refiner.py refs.bib --verbose
```

## VS Code Usage

Install the packaged extension from VSIX or from the VS Code Marketplace, then run one of these commands:

### Install in VS Code

- Open the Extensions view in VS Code
- Search for `BibCheck`
- Or install directly from the Marketplace page:
	- https://marketplace.visualstudio.com/items?itemName=Kratos-Wen.bibcheck
- Or install a local package:

```bash
code --install-extension bibcheck-0.1.0.vsix
```

- BibCheck: Verify BibTeX File
- BibCheck: Verify Active BibTeX File
- BibCheck: Scan and Verify All Workspace BibTeX Files
- BibCheck: Scan and Verify Folder BibTeX Files

You can also use the editor and explorer context menus for `.bib` files.

## Configuration

BibCheck exposes two main settings:

- `bibtexRefiner.pythonPath` - Python executable used to run the backend
- `bibtexRefiner.scriptPath` - optional path to `bibtex_refiner.py`

Example:

```json
{
	"bibtexRefiner.pythonPath": "python",
	"bibtexRefiner.scriptPath": ""
}
```

## Documentation

- [BibCheck validator guide](docs/BIBTEX_VALIDATOR_DOCUMENTATION_EN.md)
- [VS Code packaging and publishing guide](docs/VSCODE_EXTENSION_GUIDE.md)
- [Quick packaging guide](docs/QUICK_START_PACKAGING.md)

## Output Formats

BibCheck can produce:

- JSON reports for automation
- HTML reports for human review
- refined BibTeX files with corrected entries
- optional `.tex` updates when citation keys change

## Development

```bash
npm install
npm run compile
python -m unittest discover -s tests
```

## Contributing

Contributions are welcome. Please keep the implementation strict, deterministic, and publication-oriented.

Before submitting a change:

- run the tests
- verify the extension compiles
- keep documentation in sync with behavior
- preserve the BibCheck naming convention across new files and messages

## License

MIT License. See [LICENSE](LICENSE).
