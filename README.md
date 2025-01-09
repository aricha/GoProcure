# GoPro Tools

A collection of tools for working with GoPro media files.

## Tools

- `gopro-download`: Download media files from GoPro Cloud
- `gopro-organize`: Organize local media files by date
- `gopro-sync`: Download and organize files in one step

## Installation

1. Clone the repository:
```bash
git clone https://github.com/aricha/gopro-tools.git
cd gopro-tools
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make scripts executable:
```bash
chmod +x gopro-download gopro-organize gopro-sync
```

## Usage

### Download from Cloud

```bash
./gopro-download --output-dir DIR [options]
  --include-photos    # Include photos
  --max-items N      # Limit number of items
  --download-gpmf    # Download GPMF data
  --verbose          # Verbose logging
```

### Organize Local Files

```bash
./gopro-organize DIR [options]
  --copy            # Copy instead of move
  --recursive       # Process subdirectories
  --dry-run        # Show what would be done
  --verbose        # Verbose logging
```

### Download and Organize

```bash
./gopro-sync --output-dir DIR [options]
  # Supports most options from both tools above
```